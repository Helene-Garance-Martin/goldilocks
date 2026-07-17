import json
from pathlib import Path

import typer
from typer.testing import CliRunner

runner = CliRunner()


def _app(command):
    app = typer.Typer()
    app.command()(command)
    return app


def test_explicit_collapse_flag_reaches_json_orchestration(monkeypatch):
    import goldilocks_cli.commands.visualise as command

    captured = {}
    monkeypatch.setattr(
        command,
        "_render_from_json",
        lambda *args, **kwargs: captured.update(kwargs) or [],
    )

    result = runner.invoke(
        _app(command.visualise),
        ["--source", "json", "--collapse"],
    )

    assert result.exit_code == 0
    assert captured["collapse"] is True


def test_explicit_no_collapse_flag_reaches_json_orchestration(monkeypatch):
    import goldilocks_cli.commands.visualise as command

    captured = {}
    monkeypatch.setattr(
        command,
        "_render_from_json",
        lambda *args, **kwargs: captured.update(kwargs) or [],
    )

    result = runner.invoke(
        _app(command.visualise),
        ["--source", "json", "--no-collapse"],
    )

    assert result.exit_code == 0
    assert captured["collapse"] is False


def test_visualise_summary_always_contains_node_and_edge_counts(tmp_path):
    from goldilocks_cli.commands.visualise import visualise

    export = tmp_path / "export.json"
    export.write_text(
        json.dumps(
            {
                "name": "Tiny",
                "instance_id": "p1",
                "snap_map": {
                    "a": {"class_id": "mapper"},
                    "b": {"class_id": "mapper"},
                },
                "link_map": {"l": {"src_id": "a", "dst_id": "b"}},
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        _app(visualise),
        [
            "--source", "json",
            "--input", str(export),
            "--out", str(tmp_path / "diagrams"),
        ],
    )

    assert result.exit_code == 0
    assert "2 nodes · 1 edge" in result.output
    assert "Rendering full pipeline" in result.output


def test_hard_limit_is_warm_skip_not_traceback(tmp_path):
    from goldilocks_cli.commands.visualise import visualise

    snap_map = {
        f"s{index}": {
            "class_id": "com-snaplogic-snaps-transform-mapper",
            "property_map": {"info": {"label": {"value": f"Mapper {index}"}}},
        }
        for index in range(300)
    }
    link_map = {
        f"l{index}": {"src_id": f"s{index}", "dst_id": f"s{index + 1}"}
        for index in range(299)
    }
    export = tmp_path / "large.json"
    export.write_text(
        json.dumps(
            {
                "name": "Large",
                "instance_id": "large",
                "snap_map": snap_map,
                "link_map": link_map,
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        _app(visualise),
        [
            "--source", "json",
            "--input", str(export),
            "--out", str(tmp_path / "diagrams"),
            "--no-collapse",
        ],
    )

    assert result.exit_code == 0
    assert "300 nodes · 299 edges" in result.output
    assert "too large to be useful" in result.output
    assert "Traceback" not in result.output


def test_single_prompts_and_renders_only_selected_json_pipeline(tmp_path):
    from goldilocks_cli.commands.visualise import visualise

    export = tmp_path / "project.json"
    export.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "name": "First",
                        "instance_id": "p1",
                        "snap_map": {"a": {"class_id": "mapper"}},
                        "link_map": {},
                    },
                    {
                        "name": "Second",
                        "instance_id": "p2",
                        "snap_map": {"b": {"class_id": "mapper"}},
                        "link_map": {},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "diagrams"

    result = runner.invoke(
        _app(visualise),
        [
            "--source", "json",
            "--input", str(export),
            "--out", str(output),
            "--single",
        ],
        input="2\n",
    )

    assert result.exit_code == 0
    assert (output / "Second.mmd").exists()
    assert not (output / "First.mmd").exists()
    assert not (output / "goldilocks_combined.mmd").exists()


def test_combined_flag_reaches_json_orchestration(monkeypatch):
    import goldilocks_cli.commands.visualise as command

    captured = {}
    monkeypatch.setattr(
        command,
        "_render_from_json",
        lambda *args, **kwargs: captured.update(kwargs) or [],
    )

    result = runner.invoke(
        _app(command.visualise),
        ["--source", "json", "--combined"],
    )

    assert result.exit_code == 0
    assert captured["combined"] is True
