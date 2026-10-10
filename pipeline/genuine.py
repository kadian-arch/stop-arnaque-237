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

FIELDS = ["id", "label", "operator", "sender_shown", "line_type", "message_kind",
          "message_text", "message_language", "times_seen", "source"]

HEADER = re.compile(r'^\s*From\s*(.*?)\s+on\s+(?:an?\s+)?(.*?)\s*;\s*"?(.*)$', re.I)

KINDS = [  # first match wins
    ("otp_code", r"code\s*:?\s*\[?\w*\]?.*(?:login|connexion)|following code|verification code|\botp\b|your [\w ]{0,20}code\s*(?:is|:)|le num[ée]ro .* pour continuer|confidential code"),
    ("government_notice", r"passport|pré-?enr[oô]lement|pre-enrolment|dgsn|gdns"),
    ("bank_alert", r"\buba\b|\becobank\b|carte .* activ|received cr xaf|mobile banking|(?:d[ée]bit|cr[ée]dit) (?:du|au) cpte"),
    ("security_tip", r"transfer (?:error|mistake)|recover your money|last 5 transactions|fraud|official .* page|crime|protect your identity|reset your momo pin|never ask"),
    ("loan_advance", r"received an advance|received a \w+ loan"),
    ("loan_repayment", r"has been repaid|thank you for the repayment|totally refunded"),
    ("airtime_topup", r"of top-?up"),
    ("agent_withdrawal", r"via agent.*withdrawn|withdrawn .* via agent"),
    ("agent_cash_out", r"cash ?out initiated"),
    ("agent_cash_in", r"cash in of|cashed in"),
    ("money_received", r"you have received \d|received \d[\d ,.]* ?(?:xaf|fcfa) (?:of|from)"),
    ("money_sent", r"you have transferred"),
    ("bill_payment", r"your payment of"),
    ("merchant_debit", r"a transaction of .* by"),
    ("loan_offer", r"borrow|pay ?back later|advance limit|momokash|xtracash|repay after|debt of|on credit"),
    ("service_subscription", r"bibala|learn (?:your language|word by word)|wanda sur|la vid[ée]o|playvod|mtn ?zik|sonnerie|abonnement|desabo|subscription|sauve au|tones?\b"),
    ("agent_info", r"dear agent|commission|cash-?outs?|qr code|registering a customer|activations?|yello pos|sales and performances"),
    ("account_notice", r"current balance:|maintenance|restored|esim|limit has been|compatible|for a more convenient support|customer care hotline|failed|successfully activated|token"),
    ("promo", r"earn \+|bonus|stand a chance|win|gagn|promo|offered to you|free|gratuit|deposit|installments|offer|bundle|surprise|reduce|level up|yamo|zik|data|\d+U"),
]


def _kind(t):
    low = t.lower()
    for k, rx in KINDS:
        if re.search(rx, low):
            return k
    return "other"


# who actually sent it, by the sender name shown on the phone
SENDER_KIND = {
    "uba": "bank", "afriland": "bank", "ecobank": "bank", "sgc": "bank",
    "idcam": "government", "passcam": "government", "dgsn": "government",
    "payoneer": "online_service", "google": "online_service", "zoom": "online_service", "amazon": "online_service",
    "whatsapp": "online_service", "verify": "online_service", "stripelink": "online_service", "youscribe": "online_service",
    "tecno": "partner_brand", "infinix": "partner_brand", "eneoprepaid": "partner_brand",
}


def _operator(t, sender):
    kind = SENDER_KIND.get((sender or "").strip().lower().replace(" ", ""))
    if kind:
        return kind
    s = f"{sender} {t}".lower()
    if "playvod" in s:  # content service billed through the operator
        return "partner_brand"
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


def _network(desc):
    """'a normal consumer sim (MTN)' -> 'mtn': the line the screenshots came from."""
    m = re.search(r"\((mtn|orange|camtel|nexttel)\)", desc or "", re.I)
    return m.group(1).lower() if m else None


def parse(text):
    """-> list of (sender_shown, line_type, raw_message, network_of_the_line)."""
    out, sender, ltype, net = [], None, "unknown", None
    for line in text.splitlines():
        m = HEADER.match(line)
        if m:
            sender = m.group(1).strip() or None
            ltype, net = _line_type(m.group(2)), _network(m.group(2))
            line = m.group(3)
        msg = line.strip().strip('"').strip()
        if len(msg) >= 15:
            out.append((sender, ltype, msg, net))
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
        for sender, ltype, msg, _ in msgs:
            op = _operator(msg, sender or "")
            if op != "unknown":
                by_line.setdefault((sender, ltype), op)
        for sender, ltype, msg, net in msgs:
            text = A.anonymize_text(msg, cue_names=False)
            if text in seen:
                seen[text]["times_seen"] += 1
                continue
            seen[text] = {
                "id": "G-" + hashlib.sha1(text.encode()).hexdigest()[:8],
                "record_type": "genuine_message", "label": "not_scam",
                "operator": _operator(msg, sender or "") if _operator(msg, sender or "") != "unknown" else by_line.get((sender, ltype), net or "unknown"), "sender_shown": sender or "unknown",
                "line_type": ltype, "message_kind": _kind(msg), "message_text": text,
                "message_language": lang.detect(msg), "times_seen": 1, "source": "contributed",
            }
    images = [p for p in folder.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".heic")]
    if images:
        log.append(f"genuine: {len(images)} screenshot(s) in raw/genuine to transcribe into a .txt")
    return cap_templates(list(seen.values()), log)


MAX_PER_TEMPLATE = 3


def template(text):
    """The wording with amounts, dates, ids and masked values blanked out."""
    t = re.sub(r"\[[^\]]+\]", "[x]", text.lower())
    t = re.sub(r"\d[\d\s.,:/\-]*", "#", t)
    return re.sub(r"\s+", " ", t).strip()


def cap_templates(rows, log):
    """Keep at most MAX_PER_TEMPLATE messages per wording; times_seen becomes how often the wording occurred."""
    groups = OrderedDict()
    for r in rows:
        groups.setdefault(template(r["message_text"]), []).append(r)
    kept = []
    for same in groups.values():
        total = sum(r["times_seen"] for r in same)
        for r in same[:MAX_PER_TEMPLATE]:
            r["times_seen"] = total
            kept.append(r)
    if len(kept) < len(rows):
        log.append(f"genuine: {len(rows) - len(kept)} near-duplicate message(s) left out (max {MAX_PER_TEMPLATE} per wording)")
    return kept
