from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "loop" / "economics.py"
spec = importlib.util.spec_from_file_location("economics", MODULE_PATH)
economics = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(economics)


def test_charge_credit_and_solvency(tmp_path: Path) -> None:
    ledger = tmp_path / "economics.json"
    economics.cmd_init(Namespace(ledger=str(ledger), starting_balance="10", force=False))

    economics.append_entry(
        Namespace(
            ledger=str(ledger), amount="3.25", source="provider", ref="run-1", note="", quality=None
        ),
        "charge",
    )
    economics.append_entry(
        Namespace(
            ledger=str(ledger), amount="8", source="rubric", ref="task-1", note="", quality="0.75"
        ),
        "credit",
    )

    data = json.loads(ledger.read_text(encoding="utf-8"))
    assert data["starting_balance"] == "10.000000"
    assert data["total_cost"] == "3.250000"
    assert data["gross_value"] == "8.000000"
    assert data["net_value"] == "4.750000"
    assert data["balance"] == "14.750000"
    assert data["solvent"] is True


def test_bankruptcy_is_fail_closed(tmp_path: Path) -> None:
    ledger = tmp_path / "economics.json"
    economics.cmd_init(Namespace(ledger=str(ledger), starting_balance="1", force=False))
    economics.append_entry(
        Namespace(
            ledger=str(ledger), amount="1.01", source="provider", ref="run-1", note="", quality=None
        ),
        "charge",
    )
    data = json.loads(ledger.read_text(encoding="utf-8"))
    assert data["balance"] == "-0.010000"
    assert data["solvent"] is False


def test_quality_must_be_bounded(tmp_path: Path) -> None:
    ledger = tmp_path / "economics.json"
    economics.cmd_init(Namespace(ledger=str(ledger), starting_balance="10", force=False))
    args = Namespace(
        ledger=str(ledger), amount="5", source="rubric", ref="task-1", note="", quality="1.1"
    )
    try:
        economics.append_entry(args, "credit")
    except ValueError as exc:
        assert "quality" in str(exc)
    else:
        raise AssertionError("expected quality bound failure")


def test_negative_amount_rejected() -> None:
    try:
        economics.money("-0.01")
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("expected negative amount failure")
