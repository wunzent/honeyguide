
import pytest

from policy import PolicyError, worktree_path
from test_bridge import call
from test_engine_restart import drive, engine_env, runtime
from test_path_policy import hub
from test_v1_isolation import target


@pytest.fixture
def review_engine(engine_env, hub, monkeypatch):
    factory, store, now, *_ = engine_env
    for field, value in {"GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                         "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}.items():
        monkeypatch.setenv(field, value)
    worktree = worktree_path(hub.policy, 'project', 'T-1')
    (worktree / 'hello.txt').write_text('implemented\n', encoding='utf-8')
    engine = factory()
    adapter = engine.adapters['claude']
    classify = adapter.classify
    def review(*args):
        result = classify(*args)
        result.result_text = 'RESULT: {"verdict": "PASS"}'
        return result
    monkeypatch.setattr(adapter, 'classify', review)
    return engine, store, now, worktree


@pytest.fixture
def ready(review_engine):
    engine, store, now, worktree = review_engine
    state = drive(engine, store, now)
    assert state['status'] == 'ready_to_commit'
    return engine, store, now, worktree


def test_engine_auto_commit_stages_explicit_task_files_only(ready, monkeypatch):
    engine, store, now, worktree = ready
    manager = engine.worktrees
    calls = []
    git = manager.git
    def observe(args, cwd):
        calls.append(args)
        return git(args, cwd)
    monkeypatch.setattr(manager, 'git', observe)
    engine.tick(now)
    state = store.read_state('project', 'T-1')
    assert state['status'] == 'committed' and len(state['commit_sha']) == 40
    assert [args for args in calls if args[0] == 'add'] == [['add', '--', 'hello.txt']]
    assert not any(args[0] in {'push', 'merge', 'reset', 'remote'} for args in calls)
    event = next(e for e in store.read_events('project', 'T-1') if e.kind == 'commit.created')
    assert event.data['sha'] == state['commit_sha'] and event.data['files'] == ['hello.txt']
    assert manager._git(['log', '-1', '--format=%s'], worktree).strip() == (
        'T-1: Task (tests PASS, review PASS, Security Gate NOT PASS)')
    with pytest.raises(PolicyError, match='not ready'):
        engine.runner.commit_task('project', 'T-1')


@pytest.mark.parametrize('failure', ['tests-fail', 'test-round', 'missing-tests', 'review-fail', 'review-round',
    'review-run', 'review-tests', 'missing-approval', 'approval-task', 'duplicate-nonce', 'active-run',
    'file-drift', 'scope', 'policy-drift', 'plan-drift', 'wrong-branch'])
def test_commit_refuses_when_any_condition_fails(ready, hub, monkeypatch, failure):
    engine, store, now, worktree = ready
    with store.transaction('project', 'T-1') as txn:
        state = txn.state
        tests = state['runs'][state['last_test_run']]
        if failure == 'tests-fail':
            tests['passed'] = False
        elif failure == 'test-round':
            tests['round'] = 0
        elif failure == 'missing-tests':
            state['last_test_run'] = 'missing'
        elif failure == 'review-fail':
            state['review']['verdict'] = 'FAIL'
        elif failure == 'review-round':
            state['review']['round'] = 0
        elif failure == 'review-run':
            state['review']['run'] = 'missing'
        elif failure == 'review-tests':
            state['review']['test_run'] = 'other'
        elif failure == 'missing-approval':
            state['approval'] = None
        elif failure == 'approval-task':
            state['approval']['task'] = 'other'
        elif failure == 'duplicate-nonce':
            state['approval_history'].append(state['approval'])
        elif failure == 'active-run':
            state['runs']['other'] = {'status': 'intent'}
        txn.emit('fixture.conditions', {'set': state})
    if failure == 'file-drift':
        (worktree / 'hello.txt').write_text('changed after tests', encoding='utf-8')
    elif failure == 'scope':
        config = hub.root / 'projects' / 'project' / 'project.md'
        config.write_text(config.read_text(encoding='utf-8').replace('hello.txt', 'other.txt'), encoding='utf-8')
    elif failure == 'policy-drift':
        path = hub.config / 'policy.toml'
        path.write_text(path.read_text(encoding='utf-8') + '\n# changed\n', encoding='utf-8')
    elif failure == 'plan-drift':
        store.write_spec('project', 'T-1', '## Proposed Plan\nChanged\n')
    git = engine.worktrees.git
    calls = []
    def observe(args, cwd):
        calls.append(args)
        if failure == 'wrong-branch' and args == ['rev-parse', '--abbrev-ref', 'HEAD']:
            return 0, 'main', ''
        return git(args, cwd)
    monkeypatch.setattr(engine.worktrees, 'git', observe)
    with pytest.raises((ValueError, PolicyError)):
        engine.runner.commit_task('project', 'T-1')
    assert not any(args[0] in {'add', 'commit', 'push', 'merge'} for args in calls)


def test_scope_extension_reaches_engine_and_committer(review_engine, hub):
    engine, store, now, worktree = review_engine
    before = drive(engine, store, now, wanted='coding')
    call(hub.root, 'approve-scope', 'project', 'T-1', '--add', 'extra.txt',
         '--quote', 'Include extra.txt', '--desktop', 'codex')
    state = store.read_state('project', 'T-1')
    assert state['status'] == 'coding'
    assert state.get('needs_run') == before.get('needs_run')
    (worktree / 'extra.txt').write_text('extra\n', encoding='utf-8')
    assert engine.runner.scope_check('project', 'T-1', worktree, ['hello.txt', 'extra.txt']) == []
    state = drive(engine, store, now)
    assert state['review']['test_run'] == state['last_test_run']
    assert len([run for run in state['runs'].values() if run.get('role') == 'coder']) == 1
    engine.tick(now)
    assert store.read_state('project', 'T-1')['status'] == 'committed'


@pytest.mark.parametrize('file_drift', [False, True])
def test_scope_extension_preserves_ready_stage_and_commit_guards(ready, hub, file_drift):
    engine, store, now, worktree = ready
    before = store.read_state('project', 'T-1')
    call(hub.root, 'approve-scope', 'project', 'T-1', '--add', 'extra.txt',
         '--quote', 'Include extra.txt', '--desktop', 'codex')
    state = store.read_state('project', 'T-1')
    assert state['status'] == 'ready_to_commit' and state['needs_run'] is False
    assert state['review'] == before['review']
    assert state['last_test_run'] == before['last_test_run']
    if file_drift:
        (worktree / 'extra.txt').write_text('not tested\n', encoding='utf-8')
    engine.tick(now)
    state = store.read_state('project', 'T-1')
    assert state['status'] == ('needs-you' if file_drift else 'committed')
    assert state['runs'] == before['runs']


@pytest.mark.parametrize('drift', ['plan', 'policy'])
def test_reapproval_resumes_ready_stage_for_unchanged_tested_files(ready, hub, drift):
    engine, store, now, worktree = ready
    if drift == 'plan':
        store.write_spec('project', 'T-1', store.read_spec('project', 'T-1').replace('approved files', 'reviewed files'))
    else:
        path = hub.config / 'policy.toml'
        path.write_text(path.read_text(encoding='utf-8') + '\n# revised policy\n', encoding='utf-8')
    engine.tick(now)
    assert store.read_state('project', 'T-1')['status'] == 'needs-you'
    call(hub.root, 'approve', 'project', 'T-1', '--quote', 'Approve this revision', '--desktop', 'codex')
    assert store.read_state('project', 'T-1')['status'] == 'ready_to_commit'
    engine.tick(now)
    assert store.read_state('project', 'T-1')['status'] == 'committed'
