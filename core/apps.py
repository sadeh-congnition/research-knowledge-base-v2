from __future__ import annotations

import sys
import threading

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"

    def ready(self) -> None:
        import core.signals  # noqa: F401 — register signal handlers

        # Skip the background sync during management commands that don't need it
        # (e.g. migrate, collectstatic, test) and when Django runs ready() a
        # second time in the auto-reloader child process check.
        _SKIP_COMMANDS = {"migrate", "makemigrations", "collectstatic", "test", "shell"}
        argv_command = sys.argv[1] if len(sys.argv) > 1 else ""
        if argv_command in _SKIP_COMMANDS:
            return

        thread = threading.Thread(
            target=_run_chroma_sync,
            name="chroma-startup-sync",
            daemon=True,
        )
        thread.start()


def _run_chroma_sync() -> None:
    """Run sync_all_to_chroma in a background thread, wrapped in error handling."""
    try:
        from core.services import sync_all_to_chroma

        sync_all_to_chroma()
    except Exception as exc:  # noqa: BLE001
        # Deferred import so loguru is optional at module level.
        try:
            from loguru import logger

            logger.error(f"ChromaDB startup sync thread failed: {exc}")
        except Exception:
            print(f"ChromaDB startup sync thread failed: {exc}", file=sys.stderr)
