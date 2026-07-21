from __future__ import annotations

import argparse
import csv
import gzip
import html
import json
import logging
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger("fetch_aiaaic")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "rag" / "papers" / "aiaaic-incidents.csv"
OUT_DIR = ROOT / "rag" / "papers" / "aiaaic_pages"

ID_COL, URL_COL = 0, 17
DATA_START_ROW = 3

USER_AGENT = (
    "Mozilla/5.0 (compatible; MoralTimeMachine-research/1.0; "
    "VU thesis RAG ingestion; +https://www.aiaaic.org)"
)

ELEM_RE = re.compile(r'(?is)<(h[1-3]|p)\b([^>]*\bclass="[^"]*\bzfr3Q\b[^"]*"[^>]*)>(.*?)</\1>')
TAG_RE = re.compile(r"(?is)<[^>]+>")
WS_RE = re.compile(r"\s+")

DROP_SECTION_RE = re.compile(r"related|news,\s*commentary|^links\b", re.I)

NAV_RE = re.compile(r"report incident|improve page|access database", re.I)
META_LINE_RE = re.compile(r"^(occurred|page published)\b", re.I)
REPO_ID_RE = re.compile(r"^AIAAIC Repository ID", re.I)
URL_ONLY_RE = re.compile(r"^https?://\S+$")

def _clean(fragment: str) -> str:
    return WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", fragment))).strip()

def _strip_emoji_heading(text: str) -> str:
    return re.sub(r"[\s\W]+$", "", text).strip() or text

def parse_page(raw: str) -> dict | None:
    elements: list[tuple[str, str]] = []
    for m in ELEM_RE.finditer(raw):
        kind = "h" if m.group(1).lower().startswith("h") else "p"
        text = _clean(m.group(3))
        if text:
            elements.append((kind, text))
    if not elements:
        return None

    headline = ""
    summary_parts: list[str] = []
    sections: dict[str, str] = {}
    section_order: list[str] = []
    cur_heading: str | None = None
    cur_body: list[str] = []
    seen_heading = False

    def flush() -> None:
        if cur_heading is not None and cur_body:
            sections[cur_heading] = "\n\n".join(cur_body)
            section_order.append(cur_heading)

    for kind, text in elements:
        if kind == "h":
            flush()
            cur_heading = _strip_emoji_heading(text)
            cur_body = []
            seen_heading = True
            continue

        if REPO_ID_RE.match(text) or NAV_RE.search(text) or URL_ONLY_RE.match(text):
            continue
        if not seen_heading:
            if not headline:
                headline = text
                continue
            if META_LINE_RE.match(text):
                continue
            summary_parts.append(text)
        else:
            cur_body.append(text)
    flush()

    summary = "\n\n".join(summary_parts).strip()
    narrative = {
        h: sections[h] for h in section_order if not DROP_SECTION_RE.search(h)
    }

    text_blocks = [headline, summary] + [
        f"{h}\n{body}" for h, body in narrative.items()
    ]
    text = "\n\n".join(b for b in text_blocks if b).strip()

    return {
        "headline": headline,
        "summary": summary,
        "sections": narrative,
        "text": text,
        "n_sections": len(narrative),
        "n_chars": len(text),
    }

def fetch(url: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        if resp.headers.get("Content-Encoding", "").lower() == "gzip":
            body = gzip.decompress(body)
        return resp.status, body.decode("utf-8", errors="ignore")

def fetch_with_retry(url: str, timeout: float, retries: int) -> tuple[int, str]:
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fetch(url, timeout)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = 2 * attempt
                log.warning("HTTP %d on %s; retry %d/%d in %ds", e.code, url, attempt, retries, wait)
                time.sleep(wait)
                last = e
                continue
            return e.code, ""
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            if attempt < retries:
                wait = 2 * attempt
                log.warning("%s on %s; retry %d/%d in %ds", e, url, attempt, retries, wait)
                time.sleep(wait)
    raise last if last else RuntimeError("unreachable")

def load_rows() -> list[tuple[str, str]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    out: list[tuple[str, str]] = []
    for r in rows[DATA_START_ROW:]:
        if len(r) <= URL_COL:
            continue
        rid, url = r[ID_COL].strip(), r[URL_COL].strip()
        if rid and url.startswith("http"):
            out.append((rid, url))
    return out

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (politeness)")
    ap.add_argument("--timeout", type=float, default=30.0, help="per-request timeout (s)")
    ap.add_argument("--retries", type=int, default=3, help="attempts per URL on transient errors")
    ap.add_argument("--limit", type=int, default=0, help="stop after N incidents (0 = all)")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help="output directory")
    ap.add_argument("--force", action="store_true", help="re-fetch even if JSON exists")
    ap.add_argument("--retry-failed", action="store_true", help="re-fetch only incidents whose saved status != 'ok'")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    if args.limit:
        rows = rows[: args.limit]
    log.info("loaded %d incidents with URLs; output -> %s", len(rows), args.out)

    counts = {"ok": 0, "skipped": 0, "http_error": 0, "no_content": 0, "exception": 0}
    for i, (rid, url) in enumerate(rows, 1):
        dest = args.out / f"{rid}.json"
        if dest.exists() and not args.force:
            if not args.retry_failed:
                counts["skipped"] += 1
                continue
            try:
                if json.loads(dest.read_text()).get("status") == "ok":
                    counts["skipped"] += 1
                    continue
            except (json.JSONDecodeError, OSError):
                pass

        record: dict = {"id": rid, "url": url}
        try:
            status, raw = fetch_with_retry(url, args.timeout, args.retries)
            record["http_status"] = status
            if status != 200 or not raw:
                record["status"] = "http_error"
                counts["http_error"] += 1
            else:
                parsed = parse_page(raw)
                if parsed is None or not parsed["text"]:
                    record["status"] = "no_content"
                    counts["no_content"] += 1
                else:
                    record.update(parsed)
                    record["status"] = "ok"
                    counts["ok"] += 1
        except Exception as e:
            record["status"] = "exception"
            record["error"] = repr(e)
            counts["exception"] += 1
            log.error("failed %s (%s): %r", rid, url, e)

        dest.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        if i % 25 == 0 or i == len(rows):
            log.info("[%d/%d] %s", i, len(rows), counts)
        time.sleep(args.delay)

    log.info("done: %s", counts)

if __name__ == "__main__":
    main()
