import json
import os
import sqlite3
import statistics
from collections import Counter

from scipy.stats import mannwhitneyu, spearmanr

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "..", "..", "db.sqlite3")

LIKERT = [
    ("likert_1", "Relevance"),
    ("likert_2", "Specificity"),
    ("likert_6", "Groundedness"),
    ("likert_3", "Unforeseen risk"),
    ("likert_4", "Actionable mitigations"),
    ("likert_5", "Taxonomy fit"),
    ("likert_7", "Adoption"),
    ("likert_8", "Explore Deeper"),
]

SCALE = {1: "Strongly disagree", 2: "Disagree", 3: "Neutral",
         4: "Agree", 5: "Strongly agree"}

SUBGROUP_ITEMS = LIKERT[:7]
LOW_EXPERIENCE = ("Less than 1 year", "1–2 years")
EXPERIENCE_ORDER = ("Less than 1 year", "1–2 years", "3–4 years",
                    "5–10 years", "More than 10 years")
STUDENT_ROLES = ("Bachelor's student (CS or related)",
                 "Master's student (CS or related)",
                 "PhD student / researcher (CS or related)")

COLORS = {1: "#b2182b", 2: "#ef8a62", 3: "#cccccc", 4: "#67a9cf", 5: "#2166ac"}
NA_COLOR = "#f0f0f0"

def cohort_rows(con):
    q = """
        SELECT f.* FROM feedback f
        JOIN participants p ON f.participant_key = p.key
        ORDER BY f.created_at
    """
    con.row_factory = sqlite3.Row
    return con.execute(q).fetchall()

def explore_used_keys(con, rows):
    used = set()
    for r in rows:
        sid = r["session_id_fast"]
        if not sid:
            continue
        n = con.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE session_id=?", (sid,)
        ).fetchone()[0]
        if n > 0:
            used.add(r["participant_key"])
    return used

def l8_value(r, used_keys):
    if r["participant_key"] in used_keys:
        return r["likert_8"]
    return None

def print_stats(rows, con, used_keys):
    n = len(rows)
    print(f"\n=== COHORT N = {n} ===")

    keys = [r["participant_key"] for r in rows]
    labels = Counter(
        con.execute(
            "SELECT label FROM participants WHERE key=?", (k,)
        ).fetchone()[0]
        for k in keys
    )
    print("Channel split:", dict(labels))

    for col in ("role", "experience", "ethics_familiarity", "age", "gender"):
        c = Counter((r[col] or "(blank)") for r in rows)
        print(f"  {col}: {dict(c.most_common())}")

    print("\n--- Likert (median + counts 1..5; L8 over logged users only) ---")
    for col, name in LIKERT:
        if col == "likert_8":
            vals = [v for r in rows if (v := l8_value(r, used_keys)) is not None]
        else:
            vals = [r[col] for r in rows if r[col] is not None]
        na = n - len(vals)
        dist = {v: 0 for v in range(1, 6)}
        for v in vals:
            dist[v] += 1
        med = statistics.median(vals) if vals else None
        extra = f"  not-scored={na}" if na else ""
        print(f"  {name:24s} n={len(vals):2d} median={med}  "
              f"{[dist[v] for v in range(1, 6)]}{extra}")

    rated = [r for r in rows if r["likert_8"] is not None]
    scored = [r for r in rated if r["participant_key"] in used_keys]
    rated_not_used = [r for r in rated if r["participant_key"] not in used_keys]
    didnotuse_used = [r for r in rows if r["likert_8"] is None
                      and r["participant_key"] in used_keys]
    didnotuse_notused = n - len(scored) - len(rated_not_used) - len(didnotuse_used)
    print(f"\nExplore Deeper: rated={len(rated)}, used(logged chat)="
          f"{len(used_keys)}, L8 scored (rated & used)={len(scored)}, "
          f"not scored={n - len(scored)}")
    print(f"  rated+used={len(scored)}  rated+not-used={len(rated_not_used)}  "
          f"didnotuse+used={len(didnotuse_used)}  "
          f"didnotuse+notused={didnotuse_notused}")
    sess_ids = {r["session_id_fast"] for r in rows if r["session_id_fast"]}
    qmarks = ",".join("?" * len(sess_ids))
    chat = con.execute(
        f"SELECT role, COUNT(*) FROM chat_messages "
        f"WHERE session_id IN ({qmarks}) GROUP BY role", tuple(sess_ids)
    ).fetchall()
    sess_with_chat = con.execute(
        f"SELECT COUNT(DISTINCT session_id) FROM chat_messages "
        f"WHERE session_id IN ({qmarks})", tuple(sess_ids)
    ).fetchone()[0]
    print(f"Sessions with chat (cohort): {sess_with_chat}; messages: {dict(chat)}")

    print("\n--- Harm categories across reflections (cohort sessions) ---")
    harm = Counter()
    refl_count = 0
    for sid in sess_ids:
        row = con.execute(
            "SELECT reflections FROM sessions WHERE id=?", (sid,)
        ).fetchone()
        if not row:
            continue
        for refl in json.loads(row[0] or "[]"):
            refl_count += 1
            for h in refl.get("harms", []):
                cat = h.get("category")
                if cat:
                    harm[cat] += 1
    print(f"reflections parsed: {refl_count}; harm tags: {sum(harm.values())}")
    for cat, c in harm.most_common():
        print(f"  {cat:28s} {c}")

def channel_of(con, key):
    lab = con.execute(
        "SELECT label FROM participants WHERE key=?", (key,)
    ).fetchone()[0]
    return "Acquaintances" if lab == "Acquaintances" else "Prolific"

def print_subgroup_stats(rows, con, used_keys):
    print("\n=== SUBGROUP ANALYSES (L1-L7, exploratory) ===")

    def compare(split_name, name_a, group_a, name_b, group_b):
        print(f"\n--- {split_name}: {name_a} (n={len(group_a)}) vs "
              f"{name_b} (n={len(group_b)}) ---")
        for col, item in SUBGROUP_ITEMS:
            a = [r[col] for r in group_a]
            b = [r[col] for r in group_b]
            u, p = mannwhitneyu(a, b, alternative="two-sided")
            r_rb = 2 * u / (len(a) * len(b)) - 1
            print(f"  {item:24s} med {statistics.median(a):.1f} vs "
                  f"{statistics.median(b):.1f}  mean {statistics.mean(a):.2f} vs "
                  f"{statistics.mean(b):.2f}  U={u:5.1f} p={p:.3f} r_rb={r_rb:+.2f}")

    low = [r for r in rows if r["experience"] in LOW_EXPERIENCE]
    exp = [r for r in rows if r["experience"] not in LOW_EXPERIENCE]
    compare("Experience", "low (<3y)", low, "experienced (3y+)", exp)
    print("\n--- Experience as ordinal (Spearman over the five bands) ---")
    ranks = {band: i for i, band in enumerate(EXPERIENCE_ORDER, start=1)}
    xs = [ranks[r["experience"]] for r in rows]
    for col, item in SUBGROUP_ITEMS:
        rho, p = spearmanr(xs, [r[col] for r in rows])
        print(f"  {item:24s} rho={rho:+.2f} p={p:.3f}")

    pro = [r for r in rows if channel_of(con, r["participant_key"]) == "Prolific"]
    acq = [r for r in rows if channel_of(con, r["participant_key"]) != "Prolific"]
    compare("Channel", "Prolific", pro, "Acquaintances", acq)

    stu = [r for r in rows if r["role"] in STUDENT_ROLES]
    dev = [r for r in rows if r["role"] not in STUDENT_ROLES]
    compare("Role", "students", stu, "working developers", dev)

    som = [r for r in rows if r["ethics_familiarity"] == "Somewhat familiar"]
    ver = [r for r in rows if r["ethics_familiarity"] == "Very familiar"]
    compare("Ethics familiarity", "somewhat", som, "very", ver)

    print("\n--- Confound: channel x role group ---")
    ct = Counter((channel_of(con, r["participant_key"]),
                  "student" if r["role"] in STUDENT_ROLES else "developer")
                 for r in rows)
    for k, v in sorted(ct.items()):
        print(f"  {k[0]:14s} {k[1]:10s} {v}")

    print("\n--- Confound: channel x experience band ---")
    ct = Counter((channel_of(con, r["participant_key"]), r["experience"])
                 for r in rows)
    for k, v in sorted(ct.items()):
        print(f"  {k[0]:14s} {k[1]:20s} {v}")

    print("\n--- Explore Deeper uptake (logged chat) by experience band ---")
    for band in EXPERIENCE_ORDER:
        in_band = [r for r in rows if r["experience"] == band]
        if not in_band:
            continue
        used = sum(1 for r in in_band if r["participant_key"] in used_keys)
        print(f"  {band:20s} {used}/{len(in_band)} used")

def make_likert_figure(rows, used_keys):
    items = list(reversed(LIKERT))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))

    for y, (col, name) in enumerate(items):
        if col == "likert_8":
            vals = [v for r in rows if (v := l8_value(r, used_keys)) is not None]
        else:
            vals = [r[col] for r in rows if r[col] is not None]
        na = len(rows) - len(vals)
        counts = {v: sum(1 for x in vals if x == v) for v in range(1, 6)}

        neg = counts[1] + counts[2] + counts[3] / 2.0
        left = -neg
        for v in (1, 2, 3, 4, 5):
            w = counts[v]
            if v == 3:
                ax.barh(y, w / 2.0, left=left, color=COLORS[v], height=0.62,
                        edgecolor="white", linewidth=0.5)
                left += w / 2.0
                ax.barh(y, w / 2.0, left=left, color=COLORS[v], height=0.62,
                        edgecolor="white", linewidth=0.5)
                left += w / 2.0
            else:
                ax.barh(y, w, left=left, color=COLORS[v], height=0.62,
                        edgecolor="white", linewidth=0.5)
                left += w
        if na:
            ax.barh(y, na, left=left, color=NA_COLOR, height=0.62,
                    edgecolor="#bbbbbb", linewidth=0.5, hatch="///")

    ax.axvline(0, color="#444444", linewidth=0.8)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([name for _, name in items])
    ax.set_xlabel("Number of respondents (← disagree | agree →)")
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#eeeeee", linewidth=0.6)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)

    legend = [Patch(facecolor=COLORS[v], label=SCALE[v]) for v in range(1, 6)]
    legend.append(Patch(facecolor=NA_COLOR, hatch="///", edgecolor="#bbbbbb",
                        label="Not scored (L8)"))
    ax.legend(handles=legend, ncol=3, fontsize=8, loc="lower center",
              bbox_to_anchor=(0.5, -0.32), frameon=False)

    fig.tight_layout()
    out = os.path.join(HERE, "likert-distribution.pdf")
    fig.savefig(out, bbox_inches="tight")
    print(f"\nwrote {out}")

def make_participants_figure(rows, con):
    n = len(rows)

    channel = Counter()
    for r in rows:
        lab = con.execute(
            "SELECT label FROM participants WHERE key=?", (r["participant_key"],)
        ).fetchone()[0]
        channel["Acquaintances" if lab == "Acquaintances" else "Prolific"] += 1

    def counts(col):
        return Counter((r[col] or "(blank)") for r in rows)

    role_lbl = {
        "Software developer / engineer": "Software dev / engineer",
        "Senior / lead developer": "Senior / lead developer",
        "Master's student (CS or related)": "Master's student",
        "PhD student / researcher (CS or related)": "PhD / researcher",
        "Bachelor's student (CS or related)": "Bachelor's student",
    }
    panels = [
        ("Role", role_lbl, counts("role")),
        ("Experience",
         {"1–2 years": "1–2 yrs", "3–4 years": "3–4 yrs",
          "5–10 years": "5–10 yrs", "More than 10 years": ">10 yrs"},
         counts("experience")),
        ("Age",
         {"18–24": "18–24", "25–34": "25–34", "35–44": "35–44",
          "45–54": "45–54"},
         counts("age")),
        ("Ethics familiarity",
         {"Somewhat familiar": "Somewhat", "Very familiar": "Very"},
         counts("ethics_familiarity")),
        ("Recruitment channel",
         {"Prolific": "Prolific", "Acquaintances": "Acquaintances"}, channel),
        ("Gender", {"Man": "Man", "Woman": "Woman"}, counts("gender")),
    ]

    bar_color = "#4393c3"
    fig, axes = plt.subplots(3, 2, figsize=(7.2, 5.4))
    for ax, (title, order, cnt) in zip(axes.ravel(), panels):
        items = [(lbl, cnt.get(val, 0)) for val, lbl in order.items()]
        items.reverse()
        labels = [lbl for lbl, _ in items]
        vals = [v for _, v in items]
        y = range(len(labels))
        ax.barh(y, vals, color=bar_color, height=0.66)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_title(title, fontsize=9, loc="left", fontweight="bold")
        ax.set_xlim(0, max(vals) * 1.18)
        for yi, v in zip(y, vals):
            ax.text(v + max(vals) * 0.02, yi, str(v), va="center",
                    fontsize=8, color="#333333")
        ax.tick_params(axis="x", labelsize=7, colors="#888888")
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.tick_params(axis="y", length=0)

    fig.suptitle(f"Participant demographics ($N = {n}$)", fontsize=10,
                 x=0.02, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = os.path.join(HERE, "participants-overview.pdf")
    fig.savefig(out, bbox_inches="tight")
    print(f"wrote {out}")

def main():
    con = sqlite3.connect(DB)
    rows = cohort_rows(con)
    used_keys = explore_used_keys(con, rows)
    print_stats(rows, con, used_keys)
    print_subgroup_stats(rows, con, used_keys)
    make_likert_figure(rows, used_keys)
    make_participants_figure(rows, con)
    con.close()

if __name__ == "__main__":
    main()
