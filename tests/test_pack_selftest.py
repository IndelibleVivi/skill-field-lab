from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fieldlab.errors import ConfigError
from fieldlab.selftest import selftest_pack


ROOT = Path(__file__).resolve().parents[1]


class PackSelftestTests(unittest.TestCase):
    def test_demo_and_legal_expected_overlays_are_credible(self) -> None:
        demo = selftest_pack(ROOT / "examples" / "demo" / "fieldlab-pack.json")
        legal = selftest_pack(ROOT / "examples" / "legal-research" / "fieldlab-pack.json")
        self.assertEqual(demo["target_agent_invocations"], 0)
        self.assertEqual([item["case_id"] for item in demo["cases"]], ["tiny-copy"])
        self.assertEqual([item["case_id"] for item in legal["cases"]], ["authority-boundary"])

    def test_selftest_rejects_missing_expected_overlay(self) -> None:
        # The contract validator permits packs whose oracle is external/human; the
        # deterministic selftest command must fail clearly when expected/ is absent.
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cases = root / "cases" / "case-one"
            fixture = cases / "fixture"
            subject = root / "subject" / "scope"
            fixture.mkdir(parents=True)
            subject.mkdir(parents=True)
            (fixture / "value.txt").write_text("old\n", encoding="utf-8")
            (cases / "prompt.md").write_text("change it\n", encoding="utf-8")
            (cases / "case.json").write_text(
                '{"schema_version":1,"case_id":"case-one","description":"missing expected",'
                '"prompt_file":"prompt.md","sandbox":"workspace-write","timeout_seconds":30,'
                '"assertions":[{"type":"file_equals","path":"value.txt","value":"new\\n"}]}\n',
                encoding="utf-8",
            )
            (subject / "SKILL.md").write_text("---\nname: scope\ndescription: test\n---\n", encoding="utf-8")
            pack = root / "fieldlab-pack.json"
            pack.write_text(
                '{"schema_version":1,"pack_id":"missing-expected","description":"test",'
                '"cases_root":"cases","subjects":{"subject-one":{"label":"subject",'
                '"attribution":"repo_scoped","overlays":[{"source":"subject",'
                '"target":".agents/skills"}]}},"defaults":{"adapter":"codex-exec",'
                '"approval_policy":"never","network_access":false,"output_root":".fieldlab",'
                '"keep_workspace":false}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigError, "expected/ directory"):
                selftest_pack(pack)


if __name__ == "__main__":
    unittest.main()
