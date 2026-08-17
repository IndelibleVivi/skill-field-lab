from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class SchemaSyntaxTests(unittest.TestCase):
    def test_all_json_schemas_are_valid_json_and_draft_2020_12(self) -> None:
        schemas = sorted((ROOT / "schemas").glob("*.schema.json"))
        self.assertGreaterEqual(len(schemas), 7)
        for path in schemas:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(value.get("$schema"), "https://json-schema.org/draft/2020-12/schema")


if __name__ == "__main__":
    unittest.main()
