"""What every released field means, which values it may take, and the checks run before release.

The same descriptions feed the data dictionary sheet of the Excel workbook, so the
documentation and the data cannot drift apart.
"""
from . import taxonomy as T

GENUINE_KINDS = ["money_received", "money_sent", "agent_cash_in", "agent_cash_out", "agent_withdrawal", "loan_offer", "agent_info",
                 "service_subscription", "account_notice", "security_tip", "bank_alert", "government_notice",
                 "merchant_debit", "bill_payment", "loan_advance", "loan_repayment", "airtime_topup", "otp_code", "promo", "other"]

V = {  # allowed values (lists may be empty; None is always allowed)
    "channel": T.CHANNELS, "channels": T.CHANNELS, "scam_types": list(T.SCAM_TYPES),
    "message_language": T.LANGUAGES, "call_language": T.LANGUAGES, "sender_type": T.SENDER_TYPES,
    "caller_claimed": sorted(set(T.FORM_CALLER_CLAIM.values())), "caller_asked": T.REQUESTED_ACTIONS,
    "requested_actions": T.REQUESTED_ACTIONS, "call_end": sorted(set(T.FORM_CALL_END.values())),
    "outcome": T.OUTCOMES, "payment_rails": T.PAYMENT_RAILS, "actions_after": sorted(set(T.FORM_AFTER.values())),
    "region": T.REGIONS, "when": sorted(set(T.FORM_WHEN.values())), "would_use_tool": ["yes", "maybe", "no"],
    "text_origin": ["pasted", "screenshot", "reviewed", "retold"], "message_kind": GENUINE_KINDS,
    "operator": ["mtn", "orange", "camtel", "nexttel", "bank", "government", "online_service", "partner_brand", "unknown"],
    "line_type": ["consumer", "merchant_agent", "unknown"], "label": ["scam", "not_scam"],
    "text_type": ["verbatim", "retold"], "split": ["train", "test"],
    "origin": ["report", "public_alert", "social_post", "contributed"],
}

DOC = {
    "messages": {
        "id": "Id of the row; the same id appears in the detail table it comes from (R- reports, A- public alerts, G- genuine messages).",
        "text": "The message, anonymized. Scam messages as received or as the person retold them; genuine messages as received.",
        "label": "scam or not_scam.",
        "scam_types": "Kind(s) of scam (codes in TAXONOMY.md). Empty for not_scam.",
        "multi_scam": "True when the person ticked 4 or more kinds, so the labels describe their experience rather than this one message.",
        "language": "Language of the text: en, fr, pidgin, mixed.",
        "channel": "How it arrived: sms, whatsapp, phone_call, social_media...",
        "text_type": "verbatim: the message itself. retold: the person's own account of a call or chat, often quoting the scammer.",
        "origin": "report (sent to us by the person), public_alert (fact-checkers, institutions, news), social_post (public Facebook/Instagram post), contributed (genuine message shared by its receiver).",
        "split": "Suggested train/test split (80/20). Messages with the same wording are always in the same split, so a model is never tested on a copy of what it trained on.",
    },
    "reports": {
        "id": "Stable id of the report (R-...).",
        "record_type": "Always 'report'.",
        "source": "Where it came from: 'form' (the public form).",
        "submitted_month": "Month the report was sent (YYYY-MM). Exact dates are not released.",
        "when": "When the scam happened, as the person chose it (this_week, this_month, last_6_months, earlier_2026, 2025, before_2025).",
        "channel": "How the scam reached the person.",
        "scam_types": "Kind(s) of scam, codes in TAXONOMY.md. Ticked by the person, corrected during review where the text showed otherwise.",
        "multi_scam": "True when 4 or more types were ticked: the person listed several scams they have met, not one incident.",
        "message_text": "The scam message itself, anonymized. Empty when the person no longer had it.",
        "text_origin": "Where message_text comes from: pasted by the person, read from a screenshot, transcribed by hand ('reviewed'), or the person's own retelling of a call or chat, often in the scammer's words ('retold').",
        "message_language": "Language of the message: en, fr, pidgin, mixed, unknown.",
        "screenshot_text": "Other text read from uploaded screenshots (for example payment receipts), anonymized.",
        "has_screenshot": "Whether the person uploaded files. Files themselves are never released.",
        "attachment_kinds": "Kinds of files uploaded: image, pdf, audio, video, other.",
        "sender": "Who sent it, as the person wrote it, anonymized.",
        "sender_type": "What the sender looked like: a personal number, a name such as 'MTN', a social media account, hidden.",
        "sender_phone_id": "Keyed code of the sender's number: prefix + code, e.g. 678-0d4f6b. Same number, same code.",
        "phone_ids": "Codes of every phone number found in the report.",
        "domains": "Web domains found in the report (links are made unclickable).",
        "caller_claimed": "For calls: who the caller said they were.",
        "caller_asked": "For calls: what the caller asked the person to do.",
        "call_language": "For calls: language used.",
        "call_end": "For calls: how it ended.",
        "call_description": "For calls: the person's own account of the call, anonymized.",
        "outcome": "noticed (spotted it), almost, lost_money, someone_else_lost, unknown.",
        "amount_lost_fcfa": "Amount lost in FCFA, as reported. Not verified. A bare number under 1,000 is read as thousands ('50' means 50,000), the way people write amounts in Cameroon.",
        "payment_rails": "How the money left: mtn_momo, orange_money, bank, cash, airtime, crypto, other.",
        "actions_after": "What the person did afterwards.",
        "region": "Region of the person, not of the scammer.",
        "extra_notes": "Anything else the person wanted to say, anonymized.",
        "would_use_tool": "Would they use a free tool to check suspicious messages (yes, maybe, no).",
        "message_cluster": "Reports with the same message share this id.",
    },
    "public_alerts": {
        "id": "Stable id of the alert (A-...).",
        "record_type": "Always 'public_alert'.",
        "source": "Who published the alert (stopblablacam, 237check, pesacheck, minfi, a news site...), or facebook_public_post / instagram_public_post for public posts our team saved.",
        "source_url": "Link to the original article or notice. Empty for social media posts: we do not link to private people who posted a warning.",
        "date_published": "Publication date of the source (YYYY-MM-DD) when known.",
        "title": "Title of the source article.",
        "summary": "Short summary written by the project in its own words.",
        "impersonated": "Who the scammers pretended to be.",
        "target": "Who was targeted (general_public, job_seekers, students...).",
        "channels": "How the scam travelled.",
        "scam_types": "Kind(s) of scam, codes in TAXONOMY.md.",
        "requested_actions": "What the victim was asked to do.",
        "amount_requested_fcfa": "Amount asked for, in FCFA, when the source states it.",
        "example_message": "The scam message itself when the source quotes it, anonymized.",
        "phone_ids": "Keyed codes of the scam numbers the source published.",
        "domains": "Scam web domains named by the source (made unclickable).",
        "entities": "Names of schemes or platforms involved (e.g. a Ponzi scheme name).",
    },
    "genuine_messages": {
        "id": "Stable id of the message (G-...).",
        "record_type": "Always 'genuine_message'.",
        "label": "Always 'not_scam'.",
        "operator": "Who sent it: mtn, orange, camtel, a bank, a government service, an online service (verification codes), or a brand advertising through the operator (partner_brand).",
        "sender_shown": "Sender name displayed on the phone (e.g. 'Mobile Money').",
        "line_type": "consumer (personal line) or merchant_agent (shop or agent line).",
        "message_kind": "What the message is: money received or sent, cash-in, cash-out, bundle or merchant payment, loan advance or repayment, login code, promo.",
        "message_text": "The message, anonymized. Amounts and balances kept; names, numbers, accounts, ids and codes removed.",
        "message_language": "Language of the message.",
        "times_seen": "How many contributed messages share this wording once amounts, dates and ids are blanked out. At most 3 examples of each wording are included.",
        "source": "Always 'contributed': forwarded by people from their own phones, with their agreement.",
    },
    "scam_numbers": {
        "phone_id": "Keyed code of a scam number (prefix + code). The real number cannot be recovered.",
        "prefix": "First 3 digits of the number, which show the operator range.",
        "times_reported": "How many reports mention this number.",
        "times_in_alerts": "How many public alerts mention this number.",
        "top_scam_types": "Most frequent scam types linked to this number.",
        "first_seen": "Earliest month the number appears (YYYY-MM).",
    },
}

REQUIRED = {"messages": ["id", "text", "label", "split"], "reports": ["id"], "public_alerts": ["id", "summary", "scam_types"],
            "genuine_messages": ["id", "message_text", "label"], "scam_numbers": ["phone_id"]}


def validate(tables: dict) -> list:
    """Problems that must be fixed before a release: unknown codes, missing required fields, duplicate ids."""
    errs = []
    for name, rows in tables.items():
        ids = set()
        for r in rows:
            rid = r.get("id") or r.get("phone_id")
            if rid in ids:
                errs.append(f"{name}: duplicate id {rid}")
            ids.add(rid)
            for f in REQUIRED.get(name, []):
                if r.get(f) in (None, "", []):
                    errs.append(f"{name} {rid}: missing {f}")
            for f, allowed in V.items():
                if f not in r or r[f] in (None, ""):
                    continue
                vals = r[f] if isinstance(r[f], list) else [r[f]]
                bad = [v for v in vals if v not in allowed]
                if bad:
                    errs.append(f"{name} {rid}: {f} has unknown value(s) {bad}")
    return errs


def coverage(reports, alerts):
    """Real scam message examples held per scam type (single-incident reports + quoted alert messages)."""
    out = {}
    for t in T.SCAM_TYPES:
        if t == "other":
            continue
        rep = sum(1 for r in reports if t in r["scam_types"] and not r["multi_scam"]
                  and (r["message_text"] or r["call_description"] or len(r.get("extra_notes") or "") >= 40))
        al = sum(1 for a in alerts if t in a["scam_types"] and a.get("example_message"))
        out[t] = {"from_reports": rep, "from_alerts": al, "total": rep + al}
    return out
