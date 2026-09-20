from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fieldlab.errors import ConfigError
from fieldlab.io import atomic_write_json, read_json
from fieldlab.plan import build_plan
from fieldlab.runner import run_plan
from tests.test_evidence_sealing import create_lab, write_fake_codex
from tests.test_subjects import git


class SubjectDeliveryTests(unittest.TestCase):
    def prepare(self, root, *, source_type='local-path', body='', repeat=2, matched=False):
        manifest = create_lab(root, result_assertions={'text_contains': ['done']})
        source = root / 'lab' / 'subject'
        source.mkdir()
        (source / 'SKILL.md').write_text('planned A\n')
        lab = read_json(manifest)
        lab['subjects']['skill'] = {
            'kind': 'agent-skill',
            'source': {'type': source_type, 'path': 'subject'},
        }
        atomic_write_json(manifest, lab)
        fake = root / 'fake-codex'
        counter = root / 'calls.txt'
        write_fake_codex(fake, f"with Path({str(counter)!r}).open('a') as f: f.write('call\\n')\n" + body)
        plan = build_plan(
            manifest_path=manifest,
            subject_ids=['isolated-control', 'skill'] if matched else ['skill'],
            case_ids=['protected-repair'], mode='matched' if matched else 'canary',
            repeat=repeat, model='fake', reasoning_effort='high', codex_bin=str(fake),
            run_id='delivery', output_root=None, timeout_override=5, keep_workspace=False,
        )
        return manifest, plan, source, counter

    def execute(self, root, plan):
        plan_path = root / 'plan.json'
        atomic_write_json(plan_path, plan)
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_plan(plan_path, live=True, max_invocations=plan['target_invocations'], resume=False)
        run_dir = root / 'lab' / 'runs' / 'delivery'
        return code, read_json(run_dir / 'summary.json'), run_dir

    def test_mutable_source_drift_stops_later_repeats_before_invocation(self):
        for source_type in ('local-path', 'snapshot'):
            with self.subTest(source_type=source_type), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                source = root / 'lab' / 'subject' / 'SKILL.md'
                _, plan, _, counter = self.prepare(
                    root, source_type=source_type, repeat=3,
                    body=f"Path({str(source)!r}).write_text('changed B\\n')\n",
                )
                code, summary, run_dir = self.execute(root, plan)
                self.assertEqual(code, 1)
                self.assertEqual(summary['state'], 'input-drift')
                self.assertEqual(counter.read_text(), 'call\n')
                self.assertEqual(len(summary['attempts']), 2)
                self.assertEqual(summary['attempts'][0]['subject_delivery']['status'], 'verified')
                failed = summary['attempts'][1]
                self.assertEqual(failed['target_agent_invocations'], 0)
                self.assertIsNone(failed['process'])
                self.assertNotIn('trace', failed['artifacts'])
                delivery = failed['subject_delivery']
                self.assertNotEqual(delivery['expected_tree_sha256'], delivery['actual_tree_sha256'])
                attempt = run_dir / 'skill/protected-repair/repeat-002/attempt-001'
                receipt = read_json(attempt / 'receipt.json')
                verification = read_json(attempt / 'verification.json')
                self.assertEqual(receipt['subject_delivery'], delivery)
                self.assertEqual(verification['subject_delivery'], delivery)
                self.assertEqual(receipt['target_agent_invocations'], 0)
                self.assertFalse(receipt['execution_boundary']['target_started'])
                self.assertFalse((attempt / 'trace.jsonl').exists())
                self.assertFalse((attempt / 'workspace').exists())

    def test_moving_git_ref_delivers_planned_commit_to_every_repeat(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest, _, source, counter = self.prepare(root)
            repo = source.parent
            git(repo, 'init', '-q')
            git(repo, 'config', 'user.name', 'Test')
            git(repo, 'config', 'user.email', 'test@example.invalid')
            git(repo, 'add', 'subject')
            git(repo, 'commit', '--no-gpg-sign', '-qm', 'A')
            a = git(repo, 'rev-parse', 'HEAD')
            (source / 'SKILL.md').write_text('changed B\n')
            git(repo, 'commit', '--no-gpg-sign', '-qam', 'B')
            b = git(repo, 'rev-parse', 'HEAD')
            git(repo, 'branch', 'moving', a)
            lab = read_json(manifest)
            lab['subjects']['skill']['source'] = {
                'type': 'local-git-ref', 'repo': '.', 'ref': 'moving', 'subpath': 'subject',
            }
            atomic_write_json(manifest, lab)
            fake = root / 'fake-codex'
            write_fake_codex(fake, f"""import subprocess
assert (workspace / '.agents/skills/skill/SKILL.md').read_text() == 'planned A\\n'
with Path({str(counter)!r}).open('a') as f: f.write('A\\n')
subprocess.run(['git', '-C', {str(repo)!r}, 'update-ref', 'refs/heads/moving', {b!r}], check=True)
""")
            plan = build_plan(
                manifest_path=manifest, subject_ids=['skill'], case_ids=['protected-repair'],
                mode='canary', repeat=2, model='fake', reasoning_effort='high', codex_bin=str(fake),
                run_id='delivery', output_root=None, timeout_override=5, keep_workspace=False,
            )
            code, summary, _ = self.execute(root, plan)
            self.assertEqual(code, 0)
            self.assertEqual(git(repo, 'rev-parse', 'moving'), b)
            self.assertEqual(counter.read_text(), 'A\nA\n')
            self.assertEqual(summary['identity']['subjects'], plan['planned_inputs']['subjects'])
            for attempt in summary['attempts']:
                delivery = attempt['subject_delivery']
                self.assertEqual(delivery['requested_ref'], 'moving')
                self.assertEqual(delivery['resolved_commit'], a)
                self.assertEqual(delivery['status'], 'verified')

    def test_matched_matrix_records_delivery_for_each_control_and_skill_repeat(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, plan, _, counter = self.prepare(root, matched=True)
            code, summary, run_dir = self.execute(root, plan)
            self.assertEqual(code, 0)
            self.assertEqual(len(summary['attempts']), 4)
            self.assertEqual(len(counter.read_text().splitlines()), 4)
            for attempt_path in run_dir.glob('**/attempt-001'):
                receipt = read_json(attempt_path / 'receipt.json')
                verification = read_json(attempt_path / 'verification.json')
                metadata = read_json(attempt_path / 'metadata.json')
                self.assertEqual(receipt['subject_delivery'], verification['subject_delivery'])
                self.assertEqual(receipt['subject_delivery'], metadata['subject_delivery'])
                delivery = receipt['subject_delivery']
                self.assertEqual(delivery['status'], 'verified')
                self.assertEqual(delivery['actual_tree_sha256'], delivery['expected_tree_sha256'])
                if receipt['subject_id'] == 'isolated-control':
                    self.assertIsNone(delivery['mount'])
                    self.assertIsNone(delivery['actual_tree_sha256'])
                self.assertEqual(receipt['host_selection']['status'], 'unknown')
                self.assertEqual(receipt['content_application']['status'], 'requires-semantic-review')
                self.assertEqual(receipt['declared_activation'], 'implicit')

    def test_unplanned_file_in_mount_prevents_first_invocation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manifest, _, _, counter = self.prepare(root)
            extra = manifest.parent / 'cases/protected-repair/fixture/.agents/skills/skill/extra.md'
            extra.parent.mkdir(parents=True)
            extra.write_text('unplanned instructions')
            plan = build_plan(
                manifest_path=manifest, subject_ids=['skill'], case_ids=['protected-repair'],
                mode='canary', repeat=1, model='fake', reasoning_effort='high',
                codex_bin=str(root / 'fake-codex'), run_id='delivery', output_root=None,
                timeout_override=5, keep_workspace=False,
            )
            code, summary, _ = self.execute(root, plan)
            self.assertEqual(code, 1)
            self.assertEqual(summary['state'], 'input-drift')
            self.assertFalse(counter.exists())

    def test_materialization_error_is_preflight_failure_not_termination(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, plan, _, counter = self.prepare(root)
            with patch('fieldlab.runner.prepare_workspace', side_effect=ConfigError('source disappeared')):
                code, summary, _ = self.execute(root, plan)
            self.assertEqual(code, 1)
            self.assertEqual(summary['state'], 'preflight-failed')
            self.assertEqual(summary['attempts'][0]['target_agent_invocations'], 0)
            self.assertFalse(counter.exists())
