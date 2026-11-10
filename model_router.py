from __future__ import annotations

import tomllib
import math
from dataclasses import replace
from pathlib import Path

from adapters.base import Availability, Route
from policy import Policy
from state_writer import read_text_retry


class RouteError(ValueError):
    pass


_EFFORTS = ["low", "medium", "high", "xhigh", "max"]


def load_catalog(path: Path) -> dict:
    try:
        vendors = tomllib.loads(read_text_retry(Path(path)))["vendors"]
        if not isinstance(vendors, dict) or not vendors:
            raise ValueError("missing vendors")
        for vendor, entry in vendors.items():
            if vendor not in {"claude", "codex"}:
                raise ValueError("unknown vendor")
            for field in ("models", "efforts"):
                values = entry[field]
                if (
                    not isinstance(values, list)
                    or not values
                    or any(not isinstance(value, str) or not value for value in values)
                    or len(set(values)) != len(values)
                ):
                    raise ValueError(f"invalid {field}")
            if not set(entry["efforts"]) <= set(_EFFORTS):
                raise ValueError("unknown effort")
        return vendors
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RouteError(f"invalid catalog: {exc}") from None


def resolve(
    proposal: Route,
    role: str,
    *,
    policy: Policy,
    catalog: dict,
    availability: dict[str, Availability],
    quota_blocked: set[str],
    coder_vendor: str | None = None,
) -> tuple[Route, list[str]]:
    settings = policy.routing_roles.get(role)
    if settings is None:
        raise RouteError(f"unknown role: {role}")
    allowed = settings["allowed_vendors"]
    if proposal.max_budget_usd is not None and (
        proposal.vendor != "claude" or type(proposal.max_budget_usd) not in (int, float)
        or not math.isfinite(proposal.max_budget_usd) or proposal.max_budget_usd <= 0
    ):
        raise RouteError("budget must be a positive finite number for Claude only")
    entry = catalog.get(proposal.vendor, {})
    if (
        proposal.vendor not in allowed
        or proposal.model not in entry.get("models", [])
        or proposal.effort not in entry.get("efforts", [])
        or proposal.effort not in _EFFORTS
    ):
        raise RouteError("proposal vendor, model or effort is not allowed")

    def available(vendor: str) -> bool:
        value = availability.get(vendor)
        return value is not None and value.ok and vendor not in quota_blocked

    def fallback(vendor_only: str | None = None) -> Route | None:
        for item in settings["fallback"]:
            vendor, model = item.split(":", 1)
            target = catalog.get(vendor, {})
            efforts = [
                effort
                for effort in _EFFORTS[: _EFFORTS.index(proposal.effort) + 1]
                if effort in target.get("efforts", [])
            ]
            if (
                vendor not in allowed
                or not available(vendor)
                or not efforts
                or model not in target.get("models", [])
                or vendor_only is not None
                and vendor != vendor_only
            ):
                continue
            if vendor != proposal.vendor and not settings.get("auto_fallback", False):
                raise RouteError(
                    f"needs owner: vendor change {proposal.vendor} -> {vendor}"
                )
            return replace(proposal, vendor=vendor, model=model, effort=efforts[-1],
                           max_budget_usd=proposal.max_budget_usd if vendor == "claude" else None)
        return None

    reasons: list[str] = []
    route = proposal
    if not available(route.vendor):
        route = fallback()
        if route is None:
            raise RouteError("no available allowed fallback")
        reasons.append(
            f"fallback: {proposal.vendor} unavailable or quota-blocked -> {route.vendor}:{route.model}"
        )
    if role == "reviewer" and settings.get("reviewer_must_differ") and coder_vendor:
        if route.vendor == coder_vendor:
            other = "codex" if coder_vendor == "claude" else "claude"
            alternate = fallback(other) if available(other) else None
            if alternate is None:
                reasons.append("SAME-VENDOR review")
            else:
                route = alternate
                reasons.append(f"reviewer must differ: selected {route.vendor}")
    return route, reasons
