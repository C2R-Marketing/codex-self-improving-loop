from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "loop" / "economic_loop.py"


class EconomicLoopTests(unittest.TestCase):
    def _fake_codex(self, root: Path) -> Path:
        fake = root / "fake_codex.py"
        fake.write_text(
            """#!/usr/bin/env python3
from pathlib import Path
import sys
args = sys.argv[1:]
out = Path(args[args.index('-o') + 1])
out.parent.mkdir(parents=True, exist_ok=True)
if '-run.md' in out.name:
    text = 'DONE: verified task complete\\n'
elif '-watch.md' in out.name:
    text = ('GOAL: finish task\\nSCORE: 100\\nACCEPT: yes\\n'
            'KEPT: verified output\\nWASTED: none\\nFAILED: none\\nNEXT: STOP\\n')
else:
    text = 'CHANGE: no rewrite needed\\n'
out.write_text(text, encoding='utf-8')
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        return fake

    def test_accepted_work_earns_payment_after_costs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = self._fake_codex(root)
            (root / "prompt.md").write_text(
                "Complete the task. Acceptance: verified output. End with DONE:.\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--workdir",
                    str(root),
                    "--codex",
                    str(fake),
                    "--start-balance",
                    "10",
                    "--task-value",
                    "100",
                    "--runner-call-cost",
                    "0.10",
                    "--watcher-call-cost",
                    "0.10",
                    "--rewriter-call-cost",
                    "0.50",
                    "--max-cycles",
                    "1",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            state = json.loads((root / "economic-cycles" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "done")
            self.assertAlmostEqual(state["total_cost"], 0.20)
            self.assertAlmostEqual(state["total_income"], 100.0)
            self.assertAlmostEqual(state["balance"], 109.80)
            ledger = [
                json.loads(line)
                for line in (root / "economic-cycles" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(any(row.get("event") == "payment" for row in ledger))
            self.assertFalse(any(row.get("role") == "rewriter" for row in ledger))

    def test_bankruptcy_stops_before_unaffordable_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = self._fake_codex(root)
            (root / "prompt.md").write_text("Do work.\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--workdir",
                    str(root),
                    "--codex",
                    str(fake),
                    "--start-balance",
                    "0.05",
                    "--runner-call-cost",
                    "0.10",
                    "--max-cycles",
                    "1",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            state = json.loads((root / "economic-cycles" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "bankrupt")
            self.assertAlmostEqual(state["balance"], 0.05)


if __name__ == "__main__":
    unittest.main()
