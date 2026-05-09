from __future__ import annotations

from scientific_calculator.cli import main


def test_cli_success(capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["calc", "2+2"])
    code = main()
    out = capsys.readouterr().out.strip()
    assert code == 0
    assert out == "4.0"


def test_cli_error(capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["calc", "x+2"])
    code = main()
    out = capsys.readouterr().out.strip()
    assert code == 1
    assert out.startswith("error:")
