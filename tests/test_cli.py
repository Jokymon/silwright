from pathlib import Path

import pytest

from silwright import cli


def test_cli_generates_all_outputs_after_all_rendering_succeeds(tmp_path: Path) -> None:
    definition = tmp_path / "syntax.ndef"
    definition.write_text("module syntax\nnode Value\n    value: number\nend\n")
    (tmp_path / "backend_cpp.map").write_text("number: long\n")

    assert cli.main((str(definition),)) == 0

    assert (tmp_path / "syntax.hpp").exists()
    assert (tmp_path / "syntax.cpp").exists()
    assert (tmp_path / "syntax_dump.hpp").exists()
    assert (tmp_path / "syntax_dump.ipp").exists()
    assert (tmp_path / "syntax_dump.cpp").exists()
    assert (tmp_path / "syntax_visitor.hpp").exists()
    assert (tmp_path / "syntax_visitor.cpp").exists()
    assert (tmp_path / "syntax_transformer.hpp").exists()
    assert (tmp_path / "syntax_transformer.cpp").exists()


def test_cli_render_failure_does_not_write_partial_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    definition = tmp_path / "syntax.ndef"
    definition.write_text("module syntax\nnode Value\n    value: number\nend\n")
    (tmp_path / "backend_cpp.map").write_text("number: long\n")

    def fail_transformer(*args: object, **kwargs: object) -> object:
        raise RuntimeError("transformer failed")

    monkeypatch.setattr(cli, "generate_transformer_cpp", fail_transformer)

    assert cli.main((str(definition),)) == 1
    captured = capsys.readouterr()

    assert "error[SW2001]: generation failed: transformer failed" in captured.err
    assert "module syntax" in captured.err
    assert "^" in captured.err

    assert not (tmp_path / "syntax.hpp").exists()
    assert not (tmp_path / "syntax.cpp").exists()
    assert not (tmp_path / "syntax_dump.hpp").exists()
    assert not (tmp_path / "syntax_dump.ipp").exists()
    assert not (tmp_path / "syntax_dump.cpp").exists()
    assert not (tmp_path / "syntax_visitor.hpp").exists()
    assert not (tmp_path / "syntax_visitor.cpp").exists()
    assert not (tmp_path / "syntax_transformer.hpp").exists()
    assert not (tmp_path / "syntax_transformer.cpp").exists()


def test_cli_reports_syntax_error_with_source_context(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    definition = tmp_path / "syntax.ndef"
    definition.write_text("module syntax\nnode Value\n    value: \nend\n")
    (tmp_path / "backend_cpp.map").write_text("number: long\n")

    assert cli.main((str(definition),)) == 1
    captured = capsys.readouterr()

    assert f"{definition}:3:12: error[SW0001]: invalid syntax" in captured.err
    assert "    value: " in captured.err
    assert "           ^" in captured.err


def test_cli_reports_semantic_error_with_source_context(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    definition = tmp_path / "syntax.ndef"
    definition.write_text("module syntax\nnode Value\n    value: missing\nend\n")
    (tmp_path / "backend_cpp.map").write_text("number: long\n")

    assert cli.main((str(definition),)) == 1
    captured = capsys.readouterr()

    assert (
        f"{definition}:3:12: error[SW1008]: unknown field type 'missing' in Value"
        in captured.err
    )
    assert "    value: missing" in captured.err
    assert "           ^" in captured.err
