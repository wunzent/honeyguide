from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from adapters.base import Availability, Route
from model_router import RouteError, load_catalog, resolve
from state_writer import plan_hash, plan_tier, set_approval_block
from test_engine_restart import engine_env, runtime
from test_path_policy import hub
from test_v1_isolation import target


ROOT = Path(__file__).resolve().parents[1]
AVAILABLE = {vendor: Availability(True, "fixture", True, "") for vendor in ("claude", "codex")}


def spec(block=""):
    return "## Proposed Plan\nImplement approved files.\n" + block


def tier_block(tier="standard", premium="false"):
    return f"```hub-tier\ntier: {tier}\npremium: {premium}\n```\n"


@pytest.fixture
def routing(hub):
    return dict(policy=hub.policy, catalog=load_catalog(ROOT / "config/models.toml"),
                availability=AVAILABLE, quota_blocked=set())


@pytest.mark.parametrize("tier,effort", [("routine", "low"), ("standard", "medium"), ("complex", "high")])
@pytest.mark.parametrize("role", ["coder", "reviewer", "tester", "doc-keeper"])
def test_engine_tier_defaults(engine_env, tier, effort, role):
    factory, store, *_ = engine_env
    store.write_spec("project", "T-1", spec(tier_block(tier)))
    engine = factory()
    route, _ = engine._route(role, {"coder_vendor": "codex"}, set(), project="project", task="T-1")
    assert route.effort == ("low" if role in ("tester", "doc-keeper") else effort)
    assert (route.vendor, route.model) == (("claude", "sonnet") if role == "reviewer" else ("codex", "gpt-6.1-sol"))
    assert route.model not in engine.catalog[route.vendor]["premium_models"]
    assert route.model not in engine.catalog[route.vendor]["unverified_models"]


@pytest.mark.parametrize("route", [Route("claude", "opus", "high"), Route("claude", "claude-opus-5-5", "low"),
                                   Route("codex", "gpt-6.1-sol", "xhigh"), Route("claude", "sonnet", "max")])
def test_premium_requires_authority(routing, route):
    with pytest.raises(RouteError, match="premium route requires premium: true"):
        resolve(route, "coder", **routing)
    assert resolve(route, "coder", allow_premium=True, **routing)[0] == route


@pytest.mark.parametrize("vendor,model", [("claude", "haiku"), ("claude", "claude-haiku-5-5"), ("codex", "gpt-6-luna")])
@pytest.mark.parametrize("premium", [False, True])
def test_unverified_always_rejected(routing, vendor, model, premium):
    with pytest.raises(RouteError, match="model not live-verified"):
        resolve(Route(vendor, model, "high"), "coder", allow_premium=premium, **routing)


@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh"])
def test_fallback_skips_expensive_unverified_and_never_raises(routing, effort):
    roles = deepcopy(routing["policy"].routing_roles)
    roles["coder"].update(auto_fallback=True, fallback=["claude:opus", "claude:haiku", "codex:gpt-6-luna", "claude:sonnet"])
    routing.update(policy=replace(routing["policy"], routing_roles=roles), quota_blocked={"codex"})
    route, reasons = resolve(Route("codex", "gpt-6.1-sol", effort), "coder", allow_premium=True, **routing)
    assert route == Route("claude", "sonnet", "high" if effort == "xhigh" else effort)
    assert reasons


def test_reviewer_differ_and_vendor_approval_preserved(routing):
    with pytest.raises(RouteError, match="vendor change"):
        resolve(Route("codex", "gpt-6.1-sol", "low"), "reviewer", coder_vendor="codex", **routing)
    roles = deepcopy(routing["policy"].routing_roles)
    roles["reviewer"]["auto_fallback"] = True
    routing["policy"] = replace(routing["policy"], routing_roles=roles)
    route, reasons = resolve(Route("codex", "gpt-6.1-sol", "low"), "reviewer", coder_vendor="codex", **routing)
    assert route == Route("claude", "sonnet", "low")
    assert reasons == ["reviewer must differ: selected claude"]


def test_missing_tier_and_hash():
    assert plan_tier(spec()) == {"tier": "standard", "premium": False}
    assert plan_tier(spec(tier_block("routine", "true"))) == {"tier": "routine", "premium": True}
    assert plan_hash(spec(tier_block("routine"))) != plan_hash(spec(tier_block("complex")))
    assert plan_hash(spec(tier_block(premium="false"))) != plan_hash(spec(tier_block(premium="true")))
    assert plan_tier(spec() + "## Notes\n" + tier_block("complex", "true")) == {"tier": "standard", "premium": False}


BAD_BLOCKS = [tier_block("unknown"), tier_block(premium='"false"'), tier_block(premium="1"),
              tier_block() + tier_block(), "```hub-tier\ntier: routine\n", "```hub-tier\n[broken\n```\n",
              "```hub-tier\n- routine\n```\n", "```hub-tier\ntier: routine\ntier: complex\n```\n",
              "```hub-tier extra\ntier: routine\n```\n"]


@pytest.mark.parametrize("block", BAD_BLOCKS)
def test_malformed_tier_fails(block):
    with pytest.raises(ValueError):
        plan_tier(spec(block))


@pytest.mark.parametrize("block", [b for b in BAD_BLOCKS if b.count("```") % 2 == 0])
def test_malformed_tier_dispatch_blocks_without_spawn(engine_env, hub, monkeypatch, block):
    factory, store, now, *_ = engine_env
    engine = factory()
    text = spec(block)
    approval = hub.record("approve-plan", project="project", task="T-1", plan_hash=plan_hash(text), policy_hash=hub.policy.policy_hash)
    store.write_spec("project", "T-1", set_approval_block(text, approval))
    engine._update("project", "T-1", "fixture", {"approval": approval, "approval_history": [approval], "status": "approved", "needs_run": True})
    monkeypatch.setattr(engine.runner, "start", lambda *a, **k: pytest.fail("malformed tier spawned"))
    engine.tick(now)
    state = store.read_state("project", "T-1")
    assert state["status"] == "needs-you" and not state.get("runs")
    assert any(e.kind == "dispatch.blocked" and "hub-tier" in e.data["reason"] for e in store.read_events("project", "T-1"))


@pytest.mark.parametrize("premium", ["false", "true"])
def test_engine_passes_plan_premium(engine_env, premium):
    factory, store, *_ = engine_env
    store.write_spec("project", "T-1", spec(tier_block(premium=premium)))
    engine = factory()
    state = {"route_proposals": {"coder": {"vendor": "claude", "model": "opus", "effort": "high", "reason": "explicit escalation"}}}
    if premium == "false":
        with pytest.raises(RouteError, match="premium route requires"):
            engine._route("coder", state, set(), project="project", task="T-1")
    else:
        assert engine._route("coder", state, set(), project="project", task="T-1")[0] == Route("claude", "opus", "high")


def test_legacy_catalog_loads(tmp_path, routing):
    path = tmp_path / "models.toml"
    path.write_text('[vendors.codex]\nmodels = ["gpt-6.1-sol"]\nefforts = ["low", "xhigh"]\n', encoding="utf-8")
    catalog = load_catalog(path)
    assert set(catalog) == {"codex"}
    assert catalog["codex"]["premium_models"] == catalog["codex"]["unverified_models"] == []
    routing["catalog"] = catalog
    with pytest.raises(RouteError, match="premium route requires"):
        resolve(Route("codex", "gpt-6.1-sol", "xhigh"), "coder", **routing)
