import json
from pathlib import Path
from types import SimpleNamespace

from goldilocks_cli.core import renderer


def test_mmdc_config_for_supported_version_contains_safe_limits():
    assert renderer.build_mmdc_config((10, 7, 0)) == {
        "maxTextSize": 200_000,
        "maxEdges": 2_000,
    }


def test_mmdc_config_for_older_v10_omits_unsupported_max_edges():
    assert renderer.build_mmdc_config((10, 6, 1)) == {
        "maxTextSize": 200_000,
    }


def test_mmdc_config_for_unknown_version_emits_nothing_fictional():
    assert renderer.build_mmdc_config(None) == {}


def test_render_diagram_passes_limits_through_mmdc_config_file(
    tmp_path: Path,
    monkeypatch,
):
    mmd_path = tmp_path / "pipeline.mmd"
    mmd_path.write_text("flowchart LR\n", encoding="utf-8")
    observed: dict[str, object] = {}

    monkeypatch.setattr(renderer, "find_mmdc", lambda: "/usr/bin/mmdc")
    monkeypatch.setattr(renderer, "detect_mmdc_version", lambda: (10, 7, 0))

    def fake_run(command, **kwargs):
        observed["command"] = command
        config_index = command.index("--configFile") + 1
        config_path = Path(command[config_index])
        observed["config"] = json.loads(config_path.read_text(encoding="utf-8"))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(renderer.subprocess, "run", fake_run)

    result = renderer.render_diagram(mmd_path, "svg")

    assert result == mmd_path.with_suffix(".svg")
    assert "--configFile" in observed["command"]
    assert observed["config"] == {
        "maxTextSize": 200_000,
        "maxEdges": 2_000,
    }
