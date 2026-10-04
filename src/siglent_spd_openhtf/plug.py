"""OpenHTF plug for Siglent SPD4000X programmable DC power supplies.

Every SCPI string in this module is taken from ``docs/scpi_reference.md``. The manual defines
no error query, so every setter reads its value back and raises if the instrument did not
take the value.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from enum import IntEnum, StrEnum
from functools import partial
from typing import Any, NamedTuple, Protocol, cast

from openhtf.plugs import BasePlug
from openhtf.util import configuration

from .models import ChannelRating, Model, model_from_idn

CONF = configuration.CONF

CONF.declare(
    'siglent_spd_resource',
    default_value='',
    description=(
        'VISA resource name of the supply; '
        'empty = first USB instrument whose *IDN? names an SPD4xxx'
    ),
)
CONF.declare(
    'siglent_spd_outputs_off_on_teardown',
    default_value=True,
    description='Turn all outputs off in tearDown()',
)
CONF.declare(
    'siglent_spd_restore_state',
    default_value=False,
    description=(
        'Restore setpoints and protection values captured at connect in tearDown(); '
        'never re-enables outputs'
    ),
)

_LOG = logging.getLogger(__name__)

_MAX_DELAY_S = 3600.0
_RATING_EPS = 1e-9


class Channel(IntEnum):
    """Output channel; ``str(Channel.CH1)`` is the wire spelling ``CH1``."""

    CH1 = 1
    CH2 = 2
    CH3 = 3
    CH4 = 4

    def __str__(self) -> str:
        return f'CH{int(self)}'


class TrackMode(StrEnum):
    """CH2/CH3 coupling."""

    # SPEC-NOTE: the spec says (str, Enum); StrEnum is the same plus str() giving the value
    # (ruff rule UP042 asks for it).

    INDEPENDENT = 'INDEPENDENT'
    SERIES = 'SERIES'
    PARALLEL = 'PARALLEL'


class SenseMode(StrEnum):
    """Remote sense of CH2/CH3."""

    TWO_WIRE = '2W'
    FOUR_WIRE = '4W'


class Identity(NamedTuple):
    vendor: str
    model: str
    serial: str
    firmware: str


class Reading(NamedTuple):
    voltage: float
    current: float
    power: float
    mode: str  # 'CV', 'CC' or whatever the instrument returns


class ProtectionStatus(NamedTuple):
    ovp_tripped: bool
    ocp_tripped: bool


class ScpiResource(Protocol):
    """The part of a PyVISA message-based resource the plug uses."""

    timeout: Any
    read_termination: Any
    write_termination: Any

    def write(self, message: str) -> Any: ...

    def query(self, message: str) -> str: ...

    def close(self) -> None: ...


_ALL_CHANNELS = (1, 2, 3, 4)
_TRACK_BY_NUMBER = {
    '0': TrackMode.INDEPENDENT,
    '1': TrackMode.SERIES,
    '2': TrackMode.PARALLEL,
}
_SENSE_BY_NUMBER = {'0': SenseMode.TWO_WIRE, '1': SenseMode.FOUR_WIRE}


def _channel(channel: int | Channel) -> int:
    """Validate a channel argument and return it as a plain int 1..4."""
    if isinstance(channel, bool) or not isinstance(channel, int):
        raise ValueError(f'channel must be an int 1..4 or a Channel, got {channel!r}')
    if channel not in _ALL_CHANNELS:
        raise ValueError(f'channel must be 1..4, got {channel!r}')
    return int(channel)


def _nonnegative(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f'{name} must be a finite number >= 0, got {value!r}')
    return number


def _delay(name: str, value: float) -> float:
    number = _nonnegative(name, value)
    if number > _MAX_DELAY_S:
        raise ValueError(f'{name} must be within 0..{_MAX_DELAY_S:g} s, got {value!r}')
    return number


def _to_float(text: str, what: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise RuntimeError(f'{what}: expected a number, instrument answered {text!r}') from None


def _to_bool(text: str, what: str) -> bool:
    word = text.strip().upper()
    if word in ('1', 'ON'):
        return True
    if word in ('0', 'OFF'):
        return False
    raise RuntimeError(f'{what}: expected 0 or 1, instrument answered {text!r}')


def _parse_track(text: str) -> TrackMode:
    word = text.strip().upper()
    # ASSUMPTION(hw): track numbering. The manual only shows 0 = independent; 1 = series and
    # 2 = parallel is inferred from the order {0|1|2|INDEPENDENT|SERIES|PARALLEL}. Words are
    # accepted as well in case the instrument answers with one.
    if word in _TRACK_BY_NUMBER:
        return _TRACK_BY_NUMBER[word]
    for mode in TrackMode:
        if word == mode.value:
            return mode
    raise RuntimeError(f'OUTPut:TRACK?: unrecognised answer {text!r}')


def _parse_sense(text: str) -> SenseMode:
    word = text.strip().upper()
    # ASSUMPTION(hw): sense numbering. The manual does not map 0/1 to 2W/4W; 0 = 2W and
    # 1 = 4W is assumed from the order {0|1|2W|4W}. Words are accepted as well.
    if word in _SENSE_BY_NUMBER:
        return _SENSE_BY_NUMBER[word]
    for mode in SenseMode:
        if word == mode.value:
            return mode
    raise RuntimeError(f'MODE?: unrecognised answer {text!r}')


class SiglentSpdPlug(BasePlug):  # type: ignore[misc]
    """Control a Siglent SPD4000X power supply over PyVISA."""

    auto_placeholder = True

    def __init__(
        self,
        resource: ScpiResource | None = None,
        outputs_off_on_teardown: bool | None = None,
        restore_state: bool | None = None,
    ) -> None:
        super().__init__()
        self._outputs_off_on_teardown: bool = (
            bool(CONF.siglent_spd_outputs_off_on_teardown)
            if outputs_off_on_teardown is None
            else outputs_off_on_teardown
        )
        self._restore_state: bool = (
            bool(CONF.siglent_spd_restore_state) if restore_state is None else restore_state
        )
        self._rm: Any = None
        self._closed = False
        self._track: TrackMode | None = None
        self._snapshot: dict[str, Any] | None = None
        self.model: Model | None = None
        self.resource: ScpiResource
        if resource is None:
            self.resource = self._open_resource()
        else:
            self.resource = resource
        try:
            # ASSUMPTION(hw): terminator. The manual does not state which terminator commands
            # need nor what responses end with; '\n' is assumed for both directions.
            self.resource.timeout = 5000
            self.resource.read_termination = '\n'
            self.resource.write_termination = '\n'
            self.identity = self.idn()
            self.model = model_from_idn(','.join(self.identity))
            if self.model is None:
                self.logger.warning(
                    'Unknown model %r: channel limits come only from read-back',
                    self.identity.model,
                )
            if self._restore_state:
                self._snapshot = self.snapshot()
        except BaseException:
            self._close()
            raise

    # ---- connection ---------------------------------------------------------------------

    def _open_resource(self) -> ScpiResource:
        import pyvisa  # lazy: tests with a fake resource never import it

        rm = pyvisa.ResourceManager('@py')
        self._rm = rm
        try:
            name = str(CONF.siglent_spd_resource)
            if name:
                return cast(ScpiResource, rm.open_resource(name))
            for candidate in rm.list_resources('USB?*::INSTR'):
                try:
                    opened: Any = rm.open_resource(candidate)
                except Exception as exc:
                    _LOG.debug('cannot open %s: %s', candidate, exc)
                    continue
                try:
                    opened.timeout = 5000
                    opened.read_termination = '\n'
                    opened.write_termination = '\n'
                    fields = opened.query('*IDN?').strip().split(',')
                    if len(fields) > 1 and fields[1].strip().upper().startswith('SPD4'):
                        return cast(ScpiResource, opened)
                except Exception as exc:
                    _LOG.debug('%s did not answer *IDN?: %s', candidate, exc)
                opened.close()
            raise RuntimeError(
                'No Siglent SPD4xxx found on USB; set the CONF key siglent_spd_resource '
                "to a VISA resource name, for example 'TCPIP::192.0.2.10::INSTR'"
            )
        except BaseException:
            rm.close()
            self._rm = None
            raise

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.resource.close()
        except Exception as exc:
            self.logger.warning('closing the resource failed: %s', exc)
        if self._rm is not None:
            try:
                self._rm.close()
            except Exception as exc:
                self.logger.warning('closing the ResourceManager failed: %s', exc)

    # ---- low level ----------------------------------------------------------------------

    def write(self, cmd: str) -> None:
        self.logger.debug('SCPI write: %s', cmd)
        self.resource.write(cmd)

    def query(self, cmd: str) -> str:
        self.logger.debug('SCPI query: %s', cmd)
        answer = self.resource.query(cmd).strip()
        self.logger.debug('SCPI answer: %s', answer)
        return answer

    @staticmethod
    def _fmt(x: float) -> str:
        return format(x, '.9G')

    @staticmethod
    def _values_match(expected: bool | float | str, actual: str) -> bool:
        text = actual.strip()
        if isinstance(expected, bool):
            word = text.upper()
            if word in ('1', 'ON'):
                return expected
            if word in ('0', 'OFF'):
                return not expected
            return False
        if isinstance(expected, (int, float)):
            try:
                number = float(text)
            except ValueError:
                return False
            return math.isclose(float(expected), number, rel_tol=1e-6, abs_tol=5e-4)
        return text.casefold() == expected.casefold()

    def write_verified(
        self,
        cmd: str,
        query_cmd: str,
        expected: bool | float | str,
        *,
        parse: Callable[[str], Any] | None = None,
    ) -> None:
        """Write ``cmd``, read ``query_cmd`` back and raise RuntimeError on a mismatch.

        ``parse`` optionally converts the answer (for example a track number to a TrackMode)
        before it is compared with ``expected`` by equality.
        """
        self.write(cmd)
        try:
            actual = self.query(query_cmd)
            value: Any = parse(actual) if parse is not None else actual
        except Exception as exc:
            raise RuntimeError(
                f'{cmd!r}: read-back {query_cmd!r} failed ({type(exc).__name__}: {exc})'
            ) from exc
        if parse is not None:
            ok = value == expected
        else:
            ok = self._values_match(expected, actual)
        if not ok:
            raise RuntimeError(
                f'{cmd!r} was not accepted: expected {expected!r}, '
                f'{query_cmd!r} answered {actual!r}'
            )

    # ---- identity and state -------------------------------------------------------------

    def idn(self) -> Identity:
        answer = self.query('*IDN?')
        fields = [f.strip() for f in answer.split(',', 3)]
        if len(fields) < 4:
            raise RuntimeError(f'*IDN? answered {answer!r}, expected 4 comma-separated fields')
        return Identity(*fields)

    def opc(self) -> str:
        return self.query('*OPC?')

    def snapshot(self) -> dict[str, Any]:
        """Read setpoints, protection values and output states of every channel."""
        channels: dict[int, dict[str, Any]] = {}
        for n in _ALL_CHANNELS:
            channels[n] = {
                'voltage': self.voltage_setpoint(n),
                'current': self.current_setpoint(n),
                'ovp': self.ovp(n),
                'ocp': self.ocp(n),
                'ocp_enabled': self.ocp_enabled(n),
                'ocp_delay': self.ocp_delay(n),
                'output': self.output(n),
            }
        return {'channels': channels, 'track': self.track()}

    def restore(self, snapshot: dict[str, Any]) -> None:
        """Write a snapshot back. Never turns an output on; raises one error for all failures."""
        failures: list[str] = []

        def attempt(label: str, action: Callable[[], Any]) -> None:
            try:
                action()
            except Exception as exc:
                failures.append(f'{label}: {exc}')

        wanted: TrackMode = snapshot['track']
        try:
            current = self.track()
        except Exception as exc:
            failures.append(f'track: {exc}')
        else:
            if current != wanted:
                attempt('track', lambda: self.set_track(wanted))
        for n, values in snapshot['channels'].items():
            # The 'output' entry is deliberately ignored: restore never enables an output.
            setters: list[tuple[str, Callable[[int, Any], None], Any]] = [
                ('OVP', self.set_ovp, values['ovp']),
                ('OCP', self.set_ocp, values['ocp']),
                ('OCP delay', self.set_ocp_delay, values['ocp_delay']),
                ('OCP state', self.set_ocp_enabled, values['ocp_enabled']),
                ('voltage', self.set_voltage, values['voltage']),
                ('current', self.set_current, values['current']),
            ]
            for label, setter, value in setters:
                attempt(f'CH{n} {label}', partial(setter, n, value))
        if failures:
            raise RuntimeError('restore failed: ' + '; '.join(failures))

    # ---- limits -------------------------------------------------------------------------

    def _rating(self, ch: int) -> ChannelRating | None:
        """Rated limit of a channel in the current coupling, None if the model is unknown."""
        if self.model is None:
            return None
        if ch in (1, 4):
            return self.model.channels[ch - 1]
        mode = self._track if self._track is not None else self.track()
        if mode is TrackMode.SERIES:
            return self.model.series
        if mode is TrackMode.PARALLEL:
            return self.model.parallel
        return self.model.channels[ch - 1]

    def _guard_voltage(self, ch: int, volts: float) -> None:
        rating = self._rating(ch)
        if rating is not None and volts > rating.voltage + _RATING_EPS:
            raise ValueError(f'{volts:g} V exceeds the {rating.voltage:g} V rating of CH{ch}')

    def _guard_current(self, ch: int, amps: float) -> None:
        rating = self._rating(ch)
        if rating is not None and amps > rating.current + _RATING_EPS:
            raise ValueError(f'{amps:g} A exceeds the {rating.current:g} A rating of CH{ch}')

    # ---- output -------------------------------------------------------------------------

    def set_voltage(self, ch: int | Channel, volts: float) -> None:
        n = _channel(ch)
        value = _nonnegative('volts', volts)
        self._guard_voltage(n, value)
        self.write_verified(f'VOLTage CH{n},{self._fmt(value)}', f'VOLTage? CH{n}', value)

    def voltage_setpoint(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(f'VOLTage? CH{n}'), f'VOLTage? CH{n}')

    def set_current(self, ch: int | Channel, amps: float) -> None:
        n = _channel(ch)
        value = _nonnegative('amps', amps)
        self._guard_current(n, value)
        self.write_verified(f'CURRent CH{n},{self._fmt(value)}', f'CURRent? CH{n}', value)

    def current_setpoint(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(f'CURRent? CH{n}'), f'CURRent? CH{n}')

    def set_output(self, ch: int | Channel, on: bool) -> None:
        n = _channel(ch)
        state = bool(on)
        self.write_verified(f'OUTPut CH{n},{int(state)}', f'OUTPut? CH{n}', state)

    def output(self, ch: int | Channel) -> bool:
        n = _channel(ch)
        return _to_bool(self.query(f'OUTPut? CH{n}'), f'OUTPut? CH{n}')

    def set_all_outputs(self, on: bool) -> None:
        state = bool(on)
        self.write(f'OUTPut:ALL {int(state)}')
        # The all-channel query format is undocumented, so verify each channel.
        failures: list[str] = []
        for n in _ALL_CHANNELS:
            try:
                actual = self.output(n)
            except Exception as exc:
                failures.append(f'CH{n}: {exc}')
                continue
            if actual != state:
                failures.append(f'CH{n}: expected output {int(state)}, read {int(actual)}')
        if failures:
            raise RuntimeError(f'OUTPut:ALL {int(state)} not confirmed: ' + '; '.join(failures))

    def all_outputs_off(self) -> None:
        self.set_all_outputs(False)

    def set_output_delay(
        self, ch: int | Channel, on_s: float | None = None, off_s: float | None = None
    ) -> None:
        n = _channel(ch)
        if on_s is None and off_s is None:
            # SPEC-NOTE: the spec does not say what to do without any delay; refusing is the
            # safest reading because it flags a probable caller mistake.
            raise ValueError('set_output_delay needs on_s and/or off_s')
        on_value = None if on_s is None else _delay('on_s', on_s)
        off_value = None if off_s is None else _delay('off_s', off_s)
        if on_value is not None:
            self.write_verified(
                f'OUTPut:ON:DELay CH{n},{self._fmt(on_value)}', f'OUTPut:ON:DELay? CH{n}', on_value
            )
        if off_value is not None:
            self.write_verified(
                f'OUTPut:OFF:DELay CH{n},{self._fmt(off_value)}',
                f'OUTPut:OFF:DELay? CH{n}',
                off_value,
            )

    def configure_channel(
        self,
        ch: int | Channel,
        *,
        voltage: float | None = None,
        current: float | None = None,
        ovp: float | None = None,
        ocp: float | None = None,
        ocp_enabled: bool | None = None,
        ocp_delay: float | None = None,
    ) -> None:
        """Apply the given items in the order ovp, ocp, ocp_delay, ocp_enabled, voltage, current.

        Every item is attempted; one RuntimeError lists all failures.
        """
        n = _channel(ch)
        steps: list[tuple[str, Any, Callable[[Any], None]]] = [
            ('ovp', ovp, lambda x: self.set_ovp(n, x)),
            ('ocp', ocp, lambda x: self.set_ocp(n, x)),
            ('ocp_delay', ocp_delay, lambda x: self.set_ocp_delay(n, x)),
            ('ocp_enabled', ocp_enabled, lambda x: self.set_ocp_enabled(n, x)),
            ('voltage', voltage, lambda x: self.set_voltage(n, x)),
            ('current', current, lambda x: self.set_current(n, x)),
        ]
        failures: list[str] = []
        for name, value, action in steps:
            if value is None:
                continue
            try:
                action(value)
            except Exception as exc:
                failures.append(f'{name}={value!r}: {exc}')
        if failures:
            raise RuntimeError(f'configure_channel CH{n} failed: ' + '; '.join(failures))

    # ---- protection ---------------------------------------------------------------------

    def set_ovp(self, ch: int | Channel, volts: float) -> None:
        n = _channel(ch)
        value = _nonnegative('volts', volts)
        self.write_verified(f'OVP CH{n},{self._fmt(value)}', f'OVP? CH{n}', value)

    def ovp(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(f'OVP? CH{n}'), f'OVP? CH{n}')

    def set_ocp(self, ch: int | Channel, amps: float) -> None:
        n = _channel(ch)
        value = _nonnegative('amps', amps)
        self.write_verified(f'OCP CH{n},{self._fmt(value)}', f'OCP? CH{n}', value)

    def ocp(self, ch: int | Channel) -> float:
        n = _channel(ch)
        # ASSUMPTION(hw): OCP? answers a plain number like OVP?; the manual prints no response.
        return _to_float(self.query(f'OCP? CH{n}'), f'OCP? CH{n}')

    def set_ocp_enabled(self, ch: int | Channel, on: bool) -> None:
        n = _channel(ch)
        state = bool(on)
        self.write_verified(f'OCP:STATe CH{n},{int(state)}', f'OCP:STATe? CH{n}', state)

    def ocp_enabled(self, ch: int | Channel) -> bool:
        n = _channel(ch)
        return _to_bool(self.query(f'OCP:STATe? CH{n}'), f'OCP:STATe? CH{n}')

    def set_ocp_delay(self, ch: int | Channel, seconds: float) -> None:
        n = _channel(ch)
        value = _delay('seconds', seconds)
        self.write_verified(f'OCP:DELay CH{n},{self._fmt(value)}', f'OCP:DELay? CH{n}', value)

    def ocp_delay(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(f'OCP:DELay? CH{n}'), f'OCP:DELay? CH{n}')

    def protection_status(self, ch: int | Channel) -> ProtectionStatus:
        n = _channel(ch)
        # ASSUMPTION(hw): 1 means tripped, 0 means not tripped. The manual only prints 0.
        ovp = _to_bool(self.query(f'OVP:PROTect:STATe? CH{n}'), f'OVP:PROTect:STATe? CH{n}')
        ocp = _to_bool(self.query(f'OCP:PROTect:STATe? CH{n}'), f'OCP:PROTect:STATe? CH{n}')
        return ProtectionStatus(ovp_tripped=ovp, ocp_tripped=ocp)

    def clear_protection(self, ch: int | Channel) -> None:
        n = _channel(ch)
        self.write(f'RESET:PROTect CH{n}')
        status = self.protection_status(n)
        if status.ovp_tripped or status.ocp_tripped:
            raise RuntimeError(f'CH{n} is still in protection after RESET:PROTect: {status}')

    # ---- measurement --------------------------------------------------------------------

    def measure_voltage(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(f'MEASure:VOLTage? CH{n}'), f'MEASure:VOLTage? CH{n}')

    def measure_current(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(f'MEASure:CURRent? CH{n}'), f'MEASure:CURRent? CH{n}')

    def measure_power(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(f'MEASure:POWER? CH{n}'), f'MEASure:POWER? CH{n}')

    def run_mode(self, ch: int | Channel) -> str:
        n = _channel(ch)
        return self.query(f'MEASure:RUN:MODE? CH{n}')

    def measure(self, ch: int | Channel) -> Reading:
        n = _channel(ch)
        return Reading(
            voltage=self.measure_voltage(n),
            current=self.measure_current(n),
            power=self.measure_power(n),
            mode=self.run_mode(n),
        )

    def wait_for_voltage(
        self,
        ch: int | Channel,
        target: float,
        tol: float = 0.05,
        timeout: float = 5.0,
        interval: float = 0.1,
    ) -> float:
        """Poll the measured voltage until it is within ``tol`` of ``target``; return it."""
        n = _channel(ch)
        deadline = time.monotonic() + timeout
        while True:
            volts = self.measure_voltage(n)
            if abs(volts - target) <= tol:
                return volts
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f'CH{n} did not reach {target:g} V +/- {tol:g} V within {timeout:g} s '
                    f'(last reading {volts:g} V)'
                )
            time.sleep(min(interval, remaining))

    # ---- CH2/CH3 coupling and sense -----------------------------------------------------

    def set_track(self, mode: TrackMode) -> None:
        wanted = TrackMode(mode)
        for n in (2, 3):
            if self.output(n):
                raise RuntimeError(f'refusing to change the track mode while CH{n} output is on')
        self._track = None  # the cached value is untrusted until the read-back succeeds
        self.write_verified(
            f'OUTPut:TRACK {wanted.value}', 'OUTPut:TRACK?', wanted, parse=_parse_track
        )
        self._track = wanted

    def track(self) -> TrackMode:
        mode = _parse_track(self.query('OUTPut:TRACK?'))
        self._track = mode
        return mode

    def set_sense(self, ch: int | Channel, mode: SenseMode) -> None:
        n = _channel(ch)
        if n not in (2, 3):
            raise ValueError(f'remote sense exists only on CH2 and CH3, not CH{n}')
        wanted = SenseMode(mode)
        self.write_verified(
            f'MODE CH{n},{wanted.value}', f'MODE? CH{n}', wanted, parse=_parse_sense
        )

    def sense(self, ch: int | Channel) -> SenseMode:
        n = _channel(ch)
        if n not in (2, 3):
            raise ValueError(f'remote sense exists only on CH2 and CH3, not CH{n}')
        return _parse_sense(self.query(f'MODE? CH{n}'))

    # ---- lock and teardown --------------------------------------------------------------

    def set_lock(self, on: bool) -> None:
        state = bool(on)
        self.write_verified(f'LOCK {int(state)}', 'LOCK?', state)

    def locked(self) -> bool:
        return _to_bool(self.query('LOCK?'), 'LOCK?')

    def _outputs_off_safely(self) -> None:
        try:
            self.all_outputs_off()
        except Exception as exc:
            self.logger.warning('teardown: OUTPut:ALL 0 failed: %s', exc)
            # SPEC-NOTE: fall back to per-channel commands. A supply that is left on
            # because the all-channel command failed is the worst outcome of a teardown.
            for n in _ALL_CHANNELS:
                try:
                    self.set_output(n, False)
                except Exception as channel_exc:
                    self.logger.warning('teardown: CH%d output off failed: %s', n, channel_exc)

    def tearDown(self) -> None:
        """Outputs off, optional restore, unlock, close. A failing step never stops the next."""
        steps: list[tuple[str, Callable[[], None]]] = []
        if self._outputs_off_on_teardown:
            steps.append(('outputs off', self._outputs_off_safely))
        snapshot = self._snapshot
        if self._restore_state and snapshot is not None:
            steps.append(('restore state', lambda: self.restore(snapshot)))
        # ASSUMPTION(hw): needed. The panel locks itself under remote control (manual,
        # chapter 5); unlocking at the end is assumed to be required to hand it back.
        steps.append(('unlock front panel', lambda: self.set_lock(False)))
        for label, step in steps:
            try:
                step()
            except Exception as exc:
                self.logger.warning('teardown step %r failed: %s', label, exc)
        self._close()
