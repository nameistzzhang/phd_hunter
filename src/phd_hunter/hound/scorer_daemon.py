"""Hound Scorer Daemon: Background thread that auto-scores professors.

Runs as a daemon thread alongside the Flask server. Periodically polls the
database for professors without scores and invokes the LLM scorer.
"""

import asyncio
import threading
import time
import traceback
from typing import Dict, Any, Optional

from phd_hunter.database import Database
from phd_hunter.hound.scorer import score_professor, load_hound_config


class ScorerDaemon:
    """Background daemon that auto-scores professors."""

    def __init__(
        self,
        db_path: str = "phd_hunter.db",
        poll_interval: int = 10,
        max_batch_per_cycle: int = 1,
    ):
        """Initialize the scorer daemon.

        Args:
            db_path: Path to SQLite database
            poll_interval: Seconds between DB polls
            max_batch_per_cycle: Max professors to score per poll cycle
        """
        self.db_path = db_path
        self.poll_interval = poll_interval
        self.max_batch_per_cycle = max_batch_per_cycle

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        # Stats
        self.stats = {
            "total_scored": 0,
            "total_failed": 0,
            "last_run": None,
            "current_professor": None,
            "is_running": False,
        }

    def start(self) -> None:
        """Start the daemon thread."""
        if self._running:
            print("[ScorerDaemon] Already running.")
            return

        # Validate config exists before starting
        try:
            load_hound_config()
        except FileNotFoundError as e:
            print(f"[ScorerDaemon] Cannot start: {e}")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._running = True
        self.stats["is_running"] = True
        self._thread.start()
        print("[ScorerDaemon] Started.")

    def stop(self) -> None:
        """Signal the daemon to stop."""
        if not self._running:
            return
        self._stop_event.set()
        self._running = False
        self.stats["is_running"] = False
        print("[ScorerDaemon] Stop signal sent.")

    def is_alive(self) -> bool:
        """Check if daemon thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def get_status(self) -> Dict[str, Any]:
        """Get current daemon status."""
        return {
            "running": self._running and self.is_alive(),
            **self.stats,
        }

    def _run(self) -> None:
        """Main daemon loop."""
        print(f"[ScorerDaemon] Polling every {self.poll_interval}s, "
              f"max {self.max_batch_per_cycle} profs/cycle.")

        while not self._stop_event.is_set():
            try:
                self._process_cycle()
            except Exception as e:
                print(f"[ScorerDaemon] Cycle error: {e}")
                traceback.print_exc()

            # Sleep with stop check
            self._stop_event.wait(self.poll_interval)

        print("[ScorerDaemon] Stopped.")

    def _process_cycle(self) -> None:
        """One polling + scoring cycle."""
        db = Database(db_path=self.db_path)

        try:
            # Check if profile exists
            profile = db.get_profile()
            if not profile:
                db.close()
                return  # No profile yet, nothing to score

            # Find unscored professors
            professors = db.list_professors_for_scoring(
                limit=self.max_batch_per_cycle,
                unscored_only=True,
            )
            db.close()

            if not professors:
                return  # Nothing to do this cycle

            for prof in professors:
                if self._stop_event.is_set():
                    break

                prof_id = prof["id"]
                name = prof["name"]

                self.stats["current_professor"] = name
                self.stats["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")

                print(f"[ScorerDaemon] Scoring: {name} ({prof['university_name']}) — {prof['total_papers']} papers")

                try:
                    # Run async scorer in sync context
                    result = asyncio.run(
                        score_professor(
                            professor_id=prof_id,
                            db_path=self.db_path,
                        )
                    )
                    if result:
                        self.stats["total_scored"] += 1
                        print(
                            f"[ScorerDaemon]   Done: DM={result['direction_match']} "
                            f"AD={result['admission_difficulty']}"
                        )
                    else:
                        self.stats["total_failed"] += 1
                        print(f"[ScorerDaemon]   Failed (no result)")

                except Exception as e:
                    self.stats["total_failed"] += 1
                    print(f"[ScorerDaemon]   Error scoring {name}: {e}")
                    traceback.print_exc()

                self.stats["current_professor"] = None

                # Small delay between professors
                if not self._stop_event.is_set():
                    time.sleep(1)

        finally:
            if 'db' in dir() and db:
                try:
                    db.close()
                except:
                    pass


# Global singleton instance
_daemon_instance: Optional[ScorerDaemon] = None


def get_daemon(
    db_path: str = "phd_hunter.db",
    poll_interval: int = 10,
) -> ScorerDaemon:
    """Get or create the global scorer daemon."""
    global _daemon_instance
    if _daemon_instance is None:
        _daemon_instance = ScorerDaemon(
            db_path=db_path,
            poll_interval=poll_interval,
        )
    return _daemon_instance


def start_daemon(db_path: str = "phd_hunter.db") -> None:
    """Convenience: start the global daemon."""
    daemon = get_daemon(db_path=db_path)
    daemon.start()


def stop_daemon() -> None:
    """Convenience: stop the global daemon."""
    global _daemon_instance
    if _daemon_instance:
        _daemon_instance.stop()
