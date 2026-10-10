"""End-to-end: synthetic export + synthetic alert in a temp folder -> release files."""
import csv
import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path

H = {
    "id": "Submission ID", "at": "Submitted at",
    "age": "I am 18 or older / J'ai 18 ans ou plus",
    "ok": "I agree that my report, with names and phone numbers removed, can be published as open data to fight scams.",
    "ch": "How did it reach you? / Comment l'arnaque vous est-elle parvenue ?",
    "ty": "What was it about? Tick all that apply. / De quoi s'agissait-il ?",
    "txt": "Or paste the message text here / Ou collez le texte du message ici",
    "who": "Who sent it? Number, name or page, exactly as shown / Qui l'a envoyé ?",
    "lost": "Did you lose money? / Avez-vous perdu de l'argent ?",
    "amt": "How much, in FCFA? / Combien, en FCFA ?",
    "mail": "Want our free public report on the scams we find? Leave an email (optional, never published).",
    "src": "src",
}
MSG = "Sorry I sent 5000 FCFA to your number by mistake, send it back to 677 12 34 56. From Paul Ekane"
ROWS = [
    {"id": "s1", "at": "2026-09-29 10:00:00", "age": "true", "ok": "true", "ch": "SMS",
     "ty": 'Money sent "by mistake", asked to send it back / Argent envoyé', "txt": MSG, "who": "677123456",
     "lost": "Yes / Oui", "amt": "5000", "mail": "someone@example.com", "src": "group"},
    {"id": "s2", "at": "2026-09-29 11:00:00", "age": "true", "ok": "true", "ch": "SMS",
     "ty": 'Money sent "by mistake", asked to send it back / Argent envoyé', "txt": MSG, "who": "+237 677 12 34 56",
     "lost": "No, I noticed it was a scam / Non", "amt": "", "mail": "", "src": "dm"},
    {"id": "s3", "at": "2026-09-29 12:00:00", "age": "true", "ok": "", "ch": "SMS", "ty": "Other / Autre",
     "txt": "no consent row", "who": "", "lost": "", "amt": "", "mail": "", "src": ""},
]
ALERT = {"src": "stopblablacam", "url": "https://example.org/a", "date": "2025-01-01", "title": "Fake job",
         "summary": "A fake job.", "impersonated": "X", "channels": ["phone_call"], "scam_types": ["fake_job"],
         "requested_actions": ["pay_fee"], "phones": ["677123456"], "amount_requested_fcfa": 9800}


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        (cls.tmp / "raw" / "tally_exports").mkdir(parents=True)
        (cls.tmp / "raw" / "web").mkdir(parents=True)
        with open(cls.tmp / "raw" / "tally_exports" / "e.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(H.values()))
            w.writeheader()
            for r in ROWS:
                w.writerow({H[k]: v for k, v in r.items()})
        (cls.tmp / "raw" / "web" / "curated_public_alerts.jsonl").write_text(json.dumps(ALERT) + "\n", encoding="utf-8")
        os.environ["STOPARNAQUE_ROOT"] = str(cls.tmp)
        import pipeline.build as B
        cls.B = importlib.reload(B)
        cls.res = cls.B.build("test", with_screens=False)
        cls.out = cls.tmp / "release" / "test"

    @classmethod
    def tearDownClass(cls):
        os.environ.pop("STOPARNAQUE_ROOT", None)

    def rows(self, name):
        folder = self.out if name.startswith("messages") else self.out / "details"
        return [json.loads(l) for l in (folder / name).read_text(encoding="utf-8").splitlines()]

    def test_consent_filter(self):
        self.assertEqual(self.res["reports"], 2)
        self.assertEqual(self.res["dropped"].get("no_consent"), 1)

    def test_no_raw_pii_anywhere_in_release(self):
        blob = "".join(p.read_text(encoding="utf-8-sig") for p in self.out.rglob("*") if p.suffix in (".jsonl", ".csv", ".json"))
        for secret in ["677 12 34 56", "677123456", "Ekane", "someone@example.com"]:
            self.assertNotIn(secret, blob)

    def test_same_number_links_reports_and_alerts(self):
        reps = self.rows("reports.jsonl")
        alerts = self.rows("public_alerts.jsonl")
        self.assertEqual(reps[0]["sender_phone_id"], reps[1]["sender_phone_id"])
        self.assertEqual(reps[0]["sender_phone_id"], alerts[0]["phone_ids"][0])
        nums = list(csv.DictReader(open(self.out / "details" / "scam_numbers.csv", encoding="utf-8-sig")))
        self.assertEqual(nums[0]["times_reported"], "2")
        self.assertEqual(nums[0]["times_in_alerts"], "1")

    def test_same_text_same_cluster(self):
        reps = self.rows("reports.jsonl")
        self.assertIsNotNone(reps[0]["message_cluster"])
        self.assertEqual(reps[0]["message_cluster"], reps[1]["message_cluster"])

    def test_messages_table(self):
        msgs = self.rows("messages.jsonl")
        self.assertTrue(msgs)
        self.assertEqual({m["label"] for m in msgs}, {"scam"})
        for m in msgs:
            self.assertIn(m["split"], ("train", "test"))
            self.assertIn(m["origin"], ("report", "public_alert", "social_post", "contributed"))
        self.assertTrue((self.out / "data_dictionary.csv").exists())

    def test_no_internal_columns(self):
        rep = self.rows("reports.jsonl")[0]
        for internal in ("would_use_tool", "attachment_kinds", "has_screenshot", "screenshot_text", "record_type"):
            self.assertNotIn(internal, rep)
        st = json.loads((self.out / "stats.json").read_text(encoding="utf-8"))
        self.assertNotIn("dropped", st)

    def test_hugging_face_folder(self):
        import pyarrow.parquet as pq
        from pipeline.hf import build_hf
        hf = build_hf(self.tmp, "test", "someone/stop-arnaque-237")
        card = (hf / "README.md").read_text(encoding="utf-8")
        self.assertTrue(card.startswith("---\nlicense: cc-by-4.0"))
        self.assertIn('load_dataset("someone/stop-arnaque-237")', card)
        rows = sum(pq.read_metadata(hf / "data" / f"{s}.parquet").num_rows for s in ("train", "test"))
        self.assertEqual(rows, len(self.rows("messages.jsonl")))
        self.assertTrue((hf / "details" / "reports.parquet").exists())

    def test_subscriber_kept_private(self):
        self.assertIn("someone@example.com", (self.tmp / "raw" / "report_subscribers.txt").read_text())

    def test_stats(self):
        st = json.loads((self.out / "stats.json").read_text(encoding="utf-8"))
        self.assertEqual(st["reports"]["total_lost_fcfa"], 5000)
        self.assertEqual(st["public_alerts"], 1)


if __name__ == "__main__":
    unittest.main()
