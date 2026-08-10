from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
ECONOMIC_LOOP = ROOT / "loop" / "economic_loop.py"
ECONOMICS = ROOT / "loop" / "economics.py"


class EconomicGovernorTests(unittest.TestCase):
    def _write_executable(self, path: Path, body: str) -> Path:
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
        return path

    def _fake_codex(self, root: Path) -> Path:
        marker = root / "watcher-called.txt"
        return self._write_executable(
            root / "fake-codex.py",
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                from pathlib import Path
                import sys

                args = sys.argv[1:]
                model = args[args.index('-m') + 1]
                out = Path(args[args.index('-o') + 1])
                out.parent.mkdir(parents=True, exist_ok=True)
                sys.stdin.read()
                if model == 'runner':
                    out.write_text('DONE: runner claims completion\\n', encoding='utf-8')
                elif model == 'watcher':
                    Path({str(marker)!r}).write_text('called\\n', encoding='utf-8')
                    out.write_text(
                        'GOAL: prove independent acceptance\\n'
                        'LAYER: LEARNING\\n'
                        'QUALITY: 0.20\\n'
                        'ACCEPT: no\\n'
                        'KEPT: runner produced an artifact\\n'
                        'WASTED: none\\n'
                        'FAILED: acceptance evidence is missing\\n'
                        'NEXT: add the missing evidence\\n',
                        encoding='utf-8',
                    )
                elif model == 'rewriter':
                    out.write_text('CHANGE: preserve acceptance criteria and request evidence\\n', encoding='utf-8')
                else:
                    raise SystemExit(f'unexpected model: {{model}}')
                """
            ),
        )

    def _cost_hook(self, root: Path) -> tuple[Path, Path]:
        log = root / "cost-roles.txt"
        hook = self._write_executable(
            root / "cost-hook.py",
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                from pathlib import Path
                import json
                import sys

                args = sys.argv[1:]
                role = args[0] if args and args[0] in {{'runner', 'watcher', 'rewriter'}} else 'cycle'
                cycle = args[1] if len(args) > 1 else (args[0] if args else '0')
                path = Path({str(log)!r})
                with path.open('a', encoding='utf-8') as f:
                    f.write(role + '\\n')
                print(json.dumps({{
                    'amount_usd': 0.01,
                    'receipt': f'provider:{{role}}:{{cycle}}',
                    'note': 'deterministic test receipt',
                }}))
                """
            ),
        )
        return hook, log

    def _earn_hook(self, root: Path) -> tuple[Path, Path]:
        marker = root / "earn-called.txt"
        hook = self._write_executable(
            root / "earn-hook.py",
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                from pathlib import Path
                import json
                Path({str(marker)!r}).write_text('called\\n', encoding='utf-8')
                print(json.dumps({{'amount_usd': 5, 'receipt': 'order:test-1', 'note': 'must not be credited'}}))
                """
            ),
        )
        return hook, marker

    def test_runner_done_cannot_bypass_independent_watcher_or_credit_earnings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            (workdir / "prompt.md").write_text(
                "Produce evidence. DONE requires independent watcher acceptance.\n",
                encoding="utf-8",
            )
            (workdir / "log.md").write_text("", encoding="utf-8")
            codex = self._fake_codex(workdir)
            cost_hook, cost_log = self._cost_hook(workdir)
            earn_hook, earn_marker = self._earn_hook(workdir)

            env = os.environ.copy()
            env.update(
                {
                    "WORKDIR": str(workdir),
                    "CYCLES_DIR": str(workdir / "economic-cycles"),
                    "CODEX_BIN": str(codex),
                    "RUNNER_MODEL": "runner",
                    "WATCHER_MODEL": "watcher",
                    "REWRITER_MODEL": "rewriter",
                    "ECON_MODE": "real",
                    "START_BALANCE_USD": "10",
                    "MAX_CYCLES": "1",
                    "COST_HOOK": str(cost_hook),
                    "EARN_HOOK": str(earn_hook),
                }
            )
            completed = subprocess.run(
                [sys.executable, str(ECONOMIC_LOOP)],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertTrue((workdir / "watcher-called.txt").exists(), completed.stdout + completed.stderr)
            self.assertFalse(earn_marker.exists(), "real earnings hook ran even though watcher rejected the task")
            self.assertNotIn("DONE: task completed", completed.stdout)
            roles = cost_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(roles, ["runner", "watcher", "rewriter"])

    def test_duplicate_real_receipt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "economics.json"
            common = [
                sys.executable,
                str(ECONOMICS),
                "--ledger",
                str(ledger),
                "--start-balance",
                "10",
                "cost",
                "--amount",
                "0.10",
                "--receipt",
                "provider:duplicate",
            ]
            first = subprocess.run(common, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            second = subprocess.run(common, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotEqual(second.returncode, 0, "duplicate receipt was accepted twice")


if __name__ == "__main__":
    unittest.main()
