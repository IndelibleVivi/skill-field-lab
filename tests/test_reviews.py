from __future__ import annotations

import json
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from fieldlab.cli import MAX_REQUIREMENT_OUTCOMES_BYTES, main
from fieldlab.io import sha256_file
from fieldlab.receipts import human_review_record


ROOT = Path(__file__).resolve().parent.parent


class ReviewRecordTests(unittest.TestCase):
    def write_receipt(self, root: Path, requirements: list[str]) -> Path:
        path = root / "receipt.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "receipt_type": "attempt",
                    "outcome": "pass",
                    "verification_summary": {
                        "human_review": {
                            "required": bool(requirements),
                            "requirements": requirements,
                        }
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def run_review(
        self,
        receipt: Path,
        output: Path,
        outcomes: Path | None = None,
    ) -> int:
        args = [
            "review",
            str(ROOT / "examples/demo/fieldlab.json"),
            "--review-id",
            "bounded-review",
            "--receipt",
            str(receipt),
            "--independence",
            "separate-agent",
            "--judgment",
            "supported",
            "--rationale",
            "Every declared requirement is supported by the inspected evidence.",
            "--output",
            str(output),
        ]
        if outcomes is not None:
            args.extend(["--requirement-outcomes", str(outcomes)])
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return main(args)

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
            self.assertEqual(review["requirement_outcomes"], {})
            self.assertEqual(sha256_file(receipt_path), before)

    def test_public_cli_records_exact_requirement_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            requirements = ["coverage: inspect the diff", "claim: preserve the boundary"]
            receipt = self.write_receipt(root, requirements)
            outcomes = root / "outcomes.json"
            outcomes.write_text(
                json.dumps({requirement: "supported" for requirement in requirements}),
                encoding="utf-8",
            )
            before = sha256_file(receipt)
            output = root / "review.json"
            self.assertEqual(self.run_review(receipt, output, outcomes), 0)
            review = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                review["requirement_outcomes"],
                {requirement: "supported" for requirement in requirements},
            )
            self.assertEqual(review["receipt"]["sha256"], before)
            self.assertEqual(sha256_file(receipt), before)

    def test_public_cli_requires_outcomes_for_declared_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            receipt = self.write_receipt(root, ["coverage: inspect the diff"])
            output = root / "review.json"
            self.assertEqual(self.run_review(receipt, output), 2)
            self.assertFalse(output.exists())

    def test_public_cli_cannot_overwrite_immutable_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            requirement = "coverage: inspect the diff"
            receipt = self.write_receipt(root, [requirement])
            outcomes = root / "outcomes.json"
            outcomes.write_text(
                json.dumps({requirement: "supported"}), encoding="utf-8"
            )
            before = receipt.read_bytes()
            self.assertEqual(self.run_review(receipt, receipt, outcomes), 2)
            self.assertEqual(receipt.read_bytes(), before)

    def test_public_cli_rejects_invalid_outcome_files(self) -> None:
        requirement = "coverage: inspect the diff"
        variants = {
            "missing": "{}",
            "extra": json.dumps({requirement: "supported", "invented": "supported"}),
            "invalid-value": json.dumps({requirement: "looks-good"}),
            "non-object": "[]",
            "malformed": "{",
            "duplicate": f'{{{json.dumps(requirement)}: "supported", {json.dumps(requirement)}: "inconclusive"}}',
        }
        for name, content in variants.items():
            with self.subTest(variant=name), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                receipt = self.write_receipt(root, [requirement])
                outcomes = root / "outcomes.json"
                outcomes.write_text(content, encoding="utf-8")
                output = root / "review.json"
                self.assertEqual(self.run_review(receipt, output, outcomes), 2)
                self.assertFalse(output.exists())

    def test_public_cli_rejects_symlink_and_oversized_outcome_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            requirement = "coverage: inspect the diff"
            receipt = self.write_receipt(root, [requirement])
            target = root / "target.json"
            target.write_text(json.dumps({requirement: "supported"}), encoding="utf-8")
            symlink = root / "symlink.json"
            symlink.symlink_to(target)
            oversized = root / "oversized.json"
            oversized.write_text(" " * (MAX_REQUIREMENT_OUTCOMES_BYTES + 1), encoding="utf-8")
            for name, outcomes in (("symlink", symlink), ("oversized", oversized)):
                with self.subTest(variant=name):
                    output = root / f"{name}-review.json"
                    self.assertEqual(self.run_review(receipt, output, outcomes), 2)
                    self.assertFalse(output.exists())

    def test_public_cli_rejects_invalid_utf8_and_wrong_root_types(self) -> None:
        requirement = "coverage: inspect the diff"
        variants = {
            "invalid-utf8": b'{"caf\xe9": "supported"}',
            "wrong-root-number": b"42",
            "wrong-root-string": b'"supported"',
            "wrong-root-null": b"null",
        }
        for name, payload in variants.items():
            with self.subTest(variant=name), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                receipt = self.write_receipt(root, [requirement])
                outcomes = root / "outcomes.json"
                outcomes.write_bytes(payload)
                output = root / "review.json"
                self.assertEqual(self.run_review(receipt, output, outcomes), 2)
                self.assertFalse(output.exists())

    def test_public_cli_rejects_non_string_or_unrecognized_outcomes(self) -> None:
        requirement = "coverage: inspect the diff"
        variants = {
            "number": {"requirement": 3},
            "array": {"requirement": ["supported"]},
            "null": {"requirement": None},
            "object": {"requirement": {"status": "supported"}},
            "boolean": {"requirement": True},
        }
        for name, outcomes_value in variants.items():
            with self.subTest(variant=name), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                receipt = self.write_receipt(root, [requirement])
                outcomes = root / "outcomes.json"
                outcomes.write_text(json.dumps(outcomes_value), encoding="utf-8")
                output = root / "review.json"
                self.assertEqual(self.run_review(receipt, output, outcomes), 2)
                self.assertFalse(output.exists())

    def test_public_cli_rejects_symlinked_user_controlled_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            requirement = "coverage: inspect the diff"
            receipt = self.write_receipt(root, [requirement])
            real = root / "real-outcomes"
            real.mkdir()
            target = real / "outcomes.json"
            target.write_text(json.dumps({requirement: "supported"}), encoding="utf-8")
            linked = root / "linked-outcomes"
            linked.symlink_to(real, target_is_directory=True)
            output = root / "review.json"
            self.assertEqual(self.run_review(receipt, output, linked / "outcomes.json"), 2)
            self.assertFalse(output.exists())

    def test_public_cli_accepts_ordinary_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            requirement = "coverage: inspect the diff"
            receipt = self.write_receipt(root, [requirement])
            outcomes = root / "outcomes.json"
            outcomes.write_text(json.dumps({requirement: "supported"}), encoding="utf-8")
            self.assertTrue(outcomes.is_absolute())
            output = root / "review.json"
            self.assertEqual(self.run_review(receipt, output, outcomes), 0)
            self.assertTrue(output.is_file())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO regression is POSIX-only")
    def test_public_cli_rejects_a_fifo_outcome_file_promptly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            requirement = "coverage: inspect the diff"
            receipt = self.write_receipt(root, [requirement])
            fifo = root / "outcomes.fifo"
            os.mkfifo(fifo)
            output = root / "review.json"
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            started = time.monotonic()
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "fieldlab",
                    "review",
                    str(ROOT / "examples/demo/fieldlab.json"),
                    "--review-id",
                    "fifo-review",
                    "--receipt",
                    str(receipt),
                    "--independence",
                    "separate-agent",
                    "--judgment",
                    "supported",
                    "--rationale",
                    "A FIFO must not block the review command.",
                    "--requirement-outcomes",
                    str(fifo),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )
            elapsed = time.monotonic() - started
            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertFalse(output.exists())
            self.assertLess(elapsed, 15)


if __name__ == "__main__":
    unittest.main()
