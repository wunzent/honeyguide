from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path

from bridge import task_snapshots
from policy import PolicyError, load_policy
from state_writer import StateStore, read_text_retry

BANNER = "Approvals are conversational (workflow control, not identity proof) — Security Gate: NOT PASS"


def status_rows(root: Path) -> list[dict]:
    return [
        {
            key: s.get(key)
            for key in ("project", "task", "title", "status", "round", "route")
        }
        for s in task_snapshots(StateStore(root))
    ]


def agent_tree(root: Path) -> list[dict]:
    return [
        {
            "project": s["project"],
            "task": s["task"],
            "run": run_id,
            "role": run.get("role"),
            **{k: run.get("route", {}).get(k) for k in ("vendor", "model")},
            "status": run.get("status"),
            "pid": run.get("pid"),
        }
        for s in task_snapshots(StateStore(root))
        for run_id, run in s.get("runs", {}).items()
    ]


def timeline(root: Path) -> list[dict]:
    store = StateStore(root)
    events = [
        {**asdict(event), "project": s["project"]}
        for s in task_snapshots(store)
        for event in store.read_events(s["project"], s["task"])
    ]
    for event in events:
        if event["kind"] in {"approval.recorded", "answer.recorded", "scope.approved"}:
            record = event["data"].get("record", {})
            event["quote"] = record.get("quote", "")
            event["desktop"] = record.get("desktop", "")
    return sorted(events, key=lambda e: (e["ts"], e["seq"]), reverse=True)


def run_logs(
    root: Path, project: str, task: str, run: str, tail: int = 200
) -> dict[str, str]:
    if re.fullmatch(r"R-\d{14}-[0-9a-f]{4}", run) is None or not 1 <= tail <= 2000:
        raise ValueError("invalid run or tail")
    directory = StateStore(root).task_dir(project, task) / "runs" / run
    result = {}
    for name in ("output.jsonl", "test-log.txt", "result.md"):
        try:
            result[name] = "\n".join(
                read_text_retry(directory / name).splitlines()[-tail:]
            )
        except FileNotFoundError:
            result[name] = ""
    return result


def main(root: Path | None = None) -> None:
    import streamlit as st

    root = root or Path(__file__).resolve().parent
    st.set_page_config(page_title="Hub v2", layout="wide")
    st.warning(BANNER)
    try:
        policy = load_policy(root)
        st.caption(f"Policy hash: {policy.policy_hash}")
        rows = status_rows(root)
        project = st.selectbox(
            "Project filter", ["All", *sorted({r["project"] for r in rows})]
        )
        selected = [r for r in rows if project == "All" or r["project"] == project]
        status, tree, events, logs = st.tabs(
            ["Status", "Agent Tree", "Timeline", "Logs"]
        )
        with status:
            st.dataframe(selected)
        runs = [
            r for r in agent_tree(root) if project == "All" or r["project"] == project
        ]
        with tree:
            st.dataframe(runs)
        with events:
            st.dataframe(
                [
                    e
                    for e in timeline(root)
                    if project == "All" or e["project"] == project
                ]
            )
        with logs:
            selection = st.selectbox(
                "Run",
                runs,
                format_func=lambda r: f"{r['project']}/{r['task']}/{r['run']}",
            )
            if selection:
                for name, text in run_logs(
                    root, selection["project"], selection["task"], selection["run"]
                ).items():
                    st.subheader(name)
                    st.code(text, language="text")
    except (OSError, ValueError, PolicyError) as exc:
        st.error(str(exc))


if __name__ == "__main__":
    main()
