"""Rough language tag for a scam message: en, fr, pidgin, mixed or unknown.
Word lists only; good enough to filter or balance the dataset, checked during review."""
import re

FR = set("le la les un une des de du et est vous votre vos nous je tu il elle pour avec sur dans pas que qui "
         "compte argent numéro envoyé envoyer merci svp bonjour félicitations gagné erreur trompé renvoyer code "
         "retrait dépôt solde appelez composez".split())
EN = set("the a an and is are you your we i to of for with on in not that this account money number sent send "
         "please thank hello congratulations won mistake back code withdrawal deposit balance call dial".split())
PIDGIN = set("di dem na weh abeg sabi don wetin dey fit una e no go make wey oya comot chop".split())


def detect(text) -> str:
    words = re.findall(r"[a-zà-ÿ']+", (text or "").lower())
    if len(words) < 3:
        return "unknown"
    fr = sum(w in FR for w in words)
    en = sum(w in EN for w in words)
    pg = sum(w in PIDGIN for w in words)
    if pg >= 2 and pg >= 0.15 * len(words):
        return "pidgin"
    if fr and en and min(fr, en) >= 0.35 * max(fr, en):
        return "mixed"
    if fr > en:
        return "fr"
    if en > fr:
        return "en"
    return "unknown"
