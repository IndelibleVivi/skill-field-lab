from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class SchemaSyntaxTests(unittest.TestCase):
    def test_all_json_schemas_are_valid_json_and_draft_2020_12(self) -> None:
        schemas = sorted((ROOT / "schemas").rglob("*.schema.json"))
        self.assertGreaterEqual(len(schemas), 15)
        for path in schemas:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(value.get("$schema"), "https://json-schema.org/draft/2020-12/schema")

        v2_names = {path.name for path in (ROOT / "schemas" / "v2").glob("*.schema.json")}
        self.assertEqual(
            v2_names,
            {
                "candidate.schema.json",
                "case.schema.json",
                "claim.schema.json",
                "decision.schema.json",
                "lab.schema.json",
                "migration-receipt.schema.json",
                "plan.schema.json",
                "receipt.schema.json",
                "review.schema.json",
            },
        )


if __name__ == "__main__":
    unittest.main()
