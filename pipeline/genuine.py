"""Genuine operator messages (not scams), contributed by people who forwarded their own SMS.

Input: raw/genuine/*.txt, one message per line, grouped under header lines such as
    From Mobile Money on a normal consumer sim; "first message
    From MobileMoney on a merchant SIM/POS; "...
The header gives the sender name shown on the phone and the kind of line.
Screenshots under raw/genuine/ are listed for hand transcription (they go in a .txt too).

Names, numbers, account numbers, transaction ids and codes are removed by anonymize.
Amounts and balances are kept: they carry no identity once the rest is gone.
"""
import hashlib
import re
from collections import OrderedDict
from pathlib import Path

from . import anonymize as A
from . import lang

FIELDS = ["id", "record_type", "label", "operator", "sender_shown", "line_type", "message_kind",
          "message_text", "message_language", "times_seen", "source"]

HEADER = re.compile(r'^\s*From\s*(.*?)\s+on\s+(?:an?\s+)?(.*?)\s*;\s*"?(.*)$', re.I)

KINDS = [  # first match wins
    ("otp_code", r"code\s*:?\s*\[?\w*\]?.*(?:login|connexion)|following code"),
    ("loan_advance", r"received an advance"),
    ("loan_repayment", r"has been repaid"),
    ("agent_withdrawal", r"via agent.*withdrawn|withdrawn .* via agent"),
    ("agent_cash_out", r"cash ?out initiated"),
    ("agent_cash_in", r"cash in of|cashed in"),
    ("money_received", r"you have received \d|received \d[\d ,.]* ?(?:xaf|fcfa) (?:of|from)"),
    ("money_sent", r"you have transferred"),
    ("bill_payment", r"your payment of"),
    ("merchant_debit", r"a transaction of .* by"),
    ("promo", r"earn \+|bonus|stand a chance|win|gagn|promo"),
]


def _kind(t):
    low = t.lower()
    for k, rx in KINDS:
        if re.search(rx, low):
            return k
    return "other"


def _operator(t, sender):
    s = f"{sender} {t}".lower()
    if re.search(r"orange|\bom\b|#150", s):
        return "orange"
    if re.search(r"mtn|momo|mobile ?money|y'ello|\*126", s):
        return "mtn"
    return "unknown"


def _line_type(desc):
    d = (desc or "").lower()
    if re.search(r"merchant|pos|agent", d):
        return "merchant_agent"
    if re.search(r"consumer|personal|normal", d):
        return "consumer"
    return "unknown"


def parse(text):
    """-> list of (sender_shown, line_type, raw_message)."""
    out, sender, ltype = [], None, "unknown"
    for line in text.splitlines():
        m = HEADER.match(line)
        if m:
            sender = m.group(1).strip() or None
            ltype = _line_type(m.group(2))
            line = m.group(3)
        msg = line.strip().strip('"').strip()
        if len(msg) >= 15:
            out.append((sender, ltype, msg))
    return out


def build_genuine(raw: Path, log):
    folder = raw / "genuine"
    if not folder.exists():
        return []
    seen = OrderedDict()
    for f in sorted(folder.rglob("*.txt")):
        msgs = parse(f.read_text(encoding="utf-8", errors="replace"))
        # one header covers one phone line, so a line whose other messages are clearly MTN
        # (or Orange) is that operator throughout, even for messages that never name it
        by_line = {}
        for sender, ltype, msg in msgs:
            op = _operator(msg, sender or "")
            if op != "unknown":
                by_line.setdefault((sender, ltype), op)
        for sender, ltype, msg in msgs:
            text = A.anonymize_text(msg)
            if text in seen:
                seen[text]["times_seen"] += 1
                continue
            seen[text] = {
                "id": "G-" + hashlib.sha1(text.encode()).hexdigest()[:8],
                "record_type": "genuine_message", "label": "not_scam",
                "operator": by_line.get((sender, ltype), "unknown"), "sender_shown": sender or "unknown",
                "line_type": ltype, "message_kind": _kind(msg), "message_text": text,
                "message_language": lang.detect(msg), "times_seen": 1, "source": "contributed",
            }
    images = [p for p in folder.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".heic")]
    if images:
        log.append(f"genuine: {len(images)} screenshot(s) in raw/genuine to transcribe into a .txt")
    return list(seen.values())
