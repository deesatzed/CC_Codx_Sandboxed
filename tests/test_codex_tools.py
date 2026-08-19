"""Guard the Codex catalog + launcher against the exec-abort failure mode.

Evidence (session 01a01b83): the model only saw openrouter_web_search / wait /
collaboration_* tools, called `exec`, and got `aborted` with no
function_call_output. Official GPT-5.6 catalog uses tool_mode=code_mode_only
(hidden exec protocol). Third-party OpenRouter models need the GPT-5.5 shape
(no tool_mode, no multi_agent_version) so Codex advertises shell_command.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_is_function_tool_shape_not_code_mode_only():
    data = json.loads((ROOT / "model-catalog.json").read_text())
    models = data.get("models") or []
    assert models, "catalog has no models"
    for m in models:
        assert "tool_mode" not in m, (
            f"{m.get('slug')}: tool_mode={m.get('tool_mode')!r} hides exec from "
            "third-party models (code_mode_only is GPT-5.6-only)"
        )
        assert "multi_agent_version" not in m, (
            f"{m.get('slug')}: multi_agent_version advertises spawn_agent and "
            "crowds out exec"
        )
        assert m.get("shell_type") == "shell_command"
        assert m.get("supports_search_tool") is False
        assert m.get("use_responses_lite") is False
        assert m.get("apply_patch_tool_type") == "freeform"


def test_hybrid_toml_disables_collab_and_code_mode():
    text = (ROOT / "codex-hybrid.toml").read_text()
    assert "model_catalog_json" in text
    assert "/Volumes/WS4TB/" not in text.split("model_catalog_json", 1)[-1].splitlines()[0]
    assert "unified_exec = true" in text
    assert "shell_tool = true" in text
    assert "code_mode = false" in text
    assert "code_mode_only = false" in text
    assert "collaboration_modes = false" in text
    assert "multi_agent = false" in text
    assert "multi_agent_v2 = false" in text
    assert 'web_search = "disabled"' in text
    assert "collab =" not in text
    assert "web_search_request" not in text


def test_run_codex_sets_pwd_and_does_not_pass_host_tmpdir():
    text = (ROOT / "run-codex.sh").read_text()
    assert "export PWD=" in text
    flag_lines = [
        line.strip()
        for line in text.splitlines()
        if line.lstrip().startswith("--env-pass")
    ]
    assert flag_lines, "run-codex.sh missing --env-pass"
    assert all("TMPDIR" not in line for line in flag_lines)
    assert 'cd "$SCRIPT_DIR"' in text
    assert "model-catalog.json" in text
