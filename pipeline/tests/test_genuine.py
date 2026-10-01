import tempfile
import unittest
from pathlib import Path

from pipeline.genuine import build_genuine, parse

SAMPLE = '''From Mobile Money on a normal consumer sim; "You have transferred 2200 XAF to JOHN DOE TEST (237670000001) from your mobile money account 91234567 at 2026-09-12 13:27:31 FEES 8 FCFA. Your new balance: 0 XAF. Financial Transaction Id: 18751961232.
<#> Y'ello. Please enter the following code :4064 to complete your login. Be careful, do not share with anyone.
You Jane Roe Sample (237670000002) have via agent: -SOME SHOP _LTD PAUL TEST (237670000003), withdrawn 500 XAF from your mobile money account: 91234567 at 2026-09-20 23:23:52.
<#> Y'ello. Please enter the following code :4064 to complete your login. Be careful, do not share with anyone."

From on a merchant SIM/POS; "Cash out initiated by MARY TEST (237670000004) on DATETIME} is successfully completed. You can payout the amount: 500 XAF in cash to the customer."
'''


class Genuine(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "genuine").mkdir()
        (self.root / "genuine" / "msgs.txt").write_text(SAMPLE, encoding="utf-8")
        self.rows = build_genuine(self.root, [])

    def test_headers_and_lines(self):
        msgs = parse(SAMPLE)
        self.assertEqual(len(msgs), 5)
        self.assertEqual(msgs[0][1], "consumer")
        self.assertEqual(msgs[-1][1], "merchant_agent")

    def test_nothing_personal_left(self):
        blob = " ".join(r["message_text"] for r in self.rows)
        for s in ("JOHN", "Jane", "PAUL", "MARY", "SOME SHOP", "91234567", "23767000000", "4064", "18751961232"):
            self.assertNotIn(s, blob)
        self.assertIn("2200 XAF", blob)          # amounts are kept
        self.assertIn("[ACCOUNT]", blob)

    def test_dedup_kinds_operator(self):
        self.assertEqual(len(self.rows), 4)      # the repeated code message is kept once
        code = [r for r in self.rows if r["message_kind"] == "otp_code"][0]
        self.assertEqual(code["times_seen"], 2)
        self.assertEqual({r["label"] for r in self.rows}, {"not_scam"})
        cash = [r for r in self.rows if r["message_kind"] == "agent_cash_out"][0]
        self.assertEqual(cash["line_type"], "merchant_agent")


if __name__ == "__main__":
    unittest.main()
