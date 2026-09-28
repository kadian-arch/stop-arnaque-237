"""Tally CSV export -> normalized report records (still raw, not yet anonymized).

Columns are found by the English start of each question title, so the importer
survives wording tweaks. Multi-choice answers are read in either layout Tally may use:
one column holding all ticked options, or one column per option ("Title (Option)") with true/false.
"""
import csv
import re
from pathlib import Path

from . import taxonomy as T

# key -> (title prefix, kind, mapping table)
QUESTIONS = {
    "age_ok": ("i am 18 or older", "flag", None),
    "consent": ("i agree that my report", "flag", None),
    "channel": ("how did it reach you", "one", T.FORM_CHANNEL),
    "scam_types": ("what was it about", "many", T.FORM_SCAM_TYPE),
    "screenshots": ("upload screenshots", "files", None),
    "message_text": ("or paste the message text", "text", None),
    "sender": ("who sent it", "text", None),
    "sender_type": ("the sender looked like", "one", T.FORM_SENDER_TYPE),
    "caller_claimed": ("who did the caller say", "one", T.FORM_CALLER_CLAIM),
    "caller_asked": ("what did they ask you to do", "many", T.FORM_REQUESTED),
    "call_language": ("language of the call", "one", T.FORM_CALL_LANGUAGE),
    "call_end": ("how did it end", "one", T.FORM_CALL_END),
    "caller_number": ("caller's number", "text", None),
    "call_description": ("describe the call", "text", None),
    "outcome": ("did you lose money", "one", T.FORM_OUTCOME),
    "amount_lost_fcfa": ("how much, in fcfa", "number", None),
    "payment_rails": ("through what", "many", T.FORM_RAIL),
    "actions_after": ("what did you do after", "many", T.FORM_AFTER),
    "when": ("when did it happen", "one", T.FORM_WHEN),
    "region": ("your region", "one", T.FORM_REGION),
    "extra_notes": ("anything else we should know", "text", None),
    "would_use_tool": ("would you use a free tool", "one", T.FORM_WOULD_USE),
    "wants_report_email": ("want our free public report", "text", None),
    "src": ("src", "text", None),
}

TRUE = {"true", "yes", "1", "x", "checked", "oui", "vrai"}


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", (h or "").strip().lower().replace("’", "'"))


def _columns(headers):
    """question key -> list of (header, option-or-None)."""
    cols = {k: [] for k in QUESTIONS}
    for h in headers:
        n = _norm(h)
        for key, (prefix, _, _) in QUESTIONS.items():
            if key == "src":
                if n == "src":
                    cols[key].append((h, None))
                continue
            if n.startswith(prefix):
                m = re.search(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$", h or "")
                opt = m.group(1) if m and len(h) - len(m.group(0)) >= len(prefix) else None
                cols[key].append((h, opt))
                break
    return cols


def _value(row, key, cols):
    prefix, kind, table = QUESTIONS[key]
    found = cols.get(key) or []
    if not found:
        return None
    if kind in ("many", "one") and any(opt for _, opt in found):
        ticked = [opt for h, opt in found if opt and str(row.get(h, "")).strip().lower() in TRUE]
        codes = []
        for opt in ticked:
            c = T.match(opt, table)
            if c and c not in codes:
                codes.append(c)
        if kind == "one":
            return codes[0] if codes else None
        return codes
    cell = str(row.get(found[0][0], "") or "").strip()
    if kind == "flag":
        return cell.lower() in TRUE or (cell != "" and cell.lower() not in {"false", "no", "0"})
    if kind == "one":
        return T.match(cell, table)
    if kind == "many":
        return T.match_many(cell, table)
    if kind == "number":
        d = re.sub(r"[^\d]", "", cell)
        return int(d) if d else None
    if kind == "files":
        return re.findall(r"https?://\S+?(?=,\s*https?://|\s|$|,$)", cell)
    return cell or None


def read_tally_csv(path: Path) -> list:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = _columns(reader.fieldnames or [])
        rows = list(reader)
    out = []
    for row in rows:
        rec = {
            "record_type": "report",
            "source": "form",
            "submission_id": row.get("Submission ID") or row.get("Response ID") or row.get("ID"),
            "submitted_at": row.get("Submitted at") or row.get("Created at") or row.get("Date"),
        }
        for key in QUESTIONS:
            rec[key] = _value(row, key, cols)
        out.append(rec)
    return out


def missing_columns(path: Path) -> list:
    """Questions the importer could not find in this CSV (checked on every run)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        headers = next(csv.reader(f))
    cols = _columns(headers)
    return [k for k, v in cols.items() if not v and k != "src"]
