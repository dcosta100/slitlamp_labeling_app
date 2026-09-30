"""
Admin dashboard page

Tabs, in the order an admin normally needs them:
    Weekly Report  - what to send to colleagues every week
    Sessions       - when each labeler worked, and for how long
    Import         - load the files labelers send in
    Statistics     - cumulative distributions across the whole dataset
    Users          - create labelers, see their route strategy
    Label Review   - inspect and export individual labels
"""

import json
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.config import BACKUPS_DIR, LABELS_DIR, LOGS_DIR, ROUTE_STRATEGIES
from utils.auth import create_user, get_all_users, update_user_route_strategy
from utils.label_manager import LabelManager
from utils.reporting import (
    daily_breakdown,
    file_freshness,
    format_week,
    labels_dataframe,
    list_labeler_files,
    projection,
    recent_weeks,
    weekly_report_markdown,
    weekly_summary,
)
from utils.session_logger import sessions_dataframe


def show():
    """Show admin dashboard"""

    st.markdown('<p class="main-header">📊 Admin Dashboard</p>', unsafe_allow_html=True)

    tabs = st.tabs([
        "📅 Weekly Report",
        "⏱️ Sessions",
        "📥 Import",
        "📈 Statistics",
        "👥 Users",
        "🔍 Label Review",
    ])

    with tabs[0]:
        show_weekly_report()
    with tabs[1]:
        show_sessions()
    with tabs[2]:
        show_import()
    with tabs[3]:
        show_statistics()
    with tabs[4]:
        show_user_management()
    with tabs[5]:
        show_label_review()


# ======================================================
# Weekly report
# ======================================================

def show_weekly_report():
    """Week-by-week progress, ready to be shared with colleagues."""

    st.markdown("## 📅 Weekly Report")

    labels_df = labels_dataframe()
    sessions_df = sessions_dataframe()

    if labels_df.empty:
        st.info("No labels found yet. Import label files on the **Import** tab.")
        return

    weeks = recent_weeks(12)
    week_labels = [
        f"{format_week(start, end)}" + (" (current)" if i == 0 else "")
        for i, (start, end) in enumerate(weeks)
    ]

    col_week, col_refresh = st.columns([3, 1])
    with col_week:
        selected = st.selectbox("Week", options=list(range(len(weeks))),
                                format_func=lambda i: week_labels[i], index=0)
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    start, end = weeks[selected]
    previous_start, previous_end = weeks[selected + 1] if selected + 1 < len(weeks) else (None, None)

    summary = weekly_summary(start, end, labels_df, sessions_df)
    previous_summary = (
        weekly_summary(previous_start, previous_end, labels_df, sessions_df)
        if previous_start else None
    )

    # ---- headline numbers -------------------------------------------------
    total = int(summary["Labels"].sum()) if not summary.empty else 0
    previous_total = (
        int(previous_summary["Labels"].sum())
        if previous_summary is not None and not previous_summary.empty else None
    )
    active_users = int((summary["Labels"] > 0).sum()) if not summary.empty else 0
    hours = float(summary["Active hours"].sum()) if not summary.empty else 0.0
    cumulative = int(summary["Total (all time)"].sum()) if not summary.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Labels this week", f"{total:,}",
                  delta=(f"{total - previous_total:+,}" if previous_total is not None else None))
    with c2:
        st.metric("Active labelers", active_users)
    with c3:
        st.metric("Active hours", f"{hours:.1f}" if hours else "—")
    with c4:
        st.metric("Labels/hour", f"{total / hours:.1f}" if hours >= 0.1 else "—")

    if hours == 0 and total > 0:
        st.caption("⏱️ No session data for this week — active hours require session logging, "
                   "which only records sessions from the moment it was enabled.")

    st.markdown("---")

    # ---- per-user table ---------------------------------------------------
    st.markdown("### Per labeler")
    display = summary.copy()
    if previous_summary is not None and not previous_summary.empty:
        previous_map = dict(zip(previous_summary["User"], previous_summary["Labels"]))
        display.insert(2, "vs last week",
                       display.apply(lambda r: r["Labels"] - previous_map.get(r["User"], 0), axis=1))
    st.dataframe(display, use_container_width=True, hide_index=True)

    # ---- daily activity ---------------------------------------------------
    daily = daily_breakdown(start, end, labels_df)
    if not daily.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            fig = px.bar(daily, x="date", y="labels", color="user",
                         title="Labels per day", barmode="stack")
            fig.update_layout(xaxis_title="", yaxis_title="Labels")
            st.plotly_chart(fig, use_container_width=True)
        with col_b:
            trend = _weekly_trend(labels_df, weeks)
            fig = px.line(trend, x="week", y="labels", color="user", markers=True,
                          title="Weekly trend (last 12 weeks)")
            fig.update_layout(xaxis_title="", yaxis_title="Labels")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No labels recorded in this week.")

    # ---- projection -------------------------------------------------------
    projections = projection(summary)
    if not projections.empty:
        st.markdown("### Projection at this week's pace")
        st.dataframe(projections, use_container_width=True, hide_index=True)
    else:
        st.caption("📐 Projections need the route size, which is captured by session "
                   "logging. They will appear once labelers have worked a full week "
                   "with the new build.")

    # ---- shareable report -------------------------------------------------
    st.markdown("---")
    st.markdown("### 📤 Report to share")

    report = weekly_report_markdown(start, end, summary, previous_summary, projections)
    with st.expander("Preview / copy", expanded=False):
        st.markdown(report)
    st.text_area("Markdown", value=report, height=260, label_visibility="collapsed")

    col_md, col_csv = st.columns(2)
    with col_md:
        st.download_button("📥 Download report (.md)", data=report,
                           file_name=f"weekly_report_{start:%Y-%m-%d}.md",
                           mime="text/markdown", use_container_width=True)
    with col_csv:
        st.download_button("📥 Download table (.csv)", data=summary.to_csv(index=False),
                           file_name=f"weekly_summary_{start:%Y-%m-%d}.csv",
                           mime="text/csv", use_container_width=True)


def _weekly_trend(labels_df, weeks):
    """Labels per user for each of the given weeks, oldest first."""
    rows = []
    for start, end in reversed(weeks):
        in_week = labels_df[
            labels_df["labeled_at"].notna()
            & (labels_df["labeled_at"] >= start)
            & (labels_df["labeled_at"] < end)
        ]
        counts = in_week.groupby("user").size() if not in_week.empty else pd.Series(dtype=int)
        for user in sorted(labels_df["user"].dropna().unique()):
            rows.append({
                "week": start.strftime("%d %b"),
                "user": user,
                "labels": int(counts.get(user, 0)),
            })
    return pd.DataFrame(rows)


# ======================================================
# Sessions
# ======================================================

def show_sessions():
    """When labelers worked, how long, and how each session ended."""

    st.markdown("## ⏱️ Sessions & Activity")
    st.caption("Reconstructed from data/logs/*_sessions.jsonl. A session that ends as "
               "`disconnected` simply means the labeler closed the browser instead of "
               "clicking Logout — the last heartbeat is used as the end time.")

    sessions = sessions_dataframe()

    if sessions.empty:
        st.info(
            "No session logs yet.\n\n"
            "Session logging starts recording the first time a labeler logs in with this "
            "build. To collect it, ask labelers to send **data/logs/{username}_sessions.jsonl** "
            "along with their label file, then load both on the **Import** tab."
        )
        return

    users = sorted(sessions["user"].unique())
    col_user, col_days = st.columns([2, 1])
    with col_user:
        picked = st.multiselect("Labelers", users, default=users)
    with col_days:
        days_back = st.number_input("Days back", min_value=7, max_value=365, value=60, step=7)

    cutoff = datetime.now() - timedelta(days=int(days_back))
    view = sessions[sessions["user"].isin(picked) & (sessions["started_at"] >= cutoff)]

    if view.empty:
        st.warning("No sessions in the selected window.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Sessions", len(view))
    with c2:
        st.metric("Active hours", f"{view['active_minutes'].sum() / 60:.1f}")
    with c3:
        st.metric("Median session", f"{view['active_minutes'].median():.0f} min")
    with c4:
        clean = int((view["ended_by"] == "logout").sum())
        st.metric("Clean logouts", f"{clean}/{len(view)}")

    st.markdown("---")

    daily = (view.assign(date=view["started_at"].dt.date)
             .groupby(["date", "user"])
             .agg(active_hours=("active_minutes", lambda s: round(s.sum() / 60, 2)),
                  saves=("saves", "sum"))
             .reset_index())

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.bar(daily, x="date", y="active_hours", color="user",
                     title="Active hours per day", barmode="stack")
        fig.update_layout(xaxis_title="", yaxis_title="Hours")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        by_hour = view.assign(hour=view["started_at"].dt.hour).groupby(["hour", "user"]).size()
        by_hour = by_hour.rename("sessions").reset_index()
        fig = px.bar(by_hour, x="hour", y="sessions", color="user",
                     title="When sessions start (hour of day)")
        fig.update_layout(xaxis_title="Hour", yaxis_title="Sessions")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Session log")
    table = view.copy()
    table["started_at"] = table["started_at"].dt.strftime("%Y-%m-%d %H:%M")
    table["last_seen"] = table["last_seen"].dt.strftime("%Y-%m-%d %H:%M")
    table = table.rename(columns={
        "user": "User", "started_at": "Login", "last_seen": "Last seen",
        "duration_minutes": "Wall clock (min)", "active_minutes": "Active (min)",
        "saves": "Saves", "net_new": "New labels", "position": "Route position",
        "route_len": "Route size", "ended_by": "Ended by",
    })
    st.dataframe(
        table[["User", "Login", "Last seen", "Wall clock (min)", "Active (min)",
               "Saves", "New labels", "Route position", "Route size", "Ended by"]],
        use_container_width=True, hide_index=True,
    )

    st.download_button("📥 Download sessions (.csv)", data=view.to_csv(index=False),
                       file_name="sessions.csv", mime="text/csv")


# ======================================================
# Import
# ======================================================

def show_import():
    """Load the label files and session logs that labelers send in weekly."""

    st.markdown("## 📥 Weekly Import")
    st.caption("Drop in the files your labelers send you. Accepts "
               "`{username}_labels.json` and `{username}_sessions.jsonl`. "
               "Existing files are backed up before being replaced.")

    st.markdown("### Current files on this machine")
    freshness = file_freshness()
    if freshness.empty:
        st.info("No labeler files present yet.")
    else:
        st.dataframe(freshness, use_container_width=True, hide_index=True)

    st.markdown("---")
    uploaded = st.file_uploader(
        "Files received from labelers",
        type=["json", "jsonl"],
        accept_multiple_files=True,
        key="import_uploader",
    )

    if not uploaded:
        return

    parsed = [_inspect_upload(f) for f in uploaded]

    st.markdown("### What will be imported")
    st.dataframe(
        pd.DataFrame([{
            "File": p["name"],
            "Kind": p["kind"],
            "User": p["username"] or "—",
            "Incoming": p["incoming"],
            "Currently stored": p["existing"],
            "Change": p["delta"],
            "Status": p["status"],
        } for p in parsed]),
        use_container_width=True, hide_index=True,
    )

    problems = [p for p in parsed if p["error"]]
    for p in problems:
        st.error(f"**{p['name']}** — {p['error']}")

    regressions = [p for p in parsed if p["kind"] == "labels" and not p["error"]
                   and p["existing"] and p["incoming"] < p["existing"]]
    for p in regressions:
        st.warning(
            f"**{p['name']}** has {p['existing'] - p['incoming']:,} *fewer* labels than the "
            f"copy already stored ({p['incoming']:,} vs {p['existing']:,}). This usually means "
            f"an older file was sent by mistake. The current copy will be backed up either way."
        )

    importable = [p for p in parsed if not p["error"]]
    if not importable:
        return

    if st.button(f"✅ Import {len(importable)} file(s)", type="primary", use_container_width=True):
        results = [_apply_upload(p) for p in importable]
        for line in results:
            st.success(line)
        st.info("Reload the Weekly Report tab to see the updated numbers.")


def _inspect_upload(uploaded_file):
    """Validate an uploaded file without writing anything."""
    name = uploaded_file.name
    result = {
        "name": name, "kind": "unknown", "username": None, "incoming": 0,
        "existing": 0, "delta": "—", "status": "", "error": None,
        "payload": None, "target": None,
    }

    try:
        raw = uploaded_file.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        result["error"] = "File is not valid UTF-8 text."
        return result

    if name.endswith("_labels.json"):
        result["kind"] = "labels"
        result["username"] = name[: -len("_labels.json")]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            result["error"] = f"Not valid JSON ({exc.msg}, line {exc.lineno})."
            return result
        if not isinstance(data.get("labels"), dict):
            result["error"] = "Missing a 'labels' object — this is not a label file."
            return result

        result["payload"] = data
        result["target"] = LABELS_DIR / name
        result["incoming"] = len(data["labels"])
        if result["target"].exists():
            try:
                with open(result["target"], "r", encoding="utf-8") as f:
                    result["existing"] = len(json.load(f).get("labels") or {})
            except (OSError, json.JSONDecodeError):
                result["existing"] = 0
        result["delta"] = f"{result['incoming'] - result['existing']:+,}"
        result["status"] = "replace (backup kept)" if result["existing"] else "new file"

    elif name.endswith("_sessions.jsonl"):
        result["kind"] = "sessions"
        result["username"] = name[: -len("_sessions.jsonl")]
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        bad = 0
        for line in lines:
            try:
                json.loads(line)
            except json.JSONDecodeError:
                bad += 1
        if bad and bad == len(lines):
            result["error"] = "No valid JSON lines found — this is not a session log."
            return result

        result["payload"] = lines
        result["target"] = LOGS_DIR / name
        result["incoming"] = len(lines)
        if result["target"].exists():
            try:
                with open(result["target"], "r", encoding="utf-8") as f:
                    result["existing"] = sum(1 for line in f if line.strip())
            except OSError:
                result["existing"] = 0
        result["status"] = f"merge (skips duplicates){f', {bad} bad line(s) ignored' if bad else ''}"
        result["delta"] = "merge"

    else:
        result["error"] = ("Unrecognised name. Expected '{username}_labels.json' or "
                           "'{username}_sessions.jsonl'.")

    return result


def _apply_upload(item):
    """Write a validated upload to disk, backing up whatever was there."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = item["target"]

    if target.exists():
        backup = BACKUPS_DIR / f"{target.stem}_{stamp}{target.suffix}"
        backup.write_bytes(target.read_bytes())
    else:
        backup = None

    if item["kind"] == "labels":
        with open(target, "w", encoding="utf-8") as f:
            json.dump(item["payload"], f, indent=2, ensure_ascii=False)
        message = (f"**{item['username']}** — {item['incoming']:,} labels imported "
                   f"({item['delta']} vs stored)")
    else:
        # Session logs are append-only, so merge instead of replacing: keep every
        # line we already had and add the ones we have not seen before.
        existing_lines = []
        if target.exists():
            with open(target, "r", encoding="utf-8") as f:
                existing_lines = [line.strip() for line in f if line.strip()]

        seen = set(existing_lines)
        new_lines = [line for line in item["payload"] if line not in seen]
        with open(target, "w", encoding="utf-8") as f:
            for line in existing_lines + new_lines:
                f.write(line + "\n")
        message = (f"**{item['username']}** — {len(new_lines):,} new session events merged "
                   f"({len(existing_lines):,} already present)")

    if backup:
        message += f" · backup: `{backup.name}`"
    return message


# ======================================================
# Statistics
# ======================================================

def _all_detailed_stats():
    """Detailed stats per labeler, computed once (AI_prelabel excluded)."""
    stats = {}
    for username, path in list_labeler_files():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        manager = LabelManager.__new__(LabelManager)
        manager.username = username
        manager.labels_file = path
        manager.labels = data
        stats[username] = {
            "created_at": data.get("created_at"),
            "last_modified": data.get("last_modified"),
            "detailed": manager.get_detailed_statistics(),
        }
    return stats


def _merge_counts(all_stats, *path):
    """Sum a nested counter across all users, e.g. ('dry_eye', 'by_severity')."""
    merged = {}
    for data in all_stats.values():
        node = data["detailed"]["detailed"]
        for key in path:
            node = node.get(key, {})
        for name, count in node.items():
            merged[name] = merged.get(name, 0) + count
    return merged


def show_statistics():
    """Cumulative distributions across everything labeled so far."""

    st.markdown("## 📈 Cumulative Statistics")
    st.caption("All labels collected to date. AI pre-labels are excluded — these are "
               "human labels only.")

    all_stats = _all_detailed_stats()
    if not all_stats:
        st.info("No labeling data available yet.")
        return

    total_labeled = sum(d["detailed"]["total"] for d in all_stats.values())
    total_usable = sum(d["detailed"]["by_quality"].get("Usable", 0) for d in all_stats.values())
    total_not_usable = sum(d["detailed"]["by_quality"].get("Non Usable", 0) for d in all_stats.values())

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Labels", f"{total_labeled:,}")
    with c2:
        st.metric("Usable", f"{total_usable:,}")
    with c3:
        st.metric("Non Usable", f"{total_not_usable:,}")

    st.markdown("---")
    st.markdown("### 👥 Per-User Totals")

    df_users = pd.DataFrame([{
        "Username": username,
        "Total Labels": data["detailed"]["total"],
        "Usable": data["detailed"]["by_quality"].get("Usable", 0),
        "Non Usable": data["detailed"]["by_quality"].get("Non Usable", 0),
        "Last Modified": data["last_modified"],
    } for username, data in all_stats.items()])
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(df_users, x="Username", y="Total Labels", title="Labels per User",
                     color="Total Labels", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Usable", x=df_users["Username"], y=df_users["Usable"]))
        fig.add_trace(go.Bar(name="Non Usable", x=df_users["Username"], y=df_users["Non Usable"]))
        fig.update_layout(title="Quality Distribution per User", barmode="group")
        st.plotly_chart(fig, use_container_width=True)

    # ---- conditions -------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🏥 Diagnostic Conditions Distribution")

    all_conditions = {}
    for data in all_stats.values():
        for condition, count in data["detailed"]["by_condition"].items():
            all_conditions[condition] = all_conditions.get(condition, 0) + count

    if all_conditions:
        df_cond = (pd.DataFrame(list(all_conditions.items()), columns=["Condition", "Count"])
                   .sort_values("Count", ascending=False))
        col1, col2 = st.columns([1, 2])
        with col1:
            st.dataframe(df_cond, use_container_width=True, hide_index=True)
        with col2:
            fig = px.bar(df_cond, x="Condition", y="Count",
                         title="Distribution of Diagnostic Conditions",
                         color="Count", color_continuous_scale="Viridis")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🔬 Detailed Condition Statistics")

    condition_tabs = st.tabs(["👁️ Dry Eye", "🔍 Cataract", "🦠 Infectious",
                              "🔬 Tumors", "🩸 Hemorrhage"])

    with condition_tabs[0]:
        _two_panel(
            _merge_counts(all_stats, "dry_eye", "by_severity"), "Severity", "Dry Eye Severity", "pie",
            _merge_counts(all_stats, "dry_eye", "by_signs"), "Sign", "Dry Eye Signs", "barh",
            empty="No Dry Eye Disease labels yet",
        )

    with condition_tabs[1]:
        _two_panel(
            _merge_counts(all_stats, "cataract", "by_type"), "Type", "Cataract Types", "pie",
            _merge_counts(all_stats, "cataract", "by_severity"), "Severity", "Cataract Severity", "bar",
            empty="No Cataract labels yet",
        )
        features = _merge_counts(all_stats, "cataract", "by_features")
        if features:
            st.markdown("**Features Distribution**")
            st.dataframe(pd.DataFrame(list(features.items()), columns=["Feature", "Count"]),
                         use_container_width=True, hide_index=True)

    with condition_tabs[2]:
        _two_panel(
            _merge_counts(all_stats, "infectious", "by_type"), "Type", "Infectious Type", "bar",
            _merge_counts(all_stats, "infectious", "by_etiology"), "Etiology", "Infectious Etiology", "pie",
            empty="No Infectious Keratitis/Conjunctivitis labels yet",
        )

    with condition_tabs[3]:
        _two_panel(
            _merge_counts(all_stats, "tumor", "by_type"), "Type", "Tumor Types", "bar",
            _merge_counts(all_stats, "tumor", "by_malignancy"), "Malignancy", "Tumor Malignancy", "pie",
            empty="No Ocular Surface Tumor labels yet",
        )
        location = _merge_counts(all_stats, "tumor", "by_location")
        if location:
            st.markdown("**Location Distribution**")
            fig = px.bar(pd.DataFrame(list(location.items()), columns=["Location", "Count"]),
                         x="Location", y="Count", title="Tumor Location")
            st.plotly_chart(fig, use_container_width=True)

    with condition_tabs[4]:
        _two_panel(
            _merge_counts(all_stats, "sch", "by_presence"), "Presence", "Hemorrhage Presence", "pie",
            _merge_counts(all_stats, "sch", "by_extent"), "Extent", "Hemorrhage Extent", "bar",
            empty="No Subconjunctival Hemorrhage labels yet",
        )

    # ---- laterality -------------------------------------------------------
    st.markdown("---")
    st.markdown("### 👁️ Laterality Distribution")

    all_laterality = {}
    for data in all_stats.values():
        for lat, count in data["detailed"]["by_laterality"].items():
            all_laterality[lat] = all_laterality.get(lat, 0) + count

    if all_laterality:
        df_lat = pd.DataFrame(list(all_laterality.items()), columns=["Laterality", "Count"])
        col1, col2 = st.columns([1, 2])
        with col1:
            st.dataframe(df_lat, use_container_width=True, hide_index=True)
        with col2:
            fig = px.bar(df_lat, x="Laterality", y="Count",
                         title="Distribution by Laterality", color="Laterality")
            st.plotly_chart(fig, use_container_width=True)


def _two_panel(left_counts, left_name, left_title, left_kind,
               right_counts, right_name, right_title, right_kind, empty):
    """Render the standard two-chart layout used by every condition tab."""
    if not left_counts:
        st.info(empty)
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{left_name} Distribution**")
        st.plotly_chart(_chart(left_counts, left_name, left_title, left_kind),
                        use_container_width=True)
    with col2:
        if right_counts:
            st.markdown(f"**{right_name} Distribution**")
            st.plotly_chart(_chart(right_counts, right_name, right_title, right_kind),
                            use_container_width=True)


def _chart(counts, name, title, kind):
    df = pd.DataFrame(list(counts.items()), columns=[name, "Count"])
    if kind == "pie":
        return px.pie(df, values="Count", names=name, title=title)
    if kind == "barh":
        df = df.sort_values("Count", ascending=True)
        return px.bar(df, x="Count", y=name, orientation="h", title=title)
    fig = px.bar(df, x=name, y="Count", title=title)
    fig.update_xaxes(tickangle=45)
    return fig


# ======================================================
# Users
# ======================================================

def show_user_management():
    """Show user management interface"""

    st.markdown("## 👥 User Management")

    st.markdown("### Current Users")
    users = get_all_users()

    df_users = pd.DataFrame([{
        "Username": username,
        "Role": info["role"],
        "Created": info["created_at"],
        "Route Strategy": info.get("route_strategy", "forward"),
        "Route Description": ROUTE_STRATEGIES.get(info.get("route_strategy", "forward"), "—"),
    } for username, info in users.items()])
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🔀 Reassign Route Strategy")
    st.caption("Takes effect on the labeler's next page interaction — no restart needed. "
               "Their saved position belongs to the old route, so they are moved to the "
               "first unlabeled image of the new one. Labels already made are keyed by "
               "image and are not affected.")

    usernames = list(users.keys())
    with st.form("reassign_route_form"):
        col1, col2 = st.columns(2)
        with col1:
            target_user = st.selectbox("Labeler", usernames)
        with col2:
            current = users.get(target_user, {}).get("route_strategy", "forward")
            strategy_keys = list(ROUTE_STRATEGIES.keys())
            new_route = st.selectbox(
                "New route strategy",
                strategy_keys,
                index=strategy_keys.index(current) if current in strategy_keys else 0,
                format_func=lambda x: f"{x}: {ROUTE_STRATEGIES[x]}",
            )

        if st.form_submit_button("Apply", use_container_width=True):
            if new_route == users.get(target_user, {}).get("route_strategy"):
                st.info(f"{target_user} is already on `{new_route}`.")
            elif update_user_route_strategy(target_user, new_route):
                st.success(f"{target_user} reassigned to `{new_route}`.")
                st.rerun()
            else:
                st.error(f"Could not update {target_user}.")

    st.markdown("---")
    st.markdown("### ➕ Create New User")

    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
        with col2:
            new_role = st.selectbox("Role", ["labeler", "admin"])
            new_strategy = st.selectbox(
                "Route Strategy",
                list(ROUTE_STRATEGIES.keys()),
                format_func=lambda x: f"{x}: {ROUTE_STRATEGIES[x]}",
            )

        submit = st.form_submit_button("Create User", use_container_width=True)

        if submit:
            if not new_username or not new_password:
                st.error("Please provide both username and password")
            else:
                success, message = create_user(new_username, new_password, new_role, new_strategy)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


# ======================================================
# Label review
# ======================================================

def show_label_review():
    """Show label review interface"""

    st.markdown("## 🔍 Label Review")

    labeler_files = list_labeler_files()
    if not labeler_files:
        st.info("No labeling data available yet.")
        return

    usernames = [username for username, _ in labeler_files]
    selected_user = st.selectbox("Select user to review", usernames)
    if not selected_user:
        return

    label_manager = LabelManager(selected_user)

    review_queue = label_manager.get_review_queue()
    st.markdown(f"### 📌 Review Queue for {selected_user}")

    if review_queue:
        st.info(f"There are {len(review_queue)} images marked for review")
        for image_key in review_queue:
            label = label_manager.get_label(image_key)
            if not label:
                continue
            conditions = label.get("conditions", {})
            condition_names = ", ".join(conditions.keys()) if conditions else "No conditions"
            short_name = str(image_key).split("\\")[-1]

            with st.expander(f"{short_name} - {label['laterality']} - {condition_names}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Laterality:** {label['laterality']}")
                    st.write(f"**Quality:** {label['quality']}")
                    st.write(f"**Labeled at:** {label['labeled_at']}")
                with col2:
                    st.write(f"**Study ID:** {label.get('metadata', {}).get('maskedid_studyid', 'N/A')}")
                    st.caption(str(image_key))

                if conditions:
                    st.markdown("**Conditions:**")
                    for condition_name, condition_data in conditions.items():
                        st.markdown(f"- **{condition_name}**")
                        for key, value in condition_data.items():
                            if value:
                                st.write(f"  - {key}: {value}")

                if st.button("Remove from review queue", key=f"remove_{image_key}"):
                    label_manager.remove_from_review_queue(image_key)
                    st.rerun()
    else:
        st.success("No images in review queue")

    st.markdown("---")
    st.markdown(f"### 📋 All Labels from {selected_user}")

    labels = label_manager.labels.get("labels", {})
    if not labels:
        st.info("No labels found for this user")
        return

    df_labels = pd.DataFrame([{
        "Image": str(image_key).split("\\")[-1],
        "Study ID": label.get("metadata", {}).get("maskedid_studyid", "N/A"),
        "Laterality": label["laterality"],
        "Quality": label["quality"],
        "Illumination": label.get("illumination") or "—",
        "Conditions": ", ".join(label.get("conditions", {}).keys()) or "None",
        "Labeled At": label["labeled_at"],
        "Edited": "✓" if label.get("is_edit", False) else "",
    } for image_key, label in labels.items()])

    col1, col2, col3 = st.columns(3)
    with col1:
        filter_laterality = st.multiselect("Filter by Laterality",
                                           options=df_labels["Laterality"].unique())
    with col2:
        filter_quality = st.multiselect("Filter by Quality",
                                        options=df_labels["Quality"].unique())
    with col3:
        all_conditions = set()
        for conditions_str in df_labels["Conditions"]:
            if conditions_str != "None":
                all_conditions.update(c.strip() for c in conditions_str.split(","))
        filter_condition = st.multiselect("Filter by Condition", options=sorted(all_conditions))

    if filter_laterality:
        df_labels = df_labels[df_labels["Laterality"].isin(filter_laterality)]
    if filter_quality:
        df_labels = df_labels[df_labels["Quality"].isin(filter_quality)]
    if filter_condition:
        mask = df_labels["Conditions"].apply(
            lambda x: any(cond in x for cond in filter_condition))
        df_labels = df_labels[mask]

    st.dataframe(df_labels, use_container_width=True, hide_index=True)

    st.download_button(
        label="📥 Download as CSV",
        data=df_labels.to_csv(index=False),
        file_name=f"{selected_user}_labels.csv",
        mime="text/csv",
    )
