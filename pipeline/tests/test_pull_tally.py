import unittest

from pipeline.pull_tally import to_rows

QUESTIONS = [
    {"id": "c1", "type": "CHECKBOXES", "title": None},
    {"id": "ch", "type": "MULTIPLE_CHOICE", "title": "How did it reach you? / Comment l'arnaque vous est-elle parvenue ?"},
    {"id": "ty", "type": "CHECKBOXES", "title": "What was this scam about? Tick only what happened this time."},
    {"id": "up", "type": "FILE_UPLOAD", "title": "Upload screenshots of the scam (best option)"},
    {"id": "am", "type": "INPUT_NUMBER", "title": "How much, in FCFA? / Combien, en FCFA ?"},
    {"id": "hf", "type": "HIDDEN_FIELDS", "title": None},
]
SUBS = [{
    "id": "abc", "respondentId": "r1", "submittedAt": "2026-10-01T10:00:00.000Z",
    "responses": [
        {"questionId": "c1", "answer": ["I am 18 or older / J'ai 18 ans ou plus"]},
        {"questionId": "ch", "answer": ["SMS"]},
        {"questionId": "ty", "answer": ["Fake job or recruitment / Faux emploi", "Other / Autre"]},
        {"questionId": "up", "answer": [{"url": "https://x/1.png"}, {"url": "https://x/2.png"}]},
        {"questionId": "am", "answer": 25000},
        {"questionId": "hf", "answer": {"src": "fb"}},
    ],
}]


class ToRows(unittest.TestCase):
    def test_flatten(self):
        headers, rows = to_rows(QUESTIONS, SUBS)
        r = rows[0]
        self.assertEqual(r["Submission ID"], "abc")
        self.assertEqual(r["Submitted at"], "2026-10-01 10:00:00")
        self.assertEqual(r["I am 18 or older / J'ai 18 ans ou plus"], "TRUE")   # untitled consent box
        self.assertEqual(r["What was this scam about? Tick only what happened this time."],
                         "Fake job or recruitment / Faux emploi, Other / Autre")
        self.assertEqual(r["Upload screenshots of the scam (best option)"], "https://x/1.png\nhttps://x/2.png")
        self.assertEqual(r["How much, in FCFA? / Combien, en FCFA ?"], "25000")
        self.assertEqual(r["src"], "fb")
        self.assertIn("src", headers)


if __name__ == "__main__":
    unittest.main()
