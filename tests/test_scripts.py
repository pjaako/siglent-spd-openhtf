import importlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / 'example_test.py'), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_example_with_fake_exits_zero() -> None:
    result = _run('--fake')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS' in result.stdout


def test_example_help_exits_zero_without_touching_hardware() -> None:
    result = _run('--help')
    assert result.returncode == 0
    assert '--fake' in result.stdout
    assert '--resource' in result.stdout


class _Passes:
    def execute(self, **kwargs: object) -> bool:
        return True


class _Fails:
    def execute(self, **kwargs: object) -> bool:
        return False


def test_resource_flag_sets_the_conf_key_and_exit_code_follows_the_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from siglent_spd_openhtf.plug import CONF

    monkeypatch.syspath_prepend(str(ROOT))
    example = importlib.import_module('example_test')
    seen: list[bool] = []

    @CONF.save_and_restore
    def run(outcome: object) -> int:
        monkeypatch.setattr(example, 'build_test', lambda fake: seen.append(fake) or outcome)
        code = example.main(['--resource', 'TCPIP::192.0.2.10::INSTR'])
        assert CONF.siglent_spd_resource == 'TCPIP::192.0.2.10::INSTR'
        return int(code)

    assert run(_Passes()) == 0
    assert run(_Fails()) == 1
    assert seen == [False, False]


def test_example_fake_plug_keeps_the_default_teardown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT))
    example = importlib.import_module('example_test')
    plug = example.FakeSiglentSpdPlug()
    assert plug._outputs_off_on_teardown is True
    plug.set_output(1, False)
    plug.configure_channel(1, voltage=3, current=0.5)
    plug.set_output(1, True)
    fake = plug.resource
    plug.tearDown()
    assert fake.channels[1].output is False  # type: ignore[attr-defined]
    assert 'OUTPut:ALL 0' in fake.log  # type: ignore[attr-defined]
