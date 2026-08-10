#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ECON = ROOT / "loop" / "economics.py"


class EconomicsTests(unittest.TestCase):
    def invoke(self, ledger: Path, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            [sys.executable, str(ECON), "--ledger", str(ledger), "--start-balance", "10", *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if ok and proc.returncode != 0:
            self.fail(proc.stderr)
        return proc

    def test_real_entries_require_receipts_and_change_balance(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "economics.json"
            denied = self.invoke(ledger, "cost", "--amount", "1.25", ok=False)
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn("require --receipt", denied.stderr)

            self.invoke(ledger, "cost", "--amount", "1.25", "--receipt", "provider:abc")
            self.invoke(ledger, "earn", "--amount", "4.00", "--receipt", "order:123")
            state = json.loads(self.invoke(ledger, "status").stdout)
            self.assertEqual(state["real_cost"], "1.250000")
            self.assertEqual(state["real_income"], "4.000000")
            self.assertEqual(state["real_balance"], "12.750000")
            self.assertTrue(state["solvent"])

    def test_simulated_income_never_inflates_real_balance(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "economics.json"
            self.invoke(ledger, "earn", "--amount", "5000", "--mode", "simulated")
            state = json.loads(self.invoke(ledger, "status").stdout)
            self.assertEqual(state["real_balance"], "10.000000")
            self.assertEqual(state["real_income"], "0")
            self.assertEqual(state["simulated_income"], "5000.000000")

    def test_bankruptcy_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "economics.json"
            self.invoke(ledger, "cost", "--amount", "10.01", "--receipt", "provider:overrun")
            state = json.loads(self.invoke(ledger, "status").stdout)
            self.assertFalse(state["solvent"])
            self.assertEqual(state["real_balance"], "-0.010000")


if __name__ == "__main__":
    unittest.main()
