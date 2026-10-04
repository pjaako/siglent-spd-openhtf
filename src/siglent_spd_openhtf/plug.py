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
    # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q13):
    # the query answers the number, 0 = independent, 1 = series, 2 = parallel. Words are
    # accepted as well in case another firmware answers with one.
    if word in _TRACK_BY_NUMBER:
        return _TRACK_BY_NUMBER[word]
    for mode in TrackMode:
        if word == mode.value:
            return mode
    raise RuntimeError(f'OUTPut:TRACK?: unrecognised answer {text!r}')


def _parse_sense(text: str) -> SenseMode:
    word = text.strip().upper()
    # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q13):
    # the query answers the number, 0 = 2W, 1 = 4W (written on CH2; CH3 not written). Words are
    # accepted as well.
    if word in _SENSE_BY_NUMBER:
        return _SENSE_BY_NUMBER[word]
    for mode in SenseMode:
        if word == mode.value:
            return mode
    raise RuntimeError(f'MODE?: unrecognised answer {text!r}')


def _boolean(name: str, value: object) -> bool:
    """Accept only a real bool or the ints 0 and 1; anything else is a caller mistake.

    ``bool(on)`` would turn the string ``'off'`` into True and switch an output ON.
    """
    if isinstance(value, bool):
        return value
    if type(value) is int and value in (0, 1):
        return bool(value)
    raise ValueError(f'{name} must be a bool or the int 0 or 1, got {value!r}')


# Every command is sent in the exact form the manual prints in its example (leading colon,
# SOURce prefix and :SET node included); queries are derived from the printed example of the
# paired set command. This class is the only place that builds command strings.
# verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q7, Q20):
# the verbatim forms and the short forms (optional SOURce, :SET, :STATe, long or short
# keywords) both work, and the channel argument is always honoured; the verbatim forms are kept
# to avoid churn.
class _Scpi:
    IDN = '*IDN?'
    OPC = '*OPC?'
    TRACK_QUERY = 'OUTPut:TRACK?'
    LOCK_QUERY = ':SOURce:LOCK:STATe?'

    @staticmethod
    def voltage(n: int, value: str) -> str:
        return f':SOURce:VOLTage:SET CH{n},{value}'

    @staticmethod
    def voltage_query(n: int) -> str:
        return f':SOURce:VOLTage:SET? CH{n}'

    @staticmethod
    def voltage_max_query(n: int) -> str:
        # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q9,
        # Q14): MAX is the instrument's limit, 1.01 x the rating, per channel.
        return f':SOURce:VOLTage:SET? CH{n},MAXimum'

    @staticmethod
    def current(n: int, value: str) -> str:
        return f':SOURce:CURRent:SET CH{n},{value}'

    @staticmethod
    def current_query(n: int) -> str:
        return f':SOURce:CURRent:SET? CH{n}'

    @staticmethod
    def current_max_query(n: int) -> str:
        return f':SOURce:CURRent:SET? CH{n},MAXimum'

    @staticmethod
    def ovp(n: int, value: str) -> str:
        return f':SOURce:OVP CH{n},{value}'

    @staticmethod
    def ovp_query(n: int) -> str:
        return f':SOURce:OVP? CH{n}'

    @staticmethod
    def ocp(n: int, value: str) -> str:
        return f':SOURce:OCP CH{n},{value}'

    @staticmethod
    def ocp_query(n: int) -> str:
        return f':SOURce:OCP? CH{n}'

    @staticmethod
    def ocp_state(n: int, on: bool) -> str:
        # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q7):
        # the manual example is ':SOURce:OCP:STATe CH1, 1' (a space after the comma); with and
        # without the space both work, every other example has none, so none is sent.
        return f':SOURce:OCP:STATe CH{n},{int(on)}'

    @staticmethod
    def ocp_state_query(n: int) -> str:
        return f':SOURce:OCP:STATe? CH{n}'

    @staticmethod
    def ocp_delay(n: int, value: str) -> str:
        return f'OCP:DELay CH{n},{value}'

    @staticmethod
    def ocp_delay_query(n: int) -> str:
        return f'OCP:DELay? CH{n}'

    @staticmethod
    def ovp_tripped_query(n: int) -> str:
        return f':SOURce:OVP:PROTect:STATe? CH{n}'

    @staticmethod
    def ocp_tripped_query(n: int) -> str:
        return f':SOURce:OCP:PROTect:STATe? CH{n}'

    @staticmethod
    def reset_protection(n: int) -> str:
        return f':SOURce:RESET:PROTect CH{n}'

    @staticmethod
    def lock(on: bool) -> str:
        return f':SOURce:LOCK:STATe {"ON" if on else "OFF"}'

    @staticmethod
    def output(n: int, on: bool) -> str:
        return f'OUTPut CH{n},{int(on)}'

    @staticmethod
    def output_query(n: int) -> str:
        return f'OUTPut? CH{n}'

    @staticmethod
    def output_all(on: bool) -> str:
        return f'OUTPut:ALL {int(on)}'

    @staticmethod
    def on_delay(n: int, value: str) -> str:
        return f'OUTPut:ON:DELay CH{n},{value}'

    @staticmethod
    def on_delay_query(n: int) -> str:
        return f'OUTPut:ON:DELay? CH{n}'

    @staticmethod
    def off_delay(n: int, value: str) -> str:
        return f'OUTPut:OFF:DELay CH{n},{value}'

    @staticmethod
    def off_delay_query(n: int) -> str:
        return f'OUTPut:OFF:DELay? CH{n}'

    @staticmethod
    def track(word: str) -> str:
        return f'OUTPut:TRACK {word}'

    @staticmethod
    def sense(n: int, word: str) -> str:
        return f'MODE CH{n},{word}'

    @staticmethod
    def sense_query(n: int) -> str:
        return f'MODE? CH{n}'

    @staticmethod
    def measure_voltage_query(n: int) -> str:
        return f'MEASure:VOLTage? CH{n}'

    @staticmethod
    def measure_current_query(n: int) -> str:
        return f'MEASure:CURRent? CH{n}'

    @staticmethod
    def measure_power_query(n: int) -> str:
        return f'MEASure:POWER? CH{n}'

    @staticmethod
    def run_mode_query(n: int) -> str:
        return f'MEASure:RUN:MODE? CH{n}'


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
        self._transport_error: Exception | None = None  # last exception raised by the resource
        self._track: TrackMode | None = None
        self._snapshot: dict[str, Any] | None = None
        self.model: Model | None = None
        self.resource: ScpiResource
        if resource is None:
            self.resource = self._open_resource()
        else:
            self.resource = resource
        try:
            # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md
            # Q1), raw socket only: commands may end in LF (CRLF also works) and every reply
            # ends in a single LF. USB not verified.
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
        try:
            self.resource.write(cmd)
        except Exception as exc:
            self._transport_error = exc
            raise

    def query(self, cmd: str) -> str:
        self.logger.debug('SCPI query: %s', cmd)
        try:
            answer = self.resource.query(cmd).strip()
        except Exception as exc:
            self._transport_error = exc
            raise
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
        answer = self.query(_Scpi.IDN)
        fields = [f.strip() for f in answer.split(',', 3)]
        if len(fields) < 4:
            raise RuntimeError(f'*IDN? answered {answer!r}, expected 4 comma-separated fields')
        return Identity(*fields)

    def opc(self) -> str:
        return self.query(_Scpi.OPC)

    def snapshot(self) -> dict[str, Any]:
        """Read setpoints, protection values, delays and output states of every channel."""
        channels: dict[int, dict[str, Any]] = {}
        for n in _ALL_CHANNELS:
            channels[n] = {
                'voltage': self.voltage_setpoint(n),
                'current': self.current_setpoint(n),
                'ovp': self.ovp(n),
                'ocp': self.ocp(n),
                'ocp_enabled': self.ocp_enabled(n),
                'ocp_delay': self.ocp_delay(n),
                'on_delay': self._on_delay(n),
                'off_delay': self._off_delay(n),
                'output': self.output(n),
            }
        return {'channels': channels, 'track': self.track()}

    @staticmethod
    def _unchanged(wanted: bool | float, actual: bool | float) -> bool:
        """True if the value read from the instrument already equals the wanted one."""
        if isinstance(wanted, bool):
            return wanted == actual
        return math.isclose(float(wanted), float(actual), rel_tol=1e-6, abs_tol=5e-4)

    def restore(self, snapshot: dict[str, Any]) -> None:
        """Write a snapshot back. Never turns an output on; raises one error for all problems.

        The track mode is written first and only if it differs. Every other value is read first
        and written only if it differs (a write costs about 250 ms on the instrument). A channel
        whose output is on is skipped (changing setpoints under a running DUT is not a restore),
        and so are CH2 and CH3 if the track restore failed. While the track mode is SERIES or
        PARALLEL only the CH2 voltage (SERIES) or CH2 current (PARALLEL) is restored; the other
        voltage and current setpoints of CH2 and CH3 are skipped (open question 21: their write
        side is untested). Every skipped channel or item is named in the error.
        """
        failures: list[str] = []
        skipped: list[str] = []

        def attempt(label: str, action: Callable[[], Any]) -> bool:
            try:
                action()
            except Exception as exc:
                failures.append(f'{label}: {exc}')
                return False
            return True

        wanted: TrackMode = snapshot['track']
        track_ok = True
        mode: TrackMode = wanted
        try:
            current = self.track()
        except Exception as exc:
            failures.append(f'track: {exc}')
            track_ok = False
        else:
            mode = current
            if current != wanted:
                track_ok = attempt('track', lambda: self.set_track(wanted))
                mode = wanted
        for n, values in snapshot['channels'].items():
            # The 'output' entry is deliberately ignored: restore never enables an output.
            if n in (2, 3) and not track_ok:
                skipped.append(f'CH{n} (track mode not restored)')
                continue
            try:
                is_on = self.output(n)
            except Exception as exc:
                failures.append(f'CH{n} output state: {exc}')
                skipped.append(f'CH{n} (output state unknown)')
                continue
            if is_on:
                skipped.append(f'CH{n} (output is on)')
                continue
            items: list[tuple[str, Callable[[int], Any], Callable[[int, Any], None], Any]] = [
                ('OVP', self.ovp, self.set_ovp, values['ovp']),
                ('OCP', self.ocp, self.set_ocp, values['ocp']),
                ('OCP delay', self.ocp_delay, self.set_ocp_delay, values['ocp_delay']),
                ('OCP state', self.ocp_enabled, self.set_ocp_enabled, values['ocp_enabled']),
                (
                    'ON delay',
                    self._on_delay,
                    lambda ch, v: self.set_output_delay(ch, on_s=v),
                    values['on_delay'],
                ),
                (
                    'OFF delay',
                    self._off_delay,
                    lambda ch, v: self.set_output_delay(ch, off_s=v),
                    values['off_delay'],
                ),
            ]
            coupled_on = False
            if n == 2 and mode is not TrackMode.INDEPENDENT:
                # CH3 follows CH2's combined setpoint: do not touch it under a live CH3 either
                try:
                    coupled_on = self.output(3)
                except Exception as exc:
                    failures.append(f'CH3 output state: {exc}')
                    coupled_on = True
            for label, key, get_item, set_item in (
                ('voltage', 'voltage', self.voltage_setpoint, self.set_voltage),
                ('current', 'current', self.current_setpoint, self.set_current),
            ):
                reason = self._coupled_write_refusal(n, label, mode, self.model)
                if reason is None and coupled_on:
                    skipped.append(f'CH{n} {label} (CH3 follows CH2 and its output is on)')
                elif reason is None:
                    items.append((label, get_item, set_item, values[key]))
                else:
                    try:  # nothing to restore (and nothing to report) if it is already right
                        if self._unchanged(values[key], get_item(n)):
                            continue
                    except Exception:
                        pass
                    skipped.append(
                        f'CH{n} {label} ({mode.value} mode: write side of open question 21 '
                        'untested)'
                    )
            for label, getter, setter, value in items:
                attempt(f'CH{n} {label}', partial(self._restore_item, n, getter, setter, value))
        if failures or skipped:
            parts = list(failures)
            if skipped:
                parts.append('skipped: ' + ', '.join(skipped))
            raise RuntimeError('restore failed: ' + '; '.join(parts))

    def _restore_item(
        self,
        n: int,
        getter: Callable[[int], Any],
        setter: Callable[[int, Any], None],
        value: Any,
    ) -> None:
        if not self._unchanged(value, getter(n)):
            setter(n, value)

    # ---- limits -------------------------------------------------------------------------

    def _rating(
        self, ch: int, quantity: str = '', mode: TrackMode | None = None
    ) -> ChannelRating | None:
        """Rated limit of a channel, None if the model is unknown.

        The guard stays at the rated value. The instrument itself accepts up to 1.01 x the
        rating (``VOLTage? CHn,MAX``, docs/hardware_findings.md Q9, Q14) and clamps silently
        beyond; that 1 % is headroom, not a specification. The one exception is the combined
        setpoint of CH2 in a coupled mode (the voltage in SERIES, the current in PARALLEL):
        it is the combined value (docs/hardware_findings.md run 2, Q21: 5 A written to CH2 in
        PARALLEL read back 5 A), so its limit is the series or parallel rating of the model.
        Every other write in a coupled mode is refused (see ``_coupled_write_refusal``).
        """
        if self.model is None:
            return None
        if ch == 2 and quantity in ('voltage', 'current'):
            if mode is TrackMode.SERIES and quantity == 'voltage':
                return self.model.series
            if mode is TrackMode.PARALLEL and quantity == 'current':
                return self.model.parallel
        return self.model.channels[ch - 1]

    def _guard_voltage(self, ch: int, volts: float, mode: TrackMode | None = None) -> None:
        rating = self._rating(ch, 'voltage', mode)
        if rating is not None and volts > rating.voltage + _RATING_EPS:
            raise ValueError(f'{volts:g} V exceeds the {rating.voltage:g} V rating of CH{ch}')

    def _guard_current(self, ch: int, amps: float, mode: TrackMode | None = None) -> None:
        rating = self._rating(ch, 'current', mode)
        if rating is not None and amps > rating.current + _RATING_EPS:
            raise ValueError(f'{amps:g} A exceeds the {rating.current:g} A rating of CH{ch}')

    @staticmethod
    def _coupled_write_refusal(
        ch: int, quantity: str, mode: TrackMode, model: Model | None
    ) -> str | None:
        """Why a ``quantity`` ('voltage' or 'current') write on CH``ch`` is refused, or None.

        verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md run 2
        and its addendum, Q21): in SERIES the voltage written to CH2 is the combined voltage
        (CH2 reads it back, CH3 follows with half), in PARALLEL the current written to CH2 is
        the combined current; the current of CH2 in SERIES and the voltage of CH2 in PARALLEL
        are per channel and read back on CH2 as written. A voltage or current written to CH3
        in a coupled mode is ignored by the instrument (CH3 follows CH2), so it is refused
        before anything is sent. The CH2 writes are allowed only on a model with ``tested`` set
        (an unknown or untested model may behave differently).
        """
        if ch not in (2, 3) or mode is TrackMode.INDEPENDENT:
            return None
        if ch == 2 and model is not None and model.tested:
            return None
        if ch == 3:
            return (
                f'refusing to write the {quantity} setpoint of CH3 while the track mode is '
                f'{mode.value}: CH3 follows CH2 and the instrument ignores the write '
                '(write to CH2 instead; open question 21)'
            )
        return (
            f'refusing to write the {quantity} setpoint of CH2 while the track mode is '
            f'{mode.value}: its meaning is verified on the SPD4323X only (open question 21)'
        )

    def _fresh_track(self, ch: int) -> TrackMode | None:
        """The track mode read from the instrument now, for CH2/CH3 writes only (else None).

        The cached mode can be stale (the mode can be changed from the panel or by another
        client after it was read), and a wrong mode would widen the guard or let a write
        through that must be refused. One ``OUTPut:TRACK?`` costs about 4 ms.
        """
        return self.track() if ch in (2, 3) else None

    def _require_coupled_write_allowed(
        self, ch: int, quantity: str, mode: TrackMode | None
    ) -> None:
        """Raise RuntimeError before anything is sent if the coupled-mode write is unverified."""
        if mode is None:
            return
        reason = self._coupled_write_refusal(ch, quantity, mode, self.model)
        if reason is not None:
            raise RuntimeError(reason)

    # ---- output -------------------------------------------------------------------------

    def set_voltage(self, ch: int | Channel, volts: float) -> None:
        n = _channel(ch)
        value = _nonnegative('volts', volts)
        mode = self._fresh_track(n)
        self._guard_voltage(n, value, mode)
        self._require_coupled_write_allowed(n, 'voltage', mode)
        self.write_verified(_Scpi.voltage(n, self._fmt(value)), _Scpi.voltage_query(n), value)

    def voltage_setpoint(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(_Scpi.voltage_query(n)), _Scpi.voltage_query(n))

    def max_voltage(self, ch: int | Channel) -> float:
        """The instrument's own voltage limit for the channel (1.01 x the rating on the SPD4323X).

        Informational: the guard of ``set_voltage`` stays at the rated value.
        """
        n = _channel(ch)
        return _to_float(self.query(_Scpi.voltage_max_query(n)), _Scpi.voltage_max_query(n))

    def set_current(self, ch: int | Channel, amps: float) -> None:
        n = _channel(ch)
        value = _nonnegative('amps', amps)
        mode = self._fresh_track(n)
        self._guard_current(n, value, mode)
        self._require_coupled_write_allowed(n, 'current', mode)
        self.write_verified(_Scpi.current(n, self._fmt(value)), _Scpi.current_query(n), value)

    def current_setpoint(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(_Scpi.current_query(n)), _Scpi.current_query(n))

    def max_current(self, ch: int | Channel) -> float:
        """The instrument's own current limit for the channel (1.01 x the rating on the SPD4323X).

        Informational: the guard of ``set_current`` stays at the rated value.
        """
        n = _channel(ch)
        return _to_float(self.query(_Scpi.current_max_query(n)), _Scpi.current_max_query(n))

    def set_output(self, ch: int | Channel, on: bool) -> None:
        n = _channel(ch)
        state = _boolean('on', on)
        self.write_verified(_Scpi.output(n, state), _Scpi.output_query(n), state)

    def output(self, ch: int | Channel) -> bool:
        n = _channel(ch)
        return _to_bool(self.query(_Scpi.output_query(n)), _Scpi.output_query(n))

    def set_all_outputs(self, on: bool) -> None:
        state = _boolean('on', on)
        self.write(_Scpi.output_all(state))
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
            raise RuntimeError(f'{_Scpi.output_all(state)} not confirmed: ' + '; '.join(failures))

    def all_outputs_off(self) -> None:
        self.set_all_outputs(False)

    def _on_delay(self, n: int) -> float:
        return _to_float(self.query(_Scpi.on_delay_query(n)), _Scpi.on_delay_query(n))

    def _off_delay(self, n: int) -> float:
        return _to_float(self.query(_Scpi.off_delay_query(n)), _Scpi.off_delay_query(n))

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
                _Scpi.on_delay(n, self._fmt(on_value)), _Scpi.on_delay_query(n), on_value
            )
        if off_value is not None:
            self.write_verified(
                _Scpi.off_delay(n, self._fmt(off_value)), _Scpi.off_delay_query(n), off_value
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

        Every item is attempted; one RuntimeError lists all failures. A non-boolean
        ``ocp_enabled`` raises ValueError before anything is sent. On CH2 or CH3 while the track
        mode is SERIES or PARALLEL a ``voltage`` or ``current`` item that is not one of the
        two verified coupled writes (CH2 voltage in SERIES, CH2 current in PARALLEL) raises
        RuntimeError (open question 21) before anything is sent.
        """
        n = _channel(ch)
        enabled = None if ocp_enabled is None else _boolean('ocp_enabled', ocp_enabled)
        if voltage is not None or current is not None:
            mode = self._fresh_track(n)
            if voltage is not None:
                self._require_coupled_write_allowed(n, 'voltage', mode)
            if current is not None:
                self._require_coupled_write_allowed(n, 'current', mode)
        steps: list[tuple[str, Any, Callable[[Any], None]]] = [
            ('ovp', ovp, lambda x: self.set_ovp(n, x)),
            ('ocp', ocp, lambda x: self.set_ocp(n, x)),
            ('ocp_delay', ocp_delay, lambda x: self.set_ocp_delay(n, x)),
            ('ocp_enabled', enabled, lambda x: self.set_ocp_enabled(n, x)),
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
        self.write_verified(_Scpi.ovp(n, self._fmt(value)), _Scpi.ovp_query(n), value)

    def ovp(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(_Scpi.ovp_query(n)), _Scpi.ovp_query(n))

    def set_ocp(self, ch: int | Channel, amps: float) -> None:
        n = _channel(ch)
        value = _nonnegative('amps', amps)
        self.write_verified(_Scpi.ocp(n, self._fmt(value)), _Scpi.ocp_query(n), value)

    def ocp(self, ch: int | Channel) -> float:
        n = _channel(ch)
        # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q5):
        # OCP? answers a plain number like OVP? (the manual prints no response).
        return _to_float(self.query(_Scpi.ocp_query(n)), _Scpi.ocp_query(n))

    def set_ocp_enabled(self, ch: int | Channel, on: bool) -> None:
        n = _channel(ch)
        state = _boolean('on', on)
        self.write_verified(_Scpi.ocp_state(n, state), _Scpi.ocp_state_query(n), state)

    def ocp_enabled(self, ch: int | Channel) -> bool:
        n = _channel(ch)
        return _to_bool(self.query(_Scpi.ocp_state_query(n)), _Scpi.ocp_state_query(n))

    def set_ocp_delay(self, ch: int | Channel, seconds: float) -> None:
        n = _channel(ch)
        value = _delay('seconds', seconds)
        self.write_verified(_Scpi.ocp_delay(n, self._fmt(value)), _Scpi.ocp_delay_query(n), value)

    def ocp_delay(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(_Scpi.ocp_delay_query(n)), _Scpi.ocp_delay_query(n))

    def protection_status(self, ch: int | Channel) -> ProtectionStatus:
        n = _channel(ch)
        # ASSUMPTION(hw): 1 means tripped, 0 means not tripped. The manual only prints 0.
        ovp = _to_bool(self.query(_Scpi.ovp_tripped_query(n)), _Scpi.ovp_tripped_query(n))
        ocp = _to_bool(self.query(_Scpi.ocp_tripped_query(n)), _Scpi.ocp_tripped_query(n))
        return ProtectionStatus(ovp_tripped=ovp, ocp_tripped=ocp)

    def clear_protection(self, ch: int | Channel) -> None:
        n = _channel(ch)
        self.write(_Scpi.reset_protection(n))
        status = self.protection_status(n)
        if status.ovp_tripped or status.ocp_tripped:
            raise RuntimeError(
                f'CH{n} is still in protection after {_Scpi.reset_protection(n)}: {status}'
            )

    # ---- measurement --------------------------------------------------------------------

    def measure_voltage(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(_Scpi.measure_voltage_query(n)), _Scpi.measure_voltage_query(n))

    def measure_current(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(_Scpi.measure_current_query(n)), _Scpi.measure_current_query(n))

    def measure_power(self, ch: int | Channel) -> float:
        n = _channel(ch)
        return _to_float(self.query(_Scpi.measure_power_query(n)), _Scpi.measure_power_query(n))

    def run_mode(self, ch: int | Channel) -> str:
        n = _channel(ch)
        return self.query(_Scpi.run_mode_query(n))

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

    def _ch3_setpoints(self) -> tuple[float, float] | None:
        try:
            return self.voltage_setpoint(3), self.current_setpoint(3)
        except Exception as exc:
            self.logger.warning('set_track: cannot read the CH3 setpoints: %s', exc)
            return None

    @staticmethod
    def _series_offset_only(
        before: tuple[float, float],
        after: tuple[float, float],
        modes: tuple[TrackMode | None, TrackMode],
    ) -> bool:
        """True if CH3 only shows its SERIES display offset: the current reads 0.1 A above CH2's.

        verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md run 2
        addendum, Q21): in SERIES ``CURRent? CH3`` answers CH2's current plus 0.1 A (3 A ->
        3.1 A, 2 A -> 2.1 A); the stored value is unchanged, so the step into or out of SERIES
        is no change of the CH3 setpoint. An unknown previous mode counts as possibly SERIES.
        """
        if TrackMode.SERIES not in modes and None not in modes:
            return False
        return before[0] == after[0] and math.isclose(abs(before[1] - after[1]), 0.1, abs_tol=1e-3)

    def set_track(self, mode: TrackMode) -> None:
        """Select independent, series or parallel mode of CH2/CH3.

        Refused while the output of CH2 or CH3 is on. Entering SERIES or PARALLEL copies CH2's
        voltage and current setpoints into CH3, and CH3 keeps them after returning to
        INDEPENDENT (docs/hardware_findings.md Q13): a CH3 DUT switched on afterwards gets
        CH2's voltage. CH3's setpoints are read before and after and a warning names both
        values when they changed.
        """
        wanted = TrackMode(mode)
        for n in (2, 3):
            if self.output(n):
                raise RuntimeError(f'refusing to change the track mode while CH{n} output is on')
        before = self._ch3_setpoints()
        previous = self._track
        self._track = None  # the cached value is untrusted until the read-back succeeds
        self.write_verified(
            _Scpi.track(wanted.value), _Scpi.TRACK_QUERY, wanted, parse=_parse_track
        )
        self._track = wanted
        after = self._ch3_setpoints()
        if (
            before is not None
            and after is not None
            and self._series_offset_only(before, after, (previous, wanted))
        ):
            after = before
        if before is not None and after is not None and before != after:
            self.logger.warning(
                'set_track(%s): the CH3 setpoints changed from %g V / %g A to %g V / %g A '
                '(the instrument copies the CH2 setpoints into CH3 when entering series or '
                'parallel mode and CH3 keeps them afterwards)',
                wanted.value,
                before[0],
                before[1],
                after[0],
                after[1],
            )

    def track(self) -> TrackMode:
        mode = _parse_track(self.query(_Scpi.TRACK_QUERY))
        self._track = mode
        return mode

    def set_sense(self, ch: int | Channel, mode: SenseMode) -> None:
        n = _channel(ch)
        if n not in (2, 3):
            raise ValueError(f'remote sense exists only on CH2 and CH3, not CH{n}')
        wanted = SenseMode(mode)
        self.write_verified(
            _Scpi.sense(n, wanted.value), _Scpi.sense_query(n), wanted, parse=_parse_sense
        )

    def sense(self, ch: int | Channel) -> SenseMode:
        n = _channel(ch)
        if n not in (2, 3):
            raise ValueError(f'remote sense exists only on CH2 and CH3, not CH{n}')
        return _parse_sense(self.query(_Scpi.sense_query(n)))

    # ---- lock and teardown --------------------------------------------------------------

    def set_lock(self, on: bool) -> None:
        state = _boolean('on', on)
        self.write_verified(_Scpi.lock(state), _Scpi.LOCK_QUERY, state)

    def locked(self) -> bool:
        return _to_bool(self.query(_Scpi.LOCK_QUERY), _Scpi.LOCK_QUERY)

    def _zero_pending_off_delays(self) -> None:
        """Set a non-zero OFF delay of every channel that is on to 0 (a delayed switch-off
        would leave the DUT powered after the test ended)."""
        for n in _ALL_CHANNELS:
            try:
                if not self.output(n):
                    continue
                delay = self._off_delay(n)
                if delay == 0:
                    continue
                self.logger.warning(
                    'teardown: CH%d has an OFF delay of %g s; setting it to 0 so that the '
                    'output switches off at once',
                    n,
                    delay,
                )
                self.set_output_delay(n, off_s=0)
            except Exception as exc:
                self.logger.warning('teardown: CH%d OFF delay check failed: %s', n, exc)
                if self._transport_error is not None:
                    return  # the link is down; do not wait for a timeout per channel

    def _outputs_off_safely(self) -> None:
        self._zero_pending_off_delays()
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
        """Outputs off, optional restore, unlock, close. A failing step never stops the next.

        The unlock must be the **last write** of the session: the instrument sets LOCK to 1 on
        every remote write (queries do not), so any write after ``set_lock(False)`` would lock
        the front panel again. Nothing may be added after the unlock step except the close.

        A non-zero OFF delay is zeroed first (``_zero_pending_off_delays``): verified on
        SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md run 2, Q22) that
        ``OUTPut:ALL 0`` honours the delay (``OUTPut?`` answers 1 and the output stays live
        until it elapsed), and that writing the delay 0 while the switch-off is pending
        switches the output off at once.
        """
        skip_restore: str | None = None
        if self._outputs_off_on_teardown:
            self._transport_error = None
            self._teardown_step('outputs off', self._outputs_off_safely)
            if self._transport_error is not None:
                skip_restore = (
                    'a transport error occurred while turning the outputs off '
                    f'({type(self._transport_error).__name__}: {self._transport_error})'
                )
        snapshot = self._snapshot
        if self._restore_state and snapshot is not None:
            if skip_restore is not None:
                self.logger.warning('teardown: restore state skipped because %s', skip_restore)
            else:
                self._teardown_step('restore state', lambda: self.restore(snapshot))
        # Any remote write sets LOCK to 1, so this must stay the last write of the session
        # (verified at the SCPI level on SPD4323X, firmware 4.1.2.9R1, 2026-10-05,
        # docs/hardware_findings.md Q12: LOCK 0 clears it and does not re-lock).
        # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md run 2,
        # Q12): after this step LOCK? answers 0 and the owner saw the front panel unlocked.
        self._teardown_step('unlock front panel', lambda: self.set_lock(False))
        self._close()

    def _teardown_step(self, label: str, step: Callable[[], None]) -> None:
        try:
            step()
        except Exception as exc:
            self.logger.warning('teardown step %r failed: %s', label, exc)
