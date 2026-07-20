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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    definition = tmp_path / "syntax.ndef"
    definition.write_text("module syntax\nnode Value\n    value: number\nend\n")
    (tmp_path / "backend_cpp.map").write_text("number: long\n")

    def fail_transformer(*args: object, **kwargs: object) -> object:
        raise RuntimeError("transformer failed")

    monkeypatch.setattr(cli, "generate_transformer_cpp", fail_transformer)

    with pytest.raises(RuntimeError, match="transformer failed"):
        cli.main((str(definition),))

    assert not (tmp_path / "syntax.hpp").exists()
    assert not (tmp_path / "syntax.cpp").exists()
    assert not (tmp_path / "syntax_dump.hpp").exists()
    assert not (tmp_path / "syntax_dump.ipp").exists()
    assert not (tmp_path / "syntax_dump.cpp").exists()
    assert not (tmp_path / "syntax_visitor.hpp").exists()
    assert not (tmp_path / "syntax_visitor.cpp").exists()
    assert not (tmp_path / "syntax_transformer.hpp").exists()
    assert not (tmp_path / "syntax_transformer.cpp").exists()
