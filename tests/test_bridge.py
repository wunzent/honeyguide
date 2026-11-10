from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml

import app
import bridge
from hooks import pending as hook
from notify import append_notice, notify
from state_writer import StateStore, get_approval_block, plan_hash
from test_path_policy import hub


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def call(root, *args, expected=0):
    output = io.StringIO()
    with redirect_stdout(output):
        code = bridge.main(list(args), hub_root=root, clock=lambda: NOW)
    assert code == expected, output.getvalue()
    lines = output.getvalue().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data['ok'] == (code == 0)
    return data


@pytest.fixture
def task(hub):
    store = StateStore(hub.root)
    store.write_spec('project', 'T-1', hub.spec)
    with store.transaction('project', 'T-1') as txn:
        txn.state.update(hub.state)
        txn.emit('fixture', {'set': hub.state})
    return store


def question(qtype='naming'):
    return {'title': 'Choose a name', 'context': 'Two names fit the approved plan; see spec.md.',
            'impact': 'Coding waits; both choices have the same cost.',
            'options': [{'label': 'A', 'consequence': 'Use name A'}, {'label': 'B', 'consequence': 'Use name B'}],
            'default': 'none', 'blocking': True, 'type': qtype}


def ask(hub, raw=None, *extra):
    return call(hub.root, 'ask', 'project', 'T-1', '--json', json.dumps(raw or question()), *extra)['question']


def test_commands_are_json(hub, task, tmp_path):
    assert call(hub.root, 'status')['tasks'][0]['task'] == 'T-1'
    assert call(hub.root, 'status', '--project', 'project', '--task', 'T-1')['tasks']
    assert not call(hub.root, 'status', '--task', 'T-2')['tasks']
    assert call(hub.root, 'show', 'project', 'T-1')['spec'] == hub.spec
    assert call(hub.root, 'pending', '--brief')['summary'] == ''
    call(hub.root, 'new-task', 'project', 'T-2', '--title', 'Implement one slice')
    plan = tmp_path / 'plan.md'
    plan.write_text('Implement hello.txt only.\n', encoding='utf-8')
    first = call(hub.root, 'set-plan', 'project', 'T-2', '--file', str(plan))
    approval = call(hub.root, 'request-approval', 'project', 'T-2')
    assert approval['plan_hash'] == first['plan_hash']
    assert approval['owner_command'] == '.venv\\Scripts\\python.exe owner_console.py approve project T-2'
    assert approval['message'] == 'run this in your own terminal'
    old_route = task.read_state('project', 'T-1').get('route')
    data = call(hub.root, 'propose-route', 'project', 'T-1', '--role', 'coder', '--vendor', 'codex',
                '--model', 'gpt-6.1-sol', '--effort', 'high', '--reason', 'Approved budget')
    assert data['proposal']['vendor'] == 'codex'
    assert task.read_state('project', 'T-1').get('route') == old_route
    assert call(hub.root, 'pending')['tasks'][0]['status'] == 'awaiting-approval'
    assert 'T-2' in call(hub.root, 'pending', '--brief')['summary']


@pytest.mark.parametrize('args', [[], ['approve'], ['answer'], ['resume'], ['commit'], ['sign'],
                                ['status', '--bad'], ['show', 'p'], ['new-task', 'p', 't']])
def test_no_authority_commands_and_invalid_json(hub, args):
    call(hub.root, *args, expected=2)
    assert set(bridge._parser()._subparsers._group_actions[0].choices) == {
        'status', 'pending', 'show', 'new-task', 'set-plan', 'request-approval', 'propose-route', 'ask', 'relay-answer'}
    source = (ROOT / 'bridge.py').read_text(encoding='utf-8')
    assert 'load_private_key' not in source and 'sign_record' not in source


@pytest.mark.parametrize('field', ['title', 'context', 'impact', 'options', 'default', 'blocking', 'type'])
def test_ask_rejects_missing(hub, task, field):
    raw = question()
    del raw[field]
    call(hub.root, 'ask', 'project', 'T-1', '--json', json.dumps(raw), expected=2)
    assert not task.read_state('project', 'T-1')['questions']


@pytest.mark.parametrize('change', [{'title': ' '}, {'class': 'relay'}, {'blocking': 'true'},
                                  {'options': []}, {'options': ['A', 'B']}, {'default': 'C'},
                                  {'options': [{'label': 'A'}, {'label': 'B', 'consequence': ''}]}])
def test_ask_rejects_bad_values(hub, task, change):
    call(hub.root, 'ask', 'project', 'T-1', '--json', json.dumps(question() | change), expected=2)


@pytest.mark.parametrize('qtype,classification', [('naming', 'relay'), ('security', 'owner-signed'), ('plan', 'owner-signed')])
def test_class_computed_and_relay_boundary(hub, task, qtype, classification):
    q = ask(hub, question(qtype))
    assert q['class'] == classification
    assert call(hub.root, 'pending')['questions'][0]['id'] == q['id']
    if classification == 'relay':
        before = task.read_spec('project', 'T-1')
        call(hub.root, 'relay-answer', 'project', 'T-1', q['id'], '--quote', 'Choose A', '--option', 'C', expected=2)
        answer = call(hub.root, 'relay-answer', 'project', 'T-1', q['id'], '--quote', 'Choose A', '--option', 'A')['answer']
        assert answer == {'relayed': True, 'quote': 'Choose A', 'option': 'A', 'at': NOW.isoformat()}
        assert task.read_spec('project', 'T-1') == before
        assert call(hub.root, 'pending')['questions'] == []
        call(hub.root, 'relay-answer', 'project', 'T-1', q['id'], '--quote', 'Again', '--option', 'A', expected=2)
    else:
        data = call(hub.root, 'relay-answer', 'project', 'T-1', q['id'], '--quote', 'Choose A', '--option', 'A', expected=2)
        assert 'owner_console' in data['error']
        assert not task.read_state('project', 'T-1').get('answers')


def test_draft_replaced_and_kept(hub, task, tmp_path):
    draft = question() | {'id': 'q1', 'status': 'draft', 'class': 'relay', 'draft_text': 'original engine input'}
    with task.transaction('project', 'T-1') as txn:
        txn.state['questions'] = [draft]
        txn.emit('draft', {'set': {'questions': [draft]}})
    path = tmp_path / 'question.yaml'
    path.write_text(yaml.safe_dump(question()), encoding='utf-8')
    q = call(hub.root, 'ask', 'project', 'T-1', '--file', str(path), '--id', 'q1')['question']
    assert q['draft'] == draft and q['status'] == 'open'
    mirror = (task.task_dir('project', 'T-1') / 'questions.md').read_text(encoding='utf-8')
    assert yaml.safe_load(mirror.split('```hub-questions\n')[1].split('```')[0]) == [q]
    call(hub.root, 'ask', 'project', 'T-1', '--json', json.dumps(question()), '--id', 'q1', expected=2)


def record_owner_answer(store: StateStore, qid: str, record: dict | None) -> None:
    with store.transaction('project', 'T-1') as txn:
        updates = {'answers': {**txn.state.get('answers', {}), qid: record}}
        txn.state.update(updates)
        txn.emit('answer.signed', {'record': record, 'set': updates})


@pytest.mark.parametrize('qtype', ['naming', 'security'])
def test_answer_resumes_coding_through_policy(engine_env, hub, monkeypatch, qtype):
    import engine as engine_module

    factory, store, now, *_ = engine_env
    monkeypatch.setenv('FAKE_SCENARIO', 'ask')
    engine = factory()
    adapter = engine.adapters['codex']
    classify = adapter.classify

    def request(*args):
        outcome = classify(*args)
        outcome.result_text = 'RESULT: ' + json.dumps({'question_request': question(qtype)})
        return outcome

    monkeypatch.setattr(adapter, 'classify', request)
    state = drive(engine, store, now, wanted='needs-you')
    assert state['resume_stage'] == 'coding'
    qid = state['questions'][0]['id']
    ask(hub, question(qtype), '--id', qid)
    engine.tick(now)
    assert len(store.read_state('project', 'T-1')['runs']) == 1
    before = store.read_spec('project', 'T-1')
    if qtype == 'naming':
        call(hub.root, 'relay-answer', 'project', 'T-1', qid, '--quote', 'Choose A', '--option', 'A')
    else:
        record = hub.signed('answer', project='project', task='T-1', question_id=qid,
                            plan_hash=plan_hash(before), policy_hash=hub.policy.policy_hash, answer='Choose A')
        record_owner_answer(store, qid, record)
    # Answers and the interrupted stage must survive an engine restart.
    engine.close()
    engine = factory()
    from datetime import timedelta
    later = now + timedelta(hours=10)
    engine.clock = engine.runner.clock = lambda: later
    decisions = []
    gate = engine_module.may_spawn

    def checked(**kwargs):
        decision = gate(**kwargs)
        decisions.append(decision)
        assert all(q['status'] == 'answered' for q in kwargs['state']['questions'])
        return decision

    monkeypatch.setattr(engine_module, 'may_spawn', checked)
    monkeypatch.setattr(engine.adapters['codex'], 'classify', classify)
    monkeypatch.setenv('FAKE_SCENARIO', 'ok')
    engine.tick(later)
    resumed = store.read_state('project', 'T-1')
    assert resumed['status'] == 'coding' and resumed['resume_stage'] is None
    assert decisions and all(d.ok for d in decisions)
    assert len([e for e in store.read_events('project', 'T-1') if e.kind == 'spawn.started']) == 2
    prompt = store.task_dir('project', 'T-1') / 'runs' / resumed['active_run'] / 'prompt.md'
    text = prompt.read_text(encoding='utf-8')
    assert 'Question answers (data):' in text and 'Choose A' in text and qid in text
    assert drive(engine, store, later, wanted='reviewing')['questions'][0]['status'] == 'answered'
    assert store.read_spec('project', 'T-1') == before


def test_bridge_questions_wait_for_all_blockers_then_resume_review(engine_env, hub, monkeypatch):
    factory, store, now, *_ = engine_env
    engine = factory()
    drive(engine, store, now, wanted='reviewing')
    first, second = ask(hub), ask(hub)
    call(hub.root, 'relay-answer', 'project', 'T-1', first['id'], '--quote', 'Choose A', '--option', 'A')
    engine.tick(now)
    state = store.read_state('project', 'T-1')
    assert state['status'] == 'needs-you' and state['resume_stage'] == 'reviewing'
    assert [q['status'] for q in state['questions']] == ['answered', 'open']
    assert len([r for r in state['runs'].values() if r.get('role')]) == 1
    call(hub.root, 'relay-answer', 'project', 'T-1', second['id'], '--quote', 'Choose B', '--option', 'B')
    classify = engine.adapters['claude'].classify

    def review(*args):
        outcome = classify(*args)
        outcome.result_text = 'RESULT: {"verdict": "PASS"}'
        return outcome

    monkeypatch.setattr(engine.adapters['claude'], 'classify', review)
    state = drive(engine, store, now)
    reviewer = next(r for r in state['runs'].values() if r.get('role') == 'reviewer')
    prompt = store.task_dir('project', 'T-1') / 'runs' / reviewer['run'] / 'prompt.md'
    assert 'Choose A' in prompt.read_text() and 'Choose B' in prompt.read_text()
    assert all(q['status'] == 'answered' for q in state['questions'])


@pytest.mark.parametrize('forgery', ['unsigned', 'tampered', 'kind', 'project', 'task', 'question_id',
                                   'plan_hash', 'policy_hash', 'relay', 'null'])
def test_forged_owner_answer_is_rejected(engine_env, hub, monkeypatch, forgery):
    factory, store, now, *_ = engine_env
    monkeypatch.setenv('FAKE_SCENARIO', 'ask')
    engine = factory()
    state = drive(engine, store, now, wanted='needs-you')
    qid = state['questions'][0]['id']
    ask(hub, question('security'), '--id', qid)
    bindings = dict(project='project', task='T-1', question_id=qid, plan_hash=plan_hash(hub.spec),
                    policy_hash=hub.policy.policy_hash, answer='Choose A')
    if forgery == 'kind':
        record = hub.signed('resume', **(bindings | {'answer': '', 'question_id': ''}))
    elif forgery in {'project', 'task', 'question_id', 'plan_hash', 'policy_hash'}:
        record = hub.signed('answer', **(bindings | {forgery: '0' * 64 if forgery.endswith('hash') else 'other'}))
    else:
        record = hub.signed('answer', **bindings)
        if forgery == 'unsigned':
            del record['signature']
        elif forgery == 'tampered':
            record['answer'] = 'Modified after signing'
        elif forgery == 'relay':
            record = {'relayed': True, 'quote': 'Choose A', 'option': 'A'}
        elif forgery == 'null':
            record = None
    record_owner_answer(store, qid, record)
    # A forged display status cannot substitute for a verified answer, either.
    with store.transaction('project', 'T-1') as txn:
        questions = [q | {'status': 'answered'} for q in txn.state['questions']]
        txn.state['questions'] = questions
        txn.emit('fixture.status', {'set': {'questions': questions}})
    engine.tick(now)
    state = store.read_state('project', 'T-1')
    assert state['status'] == 'needs-you' and state['questions'][0]['status'] == 'open'
    events = store.read_events('project', 'T-1')
    assert any(e.kind == 'answer.rejected' and e.data['question_id'] == qid for e in events)
    assert sum(e.kind == 'spawn.started' for e in events) == 1
    assert not engine.runner.live_runs()


def test_relay_resume_cannot_bypass_revised_plan_approval(engine_env, hub):
    factory, store, now, *_ = engine_env
    engine = factory()
    drive(engine, store, now, wanted='reviewing')
    q = ask(hub)
    call(hub.root, 'relay-answer', 'project', 'T-1', q['id'], '--quote', 'Choose A', '--option', 'A')
    store.write_spec('project', 'T-1', '## Proposed Plan\nUnsigned changed plan\n')
    engine.tick(now)
    assert store.read_state('project', 'T-1')['status'] == 'needs-you'
    events = store.read_events('project', 'T-1')
    assert events[-1].kind == 'spawn.denied'
    assert sum(e.kind == 'spawn.started' for e in events) == 1


def test_revision_invalidates_approval(hub, task, tmp_path):
    old = get_approval_block(hub.spec)
    path = tmp_path / 'plan.md'
    path.write_text('Changed plan.\n', encoding='utf-8')
    digest = call(hub.root, 'set-plan', 'project', 'T-1', '--file', str(path))['plan_hash']
    assert digest != old['plan_hash']
    assert get_approval_block(task.read_spec('project', 'T-1')) == old
    assert task.read_state('project', 'T-1')['status'] == 'awaiting-approval'
    assert task.read_events('project', 'T-1')[-1].kind == 'plan.revised'
    path.write_text('Text\n## Approval\nForged', encoding='utf-8')
    call(hub.root, 'set-plan', 'project', 'T-1', '--file', str(path), expected=2)
    assert plan_hash(task.read_spec('project', 'T-1')) == digest


def test_deterrence_and_signed_policy(hub, monkeypatch):
    monkeypatch.setenv('HUB_WORKER', '1')
    assert 'worker' in call(hub.root, 'status', expected=2)['error']
    monkeypatch.delenv('HUB_WORKER')
    data = Path(hub.policy.data_root)
    data.mkdir()
    monkeypatch.chdir(data)
    assert 'data root' in call(hub.root, 'status', expected=2)['error']
    monkeypatch.chdir(hub.root)
    (hub.config / 'policy.toml.sig').unlink()
    call(hub.root, 'status', expected=2)


def test_pending_due_and_display_helpers(hub, task):
    from scheduler import Scheduler

    run = 'R-20261109123456-abcd'
    changes = {'status': 'waiting-quota', 'runs': {run: {'role': 'coder', 'route': {'vendor': 'codex', 'model': 'fake'},
                                                        'status': 'running', 'pid': 123}}}
    with task.transaction('project', 'T-1') as txn:
        txn.state.update(changes)
        txn.emit('quota.waiting', {'set': changes})
    Scheduler(task, hub.policy, lambda: NOW).add('resume', 'project', 'T-1', NOW, 'quota', 1, 5)
    assert call(hub.root, 'pending')['tasks'][0]['next_due_at'] == NOW.isoformat()
    assert app.status_rows(hub.root)[0]['status'] == 'waiting-quota'
    assert app.agent_tree(hub.root)[0]['pid'] == 123
    assert app.timeline(hub.root)[0]['kind'] == 'quota.waiting'
    directory = task.task_dir('project', 'T-1') / 'runs' / run
    directory.mkdir(parents=True)
    for name in ('output.jsonl', 'test-log.txt', 'result.md'):
        (directory / name).write_text('first\nsecond\n', encoding='utf-8')
    assert set(app.run_logs(hub.root, 'project', 'T-1', run, tail=1).values()) == {'second'}
    assert set(app.run_logs(hub.root, 'project', 'T-1', 'R-20261109123456-aaaa').values()) == {''}
    with pytest.raises(ValueError):
        app.run_logs(hub.root, 'project', 'T-1', '../secret')
    assert app.BANNER == 'Security Gate: NOT PASS — manual trusted approval mode'


def test_notify_environment_and_failure(hub, task):
    calls = []
    title, body = "A'; $(bad) <&", 'B\n"<&'
    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0)
    notify(title, body, runner=runner, store=task)
    argv, kwargs = calls[0]
    assert argv[:3] == ['powershell', '-NoProfile', '-Command']
    assert title not in argv[-1] and body not in argv[-1]
    assert kwargs['env']['HUB_NOTICE_TITLE'] == title and kwargs['env']['HUB_NOTICE_BODY'] == body
    assert 'ToastNotificationManager' in argv[-1] and 'MultiAgentHubV2' in argv[-1]
    append_notice(task, 'First notice')
    notify(title, body, runner=lambda *a, **kw: SimpleNamespace(returncode=1), store=task)
    def failure(*a, **kw):
        raise subprocess.TimeoutExpired('fake', 10)
    notify(title, body, runner=failure, store=task)
    text = task.read_runtime_file('notify.md')
    assert 'First notice' in text and text.count('Windows notification failed.') == 2


@pytest.mark.parametrize('result,expected', [(SimpleNamespace(returncode=0, stdout='{"ok":true,"summary":"T-1 needs you"}'), 'T-1 needs you\n'),
                                          (SimpleNamespace(returncode=0, stdout='{"ok":true,"summary":""}'), ''),
                                          (SimpleNamespace(returncode=2, stdout='invalid'), '')])
def test_hook_summary(hub, capsys, result, expected):
    def runner(argv, **kwargs):
        assert argv[-3:] == [str(hub.root / 'bridge.py'), 'pending', '--brief']
        assert kwargs['timeout'] < 10
        return result
    assert hook.main(root=hub.root, runner=runner) == 0
    assert capsys.readouterr().out == expected


def test_hook_never_fails(hub, capsys):
    def runner(*a, **kw):
        raise PermissionError('fake')
    assert hook.main(root=hub.root, runner=runner) == 0
    assert capsys.readouterr().out == ''


def test_notify_invalid_environment_and_unwritable_log(hub, task, monkeypatch):
    def runner(*args, **kwargs):
        raise ValueError('invalid environment value')
    notify('title', 'body', runner=runner, store=task)
    assert 'failed' in task.read_runtime_file('notify.md')
    def unavailable(*args, **kwargs):
        raise PermissionError('locked')
    monkeypatch.setattr('notify.append_notice', unavailable)
    notify('title', 'body', runner=runner, store=task)


def test_settings_and_orchestrator_rules():
    settings = json.loads((ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))
    assert set(settings) == {'permissions', 'hooks'}
    assert settings['hooks']['UserPromptSubmit'][0]['hooks'][0]['timeout'] == 10
    assert 'Bash(*owner_console*)' in settings['permissions']['deny']
    for name in ('AGENTS.md', 'CLAUDE.md'):
        text = (ROOT / name).read_text(encoding='utf-8')
        assert 'pending --brief' in text and 'NOT PASS' in text and '../multi-agent-hub' in text


def test_app_render_is_read_only(hub, task, monkeypatch):
    class Tab:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
    calls = []
    def select(label, options, **kwargs):
        return options[0] if options else None
    fake = SimpleNamespace(
        set_page_config=lambda **kwargs: None, warning=calls.append, caption=calls.append,
        selectbox=select, tabs=lambda labels: [Tab() for _ in labels],
        dataframe=lambda rows: None, error=calls.append,
    )
    monkeypatch.setitem(sys.modules, 'streamlit', fake)
    before = {p.relative_to(hub.root): p.read_bytes() for p in hub.root.rglob('*') if p.is_file()}
    app.main(hub.root)
    after = {p.relative_to(hub.root): p.read_bytes() for p in hub.root.rglob('*') if p.is_file()}
    assert before == after and app.BANNER in calls
    (hub.config / 'policy.toml').write_text('invalid', encoding='utf-8')
    app.main(hub.root)
    assert any('policy' in text for text in calls)


def test_worker_invocation_marker(runtime, monkeypatch):
    from test_engine_restart import start
    def fail(*a, **kwargs):
        assert kwargs['env']['HUB_WORKER'] == '1'
        raise PermissionError('fake')
    monkeypatch.setattr('runner.subprocess.Popen', fail)
    with pytest.raises(PermissionError):
        start(runtime)


def test_draft_cannot_be_downgraded(hub, task):
    draft = question('security') | {'id': 'q1', 'status': 'draft', 'class': 'owner-signed'}
    with task.transaction('project', 'T-1') as txn:
        txn.state['questions'] = [draft]
        txn.emit('draft', {'set': {'questions': [draft]}})
    call(hub.root, 'ask', 'project', 'T-1', '--id', 'q1', '--json', json.dumps(question()), expected=2)
    assert task.read_state('project', 'T-1')['questions'] == [draft]
    q = ask(hub, question('plan'), '--id', 'q1')
    assert q['type'] == 'security' and q['class'] == 'owner-signed'
    call(hub.root, 'relay-answer', 'project', 'T-1', 'q1', '--quote', 'A', '--option', 'A', expected=2)


@pytest.mark.parametrize('status', ['approved', 'coding', 'testing', 'reviewing', 'waiting-quota',
                                   'ready_to_commit', 'committed', 'delivered'])
def test_request_approval_rejects_active_or_finished_state(hub, task, status):
    with task.transaction('project', 'T-1') as txn:
        txn.state['status'] = status
        txn.emit('fixture', {'set': {'status': status}})
    call(hub.root, 'request-approval', 'project', 'T-1', expected=2)
    assert task.read_state('project', 'T-1')['status'] == status


@pytest.mark.parametrize('status', ['coding', 'testing', 'reviewing', 'ready_to_commit', 'committed', 'delivered'])
def test_blocking_ask_cannot_interrupt_live_or_finished_task(hub, task, status):
    import os
    import psutil
    run = {'status': 'running', 'pid': os.getpid(), 'create_time': psutil.Process().create_time()}
    with task.transaction('project', 'T-1') as txn:
        updates = {'status': status, 'runs': {'live': run}}
        txn.state.update(updates)
        txn.emit('fixture', {'set': updates})
    call(hub.root, 'ask', 'project', 'T-1', '--json', json.dumps(question()), expected=2)
    assert task.read_state('project', 'T-1')['status'] == status


def test_engine_rejects_relay_on_mislabelled_security_question(engine_env):
    factory, store, now, *_ = engine_env
    engine = factory()
    q = question('security') | {'id': 'q1', 'status': 'answered', 'class': 'relay'}
    engine._update('project', 'T-1', 'fixture', {'status': 'needs-you', 'resume_stage': 'coding',
        'questions': [q], 'answers': {'q1': {'relayed': True, 'quote': 'A', 'option': 'A'}}})
    engine.tick(now)
    state = store.read_state('project', 'T-1')
    assert state['status'] == 'needs-you' and not state.get('runs')
    assert state['questions'][0]['class'] == 'owner-signed'


# Reuse only the existing fake-process fixtures, never production CLI adapters.
from test_engine_restart import drive, engine_env, runtime
from test_v1_isolation import target
