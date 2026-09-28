"""Raw inputs -> anonymized release.

(EVERYDAY_MOMO below: the scam types people meet directly on their mobile money phone.)

Inputs (all private, under raw/):
  raw/tally_exports/*.csv             form submissions, exported from Tally
  raw/web/curated_public_alerts.jsonl  facts extracted from public alerts
  raw/screenshots/                     downloaded report screenshots (filled automatically)
  raw/review_overrides.jsonl           manual corrections after review (optional)

Outputs:
  release/<version>/reports.jsonl|csv, public_alerts.jsonl|csv, scam_numbers.csv, stats.json
  raw/review_queue.csv                 what needs a human look before release (private)
  raw/report_subscribers.txt           emails asking for the public report (private, never released)
"""
import csv
import hashlib
import hmac
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import anonymize as A
from . import taxonomy as T
from .ingest_form import read_tally_csv, missing_columns

ROOT = Path(os.environ.get("STOPARNAQUE_ROOT") or Path(__file__).resolve().parent.parent)
RAW = ROOT / "raw"
RELEASE = ROOT / "release"

EVERYDAY_MOMO = {"wrong_number_reversal", "deposit_withdrawal_trap", "account_blocked", "credential_request", "sim_swap"}

REPORT_FIELDS = [
    "id", "record_type", "source", "submitted_month", "when", "channel", "scam_types",
    "message_text", "text_origin", "has_screenshot", "sender", "sender_type", "sender_phone_id",
    "phone_ids", "domains", "caller_claimed", "caller_asked", "call_language", "call_end", "call_description",
    "outcome", "amount_lost_fcfa", "payment_rails", "actions_after", "region", "extra_notes",
    "would_use_tool", "message_cluster", "src_channel",
]
ALERT_FIELDS = [
    "id", "record_type", "source", "source_url", "date_published", "title", "summary", "impersonated",
    "target", "channels", "scam_types", "requested_actions", "amount_requested_fcfa", "example_message",
    "phone_ids", "domains", "entities",
]


# ---------------- helpers ----------------
def _hid(prefix, value):
    return f"{prefix}-" + hmac.new(A._key(), str(value).encode(), hashlib.sha256).hexdigest()[:8]


def _cluster(text):
    if not text:
        return None
    t = re.sub(r"\[PHONE:[^\]]+\]", "[PHONE]", text.lower())
    t = re.sub(r"\d+", "0", t)
    t = re.sub(r"\W+", " ", t).strip()
    return "C-" + hashlib.sha1(t.encode()).hexdigest()[:8] if len(t) > 15 else None


def _month(s):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime((s or "").strip()[:26], fmt).strftime("%Y-%m")
        except ValueError:
            continue
    m = re.search(r"(\d{4})-(\d{2})", s or "")
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _load_overrides():
    f = RAW / "review_overrides.jsonl"
    out = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                out[o["key"]] = o
    return out


# ---------------- screenshots ----------------
def fetch_screenshots(reports, log):
    """Download screenshot links from the export into raw/screenshots/<submission>/ (private)."""
    import requests
    shots = RAW / "screenshots"
    for r in reports:
        urls = r.get("screenshots") or []
        r["_shot_files"] = []
        for i, u in enumerate(urls):
            ext = Path(u.split("?")[0]).suffix.lower() or ".png"
            dest = shots / str(r["submission_id"]) / f"{i + 1}{ext}"
            if not dest.exists():
                try:
                    resp = requests.get(u, timeout=40)
                    resp.raise_for_status()
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(resp.content)
                except Exception as e:  # keep going; the review queue shows what failed
                    log.append(f"screenshot download failed for {r['submission_id']}: {e}")
                    continue
            r["_shot_files"].append(dest)
    # screenshots the maintainer dropped in by hand: raw/screenshots/<submission_id>/*
    for r in reports:
        folder = shots / str(r["submission_id"])
        if folder.exists():
            for p in sorted(folder.iterdir()):
                if p not in r["_shot_files"] and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    r["_shot_files"].append(p)


def run_ocr(reports, log):
    from .ocr import ocr_images
    files = [p for r in reports for p in r.get("_shot_files", [])]
    if not files:
        return
    try:
        res = ocr_images(files, RAW / "ocr_cache.json")
    except Exception as e:
        log.append(f"OCR unavailable: {e}")
        return
    for r in reports:
        r["_ocr"] = "\n\n".join(res[str(p.resolve())]["text"] for p in r.get("_shot_files", []) if res.get(str(p.resolve()), {}).get("text"))


# ---------------- reports ----------------
def build_reports(log, with_screens=True):
    exports = sorted((RAW / "tally_exports").glob("*.csv"))
    reports, seen_ids = [], set()
    for f in exports:
        miss = missing_columns(f)
        if miss:
            log.append(f"{f.name}: columns not found for {miss}")
        for r in read_tally_csv(f):
            if r["submission_id"] in seen_ids:  # same submission in two exports
                continue
            seen_ids.add(r["submission_id"])
            reports.append(r)
    if with_screens:
        fetch_screenshots(reports, log)
        run_ocr(reports, log)

    overrides = _load_overrides()
    subscribers, out, review, dropped = [], [], [], Counter()
    for r in reports:
        key = f"form:{r['submission_id']}"
        ov = overrides.get(key, {})
        if not (r.get("consent") and r.get("age_ok")):
            dropped["no_consent"] += 1
            continue
        if ov.get("exclude"):
            dropped[f"excluded:{ov.get('reason', 'review')}"] += 1
            continue
        if r.get("wants_report_email"):
            subscribers.append(r["wants_report_email"].strip())

        pasted = (r.get("message_text") or "").strip()
        ocr = (r.get("_ocr") or "").strip()
        raw_text = ov.get("message_text") or pasted or ocr
        origin = "reviewed" if ov.get("message_text") else ("pasted" if pasted else ("ocr" if ocr else None))
        text = A.anonymize_text(raw_text)

        sender_raw = r.get("sender") or ""
        sender_phone = (A.extract_phones(sender_raw) or [None])[0]
        if sender_phone:
            sender = f"[PHONE:{sender_phone}]"
        elif r.get("sender_type") == "alphanumeric_name":
            sender = A.anonymize_text(sender_raw)
        else:
            sender = "[REDACTED]" if sender_raw else None

        caller_ids = A.extract_phones(r.get("caller_number") or "")
        phone_ids = list(dict.fromkeys(A.extract_phones(raw_text) + ([sender_phone] if sender_phone else []) + caller_ids))
        rec = {
            "id": _hid("R", r["submission_id"]),
            "record_type": "report",
            "source": "form",
            "submitted_month": _month(r.get("submitted_at")),
            "when": r.get("when"),
            "channel": ov.get("channel", r.get("channel")),
            "scam_types": ov.get("scam_types", r.get("scam_types") or []),
            "message_text": text or None,
            "text_origin": origin,
            "has_screenshot": bool(r.get("screenshots")),
            "sender": sender,
            "sender_type": r.get("sender_type"),
            "sender_phone_id": sender_phone,
            "phone_ids": phone_ids,
            "domains": A.extract_domains(raw_text),
            "caller_claimed": r.get("caller_claimed"),
            "caller_asked": r.get("caller_asked") or [],
            "call_language": r.get("call_language"),
            "call_end": r.get("call_end"),
            "call_description": A.anonymize_text(r.get("call_description")),
            "outcome": r.get("outcome"),
            "amount_lost_fcfa": r.get("amount_lost_fcfa"),
            "payment_rails": r.get("payment_rails") or [],
            "actions_after": r.get("actions_after") or [],
            "region": r.get("region"),
            "extra_notes": A.anonymize_text(r.get("extra_notes")),
            "would_use_tool": r.get("would_use_tool"),
            "message_cluster": _cluster(text),
            "src_channel": r.get("src"),
        }
        out.append(rec)

        reasons = []
        if origin == "ocr":
            reasons.append("ocr_text: check USSD codes (*...#) and numbers against the screenshot")
        if rec["has_screenshot"] and not ov:
            reasons.append("has_screenshot: confirm nothing personal is readable in the text")
        for fld in ("message_text", "call_description", "extra_notes"):
            if A.needs_review(rec[fld]):
                reasons.append(f"possible_name_in_{fld}")
        if not rec["message_text"] and not rec["call_description"] and not rec["extra_notes"]:
            reasons.append("no_text: labels only")
        if reasons and not ov.get("reviewed"):
            review.append({"key": key, "id": rec["id"], "reasons": " | ".join(reasons),
                           "screenshots": ";".join(str(p) for p in r.get("_shot_files", [])),
                           "message_text": rec["message_text"] or "", "raw_pasted": pasted, "ocr": ocr})

    # identical double submissions -> keep the first
    uniq, sig_seen = [], set()
    for rec in out:
        sig = (rec["message_text"], rec["sender"], tuple(rec["scam_types"]), rec["outcome"], rec["region"], rec["when"])
        if rec["message_text"] and sig in sig_seen:
            dropped["duplicate_submission"] += 1
            continue
        sig_seen.add(sig)
        uniq.append(rec)
    return uniq, review, subscribers, dropped, len(reports)


# ---------------- public alerts ----------------
def build_alerts():
    f = RAW / "web" / "curated_public_alerts.jsonl"
    out = []
    if not f.exists():
        return out
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        a = json.loads(line)
        phones = [A.pseudonym(A.normalize_cm(p)) for p in a.get("phones", []) if A.normalize_cm(p)]
        example = a.get("example_message")
        phones = list(dict.fromkeys(phones + A.extract_phones(example or "")))
        out.append({
            "id": "A-" + hashlib.sha1((a["url"] + a["title"]).encode()).hexdigest()[:8],
            "record_type": "public_alert",
            "source": a["src"],
            "source_url": a["url"],
            "date_published": a["date"],
            "title": a["title"],
            "summary": a["summary"],
            "impersonated": a.get("impersonated"),
            "target": a.get("target"),
            "channels": a.get("channels", []),
            "scam_types": a.get("scam_types", []),
            "requested_actions": a.get("requested_actions", []),
            "amount_requested_fcfa": a.get("amount_requested_fcfa"),
            "example_message": A.anonymize_text(example),
            "phone_ids": phones,
            "domains": [A.defang(u) for u in a.get("extra_urls", []) if "gov.cm" not in u],
            "entities": a.get("entities", []),
        })
    return out


# ---------------- export ----------------
def _write(records, fields, base: Path):
    with open(base.with_suffix(".jsonl"), "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps({k: r.get(k) for k in fields}, ensure_ascii=False) + "\n")
    with open(base.with_suffix(".csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow({k: ("|".join(map(str, v)) if isinstance(v, list) else v) for k, v in ((k, r.get(k)) for k in fields)})


def scam_numbers(reports, alerts):
    agg = defaultdict(lambda: {"reports": 0, "alerts": 0, "scam_types": Counter(), "first_seen": None})
    for r in reports:
        for p in r["phone_ids"]:
            a = agg[p]
            a["reports"] += 1
            a["scam_types"].update(r["scam_types"])
            m = r["submitted_month"]
            a["first_seen"] = min(filter(None, [a["first_seen"], m]), default=None)
    for al in alerts:
        for p in al["phone_ids"]:
            a = agg[p]
            a["alerts"] += 1
            a["scam_types"].update(al["scam_types"])
            m = (al["date_published"] or "")[:7] or None
            a["first_seen"] = min(filter(None, [a["first_seen"], m]), default=None)
    rows = []
    for p, a in sorted(agg.items(), key=lambda kv: -(kv[1]["reports"] + kv[1]["alerts"])):
        rows.append({"phone_id": p, "prefix": p.split("-")[0], "times_reported": a["reports"], "times_in_alerts": a["alerts"],
                     "top_scam_types": "|".join(t for t, _ in a["scam_types"].most_common(3)), "first_seen": a["first_seen"]})
    return rows


def stats(reports, alerts, dropped, total_rows):
    def dist(key, recs, many=False):
        c = Counter()
        for r in recs:
            v = r.get(key)
            if many:
                c.update(v or [])
            elif v:
                c[v] += 1
        return dict(c.most_common())
    lost = [r["amount_lost_fcfa"] for r in reports if r.get("amount_lost_fcfa") and r.get("outcome") in ("lost_money", "someone_else_lost")]
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "form_rows_read": total_rows,
        "reports_released": len(reports),
        "public_alerts": len(alerts),
        "dropped": dict(dropped),
        "reports": {
            "scam_types": dist("scam_types", reports, True), "channel": dist("channel", reports),
            "outcome": dist("outcome", reports), "region": dist("region", reports),
            "with_screenshot": sum(r["has_screenshot"] for r in reports),
            "total_lost_fcfa": sum(lost), "reports_with_amount": len(lost),
            "would_use_tool": dist("would_use_tool", reports), "src_channel": dist("src_channel", reports),
        },
        "public_alerts_summary": {
            "sources": dist("source", alerts), "scam_types": dist("scam_types", alerts, True),
            "channels": dist("channels", alerts, True), "targets": dist("target", alerts),
            "years": dict(sorted(Counter(a["date_published"][:4] if a["date_published"] else "undated" for a in alerts).items())),
            "everyday_mobile_money": sum(1 for a in alerts if set(a["scam_types"]) & EVERYDAY_MOMO),
        },
    }


def build(version="dev", with_screens=True):
    log = []
    reports, review, subscribers, dropped, total = build_reports(log, with_screens)
    alerts = build_alerts()
    out = RELEASE / version
    out.mkdir(parents=True, exist_ok=True)
    _write(reports, REPORT_FIELDS, out / "reports")
    _write(alerts, ALERT_FIELDS, out / "public_alerts")
    nums = scam_numbers(reports, alerts)
    with open(out / "scam_numbers.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["phone_id", "prefix", "times_reported", "times_in_alerts", "top_scam_types", "first_seen"])
        w.writeheader()
        w.writerows(nums)
    st = stats(reports, alerts, dropped, total)
    (out / "stats.json").write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

    RAW.mkdir(exist_ok=True)
    with open(RAW / "review_queue.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["key", "id", "reasons", "screenshots", "message_text", "raw_pasted", "ocr"])
        w.writeheader()
        w.writerows(review)
    if subscribers:
        (RAW / "report_subscribers.txt").write_text("\n".join(sorted(set(subscribers))), encoding="utf-8")
    return {"out": str(out), "reports": len(reports), "alerts": len(alerts), "numbers": len(nums),
            "review": len(review), "dropped": dict(dropped), "log": log}
