"""Hardware-free stand-in for a PyVISA resource connected to an SPD4000X.

It knows only what ``docs/scpi_reference.md`` tells us, plus the assumptions marked
``# ASSUMPTION(hw)``. It does not import pyvisa.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import MODELS

CHANNELS = (1, 2, 3, 4)


class FakeTimeout(Exception):
    """Raised by a query the fake instrument never answers."""


@dataclass
class FakeChannel:
    """State of one fake channel."""

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
# TRACK, ALL, ON, OFF, MODE, RUN, LOCK, OVP and OCP with no separate short form.
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


class FakeSpdResource:
    """Fake VISA resource modelling an SPD4000X power supply.

    ``loads`` maps a channel number to a load resistance in ohms (``None`` = open circuit).
    ``reject`` maps a command prefix to a reason; a write starting with the prefix is ignored
    (state unchanged) so that read-back verification can be tested.
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
        # ASSUMPTION(hw): terminator. Answers carry no terminator here (PyVISA strips it);
        # the plug sets '\n' for both directions.
        self.timeout: float | None = 2000
        self.read_termination: str | None = None
        self.write_termination: str | None = None

        # Defaults follow "Default Settings" (docs/scpi_reference.md section 4): V and I 0,
        # OVP and OCP at the rated maximum, OCP off, delays 0, outputs off.
        self.channels: dict[int, FakeChannel] = {}
        for n in CHANNELS:
            rating = self._spec.channels[n - 1]
            self.channels[n] = FakeChannel(ovp=rating.voltage, ocp=rating.current)
        self.track = 0
        self.sense: dict[int, int] = {2: 0, 3: 0}
        self.lock = 0
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
        if any(self._normalise(message).startswith(self._normalise(p)) for p in self.reject):
            self.rejected.append(message)
            return
        parsed = self._parse(message)
        if parsed is None:
            return
        keys, args, is_query = parsed
        if is_query:
            return
        self._do_write(keys, args)
        self._update_protection()

    def query(self, message: str) -> str:
        self._check_open()
        self.log.append(message)
        self._update_protection()
        parsed = self._parse(message)
        if parsed is None:
            raise FakeTimeout(f'no answer to {message!r}')
        keys, args, is_query = parsed
        if not is_query:
            raise FakeTimeout(f'{message!r} is not a query')
        return self._do_query(message, keys, args)

    # ---- parsing ------------------------------------------------------------------------

    @staticmethod
    def _normalise(text: str) -> str:
        return text.strip().lstrip(':').upper()

    def _check_open(self) -> None:
        if self.closed:
            raise RuntimeError('resource is closed')

    def _parse(self, message: str) -> tuple[tuple[str, ...], list[str], bool] | None:
        """Return (canonical keywords, arguments, is_query) or None for an unknown header."""
        text = message.strip().lstrip(':')
        head, _, rest = text.partition(' ')
        args = [a.strip() for a in rest.split(',')] if rest.strip() else []
        head = head.upper()
        is_query = head.endswith('?')
        head = head.rstrip('?')
        if head.startswith('*'):
            return ((head,), args, is_query) if head in ('*IDN', '*OPC') else None
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
            return float(text)
        except ValueError:
            return None

    # ---- limits and measurement model ---------------------------------------------------

    def _rating(self, ch: int) -> tuple[float, float]:
        # ASSUMPTION(hw): series/parallel setpoint is the combined value on CH2. The rating of
        # CH2 and CH3 follows the track mode (series voltage, parallel current).
        if ch in (2, 3):
            if self.track == 1:
                return self._spec.series
            if self.track == 2:
                return self._spec.parallel
        return self._spec.channels[ch - 1]

    @staticmethod
    def _clamp(value: float, upper: float, lower: float = 0.0) -> float:
        # ASSUMPTION(hw): clamping. A voltage/current above the rating is clamped to the
        # rating and a negative one to 0; OVP/OCP are clamped to the panel range 0.1x..1.1x
        # rating. No error is reported, so that a plug without read-back would silently pass.
        return min(max(value, lower), upper)

    def _measure(self, ch: int) -> tuple[float, float, str]:
        state = self.channels[ch]
        if not state.output:
            return 0.0, 0.0, 'CV'
        load = self.loads[ch]
        if load is None:
            return state.voltage, 0.0, 'CV'
        if load <= 0:
            return 0.0, state.current, 'CC'
        current = state.voltage / load
        if current > state.current:
            return state.current * load, state.current, 'CC'
        return state.voltage, current, 'CV'

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

    def _do_write(self, keys: tuple[str, ...], args: list[str]) -> None:
        if keys == ('OUTP', 'TRACK'):
            if not args:
                return
            word = args[0].strip().upper()
            value = _TRACK_WORDS.get(word, self._number(word))
            if value in (0, 1, 2):
                self.track = int(value)
            return
        if keys == ('LOCK',):
            flag = _BOOL_WORDS.get(args[0].upper()) if args else None
            if flag is not None:
                self.lock = int(flag)
            return
        if keys == ('OUTP', 'ALL'):
            flag = _BOOL_WORDS.get(args[0].upper()) if args else None
            if flag is not None:
                for state in self.channels.values():
                    self._set_output(state, flag)
            return
        ch = self._channel(args[0] if args else None)
        if ch is None:
            return
        state = self.channels[ch]
        value_arg = args[1] if len(args) > 1 else None
        if keys == ('RESET', 'PROT'):
            state.ovp_tripped = False
            state.ocp_tripped = False
        elif keys == ('MODE',):
            if ch not in self.sense or value_arg is None:
                return
            sense = _SENSE_WORDS.get(value_arg.upper(), self._number(value_arg))
            if sense in (0, 1):
                self.sense[ch] = int(sense)
        elif keys in (('OUTP',), ('OCP', 'STAT')):
            flag = _BOOL_WORDS.get(value_arg.upper()) if value_arg is not None else None
            if flag is None:
                return
            if keys == ('OUTP',):
                self._set_output(state, flag)
            else:
                state.ocp_enabled = flag
        else:
            number = self._number(value_arg) if value_arg is not None else None
            if number is None:
                return
            volt_max, amp_max = self._rating(ch)
            if keys == ('VOLT',):
                state.voltage = self._clamp(number, volt_max)
            elif keys == ('CURR',):
                state.current = self._clamp(number, amp_max)
            elif keys == ('OVP',):
                state.ovp = self._clamp(number, 1.1 * volt_max, 0.1 * volt_max)
            elif keys == ('OCP',):
                state.ocp = self._clamp(number, 1.1 * amp_max, 0.1 * amp_max)
            elif keys == ('OCP', 'DEL'):
                state.ocp_delay = max(number, 0.0)
            elif keys == ('OUTP', 'ON', 'DEL'):
                state.on_delay = max(number, 0.0)
            elif keys == ('OUTP', 'OFF', 'DEL'):
                state.off_delay = max(number, 0.0)

    @staticmethod
    def _set_output(state: FakeChannel, on: bool) -> None:
        # ASSUMPTION(hw): OUTPut? during OFF delay. Switching an output off that has a
        # non-zero OFF delay leaves it on (OUTPut? keeps answering 1 and it keeps delivering
        # power) until the delay has elapsed; advance() lets the time pass. Switching on again
        # cancels the pending switch-off. The delay is read when the command arrives.
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
        if keys == ('OUTP', 'TRACK'):
            # ASSUMPTION(hw): track numbering. The query answers a number, 0 independent,
            # 1 series, 2 parallel (the manual only shows 0 = independent).
            return str(self.track)
        if keys == ('LOCK',):
            # ASSUMPTION(hw): needed. The fake never locks the panel by itself; whether the
            # real supply stays locked after a remote session is an open question.
            return str(self.lock)
        if keys == ('OUTP', 'ALL'):
            # The all-channel response format is not documented; the plug does not use it.
            return _flag(all(s.output for s in self.channels.values()))
        ch = self._channel(args[0] if args else None)
        if ch is None:
            raise FakeTimeout(f'no answer to {message!r}: missing or invalid channel')
        state = self.channels[ch]
        if keys == ('MODE',):
            if ch not in self.sense:
                raise FakeTimeout(f'no answer to {message!r}: only CH2 and CH3 have MODE')
            # ASSUMPTION(hw): sense numbering. The query answers 0 for 2W and 1 for 4W.
            return str(self.sense[ch])
        if keys[0] == 'MEAS':
            volts, amps, mode = self._measure(ch)
            if keys == ('MEAS', 'VOLT'):
                return f'{volts:.6f}'
            if keys == ('MEAS', 'CURR'):
                return f'{amps:.6f}'
            if keys == ('MEAS', 'POWER'):
                return f'{volts * amps:.6f}'
            return mode
        scalars = {
            ('VOLT',): state.voltage,
            ('CURR',): state.current,
            ('OVP',): state.ovp,
            ('OCP',): state.ocp,
            ('OCP', 'DEL'): state.ocp_delay,
            ('OUTP', 'ON', 'DEL'): state.on_delay,
            ('OUTP', 'OFF', 'DEL'): state.off_delay,
        }
        # ASSUMPTION(hw): OCP? answers a plain number like OVP? (the manual prints no response).
        if keys in scalars:
            return f'{scalars[keys]:.6f}'
        # ASSUMPTION(hw): the protection state queries answer 1 when tripped, 0 otherwise.
        flags = {
            ('OUTP',): state.output,
            ('OCP', 'STAT'): state.ocp_enabled,
            ('OVP', 'PROT', 'STAT'): state.ovp_tripped,
            ('OCP', 'PROT', 'STAT'): state.ocp_tripped,
        }
        if keys in flags:
            return _flag(flags[keys])
        raise FakeTimeout(f'no answer to {message!r}')


def _flag(value: bool) -> str:
    return '1' if value else '0'


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
    ('*IDN',),
    ('*OPC',),
}
_KNOWN_WORDS = {word for command in _COMMANDS for word in command} | {'SET', 'RUN'}
