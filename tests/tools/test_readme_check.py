"""The readme transcript is replayed, not trusted."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemwalk.tools import check_readme
from gemwalk.tools.walker import repo_root

BLOCK = """# probe

```console
$ gemwalk about
one
two
```
"""


def test_the_readme_transcript_still_prints_what_it_says_it_does() -> None:
    assert check_readme.main([]) == 0


def test_the_readme_has_a_transcript_at_all() -> None:
    steps = check_readme.parse((repo_root() / check_readme.TARGET).read_text())
    assert len(steps) > 10
    assert steps[0].command == "store init"


def test_a_step_splits_the_way_a_shell_would() -> None:
    step = check_readme.Step('site open A "Long Name" --subpart XXX', [])
    assert step.words == ["site", "open", "A", "Long Name", "--subpart", "XXX"]


def test_the_parser_takes_the_output_under_each_command() -> None:
    steps = check_readme.parse(BLOCK)
    assert len(steps) == 1
    assert steps[0].printed == ["one", "two"]


def test_a_transcript_that_lies_is_found() -> None:
    steps = check_readme.parse(BLOCK)
    played = check_readme.replay(steps)
    faults = check_readme.faults(steps, played)
    assert len(faults) == 1
    assert "the readme says" in faults[0]
    assert "and it printed" in faults[0]


def test_a_failing_command_records_its_exit_status() -> None:
    steps = [check_readme.Step("record show EX-9999", [])]
    played = check_readme.replay(steps)
    assert any("[exit" in line for line in played[0].printed)


def test_rendering_writes_the_real_output_back() -> None:
    steps = check_readme.parse(BLOCK)
    played = check_readme.replay(steps)
    rewritten = check_readme.render(BLOCK, played)
    assert "one" not in rewritten
    assert "landfill gas" in rewritten


def test_a_readme_with_no_transcript_is_a_fault(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check_readme, "repo_root", lambda: tmp_path)
    (tmp_path / check_readme.TARGET).write_text("# nothing here\n")
    assert check_readme.main([]) == 1
    assert "no console block" in capsys.readouterr().out


def test_update_writes_the_transcript_and_then_it_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check_readme, "repo_root", lambda: tmp_path)
    (tmp_path / check_readme.TARGET).write_text(BLOCK)
    assert check_readme.main([]) == 1
    assert check_readme.main(["--update"]) == 0
    assert "replayed 1 commands" in capsys.readouterr().out
    assert check_readme.main([]) == 0


def test_the_replay_runs_the_steps_in_order_against_one_book() -> None:
    steps = [
        check_readme.Step("store init", []),
        check_readme.Step(
            'site open A "A" --subpart XXX --permit p --zone UTC --capacity 1 --opened 2000-01-01',
            [],
        ),
        check_readme.Step("site list", []),
    ]
    played = check_readme.replay(steps)
    assert any("A" in line for line in played[2].printed)
