"""
Aggregation helpers for the admin dashboard.

Everything here reads the label files and session logs that live in data/ and
turns them into the numbers shown on the Weekly Report and Labeler tabs. Label
activity is derived from the timestamps stored on every label, so the reports
work retroactively - they do not depend on session logging having been enabled
at the time.

A label is counted as *new* on the date it was first saved and every later
save counts as an *edit*. `labeled_at` alone is not enough for that: it is
overwritten on every edit, and the earlier saves live in `edit_history`.
"""

import json
from datetime import datetime, timedelta

import pandas as pd

from config.config import LABELS_DIR
from utils.session_logger import sessions_dataframe

# Label files in data/labels that do not belong to a human labeler.
NON_LABELER_USERS = ("AI_prelabel",)

LABEL_COLUMNS = [
    "user", "image_key", "image_path", "first_labeled_at", "first_date",
    "labeled_at", "date", "laterality", "quality", "illumination", "studyid",
    "n_conditions", "conditions", "cataract", "is_edit", "n_edits",
]

EVENT_COLUMNS = ["user", "image_key", "saved_at", "date", "kind"]


def list_labeler_files():
    """(username, path) for every real labeler label file.

    Skips AI_prelabel and any ad-hoc backup file sitting in the same folder
    (e.g. taka_labels_pre_sixths_backup.json), which would otherwise be counted
    as extra users.
    """
    found = []
    for path in sorted(LABELS_DIR.glob("*_labels.json")):
        if not path.stem.endswith("_labels"):
            continue
        username = path.stem[: -len("_labels")]
        if username in NON_LABELER_USERS:
            continue
        found.append((username, path))
    return found


def _iter_labels(usernames=None):
    """(username, image_key, label) for every label in the labeler files."""
    for username, path in list_labeler_files():
        if usernames is not None and username not in usernames:
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        for image_key, label in (data.get("labels") or {}).items():
            yield username, image_key, label


def _save_times(label):
    """Every save of a label, oldest first: the edit history, then the current one."""
    times = [h.get("labeled_at") for h in (label.get("edit_history") or [])]
    times.append(label.get("labeled_at"))
    return sorted(t for t in times if t)


def _cataract_summary(conditions):
    cataract = conditions.get("Cataract")
    if not cataract:
        return ""
    return " ".join(v for v in (cataract.get("type"), cataract.get("severity")) if v)


def labels_dataframe(usernames=None):
    """One row per saved label, across all labelers (or only `usernames`)."""
    rows = []
    for username, image_key, label in _iter_labels(usernames):
        conditions = label.get("conditions") or {}
        times = _save_times(label)
        rows.append({
            "user": username,
            "image_key": image_key,
            "image_path": label.get("image_path"),
            "first_labeled_at": times[0] if times else None,
            "labeled_at": label.get("labeled_at"),
            "laterality": label.get("laterality"),
            "quality": label.get("quality"),
            "illumination": label.get("illumination"),
            "studyid": (label.get("metadata") or {}).get("maskedid_studyid"),
            "n_conditions": len(conditions),
            "conditions": ", ".join(sorted(conditions)) if conditions else "None",
            "cataract": _cataract_summary(conditions),
            "is_edit": bool(label.get("is_edit")),
            "n_edits": len(label.get("edit_history") or []),
        })

    if not rows:
        return pd.DataFrame(columns=LABEL_COLUMNS)

    df = pd.DataFrame(rows)
    for column in ("labeled_at", "first_labeled_at"):
        df[column] = pd.to_datetime(df[column], errors="coerce")
    df["date"] = df["labeled_at"].dt.date
    df["first_date"] = df["first_labeled_at"].dt.date
    return df[LABEL_COLUMNS]


def save_events_dataframe(usernames=None):
    """One row per save: the first save of an image is "new", the rest "edit"."""
    rows = []
    for username, image_key, label in _iter_labels(usernames):
        for i, saved_at in enumerate(_save_times(label)):
            rows.append({
                "user": username,
                "image_key": image_key,
                "saved_at": saved_at,
                "kind": "new" if i == 0 else "edit",
            })

    if not rows:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    df = pd.DataFrame(rows)
    df["saved_at"] = pd.to_datetime(df["saved_at"], errors="coerce")
    df["date"] = df["saved_at"].dt.date
    return df[EVENT_COLUMNS]


def _in_window(df, column, start, end):
    """Rows of `df` whose `column` falls in [start, end)."""
    if df.empty:
        return df
    return df[df[column].notna() & (df[column] >= start) & (df[column] < end)]


def first_save_vs_ai(user, ai_labels):
    """Per label: did the labeler's FIRST save keep the AI suggestion unchanged?

    Compares laterality and the cataract type/severity of the first save with
    the AI pre-label for the same image. A high match rate on images where the
    AI is known to be unreliable (e.g. laterality in OU studies) suggests the
    pre-filled form is being saved without review.

    `ai_labels` maps normalized image keys to AI pre-label records.
    """
    from utils.label_manager import normalize_image_path

    def cataract(record):
        c = (record.get("conditions") or {}).get("Cataract") or {}
        return (c.get("type"), c.get("severity"))

    rows = []
    for _, image_key, label in _iter_labels([user]):
        ai = ai_labels.get(normalize_image_path(image_key))
        if not ai:
            continue
        first = (label.get("edit_history") or [label])[0]
        rows.append({
            "image_key": image_key,
            "laterality_same": first.get("laterality") == ai.get("laterality"),
            "cataract_same": cataract(first) == cataract(ai),
        })
    return pd.DataFrame(rows, columns=["image_key", "laterality_same", "cataract_same"])


def file_freshness():
    """When each labeler's file was last saved, to spot stale weekly deliveries."""
    rows = []
    for username, path in list_labeler_files():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        rows.append({
            "User": username,
            "Labels": len(data.get("labels") or {}),
            "Last modified (in file)": data.get("last_modified"),
            "File mtime": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "Size (KB)": round(path.stat().st_size / 1024, 1),
        })
    return pd.DataFrame(rows)


# ======================================================
# Weeks
# ======================================================

def week_start(reference=None):
    """Monday 00:00 of the week containing `reference` (default: now)."""
    reference = reference or datetime.now()
    monday = reference - timedelta(days=reference.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def recent_weeks(count=12, reference=None):
    """[(start, end)] for the last `count` weeks, most recent first."""
    current = week_start(reference)
    return [
        (current - timedelta(weeks=i), current - timedelta(weeks=i) + timedelta(days=7))
        for i in range(count)
    ]


def format_week(start, end):
    """Human-readable label for a week, e.g. '10 Aug 2026 - 16 Aug 2026'."""
    return f"{start:%d %b %Y} - {(end - timedelta(days=1)):%d %b %Y}"


# ======================================================
# Weekly aggregation
# ======================================================

USER_WEEK_COLUMNS = [
    "Week", "week_start", "New labels", "Edits", "Days active", "Sessions",
    "Active hours", "Labels/hour", "Non Usable",
]

SUMMARY_COLUMNS = [
    "User", "Labels", "Days active", "Sessions", "Active hours", "Labels/hour",
    "Usable", "Non Usable", "Edits", "Total (all time)", "Route size",
    "Progress %", "Last activity",
]


def weekly_summary(start, end, labels_df=None, sessions_df=None, events_df=None):
    """Per-user metrics for the window [start, end).

    "Labels" counts images first labeled in the window; re-saving an image
    counts under "Edits" and does not move the label out of its original week.
    """
    labels_df = labels_dataframe() if labels_df is None else labels_df
    sessions_df = sessions_dataframe() if sessions_df is None else sessions_df
    events_df = save_events_dataframe() if events_df is None else events_df

    users = set()
    if not labels_df.empty:
        users |= set(labels_df["user"].dropna())
    if not sessions_df.empty:
        users |= set(sessions_df["user"].dropna())

    rows = []
    for user in sorted(users):
        user_labels = labels_df[labels_df["user"] == user] if not labels_df.empty else labels_df
        user_sessions = sessions_df[sessions_df["user"] == user] if not sessions_df.empty else sessions_df
        user_events = events_df[events_df["user"] == user] if not events_df.empty else events_df

        new_in_week = _in_window(user_labels, "first_labeled_at", start, end)
        events_in_week = _in_window(user_events, "saved_at", start, end)
        sessions_in_week = _in_window(user_sessions, "started_at", start, end)

        n_labels = len(new_in_week)
        active_hours = (
            float(sessions_in_week["active_minutes"].sum()) / 60
            if not sessions_in_week.empty else 0.0
        )
        route_size = None
        if not user_sessions.empty and user_sessions["route_len"].notna().any():
            route_size = int(user_sessions["route_len"].dropna().iloc[0])

        total_all_time = len(user_labels)
        rows.append({
            "User": user,
            "Labels": n_labels,
            "Days active": int(events_in_week["date"].nunique()) if not events_in_week.empty else 0,
            "Sessions": len(sessions_in_week),
            "Active hours": round(active_hours, 1),
            "Labels/hour": round(n_labels / active_hours, 1) if active_hours >= 0.1 else None,
            "Usable": int((new_in_week["quality"] == "Usable").sum()) if n_labels else 0,
            "Non Usable": int((new_in_week["quality"] == "Non Usable").sum()) if n_labels else 0,
            "Edits": int((events_in_week["kind"] == "edit").sum()) if not events_in_week.empty else 0,
            "Total (all time)": total_all_time,
            "Route size": route_size,
            "Progress %": round(100 * total_all_time / route_size, 1) if route_size else None,
            "Last activity": (
                user_labels["labeled_at"].max().strftime("%Y-%m-%d %H:%M")
                if not user_labels.empty and user_labels["labeled_at"].notna().any()
                else "-"
            ),
        })

    if not rows:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS).sort_values("Labels", ascending=False)


def user_weekly_history(user, labels_df=None, sessions_df=None, events_df=None, reference=None):
    """One row per week for a single labeler, from their first activity to now."""
    labels_df = labels_dataframe([user]) if labels_df is None else labels_df[labels_df["user"] == user]
    sessions_df = sessions_dataframe([user]) if sessions_df is None else sessions_df[sessions_df["user"] == user]
    events_df = save_events_dataframe([user]) if events_df is None else events_df[events_df["user"] == user]

    starts = []
    if not events_df.empty and events_df["saved_at"].notna().any():
        starts.append(events_df["saved_at"].min())
    if not sessions_df.empty:
        starts.append(sessions_df["started_at"].min())
    if not starts:
        return pd.DataFrame(columns=USER_WEEK_COLUMNS)

    first_week = week_start(min(starts).to_pydatetime())
    n_weeks = (week_start(reference) - first_week).days // 7 + 1
    rows = []
    for start, end in recent_weeks(count=max(1, n_weeks), reference=reference):
        summary = weekly_summary(start, end, labels_df, sessions_df, events_df)
        row = summary[summary["User"] == user]
        if row.empty:
            continue
        row = row.iloc[0]
        rows.append({
            "Week": format_week(start, end),
            "week_start": start,
            "New labels": row["Labels"],
            "Edits": row["Edits"],
            "Days active": row["Days active"],
            "Sessions": row["Sessions"],
            "Active hours": row["Active hours"],
            "Labels/hour": row["Labels/hour"],
            "Non Usable": row["Non Usable"],
        })
    return pd.DataFrame(rows, columns=USER_WEEK_COLUMNS)


def daily_breakdown(start, end, labels_df=None):
    """Labels per day per user inside the window, for the weekly chart."""
    labels_df = labels_dataframe() if labels_df is None else labels_df
    if labels_df.empty:
        return pd.DataFrame(columns=["date", "user", "labels"])

    in_week = _in_window(labels_df, "first_labeled_at", start, end)
    if in_week.empty:
        return pd.DataFrame(columns=["date", "user", "labels"])

    return (in_week.groupby(["first_date", "user"]).size()
            .rename_axis(["date", "user"])
            .rename("labels").reset_index().sort_values("date"))


def projection(summary, weeks_of_history=1):
    """Rough weeks-to-finish per user at the current pace.

    Only meaningful for users whose route size is known (i.e. who have logged
    at least one session since session logging was enabled).
    """
    rows = []
    for _, row in summary.iterrows():
        route_size = row.get("Route size")
        pace = row.get("Labels")
        # NaN is truthy, so missing values have to be tested explicitly.
        if pd.isna(route_size) or pd.isna(pace) or not route_size or pace <= 0:
            continue
        remaining = max(0, int(route_size) - int(row.get("Total (all time)") or 0))
        weekly_pace = pace / max(1, weeks_of_history)
        weeks_left = remaining / weekly_pace
        rows.append({
            "User": row["User"],
            "Remaining": remaining,
            "Pace (labels/week)": round(weekly_pace, 1),
            "Weeks to finish": round(weeks_left, 1),
            "Est. completion": (datetime.now() + timedelta(weeks=weeks_left)).strftime("%d %b %Y"),
        })
    return pd.DataFrame(rows)


# ======================================================
# Shareable text report
# ======================================================

def weekly_report_markdown(start, end, summary, previous_summary=None, projections=None):
    """A copy-pasteable weekly status report."""
    lines = []
    lines.append("# Slit lamp labeling - weekly report")
    lines.append(f"**Week:** {format_week(start, end)}")
    lines.append(f"**Generated:** {datetime.now():%d %b %Y %H:%M}")
    lines.append("")

    total = int(summary["Labels"].sum()) if not summary.empty else 0
    active_users = int((summary["Labels"] > 0).sum()) if not summary.empty else 0
    hours = float(summary["Active hours"].sum()) if not summary.empty else 0.0
    cumulative = int(summary["Total (all time)"].sum()) if not summary.empty else 0

    previous_total = (
        int(previous_summary["Labels"].sum())
        if previous_summary is not None and not previous_summary.empty else None
    )

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **{total:,} labels** completed this week by {active_users} labeler(s)")
    if previous_total is not None:
        delta = total - previous_total
        direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
        lines.append(f"- Previous week: {previous_total:,} labels ({direction} {abs(delta):,})")
    if hours > 0:
        lines.append(f"- **{hours:.1f} active hours** logged, "
                     f"{total / hours:.1f} labels/hour on average")
    lines.append(f"- **{cumulative:,} labels** in the dataset in total")
    lines.append("")

    lines.append("## Per labeler")
    lines.append("")
    if summary.empty or total == 0:
        lines.append("_No labeling activity recorded this week._")
    else:
        lines.append("| Labeler | Labels | Days | Sessions | Active h | Labels/h | Usable | Non usable | Total | Progress |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for _, row in summary.iterrows():
            rate = "-" if pd.isna(row["Labels/hour"]) else f"{row['Labels/hour']:.1f}"
            progress = "-" if pd.isna(row["Progress %"]) else f"{row['Progress %']:.1f}%"
            lines.append(
                f"| {row['User']} | {row['Labels']:,} | {row['Days active']} | {row['Sessions']} | "
                f"{row['Active hours']:.1f} | {rate} | {row['Usable']:,} | {row['Non Usable']:,} | "
                f"{row['Total (all time)']:,} | {progress} |"
            )
    lines.append("")

    if projections is not None and not projections.empty:
        lines.append("## Projection at current pace")
        lines.append("")
        lines.append("| Labeler | Remaining | Pace/week | Weeks left | Est. completion |")
        lines.append("|---|---:|---:|---:|---|")
        for _, row in projections.iterrows():
            lines.append(
                f"| {row['User']} | {row['Remaining']:,} | {row['Pace (labels/week)']:,} | "
                f"{row['Weeks to finish']} | {row['Est. completion']} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("_Active hours count only time between consecutive actions less than "
                 "15 minutes apart, so idle browser tabs are excluded._")
    return "\n".join(lines)
