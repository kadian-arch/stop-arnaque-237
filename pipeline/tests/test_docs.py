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



class Citation(unittest.TestCase):
    def test_zenodo_and_citation_agree(self):
        import json
        z = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
        cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertEqual(z["upload_type"], "dataset")
        self.assertIn(f'title: "{z["title"]}"', cff)
        for c in z["creators"]:
            family, given = c["name"].split(", ")
            self.assertIn(f"family-names: {family}\n    given-names: {given}", cff)


if __name__ == "__main__":
    unittest.main()
