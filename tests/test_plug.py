from __future__ import annotations

import logging
import math
from typing import Any

import pytest

from siglent_spd_openhtf.fake_resource import FakeSpdResource, to_float32
from siglent_spd_openhtf.plug import (
    CONF,
    Channel,
    Identity,
    ProtectionStatus,
    Reading,
    SenseMode,
    SiglentSpdPlug,
    TrackMode,
)

ALL = (1, 2, 3, 4)


def _plug(
    model: str = 'SPD4323X',
    *,
    loads: dict[int, float | None] | None = None,
    reject: dict[str, str] | None = None,
    teardown_off: bool = False,
    restore_state: bool | None = None,
    fake: FakeSpdResource | None = None,
) -> tuple[SiglentSpdPlug, FakeSpdResource]:
    fake = fake or FakeSpdResource(model=model, loads=loads, reject=reject)
    plug = SiglentSpdPlug(
        resource=fake, outputs_off_on_teardown=teardown_off, restore_state=restore_state
    )
    return plug, fake


def _new(fake: FakeSpdResource, start: int) -> list[str]:
    return fake.log[start:]


# ---- construction ---------------------------------------------------------------------


def test_init_configures_the_resource_and_reads_identity() -> None:
    plug, fake = _plug()
    assert fake.timeout == 5000
    assert fake.read_termination == '\n'
    assert fake.write_termination == '\n'
    assert fake.log == ['*IDN?']
    assert plug.identity == Identity(
        'Siglent Technologies', 'SPD4323X', 'SPD4XXXXXXXXXX', '1.0.0.0'
    )
    assert plug.model is not None
    assert plug.model.name == 'SPD4323X'


def test_init_with_unknown_model_warns_and_keeps_going(caplog: pytest.LogCaptureFixture) -> None:
    fake = FakeSpdResource()
    fake.model = 'SPD9999X'
    with caplog.at_level(logging.WARNING):
        plug, _ = _plug(fake=fake)
    assert plug.model is None
    assert 'SPD9999X' in caplog.text


def test_init_with_short_idn_raises_and_closes_the_resource() -> None:
    class Short(FakeSpdResource):
        def query(self, message: str) -> str:
            super().query(message)
            return 'Siglent Technologies,SPD4323X'

    fake = Short()
    with pytest.raises(RuntimeError, match='IDN'):
        _plug(fake=fake)
    assert fake.closed


def test_init_takes_a_snapshot_only_when_restore_is_enabled() -> None:
    _, plain = _plug()
    assert plain.log == ['*IDN?']
    _, restoring = _plug(restore_state=True)
    assert len(restoring.log) == 1 + 4 * 9 + 1
    assert restoring.log[1:10] == [
        ':SOURce:VOLTage:SET? CH1',
        ':SOURce:CURRent:SET? CH1',
        ':SOURce:OVP? CH1',
        ':SOURce:OCP? CH1',
        ':SOURce:OCP:STATe? CH1',
        'OCP:DELay? CH1',
        'OUTPut:ON:DELay? CH1',
        'OUTPut:OFF:DELay? CH1',
        'OUTPut? CH1',
    ]
    assert restoring.log[-1] == 'OUTPut:TRACK?'


@CONF.save_and_restore(siglent_spd_outputs_off_on_teardown=False, siglent_spd_restore_state=True)
def test_none_arguments_fall_back_to_conf() -> None:
    fake = FakeSpdResource()
    SiglentSpdPlug(resource=fake)
    assert fake.log[-1] == 'OUTPut:TRACK?'  # snapshot taken because of the CONF key


def test_conf_defaults() -> None:
    assert CONF.siglent_spd_resource == ''
    assert CONF.siglent_spd_outputs_off_on_teardown is True
    assert CONF.siglent_spd_restore_state is False


# ---- resource discovery (pyvisa replaced by a stub, nothing real is opened) ----------------


class _StubRm:
    def __init__(self, resources: dict[str, FakeSpdResource]) -> None:
        self.resources = resources
        self.opened: list[str] = []
        self.closed = False

    def list_resources(self, query: str) -> tuple[str, ...]:
        assert query == 'USB?*::INSTR'
        return tuple(self.resources)

    def open_resource(self, name: str) -> FakeSpdResource:
        self.opened.append(name)
        return self.resources[name]

    def close(self) -> None:
        self.closed = True


def _patch_visa(monkeypatch: pytest.MonkeyPatch, rm: _StubRm) -> list[str]:
    import pyvisa

    backends: list[str] = []

    def factory(backend: str = '') -> _StubRm:
        backends.append(backend)
        return rm

    monkeypatch.setattr(pyvisa, 'ResourceManager', factory)
    return backends


class _OtherInstrument(FakeSpdResource):
    def query(self, message: str) -> str:
        super().query(message)
        return 'Acme,Widget 9,1,1'


def test_discovery_picks_the_first_spd4_and_closes_the_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other = _OtherInstrument()
    psu = FakeSpdResource()
    rm = _StubRm({'USB0::A::INSTR': other, 'USB0::B::INSTR': psu})
    backends = _patch_visa(monkeypatch, rm)
    plug = SiglentSpdPlug(outputs_off_on_teardown=False)
    assert backends == ['@py']
    assert plug.resource is psu
    assert other.closed
    assert not psu.closed
    plug.tearDown()
    assert psu.closed
    assert rm.closed


@CONF.save_and_restore(siglent_spd_resource='TCPIP::192.0.2.10::INSTR')
def test_explicit_resource_name_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    psu = FakeSpdResource()
    rm = _StubRm({'TCPIP::192.0.2.10::INSTR': psu})
    _patch_visa(monkeypatch, rm)
    plug = SiglentSpdPlug(outputs_off_on_teardown=False)
    assert rm.opened == ['TCPIP::192.0.2.10::INSTR']
    assert plug.resource is psu


def test_discovery_without_a_supply_names_the_conf_key(monkeypatch: pytest.MonkeyPatch) -> None:
    other = _OtherInstrument()
    rm = _StubRm({'USB0::A::INSTR': other})
    _patch_visa(monkeypatch, rm)
    with pytest.raises(RuntimeError, match='siglent_spd_resource'):
        SiglentSpdPlug()
    assert other.closed
    assert rm.closed


# ---- channel argument ---------------------------------------------------------------------


def test_channel_enum_str_is_the_wire_spelling() -> None:
    assert [str(c) for c in Channel] == ['CH1', 'CH2', 'CH3', 'CH4']


def test_channel_accepts_int_and_enum() -> None:
    plug, fake = _plug()
    plug.set_output(Channel.CH3, True)
    plug.set_output(4, True)
    assert fake.log[-4:] == ['OUTPut CH3,1', 'OUTPut? CH3', 'OUTPut CH4,1', 'OUTPut? CH4']


@pytest.mark.parametrize('bad', [0, 5, -1, '1', 'CH1', 1.0, True, None])
def test_invalid_channel_raises_value_error_and_sends_nothing(bad: Any) -> None:
    plug, fake = _plug()
    for call in (
        plug.set_voltage,
        plug.voltage_setpoint,
        plug.set_output,
        plug.output,
        plug.measure,
        plug.protection_status,
        plug.clear_protection,
        plug.ovp,
        plug.run_mode,
    ):
        with pytest.raises(ValueError):
            if call in (plug.set_voltage, plug.set_output):
                call(bad, 1)
            else:
                call(bad)
    assert fake.log == ['*IDN?']


# ---- low level ------------------------------------------------------------------------------


def test_query_strips_whitespace() -> None:
    class Padded(FakeSpdResource):
        def query(self, message: str) -> str:
            return f'  {super().query(message)}\n'

    plug, _ = _plug(fake=Padded())
    assert plug.opc() == '1'


def test_fmt() -> None:
    assert SiglentSpdPlug._fmt(3.3) == '3.3'
    assert SiglentSpdPlug._fmt(2) == '2'
    assert SiglentSpdPlug._fmt(0.00019999999999999998) == '0.0002'
    assert SiglentSpdPlug._fmt(0.1 + 0.2) == '0.3'


@pytest.mark.parametrize(
    ('expected', 'actual', 'match'),
    [
        (True, '1', True),
        (True, 'ON', True),
        (True, '0', False),
        (False, 'OFF', True),
        (False, '1', False),
        (True, 'maybe', False),
        (3.3, '3.300000', True),
        (3.3, '3.300400', True),
        (3.3, '3.301000', False),
        (0.0, '0.000300', True),
        (6.0, '5.000000', False),
        (3.3, 'abc', False),
        ('cv', 'CV', True),
        ('CV', 'CC', False),
    ],
)
def test_values_match(expected: Any, actual: str, match: bool) -> None:
    assert SiglentSpdPlug._values_match(expected, actual) is match


def test_write_verified_passes_and_fails() -> None:
    plug, fake = _plug()
    plug.write_verified(':SOURce:VOLTage:SET CH1,2', ':SOURce:VOLTage:SET? CH1', 2.0)
    fake.reject = {':SOURce:VOLTage:SET CH1': 'x'}
    with pytest.raises(RuntimeError) as err:
        plug.write_verified(':SOURce:VOLTage:SET CH1,3', ':SOURce:VOLTage:SET? CH1', 3.0)
    message = str(err.value)
    assert ':SOURce:VOLTage:SET CH1,3' in message
    assert '3.0' in message
    assert '2.000000' in message


def test_write_verified_wraps_query_failures() -> None:
    plug, _ = _plug()
    with pytest.raises(RuntimeError, match='FROB CH1,1') as err:
        plug.write_verified('FROB CH1,1', 'FROB? CH1', 1)
    assert err.value.__cause__ is not None


def test_write_verified_wraps_timeouts() -> None:
    class Timeout(Exception):
        pass

    plug, fake = _plug()

    def broken(message: str) -> str:
        raise Timeout('VI_ERROR_TMO')

    fake.query = broken  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match=':SOURce:VOLTage:SET CH2,1'):
        plug.write_verified(':SOURce:VOLTage:SET CH2,1', ':SOURce:VOLTage:SET? CH2', 1.0)


# ---- identity, opc ---------------------------------------------------------------------------


def test_opc() -> None:
    plug, fake = _plug()
    assert plug.opc() == '1'
    assert fake.log[-1] == '*OPC?'


# ---- output ---------------------------------------------------------------------------------


def test_set_voltage_and_current_commands() -> None:
    plug, fake = _plug()
    plug.set_voltage(1, 3.3)
    plug.set_current(1, 0.5)
    plug.set_voltage(Channel.CH4, 0.002)
    assert fake.log[1:] == [
        ':SOURce:VOLTage:SET CH1,3.3',
        ':SOURce:VOLTage:SET? CH1',
        ':SOURce:CURRent:SET CH1,0.5',
        ':SOURce:CURRent:SET? CH1',
        ':SOURce:VOLTage:SET CH4,0.002',
        ':SOURce:VOLTage:SET? CH4',
    ]
    assert plug.voltage_setpoint(1) == pytest.approx(3.3)
    assert plug.current_setpoint(1) == pytest.approx(0.5)
    assert fake.log[-2:] == [':SOURce:VOLTage:SET? CH1', ':SOURce:CURRent:SET? CH1']


@pytest.mark.parametrize('bad', [-0.1, math.nan, math.inf])
def test_set_voltage_rejects_invalid_numbers(bad: float) -> None:
    plug, fake = _plug()
    with pytest.raises(ValueError):
        plug.set_voltage(1, bad)
    with pytest.raises(ValueError):
        plug.set_current(1, bad)
    assert fake.log == ['*IDN?']


def test_set_voltage_rejected_by_the_instrument_is_detected() -> None:
    plug, _ = _plug(reject={':SOURce:VOLTage:SET CH1': 'ignored'})
    with pytest.raises(RuntimeError, match=':SOURce:VOLTage:SET CH1,3'):
        plug.set_voltage(1, 3)


def test_clamped_value_is_detected_when_the_model_is_unknown() -> None:
    fake = FakeSpdResource()
    fake.model = 'SPD9999X'
    plug, _ = _plug(fake=fake)
    assert plug.model is None
    with pytest.raises(RuntimeError, match=':SOURce:VOLTage:SET CH1,7'):
        plug.set_voltage(1, 7)  # the fake clamps to the 6 V rating
    with pytest.raises(RuntimeError, match=':SOURce:CURRent:SET CH1,4'):
        plug.set_current(1, 4)


def test_set_output_and_query() -> None:
    plug, fake = _plug()
    plug.set_output(1, True)
    assert plug.output(1) is True
    plug.set_output(1, False)
    assert plug.output(1) is False
    assert fake.log[1:] == [
        'OUTPut CH1,1',
        'OUTPut? CH1',
        'OUTPut? CH1',
        'OUTPut CH1,0',
        'OUTPut? CH1',
        'OUTPut? CH1',
    ]


def test_set_output_detects_a_refused_output() -> None:
    plug, _ = _plug(reject={'OUTPut CH2': 'refused'})
    with pytest.raises(RuntimeError, match='OUTPut CH2,1'):
        plug.set_output(2, True)


def test_set_all_outputs_verifies_every_channel() -> None:
    plug, fake = _plug()
    plug.set_all_outputs(True)
    assert fake.log[1:] == ['OUTPut:ALL 1', *(f'OUTPut? CH{n}' for n in ALL)]
    start = len(fake.log)
    plug.all_outputs_off()
    assert _new(fake, start) == ['OUTPut:ALL 0', *(f'OUTPut? CH{n}' for n in ALL)]
    assert not any(c.output for c in fake.channels.values())


def test_set_all_outputs_lists_every_failing_channel() -> None:
    plug, _ = _plug(reject={'OUTPut:ALL': 'refused'})
    plug.set_output(1, True)
    plug.set_output(3, True)
    with pytest.raises(RuntimeError) as err:
        plug.all_outputs_off()
    assert 'CH1' in str(err.value)
    assert 'CH3' in str(err.value)
    assert 'CH2' not in str(err.value)


def test_set_output_delay() -> None:
    plug, fake = _plug()
    plug.set_output_delay(1, on_s=3, off_s=1.5)
    plug.set_output_delay(2, off_s=0)
    assert fake.log[1:] == [
        'OUTPut:ON:DELay CH1,3',
        'OUTPut:ON:DELay? CH1',
        'OUTPut:OFF:DELay CH1,1.5',
        'OUTPut:OFF:DELay? CH1',
        'OUTPut:OFF:DELay CH2,0',
        'OUTPut:OFF:DELay? CH2',
    ]


@pytest.mark.parametrize(
    'kwargs', [{'on_s': -1}, {'off_s': 3600.5}, {'on_s': 1, 'off_s': 4000}, {}]
)
def test_set_output_delay_validates_before_sending(kwargs: dict[str, float]) -> None:
    plug, fake = _plug()
    with pytest.raises(ValueError):
        plug.set_output_delay(1, **kwargs)
    assert fake.log == ['*IDN?']


def test_set_output_delay_accepts_the_limits() -> None:
    plug, _ = _plug()
    plug.set_output_delay(1, on_s=3600, off_s=0)


def test_configure_channel_order_and_commands() -> None:
    plug, fake = _plug()
    plug.configure_channel(
        1, voltage=3.3, current=0.5, ovp=4, ocp=1, ocp_enabled=True, ocp_delay=0.25
    )
    assert fake.log[1:] == [
        ':SOURce:OVP CH1,4',
        ':SOURce:OVP? CH1',
        ':SOURce:OCP CH1,1',
        ':SOURce:OCP? CH1',
        'OCP:DELay CH1,0.25',
        'OCP:DELay? CH1',
        ':SOURce:OCP:STATe CH1,1',
        ':SOURce:OCP:STATe? CH1',
        ':SOURce:VOLTage:SET CH1,3.3',
        ':SOURce:VOLTage:SET? CH1',
        ':SOURce:CURRent:SET CH1,0.5',
        ':SOURce:CURRent:SET? CH1',
    ]


def test_configure_channel_skips_unset_items() -> None:
    plug, fake = _plug()
    plug.configure_channel(1, ocp_enabled=False)
    assert fake.log[1:] == [':SOURce:OCP:STATe CH1,0', ':SOURce:OCP:STATe? CH1']


def test_configure_channel_attempts_everything_and_lists_failures() -> None:
    plug, fake = _plug(reject={':SOURce:OVP CH1': 'x', ':SOURce:CURRent:SET CH1': 'x'})
    with pytest.raises(RuntimeError) as err:
        plug.configure_channel(1, voltage=3, current=0.5, ovp=4, ocp=1)
    message = str(err.value)
    assert 'ovp' in message
    assert 'current' in message
    assert 'ocp=' not in message
    assert 'voltage=' not in message
    assert fake.channels[1].voltage == 3
    assert fake.channels[1].ocp == 1


def test_configure_channel_reports_a_guard_violation_but_applies_the_rest() -> None:
    plug, fake = _plug()
    with pytest.raises(RuntimeError, match='voltage'):
        plug.configure_channel(1, voltage=7, current=1)
    assert fake.channels[1].current == 1
    assert fake.channels[1].voltage == 0


# ---- guard rule -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('model', 'ch', 'volts', 'amps'),
    [
        ('SPD4323X', 1, 6.5, 3.3),
        ('SPD4323X', 2, 33, 3.3),
        ('SPD4323X', 4, 6.01, 3.21),
        ('SPD4121X', 1, 15.5, 1.6),
        ('SPD4121X', 3, 12.1, 10.1),
        ('SPD4306X', 2, 30.5, 6.1),
        ('SPD4306X', 4, 15.5, 1.2),
    ],
)
def test_guard_rejects_values_above_the_rating_per_model(
    model: str, ch: int, volts: float, amps: float
) -> None:
    plug, fake = _plug(model)
    start = len(fake.log)
    with pytest.raises(ValueError, match='rating'):
        plug.set_voltage(ch, volts)
    with pytest.raises(ValueError, match='rating'):
        plug.set_current(ch, amps)
    assert not [
        c
        for c in _new(fake, start)
        if c.startswith((':SOURce:VOLTage:SET ', ':SOURce:CURRent:SET '))
    ]


@pytest.mark.parametrize(
    ('model', 'ch', 'volts', 'amps'),
    [
        ('SPD4323X', 1, 6, 3.2),
        ('SPD4323X', 3, 32, 3.2),
        ('SPD4121X', 2, 12, 10),
        ('SPD4121X', 4, 15, 1.5),
        ('SPD4306X', 1, 15, 1.5),
        ('SPD4306X', 4, 15, 1),
    ],
)
def test_guard_accepts_the_rating_itself(model: str, ch: int, volts: float, amps: float) -> None:
    plug, _ = _plug(model)
    plug.set_voltage(ch, volts)
    plug.set_current(ch, amps)


def test_guard_ch1_and_ch4_do_not_query_the_track_mode() -> None:
    plug, fake = _plug()
    plug.set_voltage(1, 1)
    plug.set_current(4, 1)
    assert 'OUTPut:TRACK?' not in fake.log


def test_guard_reads_the_track_mode_once_for_ch2_and_ch3() -> None:
    plug, fake = _plug()
    plug.set_voltage(2, 5)
    plug.set_voltage(3, 5)
    plug.set_current(2, 1)
    assert fake.log.count('OUTPut:TRACK?') == 1
    assert fake.log.index('OUTPut:TRACK?') < fake.log.index(':SOURce:VOLTage:SET CH2,5')


def test_guard_stays_at_the_rating_although_the_instrument_accepts_one_percent_more() -> None:
    plug, fake = _plug()
    # The instrument itself takes up to 1.01 x the rating (6.06 V on CH1) without a word ...
    probe = FakeSpdResource()
    probe.write(':SOURce:VOLTage:SET CH1,6.05')
    assert probe.query(':SOURce:VOLTage:SET? CH1') == '6.050000'
    # ... but the guard refuses before anything is sent: it is the guard, not the fake.
    with pytest.raises(ValueError, match='rating'):
        plug.set_voltage(1, 6.05)
    with pytest.raises(ValueError, match='rating'):
        plug.set_current(4, 3.21)
    assert fake.log == ['*IDN?']
    plug.set_voltage(1, 6.0)  # the rating itself passes


def test_a_value_above_the_instrument_maximum_is_caught_by_the_read_back() -> None:
    plug, fake = _plug()
    with pytest.raises(RuntimeError, match='6.07'):
        plug.write_verified(':SOURce:VOLTage:SET CH1,6.07', ':SOURce:VOLTage:SET? CH1', 6.07)
    assert fake.query(':SOURce:VOLTage:SET? CH1') == '6.060000'  # clamped to 1.01 x rating


def test_max_voltage_and_max_current_query_the_instrument_limits() -> None:
    plug, fake = _plug()
    assert plug.max_voltage(1) == pytest.approx(6.06)
    assert plug.max_voltage(Channel.CH2) == pytest.approx(32.32)
    assert plug.max_current(4) == pytest.approx(3.232)
    assert fake.log[1:] == [
        ':SOURce:VOLTage:SET? CH1,MAXimum',
        ':SOURce:VOLTage:SET? CH2,MAXimum',
        ':SOURce:CURRent:SET? CH4,MAXimum',
    ]
    with pytest.raises(ValueError):
        plug.max_voltage(5)
    with pytest.raises(ValueError):
        plug.max_current(0)
    assert len(fake.log) == 4


def test_max_queries_do_not_follow_the_track_mode() -> None:
    plug, _ = _plug()
    plug.set_track(TrackMode.SERIES)
    assert plug.max_voltage(2) == pytest.approx(32.32)
    plug.set_track(TrackMode.PARALLEL)
    assert plug.max_current(2) == pytest.approx(3.232)


@pytest.mark.parametrize(
    ('model', 'ind_v', 'ind_a'),
    [('SPD4323X', 32, 3.2), ('SPD4121X', 12, 10), ('SPD4306X', 30, 6)],
)
def test_guard_in_independent_mode_uses_the_single_channel_rating(
    model: str, ind_v: float, ind_a: float
) -> None:
    plug, _ = _plug(model)
    plug.set_voltage(2, ind_v)
    plug.set_current(2, ind_a)
    with pytest.raises(ValueError, match='rating'):
        plug.set_voltage(2, ind_v + 0.5)
    with pytest.raises(ValueError, match='rating'):
        plug.set_current(2, ind_a + 0.1)


def test_guard_follows_a_return_to_independent_mode() -> None:
    plug, _ = _plug()
    plug.set_track(TrackMode.SERIES)
    plug.set_track(TrackMode.INDEPENDENT)
    with pytest.raises(ValueError):
        plug.set_voltage(2, 33)
    plug.set_voltage(2, 5)  # writing is possible again


# ---- coupled modes (open question 21) --------------------------------------------------------


@pytest.mark.parametrize('mode', [TrackMode.SERIES, TrackMode.PARALLEL])
@pytest.mark.parametrize('ch', [2, 3])
def test_setpoints_of_ch2_and_ch3_are_refused_in_a_coupled_mode(mode: TrackMode, ch: int) -> None:
    plug, fake = _plug()
    plug.set_track(mode)
    start = len(fake.log)
    for call in (
        lambda: plug.set_voltage(ch, 5),
        lambda: plug.set_current(ch, 1),
        lambda: plug.configure_channel(ch, voltage=5),
        lambda: plug.configure_channel(ch, ovp=10, ocp_enabled=True),
    ):
        with pytest.raises(RuntimeError, match='question 21'):
            call()
    assert not [c for c in _new(fake, start) if '?' not in c]  # nothing was sent
    assert fake.channels[2].voltage == 0


@pytest.mark.parametrize('mode', [TrackMode.SERIES, TrackMode.PARALLEL])
def test_ch1_and_ch4_and_reads_are_unaffected_by_a_coupled_mode(mode: TrackMode) -> None:
    plug, fake = _plug()
    plug.set_track(mode)
    plug.set_voltage(1, 3)
    plug.set_current(4, 1)
    plug.configure_channel(1, ovp=4)
    plug.set_ovp(2, 10)  # OVP/OCP writes are not part of the refusal
    assert plug.voltage_setpoint(2) == 0
    assert (fake.channels[1].voltage, fake.channels[4].current) == (3, 1)


def test_the_refusal_applies_with_an_unknown_model_too() -> None:
    fake = FakeSpdResource()
    fake.model = 'SPD9999X'
    plug, _ = _plug(fake=fake)
    plug.set_track(TrackMode.SERIES)
    with pytest.raises(RuntimeError, match='question 21'):
        plug.set_voltage(2, 5)


def test_the_refusal_uses_a_track_mode_read_from_the_instrument() -> None:
    fake = FakeSpdResource()
    fake.track = 1  # changed from the panel before the plug looked
    plug, _ = _plug(fake=fake)
    with pytest.raises(RuntimeError, match='SERIES'):
        plug.set_voltage(3, 5)
    assert fake.log == ['*IDN?', 'OUTPut:TRACK?']


def test_the_guard_is_checked_before_the_coupled_mode_refusal() -> None:
    plug, _ = _plug()
    plug.set_track(TrackMode.SERIES)
    with pytest.raises(ValueError, match='rating'):
        plug.set_voltage(2, 33)


# ---- protection -----------------------------------------------------------------------------


def test_protection_setters_and_getters() -> None:
    plug, fake = _plug()
    plug.set_ovp(1, 4)
    plug.set_ocp(1, 1)
    plug.set_ocp_enabled(1, True)
    plug.set_ocp_delay(1, 0.5)
    assert fake.log[1:] == [
        ':SOURce:OVP CH1,4',
        ':SOURce:OVP? CH1',
        ':SOURce:OCP CH1,1',
        ':SOURce:OCP? CH1',
        ':SOURce:OCP:STATe CH1,1',
        ':SOURce:OCP:STATe? CH1',
        'OCP:DELay CH1,0.5',
        'OCP:DELay? CH1',
    ]
    assert plug.ovp(1) == pytest.approx(4)
    assert plug.ocp(1) == pytest.approx(1)
    assert plug.ocp_enabled(1) is True
    assert plug.ocp_delay(1) == pytest.approx(0.5)
    assert fake.log[-4:] == [
        ':SOURce:OVP? CH1',
        ':SOURce:OCP? CH1',
        ':SOURce:OCP:STATe? CH1',
        'OCP:DELay? CH1',
    ]


def test_ovp_above_the_fake_rating_is_caught_by_read_back() -> None:
    plug, _ = _plug()
    with pytest.raises(RuntimeError, match=':SOURce:OVP CH1,7'):
        plug.set_ovp(1, 7)
    with pytest.raises(RuntimeError, match=':SOURce:OCP CH1,4'):
        plug.set_ocp(1, 4)


def test_float32_read_back_of_the_instrument_is_accepted() -> None:
    plug, fake = _plug()
    assert plug.ovp(2) == pytest.approx(35.2)  # the supply answers 35.200001
    assert fake.log[-1] == ':SOURce:OVP? CH2'
    plug.set_ovp(2, 35.2)  # read-back 35.200001 matches within the tolerance
    plug.set_ovp(1, 6.6)
    plug.set_ocp(3, 3.52)
    assert (plug.ovp(1), plug.ocp(3)) == (pytest.approx(6.6), pytest.approx(3.52))


@pytest.mark.parametrize('seconds', [-1, 3600.01])
def test_ocp_delay_range(seconds: float) -> None:
    plug, fake = _plug()
    with pytest.raises(ValueError):
        plug.set_ocp_delay(1, seconds)
    assert fake.log == ['*IDN?']


def test_ocp_delay_accepts_the_limits() -> None:
    plug, _ = _plug()
    plug.set_ocp_delay(1, 0)
    plug.set_ocp_delay(1, 3600)


def test_protection_status() -> None:
    plug, fake = _plug()
    assert plug.protection_status(1) == ProtectionStatus(False, False)
    assert fake.log[-2:] == [':SOURce:OVP:PROTect:STATe? CH1', ':SOURce:OCP:PROTect:STATe? CH1']
    fake.trip_ovp(1)
    fake.trip_ocp(2)
    assert plug.protection_status(1) == ProtectionStatus(True, False)
    assert plug.protection_status(2) == ProtectionStatus(False, True)


def test_ocp_trip_with_a_load_is_visible_through_the_plug() -> None:
    plug, _ = _plug(loads={1: 5.0})
    plug.configure_channel(1, voltage=5, current=3, ocp=0.5, ocp_enabled=True)
    plug.write('OUTPut CH1,1')  # bypass read-back: the trip turns the output off at once
    assert plug.output(1) is False
    assert plug.protection_status(1).ocp_tripped is True


def test_clear_protection() -> None:
    plug, fake = _plug()
    fake.trip_ovp(1)
    start = len(fake.log)
    plug.clear_protection(1)
    assert _new(fake, start) == [
        ':SOURce:RESET:PROTect CH1',
        ':SOURce:OVP:PROTect:STATe? CH1',
        ':SOURce:OCP:PROTect:STATe? CH1',
    ]


def test_clear_protection_raises_if_still_tripped() -> None:
    plug, fake = _plug(reject={':SOURce:RESET:PROTect': 'ignored'})
    fake.trip_ocp(2)
    with pytest.raises(RuntimeError, match='still in protection'):
        plug.clear_protection(2)


# ---- measurement ----------------------------------------------------------------------------


def test_measure_commands_and_values() -> None:
    plug, fake = _plug(loads={1: 10.0})
    plug.configure_channel(1, voltage=3.3, current=0.5)
    plug.set_output(1, True)
    start = len(fake.log)
    reading = plug.measure(1)
    assert _new(fake, start) == [
        'MEASure:VOLTage? CH1',
        'MEASure:CURRent? CH1',
        'MEASure:POWER? CH1',
        'MEASure:RUN:MODE? CH1',
    ]
    assert isinstance(reading, Reading)
    assert reading.voltage == pytest.approx(3.3)
    assert reading.current == pytest.approx(0.33)
    assert reading.power == pytest.approx(1.089)
    assert reading.mode == 'CV'


def test_individual_measure_methods() -> None:
    plug, fake = _plug(loads={2: 10.0})
    plug.configure_channel(2, voltage=5, current=1)
    plug.set_output(2, True)
    assert plug.measure_voltage(2) == pytest.approx(5)
    assert plug.measure_current(2) == pytest.approx(0.5)
    assert plug.measure_power(2) == pytest.approx(2.5)
    assert plug.run_mode(2) == 'CV'
    assert fake.log[-4:] == [
        'MEASure:VOLTage? CH2',
        'MEASure:CURRent? CH2',
        'MEASure:POWER? CH2',
        'MEASure:RUN:MODE? CH2',
    ]


def test_cv_to_cc_through_the_plug() -> None:
    plug, _ = _plug(loads={2: 10.0})
    plug.configure_channel(2, voltage=5, current=1)
    plug.set_output(2, True)
    assert plug.run_mode(2) == 'CV'
    plug.set_current(2, 0.2)
    reading = plug.measure(2)
    assert reading.mode == 'CC'
    assert reading.current == pytest.approx(0.2)
    assert reading.voltage == pytest.approx(2.0)


def test_measure_rejects_a_non_numeric_answer() -> None:
    class Garbage(FakeSpdResource):
        def query(self, message: str) -> str:
            answer = super().query(message)
            return '3.0V' if message.startswith('MEASure:VOLTage') else answer

    plug, _ = _plug(fake=Garbage())
    with pytest.raises(RuntimeError, match='3.0V'):
        plug.measure_voltage(1)


def test_wait_for_voltage_success() -> None:
    plug, _ = _plug()
    plug.set_voltage(1, 3)
    plug.set_output(1, True)
    assert plug.wait_for_voltage(1, 3.0, tol=0.01, timeout=1.0) == pytest.approx(3.0)


def test_wait_for_voltage_polls_until_in_tolerance() -> None:
    plug, fake = _plug()
    plug.set_voltage(1, 3)
    readings = iter(['0.000000', '1.000000', '2.990000'])
    real_query = fake.query

    def scripted(message: str) -> str:
        if message.startswith('MEASure:VOLTage?'):
            fake.log.append(message)
            return next(readings)
        return real_query(message)

    fake.query = scripted  # type: ignore[method-assign]
    assert plug.wait_for_voltage(1, 3.0, tol=0.05, timeout=5.0, interval=0.001) == pytest.approx(
        2.99
    )
    assert fake.log.count('MEASure:VOLTage? CH1') == 3


def test_wait_for_voltage_times_out() -> None:
    plug, fake = _plug()
    plug.set_voltage(1, 3)  # output stays off, so the reading stays at 0 V
    with pytest.raises(TimeoutError, match='CH1'):
        plug.wait_for_voltage(1, 3.0, timeout=0.02, interval=0.005)
    assert 'MEASure:VOLTage? CH1' in fake.log


def test_wait_for_voltage_measures_at_least_once_with_zero_timeout() -> None:
    plug, fake = _plug()
    with pytest.raises(TimeoutError):
        plug.wait_for_voltage(1, 3.0, timeout=0)
    assert fake.log.count('MEASure:VOLTage? CH1') == 1


# ---- track and sense ------------------------------------------------------------------------


def test_set_track_sends_the_word_and_reads_back() -> None:
    plug, fake = _plug()
    plug.set_track(TrackMode.SERIES)
    plug.set_track(TrackMode.PARALLEL)
    plug.set_track(TrackMode.INDEPENDENT)
    ch3 = [':SOURce:VOLTage:SET? CH3', ':SOURce:CURRent:SET? CH3']
    assert fake.log[1:] == [
        *('OUTPut? CH2', 'OUTPut? CH3', *ch3, 'OUTPut:TRACK SERIES', 'OUTPut:TRACK?', *ch3),
        *('OUTPut? CH2', 'OUTPut? CH3', *ch3, 'OUTPut:TRACK PARALLEL', 'OUTPut:TRACK?', *ch3),
        *('OUTPut? CH2', 'OUTPut? CH3', *ch3, 'OUTPut:TRACK INDEPENDENT', 'OUTPut:TRACK?', *ch3),
    ]


def test_set_track_warns_when_ch3_setpoints_were_overwritten(
    caplog: pytest.LogCaptureFixture,
) -> None:
    plug, fake = _plug()
    plug.configure_channel(2, voltage=14, current=3)
    plug.configure_channel(3, voltage=12, current=2)
    with caplog.at_level(logging.WARNING):
        plug.set_track(TrackMode.SERIES)
    assert 'CH3 setpoints changed from 12 V / 2 A to 14 V / 3 A' in caplog.text
    assert (fake.channels[3].voltage, fake.channels[3].current) == (14, 3)
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        plug.set_track(TrackMode.PARALLEL)  # CH3 already equals CH2
        plug.set_track(TrackMode.INDEPENDENT)  # and stays
    assert 'CH3 setpoints' not in caplog.text
    assert (fake.channels[3].voltage, fake.channels[3].current) == (14, 3)


def test_set_track_still_works_when_the_ch3_read_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    plug, fake = _plug()
    real_query = fake.query

    def broken(message: str) -> str:
        if message.endswith('CH3') and message.startswith(':SOURce:'):
            raise OSError('timeout')
        return real_query(message)

    fake.query = broken  # type: ignore[method-assign]
    with caplog.at_level(logging.WARNING):
        plug.set_track(TrackMode.SERIES)
    assert fake.track == 1
    assert 'cannot read the CH3 setpoints' in caplog.text


def test_track_query_maps_numbers() -> None:
    plug, fake = _plug()
    results = []
    for number in (0, 1, 2):
        fake.track = number
        results.append(plug.track())
    assert results == [TrackMode.INDEPENDENT, TrackMode.SERIES, TrackMode.PARALLEL]
    assert fake.log[-1] == 'OUTPut:TRACK?'


def test_track_query_accepts_words() -> None:
    class Words(FakeSpdResource):
        def query(self, message: str) -> str:
            answer = super().query(message)
            if message == 'OUTPut:TRACK?':
                return ('INDEPENDENT', 'SERIES', 'PARALLEL')[int(answer)]
            return answer

    plug, fake = _plug(fake=Words())
    plug.set_track(TrackMode.PARALLEL)
    assert plug.track() is TrackMode.PARALLEL


def test_track_query_rejects_garbage() -> None:
    plug, fake = _plug()
    fake.track = 7
    with pytest.raises(RuntimeError, match='OUTPut:TRACK'):
        plug.track()


@pytest.mark.parametrize('busy', [2, 3])
def test_set_track_refuses_while_ch2_or_ch3_is_on(busy: int) -> None:
    plug, fake = _plug()
    plug.set_output(busy, True)
    start = len(fake.log)
    with pytest.raises(RuntimeError, match=f'CH{busy}'):
        plug.set_track(TrackMode.SERIES)
    assert not any(c.startswith('OUTPut:TRACK ') for c in _new(fake, start))
    assert fake.track == 0


def test_set_track_allows_ch1_and_ch4_to_be_on() -> None:
    plug, fake = _plug()
    plug.set_output(1, True)
    plug.set_output(4, True)
    plug.set_track(TrackMode.SERIES)
    assert fake.track == 1


def test_set_track_detects_an_ignored_command() -> None:
    plug, _ = _plug(reject={'OUTPut:TRACK': 'x'})
    with pytest.raises(RuntimeError, match='OUTPut:TRACK SERIES'):
        plug.set_track(TrackMode.SERIES)


def test_set_sense_and_query() -> None:
    plug, fake = _plug()
    plug.set_sense(2, SenseMode.FOUR_WIRE)
    plug.set_sense(Channel.CH3, SenseMode.TWO_WIRE)
    assert fake.log[1:] == ['MODE CH2,4W', 'MODE? CH2', 'MODE CH3,2W', 'MODE? CH3']
    assert plug.sense(2) is SenseMode.FOUR_WIRE
    assert plug.sense(3) is SenseMode.TWO_WIRE
    assert fake.log[-2:] == ['MODE? CH2', 'MODE? CH3']


@pytest.mark.parametrize('ch', [1, 4])
def test_sense_is_only_for_ch2_and_ch3(ch: int) -> None:
    plug, fake = _plug()
    with pytest.raises(ValueError):
        plug.set_sense(ch, SenseMode.FOUR_WIRE)
    with pytest.raises(ValueError):
        plug.sense(ch)
    assert fake.log == ['*IDN?']


def test_sense_query_accepts_words_and_rejects_garbage() -> None:
    class Words(FakeSpdResource):
        def query(self, message: str) -> str:
            answer = super().query(message)
            return ('2W', '4W')[int(answer)] if message.startswith('MODE?') else answer

    plug, fake = _plug(fake=Words())
    plug.set_sense(2, SenseMode.FOUR_WIRE)
    assert plug.sense(2) is SenseMode.FOUR_WIRE
    plain, plain_fake = _plug()
    plain_fake.sense[2] = 5
    with pytest.raises(RuntimeError, match='MODE'):
        plain.sense(2)


def test_set_sense_detects_an_ignored_command() -> None:
    plug, _ = _plug(reject={'MODE CH2': 'x'})
    with pytest.raises(RuntimeError, match='MODE CH2,4W'):
        plug.set_sense(2, SenseMode.FOUR_WIRE)


# ---- lock -----------------------------------------------------------------------------------


def test_lock() -> None:
    plug, fake = _plug()
    plug.set_lock(True)
    assert plug.locked() is True
    plug.set_lock(False)
    assert plug.locked() is False
    assert fake.log[1:] == [
        ':SOURce:LOCK:STATe ON',
        ':SOURce:LOCK:STATe?',
        ':SOURce:LOCK:STATe?',
        ':SOURce:LOCK:STATe OFF',
        ':SOURce:LOCK:STATe?',
        ':SOURce:LOCK:STATe?',
    ]


# ---- boolean arguments --------------------------------------------------------------------

BAD_BOOLS = ['off', 'on', 'OFF', '0', '1', '', 2, -1, 0.0, 1.0, None, [], [0], Channel.CH1]


@pytest.mark.parametrize('bad', BAD_BOOLS)
def test_boolean_setters_reject_non_boolean_values_before_sending(bad: Any) -> None:
    plug, fake = _plug()
    calls = [
        lambda: plug.set_output(1, bad),
        lambda: plug.set_all_outputs(bad),
        lambda: plug.set_ocp_enabled(1, bad),
        lambda: plug.set_lock(bad),
    ]
    if bad is not None:  # configure_channel(ocp_enabled=None) means "leave it alone"
        calls.append(lambda: plug.configure_channel(1, voltage=1, ocp_enabled=bad))
    for call in calls:
        with pytest.raises(ValueError):
            call()
    assert fake.log == ['*IDN?']
    assert not any(c.output for c in fake.channels.values())


def test_string_off_does_not_turn_an_output_on() -> None:
    # Regression: set_output(1, 'off') used to be bool('off') -> True -> OUTPut CH1,1.
    plug, fake = _plug()
    with pytest.raises(ValueError):
        plug.set_output(1, 'off')  # type: ignore[arg-type]
    assert fake.channels[1].output is False
    assert 'OUTPut CH1,1' not in fake.log


@pytest.mark.parametrize(('value', 'expected'), [(True, 1), (False, 0), (1, 1), (0, 0)])
def test_boolean_setters_accept_bools_and_the_ints_0_and_1(value: Any, expected: int) -> None:
    plug, fake = _plug()
    plug.set_output(1, value)
    plug.set_ocp_enabled(1, value)
    plug.set_all_outputs(value)
    plug.set_lock(value)
    plug.configure_channel(2, ocp_enabled=value)
    assert f'OUTPut CH1,{expected}' in fake.log
    assert f':SOURce:OCP:STATe CH1,{expected}' in fake.log
    assert f'OUTPut:ALL {expected}' in fake.log
    assert f':SOURce:LOCK:STATe {"ON" if expected else "OFF"}' in fake.log
    assert f':SOURce:OCP:STATe CH2,{expected}' in fake.log


def test_configure_channel_validates_the_boolean_before_applying_anything() -> None:
    plug, fake = _plug()
    with pytest.raises(ValueError, match='ocp_enabled'):
        plug.configure_channel(1, ovp=4, voltage=3, ocp_enabled='off')  # type: ignore[arg-type]
    assert fake.log == ['*IDN?']


# ---- snapshot and restore -------------------------------------------------------------------


def test_snapshot_contents() -> None:
    plug, fake = _plug()
    plug.configure_channel(1, voltage=3, current=0.5, ovp=4, ocp=1, ocp_enabled=True, ocp_delay=2)
    plug.set_output_delay(1, on_s=3, off_s=1.5)
    snap = plug.snapshot()
    assert snap['track'] is TrackMode.INDEPENDENT
    assert snap['channels'][1] == {
        'voltage': 3.0,
        'current': 0.5,
        'ovp': 4.0,
        'ocp': 1.0,
        'ocp_enabled': True,
        'ocp_delay': 2.0,
        'on_delay': 3.0,
        'off_delay': 1.5,
        'output': False,
    }
    assert set(snap['channels']) == set(ALL)


def test_restore_writes_values_back_in_order() -> None:
    plug, fake = _plug()
    plug.configure_channel(1, voltage=3, current=0.5, ovp=4, ocp=1, ocp_enabled=True, ocp_delay=2)
    plug.set_output_delay(1, on_s=3, off_s=1.5)
    snap = plug.snapshot()
    plug.configure_channel(1, voltage=1, current=0.1, ovp=5, ocp=2, ocp_enabled=False, ocp_delay=0)
    plug.set_output_delay(1, on_s=0, off_s=0)
    start = len(fake.log)
    plug.restore(snap)
    ch1 = [c for c in _new(fake, start) if c.endswith('CH1') or 'CH1,' in c]
    assert [c for c in ch1 if '?' not in c] == [
        ':SOURce:OVP CH1,4',
        ':SOURce:OCP CH1,1',
        'OCP:DELay CH1,2',
        ':SOURce:OCP:STATe CH1,1',
        'OUTPut:ON:DELay CH1,3',
        'OUTPut:OFF:DELay CH1,1.5',
        ':SOURce:VOLTage:SET CH1,3',
        ':SOURce:CURRent:SET CH1,0.5',
    ]
    assert (fake.channels[1].voltage, fake.channels[1].ocp_enabled) == (3, True)
    assert (fake.channels[1].on_delay, fake.channels[1].off_delay) == (3, 1.5)


def test_restore_writes_the_track_mode_first_and_only_if_it_differs() -> None:
    plug, fake = _plug()
    snap = plug.snapshot()
    start = len(fake.log)
    plug.restore(snap)  # same track mode: no track write
    assert not any(c.startswith('OUTPut:TRACK ') for c in _new(fake, start))
    plug.set_track(TrackMode.SERIES)
    start = len(fake.log)
    plug.restore(snap)
    new = _new(fake, start)
    assert fake.track == 0
    assert new[0] == 'OUTPut:TRACK?'
    track_write = new.index('OUTPut:TRACK INDEPENDENT')
    first_channel_read = new.index(':SOURce:OVP? CH1')
    assert track_write < first_channel_read
    assert not [c for c in new[track_write + 1 :] if '?' not in c]  # nothing differs: no writes


def test_restore_reads_first_and_writes_only_what_differs() -> None:
    plug, fake = _plug()
    plug.configure_channel(1, voltage=3, current=0.5, ovp=4)
    snap = plug.snapshot()
    plug.set_voltage(1, 2)
    plug.set_ocp_delay(3, 1.5)
    start = len(fake.log)
    plug.restore(snap)
    new = _new(fake, start)
    assert [c for c in new if '?' not in c] == [
        ':SOURce:VOLTage:SET CH1,3',
        'OCP:DELay CH3,0',
    ]
    assert new.index(':SOURce:VOLTage:SET? CH1') < new.index(':SOURce:VOLTage:SET CH1,3')
    assert fake.channels[1].voltage == 3
    start = len(fake.log)
    plug.restore(snap)  # now everything matches: reads only
    assert not [c for c in _new(fake, start) if '?' not in c]


def test_restore_of_a_value_between_rating_and_instrument_maximum_is_reported() -> None:
    # The panel held 6.03 V (between the 6 V rating and the 6.06 V maximum); once changed, the
    # guard refuses to write it back and nothing is sent for that item.
    fake = FakeSpdResource()
    fake.write('VOLTage CH1,6.03')
    plug, _ = _plug(fake=fake, restore_state=True)
    plug.set_voltage(1, 1)
    start = len(fake.log)
    with pytest.raises(RuntimeError, match='CH1 voltage'):
        plug.restore(plug._snapshot or {})
    assert not [c for c in _new(fake, start) if c.startswith(':SOURce:VOLTage:SET CH1')]


@pytest.mark.parametrize('mode', [TrackMode.SERIES, TrackMode.PARALLEL])
def test_restore_skips_ch2_and_ch3_setpoints_in_a_coupled_mode_and_reports_them(
    mode: TrackMode,
) -> None:
    plug, fake = _plug()
    plug.set_track(mode)
    snap = plug.snapshot()
    snap['channels'][1]['voltage'] = 2.0
    snap['channels'][2]['voltage'] = 7.0
    snap['channels'][3]['current'] = 1.0
    snap['channels'][3]['ovp'] = 20.0
    start = len(fake.log)
    with pytest.raises(RuntimeError) as err:
        plug.restore(snap)
    message = str(err.value)
    assert 'CH2 voltage/current' in message
    assert 'CH3 voltage/current' in message
    assert 'question 21' in message
    writes = [c for c in _new(fake, start) if '?' not in c]
    assert ':SOURce:VOLTage:SET CH1,2' in writes  # CH1 is restored
    assert ':SOURce:OVP CH3,20' in writes  # so are the protection values of CH3
    assert not [
        c for c in writes if c.startswith((':SOURce:VOLTage:SET CH2', ':SOURce:CURRent:SET CH3'))
    ]
    assert fake.channels[2].voltage == 0


def test_restore_never_turns_an_output_on() -> None:
    plug, fake = _plug()
    for n in ALL:
        plug.set_output(n, True)
    snap = plug.snapshot()
    assert all(snap['channels'][n]['output'] for n in ALL)
    for n in ALL:
        plug.set_output(n, False)
    start = len(fake.log)
    plug.restore(snap)
    assert not any(c.output for c in fake.channels.values())
    writes = [c for c in _new(fake, start) if '?' not in c]
    assert not [c for c in writes if c.startswith(('OUTPut CH', 'OUTPut:ALL'))]


def test_restore_skips_a_channel_whose_output_is_on_and_names_it() -> None:
    plug, fake = _plug()
    plug.configure_channel(2, voltage=3, current=0.5)
    snap = plug.snapshot()
    plug.configure_channel(2, voltage=7, current=1)
    plug.configure_channel(1, voltage=2)
    plug.set_output(2, True)
    start = len(fake.log)
    with pytest.raises(RuntimeError) as err:
        plug.restore(snap)
    assert 'CH2' in str(err.value)
    assert 'output is on' in str(err.value)
    assert 'CH1' not in str(err.value)
    new = _new(fake, start)
    assert not [c for c in new if ' CH2' in c and '?' not in c]  # nothing written to CH2
    assert (fake.channels[2].voltage, fake.channels[2].current) == (7, 1)
    assert fake.channels[1].voltage == 0  # the other channels were restored
    assert fake.channels[2].output is True


def test_restore_skips_ch2_and_ch3_when_the_track_restore_is_refused() -> None:
    plug, fake = _plug()
    snap = plug.snapshot()
    plug.set_track(TrackMode.SERIES)
    fake.channels[2].voltage = 40  # set "from the panel": the plug refuses to write these
    fake.channels[3].voltage = 1
    plug.configure_channel(1, voltage=2)
    fake.reject = {'OUTPut:TRACK': 'refused'}
    start = len(fake.log)
    with pytest.raises(RuntimeError) as err:
        plug.restore(snap)
    message = str(err.value)
    assert 'track' in message
    assert 'CH2' in message
    assert 'CH3' in message
    assert 'CH1' not in message.split('skipped channels')[-1]
    new = _new(fake, start)
    assert not [c for c in new if (' CH2' in c or ' CH3' in c) and '?' not in c]
    assert (fake.channels[2].voltage, fake.channels[3].voltage) == (40, 1)
    assert fake.channels[1].voltage == 0  # CH1 and CH4 do not depend on the track mode


def test_restore_skips_ch2_and_ch3_when_the_track_query_fails() -> None:
    plug, fake = _plug()
    snap = plug.snapshot()
    real_query = fake.query

    def broken(message: str) -> str:
        if message == 'OUTPut:TRACK?':
            raise OSError('timeout')
        return real_query(message)

    fake.query = broken  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match='CH2 .*CH3') as err:
        plug.restore(snap)
    assert 'timeout' in str(err.value)


def test_restore_collects_every_failure() -> None:
    plug, fake = _plug()
    snap = plug.snapshot()
    snap['channels'][1]['voltage'] = 3.0
    snap['channels'][2]['ovp'] = 5.0
    snap['channels'][3]['ocp_delay'] = 4.0
    fake.reject = {':SOURce:VOLTage:SET CH1': 'x', ':SOURce:OVP CH2': 'x'}
    with pytest.raises(RuntimeError) as err:
        plug.restore(snap)
    message = str(err.value)
    assert 'CH1 voltage' in message
    assert 'CH2 OVP' in message
    assert 'skipped' not in message
    assert fake.channels[3].ocp_delay == 4.0  # later items were still attempted


# ---- tearDown -------------------------------------------------------------------------------


def test_teardown_turns_outputs_off_unlocks_and_closes() -> None:
    plug, fake = _plug(teardown_off=True)
    for n in ALL:
        plug.set_output(n, True)
    plug.set_lock(True)
    start = len(fake.log)
    plug.tearDown()
    assert _new(fake, start) == [
        *(c for n in ALL for c in (f'OUTPut? CH{n}', f'OUTPut:OFF:DELay? CH{n}')),
        'OUTPut:ALL 0',
        *(f'OUTPut? CH{n}' for n in ALL),
        ':SOURce:LOCK:STATe OFF',
        ':SOURce:LOCK:STATe?',
    ]
    assert not any(c.output for c in fake.channels.values())
    assert fake.lock == 0
    assert fake.closed


def test_teardown_leaves_the_panel_unlocked_with_the_unlock_as_the_last_write() -> None:
    plug, fake = _plug(teardown_off=True, restore_state=True)
    plug.configure_channel(1, voltage=3, ovp=4)
    plug.set_output(1, True)
    assert fake.lock == 1  # every remote write locks the panel on the real supply
    plug.tearDown()
    assert fake.lock == 0
    writes = [c for c in fake.log if '?' not in c]
    assert writes[-1] == ':SOURce:LOCK:STATe OFF'
    assert writes.count(':SOURce:LOCK:STATe OFF') == 1
    assert 'OUTPut:ALL 0' in writes
    assert any(c.startswith(':SOURce:OVP CH1') for c in writes[:-1])  # the restore wrote before
    assert fake.log[-1] == ':SOURce:LOCK:STATe?'  # only the read-back follows the unlock
    assert fake.closed


def test_teardown_without_outputs_off_still_unlocks_and_closes() -> None:
    plug, fake = _plug(teardown_off=False)
    plug.set_output(1, True)
    plug.tearDown()
    assert fake.channels[1].output is True
    assert 'OUTPut:ALL 0' not in fake.log
    assert fake.log[-2:] == [':SOURce:LOCK:STATe OFF', ':SOURce:LOCK:STATe?']
    assert fake.closed


def test_teardown_never_enables_an_output() -> None:
    # Outputs are on before the snapshot, so a restore that wrote the snapshot's output state
    # back would send OUTPut CHn,1; the assertion below would catch it.
    fake = FakeSpdResource()
    for n in ALL:
        fake.channels[n].output = True
    plug, _ = _plug(fake=fake, teardown_off=True, restore_state=True)
    assert plug._snapshot is not None
    assert all(plug._snapshot['channels'][n]['output'] for n in ALL)
    start = len(fake.log)
    plug.tearDown()
    sent = _new(fake, start)
    assert 'OUTPut:ALL 0' in sent
    assert not [c for c in sent if c.startswith(('OUTPut CH', 'OUTPut:ALL')) and c.endswith('1')]
    assert not [c for c in sent if c.startswith(('OUTPut CH', 'OUTPut:ALL')) and c.endswith('ON')]
    assert not any(c.output for c in fake.channels.values())


def test_teardown_falls_back_to_per_channel_off() -> None:
    plug, fake = _plug(teardown_off=True, reject={'OUTPut:ALL': 'x'})
    plug.set_output(1, True)
    plug.set_output(3, True)
    plug.tearDown()
    assert not any(c.output for c in fake.channels.values())
    assert 'OUTPut CH1,0' in fake.log
    assert fake.log[-2:] == [':SOURce:LOCK:STATe OFF', ':SOURce:LOCK:STATe?']
    assert fake.closed


def test_teardown_continues_after_every_failing_step(caplog: pytest.LogCaptureFixture) -> None:
    plug, fake = _plug(teardown_off=True, restore_state=True)
    plug.set_output(1, True)
    plug.set_lock(True)
    assert plug._snapshot is not None
    plug._snapshot['channels'][2]['ovp'] = 5.0
    fake.reject = {'OUTPut': 'x', ':SOURce:OVP': 'x', ':SOURce:LOCK': 'x'}
    with caplog.at_level(logging.WARNING):
        plug.tearDown()
    assert fake.closed
    assert ':SOURce:LOCK:STATe OFF' in fake.log  # the unlock was attempted after the failing steps
    assert 'teardown: OUTPut:ALL 0 failed' in caplog.text
    assert "teardown step 'restore state' failed" in caplog.text
    assert "teardown step 'unlock front panel' failed" in caplog.text


def test_teardown_zeroes_an_off_delay_before_switching_off(
    caplog: pytest.LogCaptureFixture,
) -> None:
    plug, fake = _plug(teardown_off=True)
    plug.configure_channel(1, voltage=3, current=0.5)
    plug.set_output_delay(1, off_s=2)
    plug.set_output_delay(2, off_s=4)  # CH2 is off: its delay is none of the teardown's business
    plug.set_output(1, True)
    start = len(fake.log)
    with caplog.at_level(logging.WARNING):
        plug.tearDown()
    sent = _new(fake, start)
    assert sent.index('OUTPut:OFF:DELay CH1,0') < sent.index('OUTPut:ALL 0')
    assert 'OUTPut:OFF:DELay CH2,0' not in sent
    assert fake.channels[1].off_delay == 0
    assert fake.channels[2].off_delay == 4
    assert fake.channels[1].output is False  # really off, not "off after the delay"
    assert fake.channels[1].off_remaining is None
    assert 'CH1 has an OFF delay of 2 s' in caplog.text


def test_a_delayed_switch_off_would_leave_the_output_on_without_the_zeroing() -> None:
    # Documents what the fake does and why the teardown has to zero the delay first.
    fake = FakeSpdResource()
    plug, _ = _plug(fake=fake, teardown_off=False)
    plug.set_output(1, True)
    plug.set_output_delay(1, off_s=2)
    plug.write('OUTPut:ALL 0')
    assert plug.output(1) is True
    fake.advance(2)
    assert plug.output(1) is False


def test_teardown_skips_the_restore_after_a_transport_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    plug, fake = _plug(teardown_off=True, restore_state=True)
    plug.configure_channel(1, voltage=3)
    real_query = fake.query

    def broken(message: str) -> str:
        if message.startswith('OUTPut'):
            raise OSError('VI_ERROR_TMO')
        return real_query(message)

    fake.query = broken  # type: ignore[method-assign]
    start = len(fake.log)
    with caplog.at_level(logging.WARNING):
        plug.tearDown()
    sent = _new(fake, start)
    assert 'OUTPut:ALL 0' in sent
    assert 'OUTPut CH1,0' in sent  # the per-channel fallback was still tried
    assert fake.channels[1].voltage == 3  # restore did not run
    assert not [c for c in sent if c.startswith(':SOURce:OVP ')]
    assert 'restore state skipped' in caplog.text
    assert 'VI_ERROR_TMO' in caplog.text
    assert ':SOURce:LOCK:STATe OFF' in sent  # the unlock still ran
    assert fake.closed


def test_teardown_still_restores_after_a_read_back_mismatch() -> None:
    # A refused write is not a transport error: the link works, so the restore runs.
    plug, fake = _plug(teardown_off=True, restore_state=True, reject={'OUTPut:ALL': 'x'})
    plug.configure_channel(1, voltage=3)
    plug.tearDown()
    assert fake.channels[1].voltage == 0


def test_teardown_restores_state_when_enabled() -> None:
    plug, fake = _plug(teardown_off=True, restore_state=True)
    plug.configure_channel(1, voltage=3, ovp=4)
    plug.set_output(1, True)
    plug.tearDown()
    assert fake.channels[1].voltage == 0
    assert fake.channels[1].ovp == to_float32(6.6)  # the supply's default, not 4 V
    assert fake.channels[1].output is False
    assert fake.closed


def test_teardown_closes_even_if_the_resource_is_broken(caplog: pytest.LogCaptureFixture) -> None:
    plug, fake = _plug(teardown_off=True)

    def boom(message: str) -> None:
        raise OSError('link down')

    fake.write = boom  # type: ignore[method-assign]
    fake.query = boom  # type: ignore[assignment,method-assign]
    with caplog.at_level(logging.WARNING):
        plug.tearDown()
    assert fake.closed
    assert 'link down' in caplog.text


def test_teardown_is_safe_to_call_twice() -> None:
    plug, fake = _plug(teardown_off=True)
    plug.tearDown()
    plug.tearDown()
    assert fake.closed


# ---- things the plug must never do ------------------------------------------------------------


def test_forbidden_commands_never_sent_in_a_full_workout() -> None:
    plug, fake = _plug(teardown_off=True, restore_state=True, loads={1: 10.0})
    plug.configure_channel(1, voltage=3, current=0.5, ovp=4, ocp=1, ocp_enabled=True, ocp_delay=1)
    plug.set_output(1, True)
    plug.measure(1)
    plug.set_track(TrackMode.SERIES)
    plug.set_sense(2, SenseMode.TWO_WIRE)
    plug.set_output_delay(1, 1, 1)
    plug.protection_status(1)
    plug.clear_protection(1)
    plug.tearDown()
    forbidden = ('*RST', 'DEFAult', 'FACTory', 'LAN:', 'SYSTem')
    assert not [c for c in fake.log if any(f.lower() in c.lower() for f in forbidden)]


def test_source_has_no_factory_reset_or_unlisted_subsystems() -> None:
    from pathlib import Path

    import siglent_spd_openhtf

    root = Path(siglent_spd_openhtf.__file__).parent
    text = '\n'.join(p.read_text() for p in root.glob('*.py'))
    for word in ('FACTory', 'DEFAult:', '*RST', 'LIST:', 'WAVE:', 'STORage', 'CALibrate'):
        assert word not in text, word
