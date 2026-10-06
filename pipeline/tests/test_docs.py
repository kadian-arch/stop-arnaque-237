import unittest
from pathlib import Path

from pipeline.docs import taxonomy_md, KIND_MEANING, OPERATOR_MEANING
from pipeline.schema import V

ROOT = Path(__file__).resolve().parents[2]


class Taxonomy(unittest.TestCase):
    def test_committed_file_is_current(self):
        self.assertEqual((ROOT / "TAXONOMY.md").read_text(encoding="utf-8"), taxonomy_md(),
                         "TAXONOMY.md is stale: run python -m pipeline taxonomy")

    def test_every_code_has_a_meaning(self):
        self.assertEqual(set(V["message_kind"]), set(KIND_MEANING))
        self.assertEqual(set(V["operator"]), set(OPERATOR_MEANING))


if __name__ == "__main__":
    unittest.main()
