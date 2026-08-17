from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from fieldlab.contracts import load_cases, load_pack


class SoftpowersCompanionTests(unittest.TestCase):
    def test_copy_into_root_manifests_resolve_after_materialization(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        companion = project_root / "softpowers-companion"
        with tempfile.TemporaryDirectory() as raw:
            softpowers = Path(raw) / "softpowers"
            (softpowers / "evals").mkdir(parents=True)
            shutil.copytree(companion / "evals" / "cases", softpowers / "evals" / "cases")
            shutil.copytree(project_root / "skills", softpowers / "skills")

            single = softpowers / "fieldlab-pack.json"
            shutil.copy2(
                companion / "fieldlab-pack.copy-into-softpowers-root.json",
                single,
            )
            pack, _, cases_root = load_pack(single)
            self.assertEqual(pack["pack_id"], "softpowers")
            self.assertEqual(set(load_cases(cases_root)), {"tiny-copy", "stale-cursor", "spec-chain"})

            baseline = softpowers / ".fieldlab-subjects" / "baseline-skills"
            shutil.copytree(project_root / "skills", baseline)
            matched = softpowers / "fieldlab-pack.matched.json"
            shutil.copy2(
                companion / "fieldlab-pack.matched.copy-into-softpowers-root.json",
                matched,
            )
            matched_pack, _, matched_cases = load_pack(matched)
            self.assertEqual(matched_pack["pack_id"], "softpowers-matched")
            self.assertEqual(len(matched_pack["subjects"]), 2)
            self.assertEqual(set(load_cases(matched_cases)), {"tiny-copy", "stale-cursor", "spec-chain"})


if __name__ == "__main__":
    unittest.main()
