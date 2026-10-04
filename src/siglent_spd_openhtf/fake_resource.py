"""Hardware-free stand-in for a PyVISA resource connected to an SPD4000X.

It knows only what ``docs/scpi_reference.md`` and the first hardware acceptance run
(``docs/hardware_findings.md``, SPD4323X, firmware 4.1.2.9R1, 2026-10-05, raw socket) tell us,
plus the assumptions marked ``# ASSUMPTION(hw)``. It does not import pyvisa.

Limitation: the real supply serves one socket client at a time (a second connection is accepted
but not answered while the first is open). A fake object has no connections, so this is not
modelled; it matters for tools and stations that share the supply.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass

from .models import MODELS, PROTECTION_RANGE, SETPOINT_MAX_FACTOR

CHANNELS = (1, 2, 3, 4)
_MAX_DELAY_S = 3600.0


class FakeTimeout(Exception):
    """Raised by a query the fake instrument never answers."""


def to_float32(value: float) -> float:
    """Round a number to the nearest 32-bit float (the instrument stores every scalar so)."""
    return float(struct.unpack('<f', struct.pack('<f', value))[0])


def _fmt6(value: float) -> str:
    # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q4): values
    # are float32, answered with 6 decimals: 1.1 x 32 V reads back as 35.200001.
    return f'{to_float32(value):.6f}'


@dataclass
class FakeChannel:
    """State of one fake channel (setpoints are float32 values; in a coupled mode CH2 holds
    its per-half value and the query answers the combined one)."""

    voltage: float = 0.0
    current: float = 0.0
    ovp: float = 0.0
    ocp: float = 0.0
    ocp_enabled: bool = False
    ocp_delay: float = 0.0
    output: bool = False
    on_delay: float = 0.0
    off_delay: float = 0.0
    ovp_tripped: bool = False
    ocp_tripped: bool = False
    # Seconds left of a delayed switch-off, None when none is pending. While it is pending the
    # channel still reports output 1 and still delivers power.
    off_remaining: float | None = None


# Long and short keyword forms -> canonical short form. The manual prints POWER, RESET,
# TRACK, ALL, ON, OFF, MODE, RUN, LOCK, OVP and OCP with no separate short form (hardware
# confirmed for POWER and TRACK: MEAS:POW? and OUTP:TRAC? get no answer).
_KEYWORDS = {
    'VOLTAGE': 'VOLT',
    'VOLT': 'VOLT',
    'CURRENT': 'CURR',
    'CURR': 'CURR',
    'OUTPUT': 'OUTP',
    'OUTP': 'OUTP',
    'MEASURE': 'MEAS',
    'MEAS': 'MEAS',
    'PROTECT': 'PROT',
    'PROT': 'PROT',
    'STATE': 'STAT',
    'STAT': 'STAT',
    'DELAY': 'DEL',
    'DEL': 'DEL',
}

_TRACK_WORDS = {'INDEPENDENT': 0, 'SERIES': 1, 'PARALLEL': 2}
_SENSE_WORDS = {'2W': 0, '4W': 1}
_BOOL_WORDS = {'1': True, 'ON': True, '0': False, 'OFF': False}
_MIN_WORDS = ('MIN', 'MINIMUM')
_MAX_WORDS = ('MAX', 'MAXIMUM')
_DEF_WORDS = ('DEF', 'DEFAULT')
_KEYWORD_ARGS = _MIN_WORDS + _MAX_WORDS + _DEF_WORDS
_ESR_OPC = 1
_ESR_COMMAND_ERROR = 32


class FakeSpdResource:
    """Fake VISA resource modelling an SPD4000X power supply.

    ``loads`` maps a channel number to a load resistance in ohms (``None`` = open circuit).
    ``reject`` maps a command prefix to a reason; a write starting with the prefix is ignored
    (state unchanged) so that read-back verification can be tested.

    Behaviour as observed on the SPD4323X (docs/hardware_findings.md): out-of-range values are
    clamped silently and nothing is ever reported, so a plug without read-back verification
    would pass; every accepted write locks the front panel (``lock = 1``); an invalid query is
    never answered (``FakeTimeout``).
    """

    def __init__(
        self,
        model: str = 'SPD4323X',
        serial: str = 'SPD4XXXXXXXXXX',
        firmware: str = '1.0.0.0',
        loads: dict[int, float | None] | None = None,
        reject: dict[str, str] | None = None,
    ) -> None:
        if model not in MODELS:
            raise ValueError(f'unknown model {model!r}, expected one of {sorted(MODELS)}')
        self.model = model
        self.serial = serial
        self.firmware = firmware
        self._spec = MODELS[model]
        self.reject: dict[str, str] = dict(reject or {})
        self.rejected: list[str] = []
        self.log: list[str] = []
        self.closed = False
        # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q1),
        # raw socket only (USB not verified): LF in, one LF out. Answers carry no terminator
        # here (PyVISA strips it); the plug sets '\n' for both directions.
        self.timeout: float | None = 2000
        self.read_termination: str | None = None
        self.write_termination: str | None = None

        # Initial values as observed on the SPD4323X (docs/hardware_findings.md Q14): V and I 0,
        # OVP and OCP at 1.1 x the rated value, OCP off, delays 0, outputs off, track 0,
        # sense 0, lock 0.
        self.channels: dict[int, FakeChannel] = {}
        for n in CHANNELS:
            rating = self._spec.channels[n - 1]
            self.channels[n] = FakeChannel(
                ovp=to_float32(PROTECTION_RANGE[1] * rating.voltage),
                ocp=to_float32(PROTECTION_RANGE[1] * rating.current),
            )
        self.track = 0
        self.sense: dict[int, int] = {2: 0, 3: 0}
        self.lock = 0
        self.esr = 0  # standard event status register
        self.loads: dict[int, float | None] = {n: None for n in CHANNELS}
        for n, ohms in (loads or {}).items():
            self.set_load(n, ohms)

    # ---- test helpers -------------------------------------------------------------------

    def set_load(self, ch: int, ohms: float | None) -> None:
        """Connect a resistive load (ohms) to a channel; None = open circuit."""
        if int(ch) not in CHANNELS:
            raise ValueError(f'channel must be 1..4, got {ch!r}')
        self.loads[int(ch)] = ohms

    def trip_ovp(self, ch: int) -> None:
        """Put a channel into the OVP-tripped state (output off)."""
        state = self.channels[int(ch)]
        state.ovp_tripped = True
        state.output = False
        state.off_remaining = None

    def trip_ocp(self, ch: int) -> None:
        """Put a channel into the OCP-tripped state (output off)."""
        state = self.channels[int(ch)]
        state.ocp_tripped = True
        state.output = False
        state.off_remaining = None

    def advance(self, seconds: float) -> None:
        """Let time pass: channels with a pending delayed switch-off count down and turn off."""
        for state in self.channels.values():
            if state.off_remaining is None:
                continue
            state.off_remaining -= seconds
            if state.off_remaining <= 0:
                state.output = False
                state.off_remaining = None

    # ---- VISA resource interface --------------------------------------------------------

    def close(self) -> None:
        self.closed = True

    def write(self, message: str) -> None:
        self._check_open()
        self.log.append(message)
        for segment in self._segments(message):
            if '?' in segment:
                try:  # the reply of a query inside a written line is not read by anyone
                    self._run_query(segment)
                except FakeTimeout:
                    pass
            else:
                self._run_write(segment)

    def query(self, message: str) -> str:
        self._check_open()
        self.log.append(message)
        replies: list[str] = []
        queried = False
        for segment in self._segments(message):
            if '?' in segment:
                queried = True
                try:
                    replies.append(self._run_query(segment))
                except FakeTimeout:
                    continue
            else:
                self._run_write(segment)
        if not queried:
            raise FakeTimeout(f'{message!r} is not a query')
        if not replies:
            raise FakeTimeout(f'no answer to {message!r}')
        # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q1):
        # the replies of a chained line are concatenated with no separator.
        return ''.join(replies)

    # ---- parsing ------------------------------------------------------------------------

    @staticmethod
    def _segments(message: str) -> list[str]:
        return [part.strip() for part in message.split(';') if part.strip()]

    @staticmethod
    def _normalise(text: str) -> str:
        return text.strip().lstrip(':').upper()

    def _check_open(self) -> None:
        if self.closed:
            raise RuntimeError('resource is closed')

    def _parse(self, segment: str) -> tuple[tuple[str, ...], list[str], bool] | None:
        """Return (canonical keywords, arguments, is_query) or None for an unknown header."""
        text = segment.strip().lstrip(':')
        question = text.find('?')
        if question >= 0:  # the space before the argument is optional ('VOLTage?CH1' works)
            head, rest = text[: question + 1], text[question + 1 :]
        else:
            head, _, rest = text.partition(' ')
        args = [a.strip() for a in rest.split(',')] if rest.strip() else []
        head = head.upper()
        is_query = head.endswith('?')
        head = head.rstrip('?')
        if head.startswith('*'):
            return ((head,), args, is_query) if head in _STAR_COMMANDS else None
        words = head.split(':')
        if words and words[0] in ('SOURCE', 'SOUR'):
            words = words[1:]
        keys: list[str] = []
        for word in words:
            canonical = _KEYWORDS.get(word, word)
            if canonical not in _KNOWN_WORDS:
                return None  # for example VOL or VOLTAG: the manual says those are errors
            keys.append(canonical)
        # Optional nodes: [:SET], [:STATe] of OUTPut and LOCK, [:RUN] of MEASure.
        if keys and keys[0] in ('VOLT', 'CURR') and keys[1:] == ['SET']:
            keys = keys[:1]
        if keys in (['OUTP', 'STAT'], ['LOCK', 'STAT'], ['OUTP', 'ALL', 'STAT']):
            keys = keys[:-1]
        if keys[:2] == ['MEAS', 'RUN']:
            keys = ['MEAS', *keys[2:]]
        key_tuple = tuple(keys)
        if key_tuple not in _COMMANDS:
            return None
        return key_tuple, args, is_query

    @staticmethod
    def _channel(arg: str | None) -> int | None:
        if arg is None:
            return None
        text = arg.strip().upper()
        if len(text) == 3 and text.startswith('CH') and text[2] in '1234':
            return int(text[2])
        return None

    @staticmethod
    def _number(text: str) -> float | None:
        try:
            number = float(text)
        except ValueError:
            return None
        return number if math.isfinite(number) else None

    # ---- limits and measurement model ---------------------------------------------------

    def _limits(self, keys: tuple[str, ...], ch: int) -> tuple[float, float, float]:
        """(lowest, highest, DEFault) value a setting accepts.

        verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q9,
        Q14): voltage and current go from 0 to 1.01 x the rating (``MAX``), OVP and OCP from
        0.1 x to 1.1 x the rating, and DEFault is 0 for voltage and current but the 1.1 x
        maximum for OVP and OCP. ``MAX`` is per channel and ignores the track mode.
        OCP:DELay goes from 0 to 3600 s, DEFault 0.
        """
        rating = self._spec.channels[ch - 1]
        low, high = PROTECTION_RANGE
        if keys == ('VOLT',):
            return 0.0, SETPOINT_MAX_FACTOR * rating.voltage, 0.0
        if keys == ('CURR',):
            return 0.0, SETPOINT_MAX_FACTOR * rating.current, 0.0
        if keys == ('OVP',):
            return low * rating.voltage, high * rating.voltage, high * rating.voltage
        if keys == ('OCP',):
            return low * rating.current, high * rating.current, high * rating.current
        # ASSUMPTION(hw): same as OCP:DELay. The ON and OFF delay writes accepted 0, 0.5 and 2 s
        # on hardware (docs/hardware_findings.md run 2) but their clamping was not tried; they
        # are assumed to clamp to the same 0..3600 s as OCP:DELay.
        return 0.0, _MAX_DELAY_S, 0.0

    def _combined(self, ch: int) -> tuple[float, float]:
        """Voltage and current setpoint as CH<ch> reports them.

        In SERIES CH2 reports the combined voltage (2 x the stored per-half value), in
        PARALLEL the combined current; CH3 always answers its own stored value
        (docs/hardware_findings.md Q21, read side).
        """
        state = self.channels[ch]
        volts, amps = state.voltage, state.current
        if ch == 2 and self.track == 1:
            volts *= 2
        elif ch == 2 and self.track == 2:
            amps *= 2
        return volts, amps

    def _measure(self, ch: int) -> tuple[float, float, str]:
        state = self.channels[ch]
        if not state.output:
            return 0.0, 0.0, 'CV'
        volt_set, amp_set = self._combined(ch)
        load = self.loads[ch]
        if load is None:
            return volt_set, 0.0, 'CV'
        if load <= 0:
            return 0.0, amp_set, 'CC'
        current = volt_set / load
        if current > amp_set:
            return amp_set * load, amp_set, 'CC'
        return volt_set, current, 'CV'

    def _update_protection(self) -> None:
        for ch, state in self.channels.items():
            if not state.output:
                continue
            volts, amps, _ = self._measure(ch)
            if state.ocp_enabled and amps >= state.ocp:
                state.ocp_tripped = True  # the OCP delay is ignored
                state.output = False
                state.off_remaining = None
            elif volts > state.ovp:
                state.ovp_tripped = True
                state.output = False
                state.off_remaining = None

    # ---- command execution --------------------------------------------------------------

    def _run_write(self, segment: str) -> None:
        if any(self._normalise(segment).startswith(self._normalise(p)) for p in self.reject):
            self.rejected.append(segment)
            return
        parsed = self._parse(segment)
        if parsed is None:
            self.esr |= _ESR_COMMAND_ERROR  # unknown header
            return
        keys, args, is_query = parsed
        if is_query:
            return
        accepted = self._do_write(keys, args)
        if accepted and keys != ('LOCK',):
            # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md
            # Q12): every accepted remote write sets LOCK to 1, queries never do, LOCK 0 clears
            # it and does not re-lock. Invalid channels, non-numeric values and ignored
            # writes change nothing and do not lock.
            self.lock = 1
        self._update_protection()

    def _run_query(self, segment: str) -> str:
        self._update_protection()
        try:
            parsed = self._parse(segment)
            if parsed is None:
                raise FakeTimeout(f'no answer to {segment!r}: unknown header')
            keys, args, is_query = parsed
            if not is_query:
                raise FakeTimeout(f'{segment!r} is not a query')
            return self._do_query(segment, keys, args)
        except FakeTimeout:
            self.esr |= _ESR_COMMAND_ERROR  # unknown header or unanswered query
            raise

    def _do_write(self, keys: tuple[str, ...], args: list[str]) -> bool:
        """Apply a write; return False if the instrument ignores it."""
        if keys == ('*CLS',):
            self.esr = 0
            return True
        if keys == ('*OPC',):
            self.esr |= _ESR_OPC
            return True
        if keys == ('*WAI',):
            return True
        if keys == ('OUTP', 'TRACK'):
            if not args:
                return False
            word = args[0].strip().upper()
            value = _TRACK_WORDS.get(word, self._number(word))
            if value not in (0, 1, 2):
                return False
            self.track = int(value)
            if self.track in (1, 2):
                # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md
                # Q13): entering SERIES or PARALLEL copies CH2's voltage and current setpoints
                # to CH3, which keeps them after returning to INDEPENDENT. OVP and OCP are not
                # changed (Q10).
                self.channels[3].voltage = self.channels[2].voltage
                self.channels[3].current = self.channels[2].current
            return True
        if keys == ('LOCK',):
            flag = _BOOL_WORDS.get(args[0].upper()) if args else None
            if flag is None:
                return False
            self.lock = int(flag)
            return True
        if keys == ('OUTP', 'ALL'):
            flag = _BOOL_WORDS.get(args[0].upper()) if args else None
            if flag is None:
                return False
            for state in self.channels.values():
                self._set_output(state, flag)
            return True
        ch = self._channel(args[0] if args else None)
        if ch is None:
            return False
        state = self.channels[ch]
        value_arg = args[1] if len(args) > 1 else None
        if keys == ('RESET', 'PROT'):
            state.ovp_tripped = False
            state.ocp_tripped = False
            return True
        if keys == ('MODE',):
            # ASSUMPTION(hw): not tried. MODE on CH1 and CH4 is ignored; the manual limits it
            # to CH2 and CH3 and a write to CH1/CH4 was never sent.
            if ch not in self.sense or value_arg is None:
                return False
            sense = _SENSE_WORDS.get(value_arg.upper(), self._number(value_arg))
            if sense not in (0, 1):
                return False
            self.sense[ch] = int(sense)
            return True
        if keys in (('OUTP',), ('OCP', 'STAT')):
            flag = _BOOL_WORDS.get(value_arg.upper()) if value_arg is not None else None
            if flag is None:
                return False
            if keys == ('OUTP',):
                self._set_output(state, flag)
            else:
                state.ocp_enabled = flag
            return True
        field = _SCALAR_FIELDS.get(keys)
        if field is None or value_arg is None:
            return False
        low, high, default = self._limits(keys, ch)
        word = value_arg.strip().upper()
        number = self._number(value_arg)
        if number is None:
            if word in _MIN_WORDS:
                number = low
            elif word in _MAX_WORDS:
                number = high
            elif word in _DEF_WORDS:
                number = default
            else:
                return False  # not a number: nothing is set
        coupled = ch == 2 and (
            (keys == ('VOLT',) and self.track == 1) or (keys == ('CURR',) and self.track == 2)
        )
        keyword = self._number(value_arg) is None
        # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q9):
        # out-of-range values are clamped silently, never rejected or reported.
        if coupled and not keyword:
            # ASSUMPTION(hw): numeric upper clamp of a combined write. 5 A written to CH2 in
            # PARALLEL was accepted (above the 3.232 A per-channel MAX), so the combined value
            # may exceed MAX; twice MAX is assumed as the limit, which was not tried.
            number = min(max(number, low), 2 * high)
        else:
            number = min(max(number, low), high)
        if coupled:
            # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md
            # run 2, Q21): in SERIES a voltage written to CH2 (in PARALLEL a current) is the
            # combined value: CH2 reads it back unchanged, each half stores half of it and CH3
            # follows CH2. The MAXimum keyword is per channel (32.32 V resp. 3.232 A, taken as
            # the combined value). Both halves keep the value after returning to INDEPENDENT.
            # OVP and OCP stay per channel. Not tried: writes to CH3 in a coupled mode, the
            # current of CH2 in SERIES and the voltage of CH2 in PARALLEL (stored per channel
            # here).
            number /= 2
            setattr(self.channels[3], field, to_float32(number))
        setattr(state, field, to_float32(number))
        if keys == ('OUTP', 'OFF', 'DEL') and number == 0 and state.off_remaining is not None:
            # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md
            # run 2, Q22): setting the OFF delay to 0 while a switch-off is pending switches
            # the output off at once. A shorter non-zero delay was not tried; the pending
            # countdown is left as it is.
            state.output = False
            state.off_remaining = None
        return True

    @staticmethod
    def _set_output(state: FakeChannel, on: bool) -> None:
        # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md run 2,
        # Q22): switching an output off that has a non-zero OFF delay, with OUTPut CHn,0 and
        # with OUTPut:ALL 0 alike, leaves it on (OUTPut? keeps answering 1 and it keeps
        # delivering voltage) until the delay has elapsed; advance() lets the time pass.
        # Switching on again cancelling the pending switch-off was not tried on hardware.
        if on:
            state.output = True
            state.off_remaining = None
        elif state.output and state.off_delay > 0:
            state.off_remaining = state.off_delay
        else:
            state.output = False
            state.off_remaining = None

    def _do_query(self, message: str, keys: tuple[str, ...], args: list[str]) -> str:
        if keys == ('*IDN',):
            return f'Siglent Technologies,{self.model},{self.serial},{self.firmware}'
        if keys == ('*OPC',):
            return '1'
        if keys == ('*ESR',):
            value, self.esr = self.esr, 0  # reading clears the register
            return str(value)
        if keys in (('*STB',), ('*ESE',), ('*SRE',)):
            return '0'
        if keys in (('OUTP', 'TRACK'), ('LOCK',), ('OUTP', 'ALL')) and args:
            # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md
            # Q8): a query that takes no channel gets no answer when it is given one
            # ('OUTPut:TRACK? CH1').
            raise FakeTimeout(f'no answer to {message!r}: this query takes no argument')
        if keys == ('OUTP', 'TRACK'):
            # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md
            # Q13): the query answers the number, 0 independent, 1 series, 2 parallel.
            return str(self.track)
        if keys == ('LOCK',):
            return str(self.lock)
        if keys == ('OUTP', 'ALL'):
            # The all-channel response format with mixed channel states is not known; the plug
            # does not use it.
            return _flag(all(s.output for s in self.channels.values()))
        if args:
            ch = self._channel(args[0])
        else:
            # ASSUMPTION(hw): CH1 or the panel-selected channel. 'VOLTage?' without a channel
            # answered CH1's setpoint (docs/hardware_findings.md Q8); the plug never omits
            # the channel.
            ch = 1
        if ch is None:
            raise FakeTimeout(f'no answer to {message!r}: invalid channel')
        state = self.channels[ch]
        if len(args) > 1:
            return self._query_with_keyword(message, keys, ch, args[1])
        if keys == ('MODE',):
            if ch == 1:
                # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md
                # Q8): 'MODE? CH1' answers 0 although the manual limits MODE to CH2/CH3.
                return '0'
            if ch not in self.sense:
                # ASSUMPTION(hw): not tried. MODE? CH4 was never sent; no answer is assumed.
                raise FakeTimeout(f'no answer to {message!r}: only CH1..CH3 answer MODE?')
            # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md
            # Q13): the query answers 0 for 2W and 1 for 4W.
            return str(self.sense[ch])
        if keys[0] == 'MEAS':
            volts, amps, mode = self._measure(ch)
            if keys == ('MEAS', 'VOLT'):
                return _fmt6(volts)
            if keys == ('MEAS', 'CURR'):
                return _fmt6(amps)
            if keys == ('MEAS', 'POWER'):
                return _fmt6(to_float32(volts) * to_float32(amps))
            return mode
        combined_volts, combined_amps = self._combined(ch)
        scalars = {
            ('VOLT',): combined_volts,
            ('CURR',): combined_amps,
            ('OVP',): state.ovp,
            ('OCP',): state.ocp,
            ('OCP', 'DEL'): state.ocp_delay,
            ('OUTP', 'ON', 'DEL'): state.on_delay,
            ('OUTP', 'OFF', 'DEL'): state.off_delay,
        }
        # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q5):
        # OCP? answers a plain number like OVP?.
        if keys in scalars:
            return _fmt6(scalars[keys])
        # ASSUMPTION(hw): the protection state queries answer 1 when tripped, 0 otherwise
        # (only 0 has been observed).
        flags = {
            ('OUTP',): state.output,
            ('OCP', 'STAT'): state.ocp_enabled,
            ('OVP', 'PROT', 'STAT'): state.ovp_tripped,
            ('OCP', 'PROT', 'STAT'): state.ocp_tripped,
        }
        if keys in flags:
            return _flag(flags[keys])
        raise FakeTimeout(f'no answer to {message!r}')

    def _query_with_keyword(
        self, message: str, keys: tuple[str, ...], ch: int, argument: str
    ) -> str:
        """``VOLTage? CH1,MAX`` and friends.

        verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Q9):
        MIN, MAX and DEF (also in the long forms) work as query arguments only for ``VOLTage?``
        and ``CURRent?``; ``OVP?``, ``OCP?`` and the delay queries get no answer.
        """
        word = argument.strip().upper()
        if keys not in (('VOLT',), ('CURR',)) or word not in _KEYWORD_ARGS:
            raise FakeTimeout(f'no answer to {message!r}: unsupported query argument')
        low, high, default = self._limits(keys, ch)
        if word in _MIN_WORDS:
            return _fmt6(low)
        if word in _MAX_WORDS:
            return _fmt6(high)
        return _fmt6(default)


def _flag(value: bool) -> str:
    return '1' if value else '0'


_STAR_COMMANDS = {'*IDN', '*OPC', '*ESR', '*CLS', '*STB', '*ESE', '*SRE', '*WAI'}
_SCALAR_FIELDS = {
    ('VOLT',): 'voltage',
    ('CURR',): 'current',
    ('OVP',): 'ovp',
    ('OCP',): 'ocp',
    ('OCP', 'DEL'): 'ocp_delay',
    ('OUTP', 'ON', 'DEL'): 'on_delay',
    ('OUTP', 'OFF', 'DEL'): 'off_delay',
}
_COMMANDS = {
    ('VOLT',),
    ('CURR',),
    ('OVP',),
    ('OCP',),
    ('OVP', 'PROT', 'STAT'),
    ('OCP', 'PROT', 'STAT'),
    ('OCP', 'DEL'),
    ('OCP', 'STAT'),
    ('OUTP',),
    ('OUTP', 'ALL'),
    ('OUTP', 'ON', 'DEL'),
    ('OUTP', 'OFF', 'DEL'),
    ('OUTP', 'TRACK'),
    ('MODE',),
    ('LOCK',),
    ('RESET', 'PROT'),
    ('MEAS', 'VOLT'),
    ('MEAS', 'CURR'),
    ('MEAS', 'POWER'),
    ('MEAS', 'MODE'),
}
_KNOWN_WORDS = {word for command in _COMMANDS for word in command} | {'SET', 'RUN'}
