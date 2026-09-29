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
from . import lang
from . import taxonomy as T
from .ingest_form import read_tally_csv, missing_columns

ROOT = Path(os.environ.get("STOPARNAQUE_ROOT") or Path(__file__).resolve().parent.parent)
RAW = ROOT / "raw"
RELEASE = ROOT / "release"

EVERYDAY_MOMO = {"wrong_number_reversal", "deposit_withdrawal_trap", "account_blocked", "credential_request", "sim_swap"}

REPORT_FIELDS = [
    "id", "record_type", "source", "submitted_month", "when", "channel", "scam_types",
    "message_text", "text_origin", "message_language", "screenshot_text", "has_screenshot", "attachment_kinds", "sender", "sender_type", "sender_phone_id",
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
def fetch_attachments(reports, log):
    """Download every uploaded file into raw/screenshots/<submission>/ (private), whatever its type.
    Files dropped in that folder by hand are picked up too."""
    import requests
    from .attachments import ext_for
    shots = RAW / "screenshots"
    for r in reports:
        r["_files"], r["_failed"] = [], 0
        folder = shots / str(r["submission_id"])
        for i, u in enumerate(r.get("screenshots") or []):
            existing = sorted(folder.glob(f"dl{i + 1}.*")) if folder.exists() else []
            if existing:
                r["_files"].append(existing[0])
                continue
            try:
                resp = requests.get(u, timeout=60, stream=True)
                resp.raise_for_status()
                size = int(resp.headers.get("content-length") or 0)
                if size > 60_000_000:
                    raise ValueError(f"file too large ({size} bytes)")
                dest = folder / f"dl{i + 1}{ext_for(u, resp.headers.get('content-type'))}"
                folder.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(resp.content)
                r["_files"].append(dest)
            except Exception as e:  # keep going; the review queue lists it
                r["_failed"] += 1
                log.append(f"download failed for {r['submission_id']} file {i + 1}: {e}")
        if folder.exists():
            for p in sorted(folder.iterdir()):
                if p.is_file() and p not in r["_files"]:
                    r["_files"].append(p)


def read_attachments(reports, log):
    """OCR images and scanned PDFs, extract text from text PDFs; audio/video are only flagged."""
    from .attachments import kind, ocr_ready, pdf_text
    from .ocr import ocr_images
    plan = {}
    for r in reports:
        r["_kinds"] = [kind(p) for p in r.get("_files", [])]
        r["_pdf_text"] = "\n\n".join(t for t in (pdf_text(p) for p in r["_files"] if kind(p) == "pdf") if t)
        for p in r["_files"]:
            plan[p] = ocr_ready(p, RAW / "ocr_work" / str(r["submission_id"]))
    images = [q for qs in plan.values() for q in qs]
    res = {}
    if images:
        try:
            res = ocr_images(images, RAW / "ocr_cache.json")
        except Exception as e:
            log.append(f"OCR unavailable: {e}")
    for r in reports:
        parts = []
        for p in r["_files"]:
            texts = [res.get(str(Path(q).resolve()), {}).get("text", "") for q in plan.get(p, [])]
            joined = "\n".join(t for t in texts if t)
            if joined:
                parts.append(joined)
        if r["_pdf_text"]:
            parts.append(r["_pdf_text"])
        r["_ocr"] = "\n\n".join(parts)
        r["_ocr_failed"] = [str(p) for p in r["_files"] if plan.get(p) and not any(
            res.get(str(Path(q).resolve()), {}).get("text") for q in plan[p])]


# ---------------- reports ----------------
def build_reports(log, with_screens=True):
    folder = RAW / "tally_exports"
    exports = sorted(list(folder.glob("*.csv")) + list(folder.glob("*.xlsx"))) if folder.exists() else []
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
        fetch_attachments(reports, log)
        read_attachments(reports, log)

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
        email = (r.get("wants_report_email") or "").strip()
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            subscribers.append(email.lower())

        pasted = (r.get("message_text") or "").strip()
        ocr = (r.get("_ocr") or "").strip()
        raw_text = ov.get("message_text") or pasted or ocr
        origin = "reviewed" if ov.get("message_text") else ("pasted" if pasted else ("screenshot" if ocr else None))
        text = A.anonymize_text(raw_text)
        shot_text = A.anonymize_text(ov.get("screenshot_text") or ocr) or None

        sender_raw = (r.get("sender") or "").strip()
        sender_phone = (A.extract_phones(sender_raw) or [None])[0]
        stype = r.get("sender_type")
        if not stype and sender_phone:
            stype = "personal_number"
        if sender_phone:
            sender = f"[PHONE:{sender_phone}]"
        elif stype == "alphanumeric_name" or re.fullmatch(r"(?i)(mobile ?money|momo|orange ?money|mtn\w*|orange\w*|om)", sender_raw):
            sender = A.anonymize_text(sender_raw)
        else:
            sender = "[REDACTED]" if sender_raw else None

        caller_ids = A.extract_phones(r.get("caller_number") or "")
        all_text = " ".join(filter(None, [raw_text, ocr, r.get("call_description"), r.get("extra_notes")]))
        phone_ids = list(dict.fromkeys(A.extract_phones(all_text) + ([sender_phone] if sender_phone else []) + caller_ids))
        kinds = r.get("_kinds") or []
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
            "message_language": ov.get("message_language") or lang.detect(raw_text),
            "screenshot_text": shot_text if shot_text != text else None,
            "has_screenshot": bool(r.get("screenshots") or r.get("_files")),
            "attachment_kinds": sorted(set(kinds)) if kinds else ([] if not r.get("screenshots") else ["unknown"]),
            "sender": sender,
            "sender_type": stype,
            "sender_phone_id": sender_phone,
            "phone_ids": phone_ids,
            "domains": A.extract_domains(all_text),
            "caller_claimed": r.get("caller_claimed"),
            "caller_asked": r.get("caller_asked") or [],
            "call_language": r.get("call_language"),
            "call_end": r.get("call_end"),
            "call_description": A.anonymize_text(r.get("call_description")),
            "outcome": r.get("outcome"),
            "amount_lost_fcfa": r.get("amount_lost_fcfa") if r.get("outcome") in ("lost_money", "someone_else_lost", None) else None,
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
        if origin == "screenshot":
            reasons.append("screenshot_text: check it word for word against the image, including USSD codes and numbers")
        if rec["has_screenshot"] and not ov:
            reasons.append("attachments: confirm nothing personal is readable and the labels match")
        for k in ("audio", "video", "other"):
            if k in kinds:
                reasons.append(f"{k}_attachment: open it by hand and transcribe what matters")
        if r.get("_failed"):
            reasons.append(f"download_failed: {r['_failed']} file(s), download from Tally into raw/screenshots/{r['submission_id']}/")
        if r.get("_ocr_failed"):
            reasons.append("ocr_empty: no text read from some images (HEIC/blurry?), read them by hand")
        for fld in ("message_text", "screenshot_text", "call_description", "extra_notes"):
            if A.needs_review(rec[fld]):
                reasons.append(f"possible_name_in_{fld}")
        if not any(rec[f] for f in ("message_text", "screenshot_text", "call_description", "extra_notes")):
            reasons.append("no_text: labels only" + ("" if rec["has_screenshot"] else ", no attachment either"))
        if not rec["scam_types"] or rec["scam_types"] == ["other"]:
            reasons.append("scam_type_other: set the real type from the text")
        if len(rec["scam_types"]) >= 4:
            reasons.append("many_types: maybe several scams in one report, split with overrides if so")
        if rec["amount_lost_fcfa"] and rec["amount_lost_fcfa"] > 50_000_000:
            reasons.append("amount_check: very large amount, typo?")
        if re.search(r"(?i)\b(test|testing|essai|lorem|ipsum|asdf|qwerty)\b", " ".join(filter(None, [pasted, r.get("extra_notes")]))) and len(pasted) < 40:
            reasons.append("maybe_test_submission")
        elif re.search(r"(?i)^\W*(n/?a|none|nothing|rien|aucun|pas encore|no message|i don'?t have\b.*|je n'?ai pas\b.*)\W*$", pasted or ""):
            reasons.append("placeholder_text: the paste box says there is no message, blank it with an override")
        if reasons and not ov.get("reviewed"):
            review.append({"key": key, "id": rec["id"], "reasons": " | ".join(reasons),
                           "files": ";".join(str(p) for p in r.get("_files", [])),
                           "message_text": rec["message_text"] or "", "raw_pasted": pasted, "ocr": ocr})

    # identical double submissions -> keep the first
    uniq, sig_seen = [], set()
    for rec in out:
        sig = (rec["message_text"], rec["screenshot_text"], rec["sender"], tuple(rec["scam_types"]), rec["outcome"],
               rec["region"], rec["when"], rec["channel"])
        if (rec["message_text"] or rec["screenshot_text"]) and sig in sig_seen:
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


LEAKS = {
    "phone": re.compile(r"(?<![\d:\-])(?!6\d\d-[0-9a-f]{6}(?![0-9a-f]))(?:\+|00)?(?:237\+?[ .\-]?)?6[5-9](?:[ .\-]?\d){7}(?!\d)"),
    "email": re.compile(r"(?<![\w.+\-\[])[\w.+\-]+@[\w\-]+\.[a-z]{2,}", re.I),
    "private_file": re.compile(r"storage\.tally\.so|accessToken=", re.I),
}


def leak_scan(out: Path) -> list:
    """Last check on the written release: any raw mobile number, email or private
    upload link left over is a bug in anonymization, so the build fails."""
    hits = []
    for f in sorted(out.iterdir()):
        if f.suffix not in (".jsonl", ".csv", ".json"):
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1):
            for kind, rx in LEAKS.items():
                for m in rx.finditer(line):
                    hits.append(f"{f.name}:{n} {kind}: {m.group(0)}")
    return hits


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
    leaks = leak_scan(out)
    if leaks:
        raise RuntimeError("possible personal data in release, nothing may be published:\n" + "\n".join(leaks[:20]))

    RAW.mkdir(exist_ok=True)
    with open(RAW / "review_queue.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["key", "id", "reasons", "files", "message_text", "raw_pasted", "ocr"])
        w.writeheader()
        w.writerows(review)
    if subscribers:
        (RAW / "report_subscribers.txt").write_text("\n".join(sorted(set(subscribers))), encoding="utf-8")
    return {"out": str(out), "reports": len(reports), "alerts": len(alerts), "numbers": len(nums),
            "review": len(review), "dropped": dict(dropped), "log": log}
