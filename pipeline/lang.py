"""Rough language tag for a scam message: en, fr, pidgin, mixed or unknown.
Word lists only; good enough to filter or balance the dataset, checked during review.
unknown means too little text to tell, or a language other than English, French or Pidgin."""
import re

# words spelled the same in English and French (code, bonus, transaction...) are in neither list
FR = set("le la les un une des de du et est sont été vous votre vos nous je tu il elle ils elles pour avec sur dans "
         "pas plus très que qui à au aux ce cette ces son sa ses mon ma mes ton ta tes leur leurs être avoir tout "
         "toute tous toutes chaque où si mais donc car comme par ou en compte argent numéro envoyé envoyer merci "
         "svp bonjour félicitations gagné gagnez erreur trompé renvoyer retrait dépôt solde appelez composez "
         "reçu recu jeunes recrutement offre".split())
EN = set("the a an and is are was were be been have has had will would you your we i to of for with on in at by "
         "from not that this it its or if but all as account money number sent send please thank hello "
         "congratulations won mistake back withdrawal deposit balance call dial received successfully activated "
         "valid till until now today get free calls subscribe enjoy".split())
# words that only Cameroonian Pidgin uses this way
PIDGIN = set("di dey na wey weh abeg sabi wetin una wuna oya comot chop pikin sotey sef wahala kam ei yi "
             "givam wan dem dis dat sey nyango ashia mbok tok kontri broda".split())
# short phrases that are Pidgin even when every word is also English ("don" but never "don't")
PIDGIN_PHRASES = re.compile(
    r"\b(?:e|i|we|them|dem|you|u|yi|ei) (?:di|dey|don(?![’'t]))\b|\bna (?:so|weti|wetin|him|we)\b"
    r"|\bmake (?:we|you|u|e|i) \w|\bfor (?:country|ma|una)\b|\bwey (?:e|i|dey|di|d)\b|\bno (?:di|dey)\b"
    r"|\bsend am\b|\bgive am\b|\bu fit\b")


def detect(text) -> str:
    low = (text or "").lower()
    words = re.findall(r"[a-zà-ÿ']+", low)
    if len(words) < 3:
        return "unknown"
    fr = sum(w in FR for w in words)
    en = sum(w in EN for w in words)
    pg = sum(w in PIDGIN for w in words) + 2 * len(PIDGIN_PHRASES.findall(low))
    if pg >= 3 or (pg >= 2 and pg >= 0.08 * len(words)):
        return "pidgin"
    if fr and en and min(fr, en) >= 0.35 * max(fr, en):
        return "mixed"
    if fr > en:
        return "fr"
    if en > fr:
        return "en"
    return "unknown"
