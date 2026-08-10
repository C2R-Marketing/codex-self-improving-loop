from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOOP = ROOT / "loop" / "loop.sh"


def _fake_codex(root: Path) -> Path:
    script = root / "fake_codex.py"
    script.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import sys
args=sys.argv[1:]
out=Path(args[args.index('-o')+1])
out.parent.mkdir(parents=True, exist_ok=True)
name=out.name
if '-run.md' in name:
    out.write_text('DONE: runner claims completion\\n', encoding='utf-8')
elif '-watch.md' in name:
    out.write_text('GOAL: verify task\\nACCEPT: no\\nKEPT: none\\nWASTED: premature DONE\\nFAILED: acceptance evidence missing\\nNEXT: add evidence\\n', encoding='utf-8')
else:
    out.write_text('CHANGE: keep acceptance criteria and request evidence\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def test_runner_done_cannot_bypass_watcher() -> None:
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        fake = _fake_codex(workdir)
        (workdir / "prompt.md").write_text("Prove the task.\n", encoding="utf-8")
        (workdir / "log.md").write_text("", encoding="utf-8")
        cycles = workdir / "cycles"
        env = os.environ.copy()
        env.update(
            {
                "CODEX_BIN": str(fake),
                "RUNNER_MODEL": "runner",
                "WATCHER_MODEL": "watcher",
                "REWRITER_MODEL": "rewriter",
                "MAX_CYCLES": "1",
                "NO_PROGRESS_LIMIT": "2",
                "CYCLES_DIR": str(cycles),
            }
        )
        proc = subprocess.run(
            ["bash", str(LOOP), "--workdir", str(workdir), "--max-cycles", "1"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        state = json.loads((cycles / "state.json").read_text(encoding="utf-8"))
        assert state["status"] != "done", state
        assert (cycles / "cycle-01-watch.md").exists()
        assert (cycles / "cycle-01-rewrite.md").exists()
