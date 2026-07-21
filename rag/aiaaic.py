from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path

from rag.schema import SPECTRUM_LABELS, Chunk

log = logging.getLogger("rag.aiaaic")

REPO_RAG_ROOT = Path(__file__).resolve().parent
CSV_PATH = REPO_RAG_ROOT / "papers" / "aiaaic-incidents.csv"
PAGES_DIR = REPO_RAG_ROOT / "papers" / "aiaaic_pages"

DATA_START_ROW = 3
COLS = {
    "id": 0, "headline": 1, "occurred": 2, "deployer": 3, "developer": 4,
    "system": 5, "technology": 6, "purpose": 7, "ethical": 9, "sector": 11,
    "harm_individual": 12, "harm_societal": 13, "harm_environmental": 14,
    "consequence": 15, "response": 16,
}

_NON_NARRATIVE_SECTIONS = {"System", "Timeline"}

STAGE_B: dict[str, list[str]] = {
    "Accountability": ["Accountability"],
    "Transparency": ["Transparency"],
    "Privacy & surveillance": ["Privacy"],
    "Consent": ["Privacy"],
    "Security": ["Privacy"],
    "Mis/disinformation": ["False information"],
    "Accuracy/reliability": ["False information"],
    "Authenticity/integrity": ["False information"],
    "Revisionism": ["False information"],
    "Fairness": ["Disparity"],
    "Diversity & inclusivity": ["Disparity"],
    "Accessibility": ["Disparity"],
    "Power inbalance": ["Disparity"],
    "Appropriation": ["Fraudulent activity"],
    "Copyright": ["Fraudulent activity"],
    "Anthropomorphism": ["Manipulation"],
    "Autonomy/agency": ["Manipulation"],
}

EMPTY_CANONICAL = frozenset({
    "Safety", "Alignment", "Automation bias", "Normalisation", "Representation",
    "Human rights/civil liberties", "Proportionality", "Oversight",
    "Autonomous weapons", "Employment/labour", "Environment",
    "Competition/monopolisation", "Dual use", "Robot rights", "Ethics/values",
    "Other",
})

_KNOWN_CANONICAL = set(STAGE_B) | EMPTY_CANONICAL

RAW_TO_CANONICAL: dict[str, str] = {

    "accountability": "Accountability", "accountabiilty": "Accountability",
    "accountabiity": "Accountability", "ownership/accountability": "Accountability",
    "liability": "Accountability", "legal": "Accountability",

    "transparency": "Transparency", "transaprency": "Transparency",
    "transpareny": "Transparency",

    "privacy & surveillance": "Privacy & surveillance",
    "privacy/surveillance": "Privacy & surveillance",
    "privacy/surveillance/surveillance": "Privacy & surveillance",
    "privacy/surveillamce": "Privacy & surveillance",
    "surveillance": "Privacy & surveillance", "surveillanc": "Privacy & surveillance",
    "privacy": "Privacy & surveillance",

    "consent": "Consent",
    "security": "Security", "confidentiality": "Security",

    "mis/disinformation": "Mis/disinformation",
    "accuracy/reliability": "Accuracy/reliability",
    "accuracy/reliablity": "Accuracy/reliability",
    "accuracy/relibaility": "Accuracy/reliability",
    "accuracy/reliabiity": "Accuracy/reliability",
    "authenticity/integrity": "Authenticity/integrity",
    "revisionism": "Revisionism",

    "fairness": "Fairness", "bias/discrimination": "Fairness",
    "diversity & inclusivity": "Diversity & inclusivity",
    "diversity/inclusivity": "Diversity & inclusivity",
    "accessibility": "Accessibility", "accessiblity": "Accessibility",
    "power inbalance": "Power inbalance",

    "appropriation": "Appropriation", "appropropriation": "Appropriation",
    "cheating/plagiarism": "Appropriation", "plagiarism": "Appropriation",
    "copyright": "Copyright",

    "anthropomorphism": "Anthropomorphism", "autonomy/agency": "Autonomy/agency",

    "safety": "Safety", "alignment": "Alignment", "automation bias": "Automation bias",
    "normalisation": "Normalisation", "scope creep/normalisation": "Normalisation",
    "representation": "Representation",
    "human rights/civil liberties": "Human rights/civil liberties",
    "human/civil rights": "Human rights/civil liberties",
    "freedom of expression": "Human rights/civil liberties",
    "freedom of expression - right of assembly": "Human rights/civil liberties",
    "proportionality": "Proportionality",
    "oversight": "Oversight", "oversight/review": "Oversight", "governance": "Oversight",
    "autonomous weapons": "Autonomous weapons",
    "lethal autonomous weapons": "Autonomous weapons",
    "employment/labour": "Employment/labour", "employment": "Employment/labour",
    "employment - jobs": "Employment/labour", "employment/labour - jobs": "Employment/labour",
    "job loss/losses loss": "Employment/labour",
    "environment": "Environment",
    "competition/monopolisation": "Competition/monopolisation",
    "compeititon/monopolisation": "Competition/monopolisation",
    "competition/collusion": "Competition/monopolisation",
    "dual use": "Dual use", "dual/multi-use": "Dual use",
    "robot rights": "Robot rights", "ethics/values": "Ethics/values",

    "effectiveness/value": "Other", "business model": "Other", "risk management": "Other",
    "information degradation": "Other", "demonetisation": "Other",
    "involvement/participation": "Other", "prioritisation": "Other",
    "supply chain management": "Other", "complaints/appeals": "Other",
    "robustness": "Other", "appropriateness/need": "Other", "financial loss": "Other",
}

_FAIRNESS_QUALIFIED_RE = re.compile(r"(?i)fairness\s*-\s*[^;]*")
_SPLIT_RE = re.compile(r"[;,:]")

def normalize_issues(raw: str) -> set[str]:
    if not raw or not raw.strip():
        return set()
    collapsed = _FAIRNESS_QUALIFIED_RE.sub("Fairness", raw)
    out: set[str] = set()
    for tok in _SPLIT_RE.split(collapsed):
        key = tok.strip().lower()
        if not key:
            continue
        canon = RAW_TO_CANONICAL.get(key)
        if canon is None and key in {c.lower() for c in _KNOWN_CANONICAL}:
            canon = next(c for c in _KNOWN_CANONICAL if c.lower() == key)
        if canon is None:
            log.debug("unmapped ethical-issue token %r -> dropped", tok.strip())
            continue
        out.add(canon)
    return out

def harm_labels_for(raw: str) -> list[str]:
    labels: set[str] = set()
    for canon in normalize_issues(raw):
        labels.update(STAGE_B.get(canon, ()))
    bad = labels - SPECTRUM_LABELS
    if bad:
        raise ValueError(f"STAGE_B produced non-Spectrum label(s): {bad}")
    return sorted(labels)

def _usable_scrape(page: dict | None) -> str:
    if not page or page.get("status") != "ok":
        return ""
    summary = (page.get("summary") or "").strip()
    sections = page.get("sections") or {}
    narrative = {k: v for k, v in sections.items() if k not in _NON_NARRATIVE_SECTIONS}
    if not summary and not narrative:
        return ""
    blocks = [summary] + [f"{k}\n{v}" for k, v in narrative.items()]
    return "\n\n".join(b for b in blocks if b).strip()

def _build_body(row: dict, scraped: str) -> str:
    header = f"[Real incident — {row['id']}: {row['headline']}]"
    meta = []
    for label, key in (("Sector", "sector"), ("Occurred", "occurred"),
                       ("Technology", "technology"), ("Purpose", "purpose")):
        if row[key]:
            meta.append(f"{label}: {row[key]}")
    who = " / ".join(x for x in (row["deployer"], row["developer"]) if x)
    if who:
        meta.append(f"Deployer/Developer: {who}")
    harms = "; ".join(
        x for x in (row["harm_individual"], row["harm_societal"], row["harm_environmental"]) if x
    )

    lines = [header, ""]
    if meta:
        lines.append(" | ".join(meta))
    if row["ethical"]:
        lines.append(f"Ethical issues (AIAAIC): {row['ethical']}")
    if harms:
        lines.append(f"External harms: {harms}")
    if scraped:
        lines += ["", scraped]
    return "\n".join(lines).strip()

def _load_page(incident_id: str) -> dict | None:
    path = PAGES_DIR / f"{incident_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("could not read page %s: %s", path.name, e)
        return None

def _read_rows() -> list[dict]:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        raw = list(csv.reader(f))
    rows: list[dict] = []
    seen: set[str] = set()
    for r in raw[DATA_START_ROW:]:
        if len(r) <= max(COLS.values()):
            r = r + [""] * (max(COLS.values()) + 1 - len(r))
        rid = r[COLS["id"]].strip()
        headline = r[COLS["headline"]].strip()
        if not rid or not headline:
            continue
        if rid in seen:
            log.warning("duplicate AIAAIC id %s in CSV; keeping first occurrence", rid)
            continue
        seen.add(rid)
        rows.append({k: r[i].strip() for k, i in COLS.items()})
    return rows

def build_aiaaic_chunks() -> list[Chunk]:
    rows = _read_rows()
    if not PAGES_DIR.exists():
        log.warning("no scraped pages dir at %s; all incidents use structured fallback", PAGES_DIR)

    chunks: list[Chunk] = []
    n_skipped = n_labeled = 0
    for row in rows:
        scraped = _usable_scrape(_load_page(row["id"]))
        if not scraped:

            n_skipped += 1
            continue
        harm_labels = harm_labels_for(row["ethical"])
        if harm_labels:
            n_labeled += 1
        title = f"AIAAIC {row['id'].removeprefix('AIAAIC')}: {row['headline']}"
        if row["occurred"]:
            title += f" ({row['occurred']})"
        chunks.append(
            Chunk(
                chunk_id=row["id"],
                source=f"aiaaic-{row['id']}",
                source_full_title=title,
                chunk_type="real-incident",
                original_label=row["headline"],
                harm_labels=harm_labels,
                body=_build_body(row, scraped),
            )
        )
    log.info(
        "aiaaic: %d incidents with rich prose (%d with harm labels); "
        "skipped %d without usable scrape",
        len(chunks), n_labeled, n_skipped,
    )
    return chunks
