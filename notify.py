from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable

from state_writer import StateStore, atomic_write_text

_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml('<toast><visual><binding template="ToastGeneric"><text/><text/></binding></visual></toast>')
$nodes = $xml.GetElementsByTagName('text')
$nodes.Item(0).AppendChild($xml.CreateTextNode($env:HUB_NOTICE_TITLE)) > $null
$nodes.Item(1).AppendChild($xml.CreateTextNode($env:HUB_NOTICE_BODY)) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('MultiAgentHubV2').Show($toast)
"""


def append_notice(store: StateStore, text: str) -> None:
    with store._writer_lock():
        try:
            previous = store.read_runtime_file("notify.md")
        except FileNotFoundError:
            previous = "# Notifications\n\n"
        atomic_write_text(
            store.root / "runtime" / "notify.md",
            previous + text + "\n",
            store.replace_retries,
            store.replace_backoff,
        )


def notify(
    title: str,
    body: str,
    *,
    runner: Callable = subprocess.run,
    store: StateStore | None = None,
) -> None:
    store = store or StateStore(Path(__file__).resolve().parent)
    try:
        result = runner(
            ["powershell", "-NoProfile", "-Command", _SCRIPT],
            env={**os.environ, "HUB_NOTICE_TITLE": title, "HUB_NOTICE_BODY": body},
            capture_output=True,
            timeout=10,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode:
            raise OSError("toast unavailable")
    except (OSError, ValueError, subprocess.SubprocessError):
        try:
            append_notice(store, "Windows notification failed.")
        except OSError:
            pass
