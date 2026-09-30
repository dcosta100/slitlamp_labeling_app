"""
Session activity logging for labelers.

Each user gets an append-only log at data/logs/{username}_sessions.jsonl with
one JSON object per line. Three event types are written:

    login      - written once, when the labeler authenticates
    heartbeat  - written periodically while the labeler is working, and
                 immediately whenever a label is saved
    logout     - written only when the labeler clicks the Logout button

Streamlit has no callback for "the user closed the tab", so most sessions end
without a logout event. That is why the heartbeat exists: the last heartbeat is
the best available estimate of when the labeler stopped working, and it also
lets us separate wall-clock time from time actually spent labeling.

Writing to the log is best effort. A failure here must never interrupt labeling.
"""

import json
import uuid
from datetime import datetime, timedelta

from config.config import (
    LOGS_DIR,
    HEARTBEAT_INTERVAL_SECONDS,
    SESSION_IDLE_TIMEOUT_MINUTES,
)

EVENT_LOGIN = "login"
EVENT_HEARTBEAT = "heartbeat"
EVENT_LOGOUT = "logout"


def _now():
    """Local time with the UTC offset attached.

    Labelers may sit in different timezones, so a bare local timestamp would be
    ambiguous once the files are collected in one place.
    """
    return datetime.now().astimezone()


def session_log_path(username):
    """Path of a user's session log."""
    return LOGS_DIR / f"{username}_sessions.jsonl"


class SessionTracker:
    """Tracks one labeling session and appends its events to the user's log."""

    def __init__(self, username, labels_at_start=0):
        self.username = username
        self.session_id = uuid.uuid4().hex[:12]
        self.started_at = _now()
        self.labels_at_start = labels_at_start
        self.closed = False
        self._last_written_at = None
        self._last_written_saves = None

    def _append(self, event, **fields):
        record = {
            "ts": _now().isoformat(timespec="seconds"),
            "event": event,
            "session_id": self.session_id,
            "user": self.username,
        }
        record.update(fields)

        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(session_log_path(self.username), "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            return False

        self._last_written_at = _now()
        self._last_written_saves = fields.get("saves")
        return True

    def login(self):
        """Record the start of the session."""
        self._append(EVENT_LOGIN, saves=0, labels_at_start=self.labels_at_start)

    def heartbeat(self, saves=0, labels_total=None, position=None, route_len=None):
        """Record that the labeler is still working.

        Called on every Streamlit rerun, so it is throttled: it writes only when
        HEARTBEAT_INTERVAL_SECONDS have passed, or when a label was saved since
        the last write (so no save is ever missed, even in a fast burst).
        """
        if self.closed:
            return

        saved_since_last_write = saves != self._last_written_saves
        due = (
            self._last_written_at is None
            or (_now() - self._last_written_at).total_seconds() >= HEARTBEAT_INTERVAL_SECONDS
        )
        if not (saved_since_last_write or due):
            return

        self._append(
            EVENT_HEARTBEAT,
            saves=saves,
            labels_total=labels_total,
            position=position,
            route_len=route_len,
        )

    def logout(self, saves=0, labels_total=None, position=None, route_len=None):
        """Record a clean exit via the Logout button."""
        if self.closed:
            return
        self._append(
            EVENT_LOGOUT,
            saves=saves,
            labels_total=labels_total,
            position=position,
            route_len=route_len,
        )
        self.closed = True


# ======================================================
# Streamlit glue
# ======================================================

def _state_snapshot(state):
    """Pull the numbers we log out of Streamlit's session state."""
    label_manager = state.get("label_manager")
    route_indices = state.get("route_indices") or []
    return {
        "saves": state.get("labels_saved", 0) or 0,
        "labels_total": label_manager.get_labeled_count() if label_manager else None,
        "position": state.get("current_position"),
        "route_len": len(route_indices) or None,
    }


def start_session(state, username, labels_at_start=0):
    """Create a tracker for this login and store it in the session state."""
    try:
        tracker = SessionTracker(username, labels_at_start=labels_at_start)
        tracker.login()
        state["session_tracker"] = tracker
    except Exception:
        pass


def heartbeat(state):
    """Heartbeat for the current session, if there is one."""
    tracker = state.get("session_tracker")
    if tracker is None:
        return
    try:
        tracker.heartbeat(**_state_snapshot(state))
    except Exception:
        pass


def close_session(state):
    """Close the current session. Call this *before* clearing the session state."""
    tracker = state.get("session_tracker")
    if tracker is None:
        return
    try:
        tracker.logout(**_state_snapshot(state))
    except Exception:
        pass


# ======================================================
# Reading the logs back
# ======================================================

def read_events(username):
    """All events logged for a user, oldest first. Corrupt lines are skipped."""
    path = session_log_path(username)
    if not path.exists():
        return []

    events = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return events


def list_logged_users():
    """Users that have a session log on this machine."""
    return sorted(
        path.stem[: -len("_sessions")]
        for path in LOGS_DIR.glob("*_sessions.jsonl")
        if path.stem.endswith("_sessions")
    )


def parse_timestamp(value):
    """Parse a logged ISO timestamp into a naive local datetime.

    Timezone info is dropped on purpose: every comparison in the reports is
    against the labeler's own wall clock, and the label files themselves store
    naive local timestamps.
    """
    try:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def sessions_dataframe(usernames=None):
    """Rebuild one row per session from the event logs.

    Columns: user, session_id, started_at, last_seen, duration_minutes,
    active_minutes, saves, labels_at_start, labels_end, net_new, position,
    route_len, ended_by, events.
    """
    import pandas as pd

    users = list_logged_users() if usernames is None else usernames
    idle_gap = timedelta(minutes=SESSION_IDLE_TIMEOUT_MINUTES)
    rows = []

    for user in users:
        by_session = {}
        for event in read_events(user):
            session_id = event.get("session_id")
            timestamp = parse_timestamp(event.get("ts"))
            if not session_id or timestamp is None:
                continue
            event["_ts"] = timestamp
            by_session.setdefault(session_id, []).append(event)

        for session_id, events in by_session.items():
            events.sort(key=lambda e: e["_ts"])
            times = [e["_ts"] for e in events]

            # Time actually worked: sum the gaps between consecutive events,
            # ignoring any gap long enough to mean the labeler walked away.
            active = timedelta()
            for earlier, later in zip(times, times[1:]):
                gap = later - earlier
                if gap <= idle_gap:
                    active += gap

            def last_of(field):
                values = [e.get(field) for e in events if e.get(field) is not None]
                return values[-1] if values else None

            labels_at_start = next(
                (e.get("labels_at_start") for e in events if e.get("labels_at_start") is not None),
                None,
            )
            labels_end = last_of("labels_total")
            saves = max([e.get("saves") or 0 for e in events], default=0)

            rows.append({
                "user": user,
                "session_id": session_id,
                "started_at": times[0],
                "last_seen": times[-1],
                "duration_minutes": round((times[-1] - times[0]).total_seconds() / 60, 1),
                "active_minutes": round(active.total_seconds() / 60, 1),
                "saves": saves,
                "labels_at_start": labels_at_start,
                "labels_end": labels_end,
                "net_new": (
                    labels_end - labels_at_start
                    if labels_end is not None and labels_at_start is not None
                    else None
                ),
                "position": last_of("position"),
                "route_len": last_of("route_len"),
                "ended_by": (
                    "logout"
                    if any(e.get("event") == EVENT_LOGOUT for e in events)
                    else "disconnected"
                ),
                "events": len(events),
            })

    columns = [
        "user", "session_id", "started_at", "last_seen", "duration_minutes",
        "active_minutes", "saves", "labels_at_start", "labels_end", "net_new",
        "position", "route_len", "ended_by", "events",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values("started_at", ascending=False)
