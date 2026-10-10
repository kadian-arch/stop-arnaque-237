"""Controlled vocabularies shared by every source (form reports and public alerts).

Form options are matched on their English part (text before " / "), lower-cased,
so small wording edits in Tally don't break the mapping.
"""

SCAM_TYPES = {
    "wrong_number_reversal": "Money sent 'by mistake', victim asked to send it back",
    "deposit_withdrawal_trap": "Small deposit followed by a withdrawal request the victim approves",
    "fake_prize_promo": "Fake prize, promo, lottery, coupon or giveaway",
    "account_blocked": "'Your account is blocked or suspended'",
    "fake_agent_support": "Fake operator/bank agent or customer care",
    "credential_request": "Asked for PIN, OTP, code, or to dial a code",
    "family_emergency": "Relative or friend 'in an emergency'",
    "hacked_account_money": "Hacked social media account asking contacts for money",
    "fake_job": "Fake job, recruitment or internship",
    "fake_scholarship_visa": "Fake scholarship, visa, DV lottery or travel abroad",
    "fake_concours_admission": "Fake concours, exam results, admission or leaked exams",
    "investment_ponzi_crypto": "Investment, 'double your money', Ponzi, crypto",
    "loan_scam": "Loan offer or loan app",
    "fake_seller_delivery": "Fake seller, online shopping, tickets or delivery",
    "official_impersonation": "Fake government, police, customs, tax or public body",
    "romance": "Romance or relationship scam",
    "threat_extortion": "Threats or blackmail to extort money (fake armed group, intimate images)",
    "sim_swap": "SIM swap / lost control of number",
    "fake_social_profile": "Fake social media profile or page of a public figure or brand",
    "fake_document": "Forged communique, memo or tender circulated online",
    "phishing_link": "Link or site that harvests personal data or logins",
    "advance_fee": "Upfront fee demanded for a service, file, auction or funding",
    "other": "Other",
}

CHANNELS = ["sms", "whatsapp", "phone_call", "social_media", "website_app", "email", "in_person", "other"]

REQUESTED_ACTIONS = ["give_pin_code", "dial_code", "send_money", "send_airtime", "give_id_personal_info",
                     "install_app", "open_link", "pay_fee", "nothing_yet"]

OUTCOMES = ["noticed", "almost", "lost_money", "someone_else_lost", "unknown"]

PAYMENT_RAILS = ["mtn_momo", "orange_money", "bank", "cash", "airtime", "crypto", "other"]

SENDER_TYPES = ["personal_number", "alphanumeric_name", "social_account", "hidden", "unknown", "other"]

LANGUAGES = ["en", "fr", "pidgin", "local", "mixed", "unknown"]

REGIONS = ["adamaoua", "centre", "east", "far_north", "littoral", "north", "north_west", "west",
           "south", "south_west", "outside_cameroon", "undisclosed"]

# ---- form label (English half, lower-case, prefix match) -> code ----

FORM_CHANNEL = {
    "sms": "sms",
    "whatsapp": "whatsapp",
    "phone call": "phone_call",
    "facebook, tiktok": "social_media",
    "website or app": "website_app",
    "email": "email",
    "in person": "in_person",
    "other": "other",
}

FORM_SCAM_TYPE = {
    "money sent \"by mistake\"": "wrong_number_reversal",
    "small deposit, then": "deposit_withdrawal_trap",
    "you \"won\"": "fake_prize_promo",
    "\"your account is blocked": "account_blocked",
    "fake mtn, orange or bank": "fake_agent_support",
    "asked for your pin": "credential_request",
    "family member or friend": "family_emergency",
    "hacked whatsapp": "hacked_account_money",
    "fake job": "fake_job",
    "fake scholarship": "fake_scholarship_visa",
    "fake concours": "fake_concours_admission",
    "investment, \"double": "investment_ponzi_crypto",
    "loan offer": "loan_scam",
    "fake seller": "fake_seller_delivery",
    "fake government": "official_impersonation",
    "romance": "romance",
    "lost control of my number": "sim_swap",
    "other": "other",
}

FORM_SENDER_TYPE = {
    "a normal phone number": "personal_number",
    "a name like": "alphanumeric_name",
    "a whatsapp, facebook": "social_account",
    "hidden or unknown": "hidden",
    "i don't remember": "unknown",
    "other": "other",
}

FORM_CALLER_CLAIM = {
    "mtn or orange staff": "operator_staff",
    "bank staff": "bank_staff",
    "police, gendarmerie": "government_security",
    "a relative or friend": "relative_friend",
    "an employer or recruiter": "employer_recruiter",
    "someone who \"sent money": "wrong_number_sender",
    "other": "other",
}

FORM_REQUESTED = {
    "give my pin": "give_pin_code",
    "dial a code": "dial_code",
    "send money": "send_money",
    "buy or send airtime": "send_airtime",
    "give my id": "give_id_personal_info",
    "install an app": "install_app",
    "open a link": "open_link",
    "nothing yet": "nothing_yet",
}

FORM_CALL_LANGUAGE = {"english": "en", "français": "fr", "pidgin": "pidgin", "another local language": "local"}

FORM_CALL_END = {
    "i hung up": "hung_up",
    "i did what they asked": "complied",
    "they stopped": "they_stopped",
    "it is still going on": "ongoing",
}

FORM_OUTCOME = {
    "no, i noticed": "noticed",
    "almost": "almost",
    "yes": "lost_money",
    "no, but someone": "someone_else_lost",
}

FORM_RAIL = {
    "mtn momo": "mtn_momo",
    "orange money": "orange_money",
    "bank": "bank",
    "cash": "cash",
    "airtime": "airtime",
    "crypto": "crypto",
    "other": "other",
}

FORM_AFTER = {
    "nothing": "nothing",
    "told family": "told_family",
    "reported to mtn or orange": "reported_operator",
    "reported to police": "reported_police",
    "reported to antic": "reported_antic",
    "blocked the number": "blocked_number",
    "got the money back": "recovered_money",
}

FORM_WHEN = {
    "this week": "this_week",
    "this month": "this_month",
    "in the last 6 months": "last_6_months",
    "earlier in 2026": "earlier_2026",
    "2025": "2025",
    "before 2025": "before_2025",
}

FORM_REGION = {
    "adamaoua": "adamaoua",
    "centre": "centre",
    "est": "east",
    "extrême-nord": "far_north",
    "littoral": "littoral",
    "nord-ouest": "north_west",
    "nord": "north",
    "ouest": "west",
    "sud-ouest": "south_west",
    "sud": "south",
    "outside cameroon": "outside_cameroon",
    "prefer not to say": "undisclosed",
}

FORM_WOULD_USE = {"yes": "yes", "maybe": "maybe", "no": "no"}


def english_half(label: str) -> str:
    return label.split(" / ")[0].strip().lower()


def match(label: str, table: dict):
    """Map one form label to a code. Longest key wins, so 'nord-ouest' beats 'nord'."""
    if not label:
        return None
    candidates = [label.strip().lower(), english_half(label)]
    best = None
    for key, code in table.items():
        for c in candidates:
            if c.startswith(key) and (best is None or len(key) > len(best[0])):
                best = (key, code)
    return best[1] if best else None


def match_many(text: str, table: dict) -> list:
    """Multi-select answers arrive as one string. Options can contain commas,
    so find each known option inside the string instead of splitting on ','."""
    if not text:
        return []
    low = text.lower()
    found = []
    for key, code in sorted(table.items(), key=lambda kv: -len(kv[0])):
        if key in low and code not in found:
            found.append(code)
            low = low.replace(key, " ")
    return found
