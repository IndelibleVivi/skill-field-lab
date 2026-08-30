from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fieldlab.io import sha256_file
from fieldlab.receipts import human_review_record


class ReviewRecordTests(unittest.TestCase):
    def test_human_review_binds_digest_without_mutating_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            receipt_path = Path(raw) / "receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "receipt_type": "attempt",
                        "outcome": "pass",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            before = sha256_file(receipt_path)
            review = human_review_record(
                review_id="bounded-review",
                receipt_path=receipt_path,
                independence="separate-agent",
                judgment="supported",
                rationale="The final response stays within the supplied authority.",
            )
            self.assertEqual(review["receipt"]["sha256"], before)
            self.assertEqual(sha256_file(receipt_path), before)


if __name__ == "__main__":
    unittest.main()
