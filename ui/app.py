"""Point this at a folder of git repositories and see which histories look fabricated.

Everything is computed live by the same functions the CLI uses - `git log` is read
at page load, so the verdicts are about the repositories as they are right now.

Run:  streamlit run ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from features import find_repos
from score import report

st.set_page_config(page_title="commit history forensics", layout="wide")

RED, AMBER, BLUE, GREEN, GREY = "#dc2626", "#f59e0b", "#2563eb", "#16a34a", "#94a3b8"
VERDICT_COLOR = {"FABRICATED": RED, "SUSPICIOUS": AMBER, "ONE FLAG": BLUE, "CLEAN": GREEN}

st.title("Does this commit history describe work that happened?")
st.caption(
    "A fabricated contribution graph is easy to make and, it turns out, easy to spot. "
    "Every signal below is a **structural** property of how the commits were made - "
    "timestamps, uniformity, cadence - so it holds regardless of what the code says. "
    "Nothing is trained: each threshold is stated in `src/score.py` with its reasoning."
)

default_root = str(ROOT.parent.parent)
root = st.text_input("Folder containing git repositories", value=default_root)
root_path = Path(root)

if not root_path.exists():
    st.error(f"Not found: {root_path}")
    st.stop()

repos = find_repos(root_path)
if not repos:
    st.warning(f"No git repositories directly inside {root_path}.")
    st.stop()


@st.cache_data(show_spinner="Reading git logs...")
def scan(paths: list[str]) -> list[dict]:
    out = []
    for p in paths:
        try:
            out.append(report(Path(p)))
        except (RuntimeError, ValueError):
            continue
    return out


results = scan([str(p) for p in repos])
if not results:
    st.warning("No repository had a readable history.")
    st.stop()

counts = {v: sum(1 for r in results if r["verdict"] == v) for v in VERDICT_COLOR}

a, b, c, d = st.columns(4)
a.metric("Repositories", len(results))
b.metric("Clean", counts["CLEAN"])
c.metric("Suspicious", counts["SUSPICIOUS"] + counts["ONE FLAG"])
d.metric("Fabricated", counts["FABRICATED"])

if counts["FABRICATED"]:
    st.error(f"{counts['FABRICATED']} repository(ies) show three or more independent signals.")
else:
    st.success("No repository tripped enough signals to be called fabricated.")

# --- table ---------------------------------------------------------------------------

st.subheader("Verdicts")
frame = pd.DataFrame(
    [
        {
            "repo": r["repo"],
            "commits": r["commits"],
            "verdict": r["verdict"],
            "flags": r["flags"],
            "skew (days)": round(r["fingerprint"].skew_median / 86400, 2),
            "files/commit": round(r["fingerprint"].files_mean, 2),
            "commits/active day": round(r["fingerprint"].commits_per_active_day, 2),
        }
        for r in sorted(results, key=lambda r: (-r["flags"], r["repo"]))
    ]
)
st.dataframe(frame, hide_index=True, width="stretch")

# --- the two discriminating features ---------------------------------------------------

st.subheader("Why the verdicts differ")
st.caption(
    "Backdating shows up as a gap between author and committer time. A careful forger "
    "sets both - but still edits exactly one file per commit, which real work does not."
)

left, right = st.columns(2)

with left:
    chart = (
        alt.Chart(frame)
        .mark_bar()
        .encode(
            x=alt.X("repo:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-40)),
            y=alt.Y("skew (days):Q", title="median author->committer gap (days)"),
            color=alt.Color(
                "verdict:N",
                scale=alt.Scale(domain=list(VERDICT_COLOR), range=list(VERDICT_COLOR.values())),
                legend=alt.Legend(orient="top", title=None),
            ),
            tooltip=list(frame.columns),
        )
        .properties(height=340)
    )
    st.altair_chart(chart, width="stretch")

with right:
    chart = (
        alt.Chart(frame)
        .mark_circle(size=160, opacity=0.85)
        .encode(
            x=alt.X("commits:Q", title="commits", scale=alt.Scale(type="symlog")),
            y=alt.Y("files/commit:Q", title="mean files touched per commit"),
            color=alt.Color(
                "verdict:N",
                scale=alt.Scale(domain=list(VERDICT_COLOR), range=list(VERDICT_COLOR.values())),
                legend=alt.Legend(orient="top", title=None),
            ),
            tooltip=list(frame.columns),
        )
        .properties(height=340)
    )
    rule = (
        alt.Chart(pd.DataFrame({"y": [1.0]}))
        .mark_rule(strokeDash=[6, 4], color=GREY)
        .encode(y="y:Q")
    )
    st.altair_chart(chart + rule, width="stretch")
    st.caption("Dashed line: exactly one file per commit - where generators sit.")

# --- per-repo evidence -----------------------------------------------------------------

st.subheader("Evidence for one repository")
names = [r["repo"] for r in sorted(results, key=lambda r: (-r["flags"], r["repo"]))]
picked = st.selectbox("Repository", names)
chosen = next(r for r in results if r["repo"] == picked)

st.markdown(f"### {chosen['repo']} — **{chosen['verdict']}** ({chosen['flags']}/5 signals)")
for signal in chosen["signals"]:
    icon = "🚩" if signal.fired else "✅"
    with st.expander(f"{icon} {signal.name.replace('_', ' ')}", expanded=signal.fired):
        st.write(signal.detail)
        st.caption(f"measured value: {signal.value:,.4g}")

with st.expander("Full fingerprint"):
    st.json(chosen["fingerprint"].as_dict())

st.divider()
st.caption(
    "Signals are heuristics with stated thresholds, not a trained classifier. A short "
    "fabricated history that also fakes the committer date defeats three of the five "
    "signals - see the README for that limitation, which is asserted in the test suite "
    "so it cannot regress silently."
)
