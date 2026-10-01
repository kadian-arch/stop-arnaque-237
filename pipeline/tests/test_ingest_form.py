import csv
import tempfile
import unittest
from pathlib import Path

from pipeline.ingest_form import read_tally_csv, missing_columns

Q_CHANNEL = "How did it reach you? / Comment l'arnaque vous est-elle parvenue ?"
Q_TYPES = "What was it about? Tick all that apply. / De quoi s'agissait-il ? Cochez tout ce qui s'applique."
Q_REQ = "What did they ask you to do? / Que vous a-t-on demandé ?"
OPT_A = 'Money sent "by mistake", asked to send it back / Argent envoyé "par erreur", à renvoyer'
OPT_B = "Asked for your PIN, a code, or to dial a code / On vous a demandé votre PIN, un code, ou de composer un code"
OPT_DIAL = "Dial a code (like *126*... or #150*...) / Composer un code"

BASE = {
    "Submission ID": "abc123",
    "Submitted at": "2026-09-29 10:00:00",
    "I am 18 or older / J'ai 18 ans ou plus": "true",
    "I agree that my report, with names and phone numbers removed, can be published as open data to fight scams. / J'accepte ...": "true",
    "Upload screenshots of the scam (best option) / Téléversez les captures d'écran de l'arnaque (le mieux)":
        "https://storage.tally.so/a/one.png, https://storage.tally.so/a/two.jpg",
    "Or paste the message text here / Ou collez le texte du message ici": "I sent 5000 by mistake",
    "Who sent it? Number, name or page, exactly as shown / Qui l'a envoyé ? Numéro, nom ou page, tel qu'affiché": "677123456",
    "The sender looked like: / L'expéditeur ressemblait à :": "A normal phone number / Un numéro de téléphone normal",
    "Did you lose money? / Avez-vous perdu de l'argent ?": "Yes / Oui",
    "How much, in FCFA? / Combien, en FCFA ?": "25 000",
    "Your region / Votre région": "Nord-Ouest / North West",
    "When did it happen? / Quand est-ce arrivé ?": "This month / Ce mois-ci",
    "src": "group",
}


def write(rows, headers):
    tmp = Path(tempfile.mkdtemp()) / "export.csv"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return tmp


class Combined(unittest.TestCase):
    def test_single_column_layout(self):
        row = dict(BASE)
        row[Q_CHANNEL] = "Phone call / Appel téléphonique"
        row[Q_TYPES] = f"{OPT_A}, {OPT_B}"
        row[Q_REQ] = f"{OPT_DIAL}, Send money / Envoyer de l'argent"
        path = write([row], list(row))
        r = read_tally_csv(path)[0]
        self.assertEqual(r["channel"], "phone_call")
        self.assertEqual(sorted(r["scam_types"]), ["credential_request", "wrong_number_reversal"])
        self.assertEqual(sorted(r["caller_asked"]), ["dial_code", "send_money"])
        self.assertEqual(r["amount_lost_fcfa"], 25000)
        self.assertEqual(r["region"], "north_west")
        self.assertEqual(r["outcome"], "lost_money")
        self.assertEqual(r["sender_type"], "personal_number")
        self.assertEqual(len(r["screenshots"]), 2)
        self.assertTrue(r["consent"] and r["age_ok"])
        self.assertEqual(r["src"], "group")


class PerOption(unittest.TestCase):
    def test_one_column_per_option(self):
        row = dict(BASE)
        row[f"{Q_CHANNEL} (SMS)"] = "true"
        row[f"{Q_CHANNEL} (WhatsApp)"] = "false"
        row[f"{Q_TYPES} ({OPT_A})"] = "true"
        row[f"{Q_TYPES} ({OPT_B})"] = "false"
        row[f"{Q_REQ} ({OPT_DIAL})"] = "true"
        path = write([row], list(row))
        r = read_tally_csv(path)[0]
        self.assertEqual(r["channel"], "sms")
        self.assertEqual(r["scam_types"], ["wrong_number_reversal"])
        self.assertEqual(r["caller_asked"], ["dial_code"])

    def test_google_sheets_untitled_consent(self):
        # the Sheets integration names titleless checkbox blocks "Untitled checkboxes field (...)"
        row = {k: v for k, v in BASE.items() if not k.startswith(("I am 18", "I agree"))}
        row["Untitled checkboxes field"] = "I am 18 or older / J'ai 18 ans ou plus"
        row["Untitled checkboxes field (I am 18 or older / J'ai 18 ans ou plus)"] = "TRUE"
        row["Untitled checkboxes field (I agree that my report, with names removed, can be published. / J'accepte ...)"] = "TRUE"
        path = write([row], list(row))
        self.assertNotIn("consent", missing_columns(path))
        r = read_tally_csv(path)[0]
        self.assertTrue(r["consent"] and r["age_ok"])

    def test_untitled_consent_unticked(self):
        row = {k: v for k, v in BASE.items() if not k.startswith(("I am 18", "I agree"))}
        row["Untitled checkboxes field (I am 18 or older / J'ai 18 ans ou plus)"] = "TRUE"
        row["Untitled checkboxes field (I agree that my report ... / J'accepte ...)"] = "FALSE"
        r = read_tally_csv(write([row], list(row)))[0]
        self.assertFalse(r["consent"])

    def test_renamed_scam_type_question(self):
        # title changed on the live form on 2026-09-30
        new_q = "What was this scam about? Tick only what happened this time. / De quoi s'agissait-il cette fois ?"
        row = dict(BASE)
        row[f"{new_q} ({OPT_A})"] = "TRUE"
        row[f"{new_q} ({OPT_B})"] = "FALSE"
        r = read_tally_csv(write([row], list(row)))[0]
        self.assertEqual(r["scam_types"], ["wrong_number_reversal"])

    def test_reports_missing_columns(self):
        path = write([{"Submission ID": "x"}], ["Submission ID"])
        self.assertIn("scam_types", missing_columns(path))


if __name__ == "__main__":
    unittest.main()
