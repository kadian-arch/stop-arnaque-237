"""Anonymization applied to every text field before anything is stored in a release.

Phone numbers  -> [PHONE:676-3fa91c]  keeps the 3-digit operator prefix and a keyed code.
                  Same number, same code (so repeat scammers link up), but the code
                  can't be reversed: it's an HMAC with a private key, not a plain hash.
                  A plain hash of a 9-digit number is brute-forced in seconds.
Transaction IDs-> [TXN_ID]
Emails         -> [EMAIL@domain]      keeps the domain (gmail.com vs gov.cm is signal)
URLs           -> hxxp://domain[.]tld/...  defanged so nobody clicks a live scam link
Personal names -> [NAME]              the rules below, plus manual review before release
Amounts        -> kept as is (decision 2026-09-26)
"""
import hashlib
import os
import hmac
import re
import secrets
from pathlib import Path

KEY_FILE = Path(__file__).with_name(".pseudonym_key")


def load_key() -> bytes:
    if not KEY_FILE.exists():
        # a new key would give every number a different code, so only tests may create one
        if not os.environ.get("STOPARNAQUE_ALLOW_NEW_KEY"):
            raise SystemExit(f"Missing {KEY_FILE.name}: restore it from the password manager (never create a new one).")
        KEY_FILE.write_text(secrets.token_hex(32))
    return bytes.fromhex(KEY_FILE.read_text().strip())


_KEY = None


def _key():
    global _KEY
    if _KEY is None:
        _KEY = load_key()
    return _KEY


# ---------- phones ----------
# Cameroon: 9 digits starting 6 (mobile) or 2 (fixed), optional +237 / 00237 / 237,
# separators: space . - between groups.
_SEP = r"[ .\-]?"
CM_PHONE = re.compile(  # not followed by a currency: "200 000 000 FCFA" is an amount
    r"(?<![\d\w+])(?:(?:\((?:\+|00)?237\)|(?:\+|00)?237)\+?" + _SEP + r")?([26](?:" + _SEP + r"\d){8})(?!\d)(?!\s*(?:f?cfa|xaf|francs?|frs)\b)",
    re.I,
)
# other international numbers (+234..., +33..., etc.)
INTL_PHONE = re.compile(r"(?<![\d\w])\+(?!237)\d{1,3}(?:[ .\-]?\(?\d{2,4}\)?){2,5}(?!\d)")
# North American format without the +1: "(619) 705-8649", "619-705-8649"
NANP_PHONE = re.compile(r"(?<![\d\w])\(\d{3}\)[ .\-]?\d{3}[ .\-]\d{4}(?!\d)|(?<![\d\w\-])\d{3}-\d{3}-\d{4}(?![\d\-])")


def pseudonym(digits: str) -> str:
    code = hmac.new(_key(), digits.encode(), hashlib.sha256).hexdigest()[:6]
    return f"{digits[:3]}-{code}"


def normalize_cm(raw: str):
    d = re.sub(r"\D", "", raw)
    if d.startswith("00237"):
        d = d[5:]
    elif d.startswith("237") and len(d) == 12:
        d = d[3:]
    return d if len(d) == 9 and d[0] in "26" else None


# Public operator numbers printed in their own messages and campaigns. Kept as they are:
# telling the real MTN/Orange numbers from look-alikes is the point.
OFFICIAL = {
    "650528787",                            # MTN MoMo WhatsApp
    "698717171",                            # Orange Money anti-scam WhatsApp
    "690009500", "690009300", "690009200",  # Orange Money service lines
    "670362187",                            # MTN MoMo POS chatbot (wa.me link in MTN's own SMS)
}


def phone_token(raw: str) -> str:
    d = normalize_cm(raw)
    if d in OFFICIAL:
        return raw
    if d:
        return f"[PHONE:{pseudonym(d)}]"
    d = re.sub(r"\D", "", raw)
    return f"[PHONE:intl-{hmac.new(_key(), d.encode(), hashlib.sha256).hexdigest()[:6]}]"


def extract_phones(text: str) -> list:
    """Pseudonyms of every phone in the text (for the sender/linkage columns)."""
    out = []
    for m in CM_PHONE.finditer(text or ""):
        d = normalize_cm(m.group(0))
        if d:
            out.append(pseudonym(d))
    return out


# ---------- ids, emails, urls ----------
TXN = re.compile(r"(?<![\d])\d{10,19}(?![\d])")
TXN_LABELED = re.compile(r"(?i)(transaction\s*(?:id|ref)[^:]*:\s*|txn\s*id\s*:\s*|r[ée]f(?:[ée]rence)?\s*:\s*)([A-Z0-9_\-]{6,})")
ACCOUNT = re.compile(r"(?i)((?:mobile money account|account(?: number| no\.?)?|compte)\s*:?\s*(?:FRI:)?)\d{6,12}")
# Names of people who contributed their own messages (they appear in "Congratulations <NAME>").
# Private list, one name per line, in raw/names_to_mask.txt; never committed.
_NAMES_FILE = Path(__file__).resolve().parent.parent / "raw" / "names_to_mask.txt"
EXTRA_NAMES = sorted({w.strip() for w in _NAMES_FILE.read_text(encoding="utf-8").splitlines() if len(w.strip()) >= 3},
                     key=len, reverse=True) if _NAMES_FILE.exists() else []

# one-time codes: the value must contain a digit, so ordinary words are never touched
OTP = re.compile(r"(?i)((?:following code|(?:your\s+)?(?:[\w.]+\s+){0,3}code\s+is|verification code(?:\s+is)?|code de (?:confirmation|v[ée]rification)|votre code est|OTP(?:\s+for\s+[\w ]{2,30})?\s+is|with code|le num[ée]ro|enter the number|(?:your\s+)?[\w.]+\s+code\s*:)\s*:?\s*)(?=[\w•.\-]*\d)[A-Za-z0-9][\w•.\-]{2,11}\b")
# the code written before the phrase: "G-597W is your Google verification code", "1234 is your Link verification code"
OTP_BEFORE = re.compile(r"(?i)(?<![\w\[])(?=[\w•*.\-]*\d)[\w•*.\-]{3,12}(?=\s*(?:'?s|is)\s+your\s+[\w ]{0,25}code\b)")
# credentials sent by subscription services: "LOGIN : 06... PASS : 863353"
CRED = re.compile(r"(?i)\b((?:PASS(?:WORD)?|mot de passe|LOGIN|identifiant|username)\s*:\s*|(?:gives? access to|donne acc[eè]s [àa])\s+(?:your|votre)\s+[\w ]{0,20}(?:account|compte)\s*:?\s*)\S{3,60}")
# identity documents and applications: "Passport #AB502...", "application #PO-2026..."
DOC_ID = re.compile(r"(?i)\b((?:passport|passeport|application|demande|carte|card|CNI|r[ée]c[ée]piss[ée])\s*(?:n[o°]\.?|#)\s*)[A-Z0-9][\w•\-/]{3,}")
# safety net: a number cut off by the screen edge, or any other 8-9 digit number that is not an amount
LONGNUM = re.compile(r"(?<![\w\[:\-])\(?\+?\d{6,}(?:\.\.\.|…)|(?<![\w\[:\-.,])\d{8,9}(?![\d.,])(?!\s*(?:f?cfa|xaf|francs?|frs)\b)", re.I)
EMAIL = re.compile(r"(?i)\b[\w.+\-]+@([\w\-]+(?:\.[\w\-]+)+)\b")
URL = re.compile(r"(?i)(?<![@\w.\-])((?:https?://|www\.)[^\s<>\"')\]]+|(?:[a-z0-9\-]+\.)+(?:com|net|org|cm|info|xyz|online|site|top|link|me|ly|io|co|app|club|shop)(?:/[^\s<>\"')\]]*)?)")


def defang(url: str) -> str:
    u = re.sub(r"(?i)^http", "hxxp", url)
    if "://" in u:
        scheme, rest = u.split("://", 1)
    else:
        scheme, rest = None, u
    host, _, path = rest.partition("/")
    out = host.replace(".", "[.]") + (f"/{path}" if path else "")
    return f"{scheme}://{out}" if scheme else out

def extract_domains(text: str) -> list:
    out = []
    for m in URL.finditer(text or ""):
        u = m.group(1)
        host = re.sub(r"(?i)^(https?://)?(www\.)?", "", u).split("/")[0].lower()
        if host and host not in out:
            out.append(host)
    return out


# ---------- names ----------
# Operator messages print the counterparty as "FULL NAME (2376XXXXXXXX)".
# Any case and single letters too: "MOKETSI FELICITAS N A (2376...)", "Abel Ndzi Mih (2376...)".
NAME_BEFORE_PHONE = re.compile(r"\b([A-ZÀ-Ý][A-Za-zÀ-ÿ'\-]*(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'\-]*){0,5})\s*(?=\(\s*(?:\+?237)?\s*[26]\d)")
# ...and the name repeated after the number: "(237650320932 MAJOLIE NKININGI TANGWA)"
NAME_IN_PARENS = re.compile(r"(\(\s*\+?237\s*[26]\d{8})\s+[A-Za-zÀ-ÿ][^()\n]*\)")
# Operator messages: "of|to|from|by|via agent: <anything> (2376...)". The whole counterparty goes,
# because agents print shop and business names that point to the person running them.
COUNTERPARTY = re.compile(r"\b((?:of|to|from|by|agent:|de|à|a|par|agent\s*:))\s+(?!\[)((?:(?!\b(?:of|to|from|by|de|à|par)\s)[^()\[\]]){2,140}?)\s*(?=\(\s*\+?237\s*[26]\d)")
# "You Stephene Entum Tibung (2376...) have via agent"
NAME_AFTER_YOU = re.compile(r"\b(You)\s+(?:[A-ZÀ-Ý][A-Za-zÀ-ÿ'\-]*\s+){1,5}(?=\(\s*\+?237)")
NAME_AFTER_CUE = re.compile(
    r"((?i:\b(?:from|to|by|at|de|à|par|chez|mr\.?|mrs\.?|mme\.?|m\.|dr\.?|madame|monsieur|name is|je m'appelle|my name is|i am|je suis))\s+)"
    r"((?:[A-ZÀ-Ý][a-zà-ÿ'\-]+|[A-ZÀ-Ý]{2,}[A-ZÀ-Ý'\-]*)(?:\s+(?:[A-ZÀ-Ý][a-zà-ÿ'\-]+|[A-ZÀ-Ý]{2,}[A-ZÀ-Ý'\-]*)){1,5})"
)
GREETING_NAME = re.compile(r"\b((?:Congratulations|Congrats|Dear|F[ée]licitations|Cher|Ch[èe]re|Hello|Bonjour|Hi)\s+)([A-ZÀ-Ý]{2,}(?:\s+[A-ZÀ-Ý]{2,}){0,3})(?![a-zà-ÿ])")
LEADING_NAME = re.compile(r"^([A-ZÀ-Ý]{2,}(?:\s+[A-ZÀ-Ý]{2,}){1,3})(?=\s*,)")
# Words that look like names but are organisations, places or product names we keep.
KEEP = {
    "MTN", "ORANGE", "MOMO", "MOBILE", "MONEY", "CAMEROON", "CAMEROUN", "XAF", "FCFA", "CFA", "MTNC",
    "BUNDLES_FORFAITS", "CAMTEL", "NEXTTEL", "BEAC", "CNPS", "ANTIC", "MINFI", "MINFOPRA", "MINPOSTEL",
    "DGSN", "FNE", "CCAA", "WHATSAPP", "FACEBOOK", "TIKTOK", "GOOGLE", "PIN", "OTP", "SMS", "USSD",
    "BONUS", "QR", "API", "ID", "CNI", "BEPC", "BAC", "GCE", "OK", "NEW", "APP", "OM", "EXPRESS", "UNION",
    "YAOUNDE", "YAOUNDÉ", "DOUALA", "BUEA", "BAMENDA", "LIMBE", "GAROUA", "MAROUA", "BAFOUSSAM",
    "NGAOUNDERE", "NGAOUNDÉRÉ", "BERTOUA", "EBOLOWA", "KRIBI", "KUMBA", "TIKO",
    # merchants seen in genuine operator messages (businesses, not people)
    "ENNOVATIVE", "GAMING", "LEEDTECH", "LTD", "BETPAWA",
    # words operators put in capitals after a greeting
    "CUSTOMER", "CLIENT", "AGENT", "ABONNE", "ABONNÉ", "SUBSCRIBER", "PARTNER", "ALL", "TOUS",
    # banks and bank-alert wording
    "ECOBANK", "UBA", "AFRILAND", "BICEC", "SGC", "SCB", "CCA", "BANK", "BANQUE",
    "PACKAGE", "COMPTE", "EPARGNE", "ÉPARGNE", "FRAIS",
    # fake organisation names used as senders in lures (a signal, not a person)
    "AFRICA", "AFRIQUE", "DEVELOPMENT", "FOUNDATION", "FONDATION", "FUND", "FUNDS", "GRANT", "PROGRAM", "PROGRAMME",
}


def _is_kept(phrase: str) -> bool:
    words = [w.strip("'-").upper() for w in phrase.split()]
    return all(w in KEEP for w in words) or any(w in KEEP for w in words[:1]) and len(words) <= 2


def scrub_names(text: str, cue_names: bool = True) -> str:
    def before_phone(m):
        return m.group(0) if _is_kept(m.group(1)) else "[NAME] "
    text = NAME_IN_PARENS.sub(lambda m: m.group(1) + " [NAME])", text)
    text = COUNTERPARTY.sub(lambda m: m.group(0) if _is_kept(m.group(2)) else f"{m.group(1)} [NAME] ", text)
    text = NAME_AFTER_YOU.sub(lambda m: m.group(1) + " [NAME] ", text)
    text = NAME_BEFORE_PHONE.sub(before_phone, text)
    # operators greet people by name in capitals: "Congratulations JOHN DOE Your...", "JOHN DOE, We have a surprise"
    text = GREETING_NAME.sub(lambda m: m.group(0) if _is_kept(m.group(2)) else m.group(1) + "[NAME]", text)
    text = LEADING_NAME.sub(lambda m: m.group(0) if _is_kept(m.group(1)) else "[NAME]", text)

    def after_cue(m):
        return m.group(0) if _is_kept(m.group(2)) else m.group(1) + "[NAME]"
    return NAME_AFTER_CUE.sub(after_cue, text) if cue_names else text


# ---------- main entry ----------
def anonymize_text(text, cue_names: bool = True):
    """cue_names=False skips the "from/to/at <Capitalised Words>" guess. Official operator messages
    only name people in fixed formats (before a number, after "Congratulations"), and the guess
    there hits product names like "Yamo Class"."""
    if not text:
        return text
    t = str(text)
    t = TXN_LABELED.sub(lambda m: m.group(1) + "[TXN_ID]", t)
    t = scrub_names(t, cue_names)      # before phones: the name cue uses the phone as anchor
    t = INTL_PHONE.sub(lambda m: phone_token(m.group(0)), t)
    t = NANP_PHONE.sub(lambda m: phone_token("+1" + m.group(0)), t)
    t = CM_PHONE.sub(lambda m: phone_token(m.group(0)), t)
    t = TXN.sub("[TXN_ID]", t)
    t = ACCOUNT.sub(lambda m: m.group(1) + "[ACCOUNT]", t)
    t = OTP.sub(lambda m: m.group(1) + "[CODE]", t)
    t = OTP_BEFORE.sub("[CODE]", t)
    t = CRED.sub(lambda m: m.group(1) + "[CREDENTIAL]", t)
    t = DOC_ID.sub(lambda m: m.group(1) + "[ID]", t)
    for name in EXTRA_NAMES:
        t = re.sub(r"(?i)\b" + re.escape(name) + r"\b", "[NAME]", t)
    t = LONGNUM.sub("[NUMBER]", t)
    t = EMAIL.sub(lambda m: f"[EMAIL@{m.group(1).lower()}]", t)
    t = URL.sub(lambda m: defang(m.group(1)), t)
    return t


LEFTOVER = re.compile(r"\b([A-ZÀ-Ý][a-zà-ÿ]{2,}|[A-ZÀ-Ý]{3,})\s+([A-ZÀ-Ý][a-zà-ÿ]{2,}|[A-ZÀ-Ý]{3,})\b")

COMMON = set("""
your you the this that new cash out in with from for and message money mobile account transaction
financial external fee fees balance amount completed successfully received sent send transfer
withdrawal deposit code app download switch today earn faster safer bonus make double commission
dear customer customers congratulations winner won win promo prize lottery please call urgent
bonjour cher chère client clients votre vous compte argent transfert retrait dépôt code solde
félicitations gagné gagnant promo tirage sort appelez urgent merci pardon numéro erreur
mtn orange momo camtel nexttel cameroun cameroon yaounde douala buea bamenda
the of a an to is are was be not no yes ok hi hello good morning evening sir madam mama papa
""".split())


def vocab_from(texts) -> set:
    """Words seen in lower case anywhere in the corpus: capitalised copies of them
    are ordinary words at a sentence start, not names."""
    v = set()
    for t in texts:
        v.update(w for w in re.findall(r"\b[a-zà-ÿ]{3,}\b", t or ""))
    return v


def needs_review(text, vocab=frozenset()) -> bool:
    """True when a capitalised word pair survives that isn't made of known words:
    a possible name the rules missed. Flagged records are checked by hand."""
    if not text:
        return False
    for m in LEFTOVER.finditer(text):
        words = [m.group(1), m.group(2)]
        if _is_kept(" ".join(words)):
            continue
        unknown = [w for w in words if w.lower() not in COMMON and w.lower() not in vocab]
        if len(unknown) == 2:
            return True
    return False