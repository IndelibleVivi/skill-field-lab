from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from fieldlab.process import run_bounded_process


def pid_is_running(pid: int) -> bool:
    try:
        completed = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    status = completed.stdout.strip()
    return bool(status) and not status.startswith("Z")


@unittest.skipUnless(os.name == "posix", "v0.2 live execution is POSIX-only")
class ProcessIsolationTests(unittest.TestCase):
    def test_timeout_kills_descendant_before_artifacts_are_sealed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            sentinel = root / "late.txt"
            parent = root / "parent.py"
            parent.write_text(
                """#!/bin/sh
sentinel="$1"
(
  sleep 5
  printf late > "$sentinel"
  printf 'late-trace\n'
  sleep 60
) &
printf 'child_pid=%s\n' "$!"
sleep 60
""",
                encoding="utf-8",
            )
            parent.chmod(0o755)
            stdout = root / "trace.jsonl"
            stderr = root / "stderr.log"
            result = run_bounded_process(
                [str(parent), str(sentinel)],
                cwd=root,
                stdout_path=stdout,
                stderr_path=stderr,
                timeout_seconds=2,
                grace_seconds=0.3,
                kill_seconds=0.5,
            )
            sealed_size = stdout.stat().st_size
            text = stdout.read_text(encoding="utf-8")
            self.assertIn(
                "child_pid=",
                text,
                f"descendant did not start before the process timeout; trace={text!r}",
            )
            child_pid = int(text.split("child_pid=", 1)[1].splitlines()[0])
            time.sleep(5.2)
            self.assertTrue(result.timed_out)
            self.assertTrue(result.quiescent)
            self.assertFalse(sentinel.exists())
            self.assertEqual(stdout.stat().st_size, sealed_size)
            self.assertNotIn("late-trace", stdout.read_text(encoding="utf-8"))
            self.assertFalse(pid_is_running(child_pid))

    def test_clean_success_remains_clean(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            script = root / "ok.py"
            script.write_text("print('ok', flush=True)\n", encoding="utf-8")
            result = run_bounded_process(
                [sys.executable, str(script)],
                cwd=root,
                stdout_path=root / "stdout.log",
                stderr_path=root / "stderr.log",
                timeout_seconds=2,
            )
            self.assertEqual(result.return_code, 0)
            self.assertFalse(result.timed_out)
            self.assertTrue(result.quiescent)
            self.assertFalse(result.orphan_descendants)
            self.assertEqual(result.termination_reason, "exited")


    def test_parent_exit_with_live_descendant_is_not_clean_success(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            sentinel = root / "orphan-late.txt"
            script = root / "orphan.sh"
            script.write_text(
                """#!/bin/sh
sentinel="$1"
(sleep 1.0; printf late > "$sentinel"; sleep 60) &
exit 0
""",
                encoding="utf-8",
            )
            script.chmod(0o755)
            result = run_bounded_process(
                [str(script), str(sentinel)],
                cwd=root,
                stdout_path=root / "orphan-stdout.log",
                stderr_path=root / "orphan-stderr.log",
                timeout_seconds=3,
                grace_seconds=0.3,
                kill_seconds=0.5,
            )
            time.sleep(1.2)
            self.assertTrue(result.quiescent)
            self.assertTrue(result.orphan_descendants)
            self.assertEqual(result.termination_reason, "orphan-descendants")
            self.assertFalse(sentinel.exists())

    def test_keyboard_interrupt_uses_same_group_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            sentinel = root / "interrupt-late.txt"
            target = root / "target.py"
            target.write_text(
                """import subprocess
import sys
import time
from pathlib import Path

sentinel = Path(sys.argv[1])
code = (
    "import time; from pathlib import Path; "
    "time.sleep(0.9); "
    f"Path({str(sentinel)!r}).write_text('late', encoding='utf-8'); time.sleep(60)"
)
subprocess.Popen([sys.executable, "-c", code])
time.sleep(60)
""",
                encoding="utf-8",
            )
            harness = root / "harness.py"
            package_root = Path(__file__).resolve().parent.parent
            harness.write_text(
                f"""import os
import signal
import sys
import threading
from pathlib import Path
sys.path.insert(0, {str(package_root)!r})
from fieldlab.process import run_bounded_process

def interrupt():
    os.kill(os.getpid(), signal.SIGINT)

timer = threading.Timer(0.25, interrupt)
timer.start()
try:
    run_bounded_process(
        [sys.executable, {str(target)!r}, {str(sentinel)!r}],
        cwd=Path({str(root)!r}),
        stdout_path=Path({str(root / 'ki-stdout.log')!r}),
        stderr_path=Path({str(root / 'ki-stderr.log')!r}),
        timeout_seconds=60,
        grace_seconds=0.3,
        kill_seconds=0.5,
    )
except KeyboardInterrupt:
    print('caught')
else:
    raise SystemExit('interrupt was not raised')
finally:
    timer.cancel()
""",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(harness)],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            time.sleep(1.1)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("caught", completed.stdout)
            self.assertFalse(sentinel.exists())


if __name__ == "__main__":
    unittest.main()
