import re
import unittest

from pipeline import anonymize as A

# All names and numbers below are invented.


class Phones(unittest.TestCase):
    def test_formats_map_to_same_pseudonym(self):
        forms = ["677123456", "677 12 34 56", "6 77 12 34 56", "+237 677 12 34 56",
                 "00237677123456", "237677123456", "677.12.34.56", "677-12-34-56"]
        codes = {A.extract_phones(f)[0] for f in forms}
        self.assertEqual(len(codes), 1)
        self.assertTrue(next(iter(codes)).startswith("677-"))

    def test_keeps_prefix_hides_rest(self):
        out = A.anonymize_text("Call me on 699 88 77 66 now")
        self.assertRegex(out, r"\[PHONE:699-[0-9a-f]{6}\]")
        self.assertNotIn("88 77 66", out)

    def test_different_numbers_different_codes(self):
        self.assertNotEqual(A.extract_phones("655000001"), A.extract_phones("655000002"))

    def test_amount_is_not_a_phone(self):
        for t in ["200 000 000 FCFA", "600000000 XAF", "250 000 000 francs"]:
            self.assertNotIn("[PHONE", A.anonymize_text(t), t)

    def test_dates_and_times_untouched(self):
        t = "completed at 2026-09-24 20:00:52. Your new balance:128 XAF"
        self.assertEqual(A.anonymize_text(t), t)

    def test_foreign_number(self):
        self.assertIn("[PHONE:intl-", A.anonymize_text("WhatsApp +234 803 555 1234"))

    def test_odd_prefixes(self):
        # seen in a real Orange promo scam SMS: "<<237+691105214>>"
        for t in ("<<237+691105214>>", "(+237) 691 10 52 14", "00237691105214"):
            out = A.anonymize_text(t)
            self.assertNotRegex(out, r"691\s?10", t)
            self.assertIn("[PHONE:691-", out)


class FrenchCounterparty(unittest.TestCase):
    def test_name_after_de_and_a(self):
        for t in ("Vous avez recu 69500 XAF de N A City embolo asanga (237670000001) sur votre compte",
                  "Vous avez transféré 5000 FCFA à JEAN TEST NOM (237670000002) depuis votre compte"):
            out = A.anonymize_text(t)
            self.assertIn("[NAME] ([PHONE:", out)
            self.assertNotRegex(out, r"embolo|JEAN|NOM")


class CodesAndCredentials(unittest.TestCase):
    def test_codes_masked_words_kept(self):
        cases = {
            "G-597W is your Google verification code.": "[CODE] is your Google",
            "The OTP for UBA Mobile Banking is 93714051.": "is [CODE].",
            "Veuillez entrer le numéro 749463 pour continuer": "numéro [CODE]",
            "LOGIN : 0670000001 PASS : 863353": "LOGIN : [CREDENTIAL] PASS : [CREDENTIAL]",
            "This confidential code gives access to your MoMo account:lQbJJNJMQ2VNi": "account:[CREDENTIAL]",
            "Passport #AB502123 is ready": "Passport #[ID]",
        }
        for raw, expected in cases.items():
            self.assertIn(expected, A.anonymize_text(raw), raw)
        self.assertEqual(A.anonymize_text("You must pass the exam. Pass 3 levels."), "You must pass the exam. Pass 3 levels.")


class LeakScan(unittest.TestCase):
    def test_catches_raw_data_but_not_tokens(self):
        import tempfile
        from pathlib import Path
        from pipeline.build import leak_scan
        d = Path(tempfile.mkdtemp())
        (d / "ok.csv").write_text("[PHONE:677-123456],677-123456,[EMAIL@gmail.com],25 000 FCFA\n", encoding="utf-8")
        self.assertEqual(leak_scan(d), [])
        (d / "bad.jsonl").write_text('{"t": "call 677 12 34 56 or a@b.com https://storage.tally.so/x"}\n', encoding="utf-8")
        kinds = {h.split()[1] for h in leak_scan(d)}
        self.assertTrue({"phone:", "email:", "private_file:"} <= kinds)
        (d / "bad.jsonl").write_text('{"t": "account 93417225, +1 (619) 705-8649"}\n', encoding="utf-8")
        self.assertIn("long_number:", {h.split()[1] for h in leak_scan(d)})


class Names(unittest.TestCase):
    def test_operator_style_name_before_number(self):
        t = "You have received 7000 XAF from JEAN PAUL MBARGA NDONGO (237677123456) on your account"
        out = A.anonymize_text(t)
        self.assertNotIn("MBARGA", out)
        self.assertIn("[NAME]", out)
        self.assertIn("[PHONE:677-", out)

    def test_cue_name(self):
        out = A.anonymize_text("Bonjour, je suis Paul Ekane de MTN, votre compte est bloqué")
        self.assertNotIn("Ekane", out)
        self.assertIn("MTN", out)

    def test_orgs_kept(self):
        out = A.anonymize_text("A transaction of 500 XAF by MTNC BUNDLES_FORFAITS (MTN_Bundles)")
        self.assertIn("MTNC BUNDLES_FORFAITS", out)
        out = A.anonymize_text("XAF 193.00 Débit du cpte REF:S11FRGEXAFL00002 FRAIS DE PACKAGE COMPTE D EPARGNE")
        self.assertIn("FRAIS DE PACKAGE COMPTE", out)

    def test_review_flag(self):
        self.assertTrue(A.needs_review("then Marie Ngono called again"))
        self.assertFalse(A.needs_review("dial *126# and select option 7"))


class IdsLinksEmails(unittest.TestCase):
    def test_transaction_ids(self):
        out = A.anonymize_text("Financial Transaction Id: 18935634160. External Transaction Id: GOALS_REQ_441279.")
        self.assertNotIn("18935634160", out)
        self.assertNotIn("GOALS_REQ_441279", out)
        # loan ids embed the borrower's number at the end
        out = A.anonymize_text("Loan ID : BC0004X01T202607221257160681M70000001. Refund ID : BC0004X02T20260806RM70000001.")
        self.assertNotIn("70000001", out)

    def test_email_keeps_domain(self):
        self.assertEqual(A.anonymize_text("write to recrutement.minfi@gmail.com"), "write to [EMAIL@gmail.com]")

    def test_url_defanged(self):
        out = A.anonymize_text("claim here https://mtn-promo.xyz/win?id=3 fast")
        self.assertIn("hxxps://mtn-promo[.]xyz/win?id=3", out)
        self.assertNotIn("https://", out)

    def test_bare_domain_defanged(self):
        self.assertIn("link[.]mtn[.]cm/NewMoMoAppRef", A.anonymize_text("access link.mtn.cm/NewMoMoAppRef"))

    def test_amounts_kept(self):
        t = "Pay 25,000 FCFA for the concours list"
        self.assertEqual(A.anonymize_text(t), t)

    def test_empty(self):
        self.assertIsNone(A.anonymize_text(None))
        self.assertEqual(A.anonymize_text(""), "")


if __name__ == "__main__":
    unittest.main()
