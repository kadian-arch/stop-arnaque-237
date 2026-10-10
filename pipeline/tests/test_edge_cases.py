"""Everything the real form can throw at the pipeline."""
import csv
import importlib
import json
import os
import platform
import tempfile
import unittest
from pathlib import Path

from pipeline.ingest_form import parse_amount, read_tally_csv
from pipeline.attachments import ocr_ready, kind
from pipeline import lang

AGE = "I am 18 or older / J'ai 18 ans ou plus"
OK = "I agree that my report, with names and phone numbers removed, can be published as open data to fight scams."
CH = "How did it reach you? / Comment l'arnaque vous est-elle parvenue ?"
TY = "What was it about? Tick all that apply. / De quoi s'agissait-il ?"
UP = "Upload screenshots of the scam (best option) / Téléversez les captures d'écran de l'arnaque (le mieux)"
TXT = "Or paste the message text here / Ou collez le texte du message ici"
WHO = "Who sent it? Number, name or page, exactly as shown / Qui l'a envoyé ?"
LOOK = "The sender looked like: / L'expéditeur ressemblait à :"
LOST = "Did you lose money? / Avez-vous perdu de l'argent ?"
AMT = "How much, in FCFA? / Combien, en FCFA ?"
MAIL = "Want our free public report on the scams we find? Leave an email (optional, never published)."
HEAD = ["Submission ID", "Submitted at", AGE, OK, CH, TY, UP, TXT, WHO, LOOK, LOST, AMT, MAIL]


class Amounts(unittest.TestCase):
    def test_variants(self):
        cases = {"25000": 25000, "25 000": 25000, "25.000": 25000, "1,500,000": 1500000, "25000.00": 25000,
                 "25k": 25000, "2,5 millions": 2500000, "1.5m": 1500000, "150 000 FCFA": 150000,
                 "": None, "je ne sais pas": None, "5000frs": 5000, "50": 50000, "6500": 6500}
        for raw, want in cases.items():
            self.assertEqual(parse_amount(raw), want, raw)


class Formats(unittest.TestCase):
    def test_excel_resaved_semicolon_cp1252(self):
        tmp = Path(tempfile.mkdtemp()) / "e.csv"
        with open(tmp, "w", newline="", encoding="cp1252") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(HEAD)
            w.writerow(["x1", "29/09/2026 10:00", "true", "true", "SMS", "Other / Autre", "", "Félicitations vous avez gagné",
                        "", "", "", "", ""])
        r = read_tally_csv(tmp)[0]
        self.assertEqual(r["channel"], "sms")
        self.assertIn("Félicitations", r["message_text"])
        self.assertEqual(r["src"], "direct")

    def test_xlsx(self):
        from openpyxl import Workbook
        tmp = Path(tempfile.mkdtemp()) / "e.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(HEAD)
        ws.append(["x2", "2026-09-29 10:00:00", "true", "true", "WhatsApp", "Fake job or recruitment / Faux emploi", None,
                   "pay 5000 for the job", None, None, "Yes / Oui", 5000, None])
        wb.save(tmp)
        r = read_tally_csv(tmp)[0]
        self.assertEqual((r["channel"], r["scam_types"], r["amount_lost_fcfa"]), ("whatsapp", ["fake_job"], 5000))


class Attachments(unittest.TestCase):
    def test_long_screenshot_is_sliced(self):
        from PIL import Image
        d = Path(tempfile.mkdtemp())
        p = d / "long.png"
        Image.new("RGB", (1080, 21000), "white").save(p)
        parts = ocr_ready(p, d / "work")
        self.assertGreaterEqual(len(parts), 3)
        for q in parts:
            self.assertLessEqual(max(Image.open(q).size), 9500)

    def test_unreadable_image_does_not_crash(self):
        d = Path(tempfile.mkdtemp())
        p = d / "photo.heic"
        p.write_bytes(b"not really heic")
        self.assertEqual(ocr_ready(p, d / "w"), [p])

    def test_kinds(self):
        for name, k in {"a.JPG": "image", "b.pdf": "pdf", "c.opus": "audio", "d.mp4": "video", "e.docx": "other"}.items():
            self.assertEqual(kind(Path(name)), k)


class Language(unittest.TestCase):
    def test_tags(self):
        self.assertEqual(lang.detect("Bonjour, vous avez gagné 400.000 FCFA, appelez ce numéro"), "fr")
        self.assertEqual(lang.detect("Sorry I sent money to your number by mistake please send it back"), "en")
        self.assertEqual(lang.detect("abeg my broda I don send money for your number, send am back make I no suffer"), "pidgin")
        self.assertEqual(lang.detect("ok"), "unknown")
        # Pidgin mixed with English, seen in real reports
        self.assertEqual(lang.detect("As e di hot for country, people na some bad egg this. He di post things for market place say e di sell phones"), "pidgin")
        self.assertEqual(lang.detect("Abeg I get some issue and I wish u fit share. This person na scammer wey d do online clothes delivery"), "pidgin")
        self.assertEqual(lang.detect("Plenty bonus! 1GB on the NewMoMoApp. Download, log in, make a transaction, then get 1GB valid"), "en")


@unittest.skipUnless(platform.system() == "Windows", "Windows OCR")
class FullBuildWithFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import fitz
        from PIL import Image, ImageDraw, ImageFont
        cls.tmp = Path(tempfile.mkdtemp())
        ex = cls.tmp / "raw" / "tally_exports"
        ex.mkdir(parents=True)
        rows = [
            # 3 files of 3 kinds dropped in by hand, plus a dead link
            ["m1", "2026-09-29 10:00:00", "true", "true", "SMS", "Other / Autre", "https://invalid.invalid/9.png", "",
             "MobileMoney", "", "", "", "not-an-email"],
            # almost nothing filled
            ["m2", "2026-09-29 11:00:00", "true", "true", "", "", "", "", "", "", "", "", ""],
        ]
        with open(ex / "e.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(HEAD)
            w.writerows(rows)
        shots = cls.tmp / "raw" / "screenshots" / "m1"
        shots.mkdir(parents=True)
        im = Image.new("RGB", (1000, 300), "white")
        ImageDraw.Draw(im).text((30, 100), "You have won 400,000 FCFA call now", fill="black",
                                font=ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 40))
        im.save(shots / "1.png")
        doc = fitz.open()
        doc.new_page().insert_text((72, 72), "Recrutement special: payez 15000 FCFA de frais de dossier")
        doc.save(shots / "2.pdf")
        (shots / "3.opus").write_bytes(b"voice note")
        os.environ["STOPARNAQUE_ROOT"] = str(cls.tmp)
        import pipeline.build as B
        cls.res = importlib.reload(B).build("dev", with_screens=True)
        cls.reps = {json.loads(l)["id"]: json.loads(l) for l in
                    (cls.tmp / "release" / "dev" / "details" / "reports.jsonl").read_text(encoding="utf-8").splitlines()}
        cls.queue = list(csv.DictReader(open(cls.tmp / "raw" / "review_queue.csv", encoding="utf-8-sig")))
        cls.B = B

    def test_numbered_release_needs_review_done(self):
        with self.assertRaisesRegex(RuntimeError, "review them before releasing"):
            self.B.build("v9.9", with_screens=False)

    def test_publish_only_takes_numbered_releases(self):
        for bad in ("dev", "test", "latest"):
            with self.assertRaisesRegex(RuntimeError, "numbered version"):
                self.B.publish(bad)

    def test_excel_and_parquet_written(self):
        out = self.tmp / "release" / "dev"
        self.assertTrue((out / "stop_arnaque_237_dev.xlsx").exists())
        self.assertTrue((out / "messages.parquet").exists())
        self.assertTrue((out / "details" / "reports.parquet").exists())

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("STOPARNAQUE_ROOT", None)

    def test_both_rows_released(self):
        self.assertEqual(self.res["reports"], 2)

    def test_mixed_files_read(self):
        r = next(r for r in self.reps.values() if "400,000" in (r["message_text"] or ""))
        self.assertIn("400,000", r["message_text"])
        self.assertIn("15000", r["message_text"])
        self.assertEqual(r["sender"], "MobileMoney")

    def test_review_queue_explains(self):
        reasons = " ".join(q["reasons"] for q in self.queue)
        for want in ["audio_attachment", "download_failed", "no_text", "scam_type_other", "screenshot_text"]:
            self.assertIn(want, reasons)

    def test_bad_email_not_kept(self):
        self.assertFalse((self.tmp / "raw" / "report_subscribers.txt").exists())


if __name__ == "__main__":
    unittest.main()
