#!/usr/bin/env python3
# ruff: noqa: UP031, E501  (percent-format and long message lines are deliberate in this operator tool)
"""Hardware acceptance run for the Siglent SPD4000X (tested target: SPD4323X).

Answers the open questions of docs/scpi_reference.md section 8 in one logged
session and writes a Markdown report (default ./acceptance_report.md) from which
the project owner fills README "Things the manual does not tell you".

Run tools/bare_socket_check.py first. See docs/acceptance.md for the protocol.

SAFETY (enforced in code, see SafetyPolicy and the finally-blocks):
  * Default is "no output" mode: this tool never sends 'OUTPut CHn,1' or
    'OUTPut:ALL 1'. It queries every channel's output state first and refuses to
    continue if any output is on (override: --i-know-outputs-are-on).
  * Before any write it snapshots setpoints, OVP, OCP, OCP state, OCP delay,
    output on/off delays, track mode, sense mode and lock for every channel
    (read-only), prints them, saves them to acceptance_snapshot.local.json
    ('*.local.*' is git-ignored) and restores them in a finally-block with
    read-back. Values that cannot be restored are reported loudly. If a run is
    killed, 'hw_acceptance.py --restore-snapshot' restores from that file.
  * Writes touch CH1 only (--channel to change); the track/sense experiments
    necessarily touch CH2/CH3 and run only while their outputs are off.
  * Output-on experiment: only with --allow-output AND --confirm-no-load, CH1
    only, 1.0 V / 0.1 A, always followed by output off and snapshot restore.
  * Never sent, enforced by an allow/deny check on every string: *RST,
    DEFault:RESET, FACTory:RESET, anything under LAN, DHCP, GPIB, STORage,
    CALibrate, WAVE, LIST; any write whose header is not on a short allow list.

Transport: pyvisa with the '@py' backend (imported lazily). The wrapper handed
to the experiments is ScpiResource-compatible (write, query, close, timeout,
read_termination, write_termination), the same shape the plug uses, so the
read-only 'plug_smoke' experiment can pass it to SiglentSpdPlug when the package
is installed. Without the package the tool talks to pyvisa directly.

  export PSU_HOST=192.0.2.10
  python3 tools/hw_acceptance.py --dry-run                 # plan, no connection
  python3 tools/hw_acceptance.py --read-only               # first, safest pass
  python3 tools/hw_acceptance.py                           # + CH1 write experiments
  python3 tools/hw_acceptance.py --allow-output --confirm-no-load
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import statistics
import sys
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_REPORT = 'acceptance_report.md'
DEFAULT_SNAPSHOT = 'acceptance_snapshot.local.json'
DEFAULT_LOG = 'hw_acceptance.local.log'
PORT = 5025

READ, WRITE, OUTPUT = 'read', 'write', 'output'

# Copy of docs/scpi_reference.md section 6, used ONLY to choose test values
# (e.g. "25 % above the rating"). Nothing here is sent to the instrument as a limit.
RATINGS: dict[str, dict[int, tuple[float, float]]] = {
    'SPD4323X': {1: (6, 3.2), 2: (32, 3.2), 3: (32, 3.2), 4: (6, 3.2)},
    'SPD4121X': {1: (15, 1.5), 2: (12, 10), 3: (12, 10), 4: (15, 1.5)},
    'SPD4306X': {1: (15, 1.5), 2: (30, 6), 3: (30, 6), 4: (15, 1.0)},  # CH4 as printed
}

Q_TITLES = {
    1: 'Termination (commands, multi-command lines)',
    2: 'USB identity',
    3: 'LAN (VXI-11, simultaneous connections, web, telnet)',
    4: 'Response formats',
    5: 'Missing responses',
    6: 'Error reporting',
    7: 'Case / forms (leading colon, SOURce, short forms, spacing)',
    8: 'Channel argument (optional? invalid channel?)',
    9: 'Parameter keywords and out-of-range behaviour',
    10: 'OVP/OCP interaction with other settings',
    11: 'Timing / settling / *OPC',
    12: 'Remote lock',
    13: 'OUTPut:TRACK and MODE mappings',
    14: 'Rated table / MAX queries',
    15: 'LIST',
    16: 'WAVE',
    17: 'STORAGE',
    18: '*RST',
    19: 'Programming examples',
}
STATIC_COVERAGE = {
    2: 'needs USB (this tool uses the LAN socket)',
    3: 'partly: second connection is in bare_socket_check.py; VXI-11 here only with --try-vxi11; web/telnet via bare_socket_check.py --probe-ports',
    5: 'partly: OCP? covered; LAN/GPIB/STORage queries are out of scope and blocked by the safety policy',
    10: 'partly: output state after a trip and after RESET:PROTect needs a load that trips protection (out of scope)',
    13: 'partly: rejection of OUTPut:TRACK while outputs are on is not tested (would need an output on)',
    14: 'partly: SPD4306X CH4 needs that model (out of scope)',
    15: 'out of scope (LIST blocked by the safety policy)',
    16: 'out of scope (WAVE blocked by the safety policy)',
    17: 'out of scope (STORage blocked by the safety policy)',
    18: 'out of scope (*RST is never sent)',
    19: 'out of scope',
}


# ---------------------------------------------------------------------------
# Safety policy
# ---------------------------------------------------------------------------


class SafetyViolation(Exception):
    """A string was refused before it reached the instrument. Always a tool bug."""


_FORBIDDEN_PREFIXES = ('LAN', 'DHCP', 'GPIB', 'STOR', 'CAL', 'WAVE', 'LIST', 'FACT', 'DEFA')
_PREFIX_NODES = {'SOURCE', 'SOUR', 'SYSTEM', 'SYST', 'SYS'}
_SHORT = {'VOLTAGE': 'VOLT', 'CURRENT': 'CURR', 'OUTPUT': 'OUTP', 'STATE': 'STAT', 'DELAY': 'DEL'}
_WRITE_ALLOWED: set[tuple[str, ...]] = {
    ('VOLT',),
    ('VOLT', 'SET'),
    ('CURR',),
    ('CURR', 'SET'),
    ('OVP',),
    ('OCP',),
    ('OCP', 'STAT'),
    ('OCP', 'DEL'),
    ('OUTP',),
    ('OUTP', 'STAT'),
    ('OUTP', 'ALL'),
    ('OUTP', 'ALL', 'STAT'),
    ('OUTP', 'ON', 'DEL'),
    ('OUTP', 'OFF', 'DEL'),
    ('OUTP', 'TRAC'),
    ('OUTP', 'TRACK'),
    ('MODE',),
    ('LOCK',),
    ('LOCK', 'STAT'),
    ('*CLS',),
    ('*OPC',),
    ('*WAI',),
}
_HEADER = re.compile(r'([^\s?]+)(\?)?\s*(.*)$', re.S)


class SafetyPolicy:
    def __init__(self) -> None:
        self.writes_enabled = False  # set True only after the snapshot is saved
        self.on_allowed: set[int] = set()  # channels that may be switched on right now
        self.turned_on: set[int] = set()  # channels an ON command was released for
        self.allow_selftest = False

    @staticmethod
    def _parse(segment: str) -> tuple[list[str], bool, str]:
        m = _HEADER.match(segment.strip())
        if not m:
            raise SafetyViolation('cannot parse %r' % segment)
        header, q, args = m.group(1), bool(m.group(2)), m.group(3)
        nodes = [n for n in header.lstrip(':').upper().split(':')]
        while len(nodes) > 1 and nodes[0] in _PREFIX_NODES:
            nodes = nodes[1:]
        return [_SHORT.get(n, n) for n in nodes], q, args

    def check(self, cmd: str) -> None:
        if '\n' in cmd or '\r' in cmd or not cmd.strip():
            raise SafetyViolation('empty command or embedded line break: %r' % cmd)
        for seg in cmd.split(';'):
            self._check_segment(seg, cmd)

    def _check_segment(self, seg: str, whole: str) -> None:
        nodes, is_query, args = self._parse(seg)
        if nodes[0] == '*RST':
            raise SafetyViolation('*RST is never sent: %r' % whole)
        for n in nodes:
            if n.startswith(_FORBIDDEN_PREFIXES):
                raise SafetyViolation('forbidden subsystem node %r in %r' % (n, whole))
        if nodes[0] == '*TST' and not self.allow_selftest:
            raise SafetyViolation('*TST? needs --allow-selftest: %r' % whole)
        if is_query:
            return
        if not self.writes_enabled:
            raise SafetyViolation('write before the snapshot was saved: %r' % whole)
        if tuple(nodes) not in _WRITE_ALLOWED:
            raise SafetyViolation('write header not on the allow list: %r' % whole)
        if nodes[0] == 'OUTP':
            self._check_output(nodes[1:], args, whole)

    def _check_output(self, rest: list[str], args: str, whole: str) -> None:
        parts = [a.strip().upper() for a in args.split(',')] if args.strip() else []
        if rest in ([], ['STAT']):
            if len(parts) < 2:
                raise SafetyViolation('OUTPut set without channel and value: %r' % whole)
            if parts[1] in ('0', 'OFF'):
                return
            m = re.fullmatch(r'CH([1-4])', parts[0])
            if not m or int(m.group(1)) not in self.on_allowed:
                raise SafetyViolation('output ON is not allowed here: %r' % whole)
            self.turned_on.add(int(m.group(1)))
        elif rest and rest[0] == 'ALL':
            if not parts or parts[0] not in ('0', 'OFF'):
                raise SafetyViolation('OUTPut:ALL ON is never sent: %r' % whole)


# ---------------------------------------------------------------------------
# Transport wrapper with transcript
# ---------------------------------------------------------------------------


class QueryFailed(Exception):
    def __init__(self, cmd: str, err: BaseException, timeout: bool):
        super().__init__('%s: %s: %s' % (cmd, type(err).__name__, err))
        self.cmd, self.err, self.timeout = cmd, err, timeout


@dataclass
class Txn:
    idx: int
    kind: str  # W, Q, LATE
    cmd: str
    raw: bytes | None
    ms: float
    error: str = ''

    def line(self) -> str:
        if self.kind == 'W':
            return ' W  %-40r %7.1f ms%s' % (
                self.cmd,
                self.ms,
                ('  ERROR ' + self.error) if self.error else '',
            )
        if self.kind == 'LATE':
            return ' LATE bytes after a miss: %r' % self.raw
        if self.error:
            return ' Q  %-40r -> %s  %7.1f ms' % (self.cmd, self.error, self.ms)
        return ' Q  %-40r -> %-34r %7.1f ms' % (self.cmd, self.raw, self.ms)


def is_timeout(exc: BaseException) -> bool:
    text = ('%s %s' % (type(exc).__name__, exc)).lower()
    return 'timeout' in text or 'tmo' in text or 'timed out' in text


class Link:
    """ScpiResource-compatible wrapper: policy check, raw capture, transcript."""

    def __init__(self, res: Any, policy: SafetyPolicy, log_path: str | None = None):
        self._res = res
        self.policy = policy
        self.txns: list[Txn] = []
        self._log = open(log_path, 'a', encoding='utf-8') if log_path else None
        if self._log:
            self._log.write(
                '\n===== hw_acceptance %s =====\n' % dt.datetime.now().isoformat(timespec='seconds')
            )

    # --- ScpiResource attributes the plug sets -------------------------------
    def _attr(name: str) -> property:  # type: ignore[misc]
        return property(lambda s: getattr(s._res, name), lambda s, v: setattr(s._res, name, v))

    timeout = _attr('timeout')
    read_termination = _attr('read_termination')
    write_termination = _attr('write_termination')
    del _attr

    def close(self) -> None:
        try:
            self._res.close()
        finally:
            if self._log:
                self._log.close()
                self._log = None

    # --- bookkeeping ---------------------------------------------------------
    def _add(self, kind: str, cmd: str, raw: bytes | None, ms: float, error: str = '') -> Txn:
        t = Txn(len(self.txns), kind, cmd, raw, ms, error)
        self.txns.append(t)
        if self._log:
            self._log.write(dt.datetime.now().strftime('%H:%M:%S.%f')[:-3] + t.line() + '\n')
            self._log.flush()
        return t

    @property
    def last_ms(self) -> float:
        return self.txns[-1].ms if self.txns else 0.0

    # --- operations ----------------------------------------------------------
    def write(self, cmd: str) -> None:
        self.policy.check(cmd)
        t0 = time.perf_counter()
        try:
            self._res.write(cmd)
        except Exception as exc:
            self._add(
                'W',
                cmd,
                None,
                (time.perf_counter() - t0) * 1000,
                '%s: %s' % (type(exc).__name__, exc),
            )
            raise
        self._add('W', cmd, None, (time.perf_counter() - t0) * 1000)

    def query(self, cmd: str, timeout_ms: int | None = None) -> str:
        self.policy.check(cmd)
        n_lines = sum(1 for s in cmd.split(';') if '?' in s.split()[0]) or 1
        old = None
        if timeout_ms is not None:
            old = self._res.timeout
            self._res.timeout = timeout_ms
        t0 = time.perf_counter()
        raw = b''
        err: BaseException | None = None
        try:
            if hasattr(self._res, 'read_raw'):
                self._res.write(cmd)
                for _ in range(n_lines):
                    raw += bytes(self._res.read_raw())
            else:  # fakes without read_raw: reply text only, terminator is synthetic
                raw = (str(self._res.query(cmd)) + '\n').encode('ascii', 'replace')
        except Exception as exc:
            err = exc
        finally:
            if old is not None:
                self._res.timeout = old
        ms = (time.perf_counter() - t0) * 1000
        if err is not None:
            self._add('Q', cmd, None, ms, '%s: %s' % (type(err).__name__, err))
            self.drain()
            raise QueryFailed(cmd, err, is_timeout(err))
        self._add('Q', cmd, raw, ms)
        return raw.decode('ascii', 'replace').rstrip('\r\n')

    def drain(self, quiet_ms: int = 150) -> bytes:
        """Collect bytes that arrive late after a miss so the stream stays in step."""
        if not hasattr(self._res, 'read_raw'):
            return b''
        old = self._res.timeout
        self._res.timeout = quiet_ms
        got = b''
        try:
            for _ in range(20):
                try:
                    chunk = bytes(self._res.read_raw())
                except Exception:
                    break
                if not chunk:
                    break
                got += chunk
        finally:
            self._res.timeout = old
        if got:
            self._add('LATE', '', got, 0.0)
        return got


class DryResource:
    """Tiny stateful stand-in used by --dry-run (no network, not an instrument model)."""

    def __init__(self, model: str = 'SPD4323X'):
        self.timeout = 5000
        self.read_termination = '\n'
        self.write_termination = '\n'
        self.model = model
        self.state: dict[str, str] = {}

    def close(self) -> None:
        pass

    @staticmethod
    def _key(seg: str) -> tuple[str, list[str]]:
        nodes, _, args = SafetyPolicy._parse(seg)
        if nodes and nodes[-1] == 'SET':
            nodes = nodes[:-1]
        parts = [a.strip().upper() for a in args.split(',')] if args.strip() else []
        return ':'.join(n[:5] if n.startswith('*') else n[:4] for n in nodes), parts

    def write(self, cmd: str) -> None:
        for seg in cmd.split(';'):
            if '?' in seg.split()[0]:
                continue
            key, parts = self._key(seg)
            if key.startswith('*'):
                continue
            ch = parts[0] if parts and parts[0].startswith('CH') else ''
            val = parts[1] if ch and len(parts) > 1 else (parts[0] if parts else '')
            val = {
                'SERIES': '1',
                'PARALLEL': '2',
                'INDEPENDENT': '0',
                '4W': '1',
                '2W': '0',
                'ON': '1',
                'OFF': '0',
            }.get(val, val)
            try:
                val = (
                    '%.6f' % float(val)
                    if key not in ('OUTP', 'OUTP:STAT', 'OCP:STAT', 'LOCK', 'OUTP:TRAC', 'MODE')
                    else val
                )
            except ValueError:
                pass
            self.state[key + '|' + ch] = val

    def query(self, cmd: str) -> str:
        replies = []
        for seg in cmd.split(';'):
            if '?' not in seg.split()[0]:
                self.write(seg)
                continue
            replies.append(self._answer(seg.strip()))
        if not replies:
            raise TimeoutError('dry-run: no answer')
        return replies[0]

    def _answer(self, seg: str) -> str:
        s = seg.upper()
        if s == '*IDN?':
            return 'Siglent Technologies,%s,SPD4XXXXXXXXXX,1.0.0.0' % self.model
        if s == '*OPC?':
            return '1'
        if s in ('*ESR?', '*STB?', '*ESE?', '*SRE?', '*TST?'):
            return '0'
        key, parts = self._key(seg)
        ch = parts[0] if parts and parts[0].startswith('CH') else ''
        if ch and ch not in ('CH1', 'CH2', 'CH3', 'CH4'):
            raise TimeoutError('dry-run: invalid channel')
        if key == 'MEAS:RUN:MODE':
            return 'CV'
        if key == 'MEAS:VOLT':
            return (
                self.state.get('VOLT|' + ch, '0.000000')
                if self.state.get('OUTP|' + ch) == '1'
                else '0.000000'
            )
        if len(parts) > 1:  # MIN/MAX/DEF queries
            return '6.000000'
        if key in self.state_keys_default_int():
            return self.state.get(key + '|' + ch, '0')
        return self.state.get(key + '|' + ch, '0.000000')

    @staticmethod
    def state_keys_default_int() -> tuple[str, ...]:
        return (
            'OUTP',
            'OUTP:STAT',
            'OUTP:ALL',
            'OCP:STAT',
            'OVP:PROT:STAT',
            'OCP:PROT:STAT',
            'LOCK',
            'LOCK:STAT',
            'OUTP:TRAC',
            'MODE',
        )


# ---------------------------------------------------------------------------
# Context, findings
# ---------------------------------------------------------------------------


class Skip(Exception):
    """Raised by an experiment that cannot run safely or meaningfully."""


@dataclass
class Experiment:
    num: int
    key: str
    tier: str
    questions: tuple[int, ...]
    fn: Callable[[Ctx], None]
    flag: str = ''  # opt-in flag that must be given

    @property
    def doc(self) -> str:
        return (self.fn.__doc__ or '').strip()

    @property
    def title(self) -> str:
        return self.doc.splitlines()[0] if self.doc else self.key


@dataclass
class ExpResult:
    exp: Experiment
    status: str = 'pending'  # done | skipped | error
    notes: list[str] = field(default_factory=list)
    findings: list[tuple[int, str]] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    txn_range: tuple[int, int] = (0, 0)
    error: str = ''


EXPERIMENTS: list[Experiment] = []


def experiment(num: int, key: str, tier: str, questions: tuple[int, ...], flag: str = ''):
    def deco(fn: Callable[[Ctx], None]) -> Callable[[Ctx], None]:
        if not (fn.__doc__ or '').strip():
            raise RuntimeError('experiment %d has no docstring' % num)
        EXPERIMENTS.append(Experiment(num, key, tier, questions, fn, flag))
        return fn

    return deco


_NUM = re.compile(r'\s*[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?\s*')


def fnum(text: str | None) -> float | None:
    if text is None or not _NUM.fullmatch(text):
        return None
    return float(text)


def close_to(a: float | None, b: float | None, tol: float = 5e-4) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol + 1e-6 * abs(b)


def values_match(orig: str, now: str) -> bool:
    fo, fn = fnum(orig), fnum(now)
    if fo is not None and fn is not None:
        return close_to(fn, fo)
    return orig.strip().upper() == now.strip().upper()


class Ctx:
    def __init__(
        self, link: Link, args: argparse.Namespace, policy: SafetyPolicy, dry: bool = False
    ):
        self.link, self.args, self.policy, self.dry = link, args, policy, dry
        self.ch: int = args.channel
        self.idn = ''
        self.model: str | None = None
        self.serial = ''
        self.snapshot: dict[str, Any] = {}
        self.cur = ExpResult(Experiment(0, '', READ, (), lambda c: None))
        self._vt = 0.0  # virtual clock for --dry-run
        self.secrets: list[str] = []
        self.no_ocp = False  # True when 'OCP? CHn' is unanswered: OCP can then not be restored, so it is never written

    # --- time ----------------------------------------------------------------
    def now(self) -> float:
        return self._vt if self.dry else time.monotonic()

    def sleep(self, s: float) -> None:
        if s <= 0:
            return
        if self.dry:
            self._vt += s
        else:
            time.sleep(s)

    # --- ratings -------------------------------------------------------------
    @property
    def rating(self) -> tuple[float, float] | None:
        return RATINGS.get(self.model or '', {}).get(self.ch)

    # --- I/O -----------------------------------------------------------------
    def q(self, cmd: str, timeout_ms: int | None = None) -> str | None:
        try:
            return self.link.query(cmd, timeout_ms)
        except QueryFailed as exc:
            self.cur.notes.append(
                'no answer to %r (%s)' % (cmd, 'timeout' if exc.timeout else type(exc.err).__name__)
            )
            return None

    def probe(self, cmd: str) -> str | None:
        return self.q(cmd, self.args.probe_timeout_ms)

    def w(self, cmd: str) -> None:
        self.link.write(cmd)

    def setq(self, set_cmd: str, query_cmd: str) -> str | None:
        self.w(set_cmd)
        return self.q(query_cmd)

    def outputs_on(self, channels: tuple[int, ...] = (1, 2, 3, 4)) -> list[int]:
        """Channels whose output is on or unknown (query failed)."""
        bad = []
        for n in channels:
            r = self.q('OUTPut? CH%d' % n)
            if r is None or r.strip() not in ('0', 'OFF'):
                bad.append(n)
        return bad

    def require_outputs_off(self, channels: tuple[int, ...] = (1, 2, 3, 4)) -> None:
        if self.args.i_know_outputs_are_on:
            return
        bad = self.outputs_on(channels)
        if bad:
            raise Skip(
                'output of CH%s is on or unreadable; refusing to write' % ','.join(map(str, bad))
            )

    def require_independent(self) -> None:
        if self.ch in (2, 3):
            t = self.q('OUTPut:TRACK?')
            if t is None or t.strip().upper() not in ('0', 'INDEPENDENT'):
                raise Skip('CH%d tested only in independent mode; track reads %r' % (self.ch, t))

    # --- reporting -----------------------------------------------------------
    def note(self, text: str) -> None:
        self.cur.notes.append(text)

    def finding(self, question: int, text: str) -> None:
        self.cur.findings.append((question, text))

    def block(self, text: str) -> None:
        self.cur.blocks.append(text)


def classify_set(
    prev: float | None, requested: float | None, resp: str | None, limit: float | None = None
) -> str:
    r = fnum(resp)
    if resp is None:
        return 'no read-back (timeout)'
    if r is None:
        return 'non-numeric read-back %r' % resp
    shown = resp.strip()
    if requested is None:  # MINimum / MAXimum / DEFault: the read-back is the finding
        return 'keyword; read-back %s' % shown
    if close_to(r, requested, 5e-4):
        return 'accepted as sent (read-back %s)' % shown
    if limit is not None and close_to(r, limit):
        return 'CLAMPED to the limit %g (read-back %s)' % (limit, shown)
    if prev is not None and close_to(r, prev):
        return 'NOT APPLIED, read-back %s equals the previous value (ignored)' % shown
    return 'CHANGED to %s (clamped or rounded)' % shown


# ---------------------------------------------------------------------------
# Snapshot and restore
# ---------------------------------------------------------------------------

CH_FIELDS: list[tuple[str, str, str]] = [
    ('voltage', 'VOLTage? CH{n}', 'VOLTage CH{n},{v}'),
    ('current', 'CURRent? CH{n}', 'CURRent CH{n},{v}'),
    ('ovp', 'OVP? CH{n}', 'OVP CH{n},{v}'),
    ('ocp', 'OCP? CH{n}', 'OCP CH{n},{v}'),
    ('ocp_state', 'OCP:STATe? CH{n}', 'OCP:STATe CH{n},{v}'),
    ('ocp_delay', 'OCP:DELay? CH{n}', 'OCP:DELay CH{n},{v}'),
    ('on_delay', 'OUTPut:ON:DELay? CH{n}', 'OUTPut:ON:DELay CH{n},{v}'),
    ('off_delay', 'OUTPut:OFF:DELay? CH{n}', 'OUTPut:OFF:DELay CH{n},{v}'),
]
RESTORE_ORDER = [
    'ovp',
    'ocp',
    'ocp_delay',
    'ocp_state',
    'voltage',
    'current',
    'on_delay',
    'off_delay',
]
CORE_FIELDS = ('voltage', 'current', 'ovp', 'ocp', 'ocp_state', 'ocp_delay')


def take_snapshot(c: Ctx) -> dict[str, Any]:
    snap: dict[str, Any] = {'channels': {}, 'sense': {}}
    for n in (1, 2, 3, 4):
        d: dict[str, str | None] = {}
        for name, qcmd, _ in CH_FIELDS:
            d[name] = c.q(qcmd.format(n=n))
        d['output'] = c.q('OUTPut? CH%d' % n)
        snap['channels'][str(n)] = d
    snap['track'] = c.q('OUTPut:TRACK?')
    for n in (2, 3):
        snap['sense'][str(n)] = c.q('MODE? CH%d' % n)
    snap['lock'] = c.q('LOCK?')
    return snap


def snapshot_table(snap: dict[str, Any]) -> list[str]:
    names = [f[0] for f in CH_FIELDS] + ['output']
    lines = ['%-10s ' % '' + ' '.join('CH%s' % n.rjust(9) for n in '1234')]
    for name in names:
        row = [str(snap['channels'][str(n)].get(name)) for n in (1, 2, 3, 4)]
        lines.append('%-10s ' % name + ' '.join('%12s' % v for v in row))
    lines.append(
        'track=%r  sense CH2=%r CH3=%r  lock=%r'
        % (snap.get('track'), snap['sense'].get('2'), snap['sense'].get('3'), snap.get('lock'))
    )
    return lines


@dataclass
class RestoreItem:
    name: str
    query: str
    setter: str
    orig: str | None
    status: str = 'pending'  # unchanged | restored | FAILED | skipped
    now: str | None = None


def build_restore_items(snap: dict[str, Any], channels: list[int]) -> list[RestoreItem]:
    items = [RestoreItem('track', 'OUTPut:TRACK?', 'OUTPut:TRACK {v}', snap.get('track'))]
    for n in (2, 3):
        items.append(
            RestoreItem(
                'sense CH%d' % n, 'MODE? CH%d' % n, 'MODE CH%d,{v}' % n, snap['sense'].get(str(n))
            )
        )
    for n in channels:
        d = snap['channels'][str(n)]
        by_name = {f[0]: f for f in CH_FIELDS}
        for name in RESTORE_ORDER:
            _, qcmd, scmd = by_name[name]
            items.append(
                RestoreItem(
                    'CH%d %s' % (n, name),
                    qcmd.format(n=n),
                    scmd.replace('{n}', str(n)),
                    d.get(name),
                )
            )
    items.append(RestoreItem('lock', 'LOCK?', 'LOCK {v}', snap.get('lock')))
    return items


def restore_snapshot(c: Ctx, snap: dict[str, Any], channels: list[int]) -> list[RestoreItem]:
    """Read each value; write the snapshot value only where it differs; read back. Up to 3 passes."""
    items = build_restore_items(snap, channels)
    for it in items:
        if it.orig is None:
            it.status = 'skipped'
    first = True
    for _attempt in range(3):
        pending = [i for i in items if i.status in ('pending', 'FAILED')]
        if not pending:
            break
        for it in pending:
            it.now = c.q(it.query)
            if it.now is not None and values_match(it.orig or '', it.now):
                it.status = 'unchanged' if first and it.status == 'pending' else 'restored'
                continue
            try:
                c.w(it.setter.format(v=it.orig))
            except SafetyViolation:
                raise
            except Exception:
                pass
            it.now = c.q(it.query)
            ok = it.now is not None and values_match(it.orig or '', it.now)
            it.status = 'restored' if ok else 'FAILED'
        first = False
    return items


def save_json(path: str, data: dict[str, Any]) -> None:
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Experiments: read-only tier
# ---------------------------------------------------------------------------


@experiment(1, 'identity', READ, (1, 4))
def exp_identity(c: Ctx) -> None:
    """Identity string and raw reply shape.

    Open question 1 (Termination: which terminator the instrument expects and
    sends) and 4 (Responses: what the literal `\\s` in the *IDN? example looks
    like on the wire, actual *IDN? string, `\\n` after every reply).
    """
    r = c.q('*IDN?')
    raw = c.link.txns[-1].raw if c.link.txns and c.link.txns[-1].kind == 'Q' else None
    c.finding(4, '*IDN? raw reply %r' % raw)
    if r is None:
        return
    fields = r.split(',')
    c.finding(4, '*IDN? has %d comma-separated fields: %r' % (len(fields), fields))
    if '\\s' in r:
        c.finding(4, "the manual's `\\s` is sent LITERALLY as backslash-s")
    elif 'Siglent Technologies' in r:
        c.finding(4, "the manual's `\\s` is a plain space on the wire")
    if raw is not None:
        term = 'CRLF' if raw.endswith(b'\r\n') else 'LF' if raw.endswith(b'\n') else 'none'
        c.finding(
            1,
            'reply terminator seen through pyvisa read_termination=\\n: %s (command terminator used: %r)'
            % (term, c.args.term),
        )


@experiment(2, 'formats', READ, (4, 5, 8))
def exp_formats(c: Ctx) -> None:
    """Raw reply of every read-only query, every channel.

    Open question 4 (Responses: decimals, units, `0`/`1`, `CV`, number vs word
    for OUTPut:TRACK? and MODE?), 5 (Missing responses: `OCP?` has no printed
    response) and 8 (Channel argument: MODE? CH1, which the manual says is
    CH2/CH3 only).
    """
    rows = []
    for n in (1, 2, 3, 4):
        for fmt in (
            'VOLTage? CH{n}',
            'CURRent? CH{n}',
            'OVP? CH{n}',
            'OCP? CH{n}',
            'OCP:STATe? CH{n}',
            'OCP:DELay? CH{n}',
            'OUTPut:ON:DELay? CH{n}',
            'OUTPut:OFF:DELay? CH{n}',
            'OVP:PROTect:STATe? CH{n}',
            'OCP:PROTect:STATe? CH{n}',
            'MEASure:VOLTage? CH{n}',
            'MEASure:CURRent? CH{n}',
            'MEASure:POWER? CH{n}',
            'MEASure:RUN:MODE? CH{n}',
            'OUTPut? CH{n}',
        ):
            cmd = fmt.format(n=n)
            r = c.probe(cmd)
            rows.append((cmd, r))
    for cmd in ('OUTPut:ALL?', 'OUTPut:TRACK?', 'MODE? CH2', 'MODE? CH3', 'MODE? CH1', 'LOCK?'):
        rows.append((cmd, c.probe(cmd)))
    for cmd in ('*OPC?', '*ESE?', '*ESR?', '*SRE?', '*STB?'):
        rows.append((cmd, c.q(cmd)))
        raw = c.link.txns[-1].raw
        c.note('%s raw %r' % (cmd, raw))
    answered = {cmd: r for cmd, r in rows if r is not None}
    decs = {
        len(r.split('.')[1])
        for cmd, r in answered.items()
        if cmd.split('?')[0].split()[0]
        in (
            'VOLTage',
            'CURRent',
            'OVP',
            'OCP',
            'OCP:DELay',
            'MEASure:VOLTage',
            'MEASure:CURRent',
            'MEASure:POWER',
        )
        and fnum(r) is not None
        and '.' in r
    }
    c.finding(4, 'scalar V/A/W/s replies use %s decimal places' % (sorted(decs) or 'n/a'))
    unit = [
        cmd
        for cmd, r in answered.items()
        if r and re.search(r'\d\s*[A-Za-z]+$', r) and fnum(r) is None and ',' not in r
    ]
    c.finding(4, 'replies with a unit suffix: %s' % (unit or 'none'))
    c.finding(
        4,
        'OUTPut:ALL? -> %r, OUTPut:TRACK? -> %r, MODE? CH2 -> %r, MEASure:RUN:MODE? CH1 -> %r, LOCK? -> %r'
        % (
            answered.get('OUTPut:ALL?'),
            answered.get('OUTPut:TRACK?'),
            answered.get('MODE? CH2'),
            answered.get('MEASure:RUN:MODE? CH1'),
            answered.get('LOCK?'),
        ),
    )
    c.finding(
        5,
        'OCP? CH1 -> %r (CH2..4: %s)'
        % (answered.get('OCP? CH1'), [answered.get('OCP? CH%d' % n) for n in (2, 3, 4)]),
    )
    c.finding(8, 'MODE? CH1 -> %r (manual: CH2/CH3 only)' % answered.get('MODE? CH1'))
    c.block(
        '| query | reply |\n|---|---|\n'
        + '\n'.join('| `%s` | `%r` |' % (cmd, r) for cmd, r in rows)
    )


@experiment(3, 'forms', READ, (1, 7, 8))
def exp_forms(c: Ctx) -> None:
    """Syntax forms as read-only queries (same table as bare_socket_check.py).

    Open question 7 (Case/forms: leading colon, `[:SOURce]`, short forms,
    literal brackets, spacing), 8 (Channel argument: no channel, CH0, CH5,
    bare number) and 1 (Termination: two queries on one line separated by `;`).
    """
    try:
        import bare_socket_check as bsc
    except ImportError as exc:
        raise Skip('cannot import tools/bare_socket_check.py: %s' % exc) from exc
    base: dict[str, str | None] = {}
    for _, _cmd, ref, _ in bsc.FORMS:
        if ref and ref not in base:
            base[ref] = c.probe(ref)
    rows, diffs = [], []
    for label, cmd, ref, manual in bsc.FORMS:
        r = c.probe(cmd)
        if r is None:
            observed = 'SILENT'
        elif ref and base.get(ref) is not None:
            a, b = fnum(r), fnum(base[ref])
            observed = (
                'same as `%s`' % ref
                if (r == base[ref] or (a is not None and b is not None and abs(a - b) <= 0.01))
                else 'DIFFERENT value'
            )
        else:
            observed = 'answered'
        if (manual == 'accept' and r is None) or (manual == 'reject' and r is not None):
            diffs.append(label)
        rows.append((label, cmd, manual, observed, r))
    c.finding(7, 'forms that differ from what the manual implies: %s' % (diffs or 'none'))
    accepted = [cmd for _, cmd, _, o, r in rows if r is not None]
    silent = [cmd for _, cmd, _, o, r in rows if r is None]
    c.finding(7, 'answered: %s' % accepted)
    c.finding(7, 'no answer: %s' % silent)
    multi = next((r for r in rows if r[1] == '*IDN?;*OPC?'), None)
    c.finding(
        1,
        '`*IDN?;*OPC?` on one line -> %s (reply %r)'
        % (
            'both queries answered' if multi and multi[4] is not None else 'no answer',
            multi[4] if multi else None,
        ),
    )
    nochan = next((r for r in rows if r[1] == 'VOLTage?'), None)
    c.finding(
        8,
        '`VOLTage?` without channel -> %r; CH0 -> %r; CH5 -> %r; `VOLTage? 1` -> %r'
        % (
            nochan[4] if nochan else None,
            next((r[4] for r in rows if r[1] == 'VOLTage? CH0'), None),
            next((r[4] for r in rows if r[1] == 'VOLTage? CH5'), None),
            next((r[4] for r in rows if r[1] == 'VOLTage? 1'), None),
        ),
    )
    c.block(
        '| form | command | manual | observed | reply |\n|---|---|---|---|---|\n'
        + '\n'.join('| %s | `%s` | %s | %s | `%r` |' % row for row in rows)
    )


@experiment(4, 'min_max', READ, (9, 14))
def exp_min_max(c: Ctx) -> None:
    """MINimum / MAXimum / DEFault as queries (`VOLTage? CH1,MAX`).

    Open question 9 (Parameter keywords: do they work, what do they return) and
    14 (Rated table: real limits returned by `VOLT? CHn,MAX` / `CURR? CHn,MAX`).
    Queries only; nothing is set.
    """
    try:
        import bare_socket_check as bsc
    except ImportError as exc:
        raise Skip('cannot import tools/bare_socket_check.py: %s' % exc) from exc
    rows = []
    for cmd, _why in bsc.PARAMS:
        rows.append((cmd, c.probe(cmd)))
    if any(
        r is not None for cmd, r in rows if cmd.startswith(('VOLTage? CH1,M', 'CURRent? CH1,M'))
    ):
        for n in (1, 2, 3, 4):
            for kind in ('VOLTage', 'CURRent', 'OVP', 'OCP'):
                for kw in ('MIN', 'MAX', 'DEF'):
                    cmd = '%s? CH%d,%s' % (kind, n, kw)
                    if cmd not in [r[0] for r in rows]:
                        rows.append((cmd, c.probe(cmd)))
    else:
        c.note('no MIN/MAX query on CH1 was answered; the all-channel grid was skipped')
    got = {cmd: r for cmd, r in rows}
    answered = [cmd for cmd, r in rows if r is not None]
    c.finding(9, '`<query>? CHn,MAX|MIN|DEF` answered for: %s' % answered)
    c.finding(9, 'no answer for: %s' % [cmd for cmd, r in rows if r is None])
    rating = RATINGS.get(c.model or '')
    for n in (1, 2, 3, 4):
        vmax, imax = got.get('VOLTage? CH%d,MAX' % n), got.get('CURRent? CH%d,MAX' % n)
        printed = rating.get(n) if rating else None
        c.finding(
            14, 'CH%d MAX: voltage %r, current %r (manual table: %s)' % (n, vmax, imax, printed)
        )
    c.block('| query | reply |\n|---|---|\n' + '\n'.join('| `%s` | `%r` |' % row for row in rows))


@experiment(5, 'timing', READ, (11,))
def exp_timing(c: Ctx) -> None:
    """Round-trip time per query, median of 5.

    Open question 11 (Timing: response time of MEASure, measurement refresh
    rate); the numbers size the plug's timeouts and polling interval.
    """
    n = c.ch
    cmds = [
        '*IDN?',
        '*OPC?',
        'OUTPut? CH%d' % n,
        'VOLTage? CH%d' % n,
        'OVP? CH%d' % n,
        'MEASure:VOLTage? CH%d' % n,
        'MEASure:CURRent? CH%d' % n,
        'MEASure:POWER? CH%d' % n,
        'MEASure:RUN:MODE? CH%d' % n,
        'OUTPut:TRACK?',
    ]
    rows = []
    for cmd in cmds:
        ms = []
        for _ in range(5):
            if c.q(cmd) is not None:
                ms.append(c.link.last_ms)
        if ms:
            rows.append((cmd, statistics.median(ms), min(ms), max(ms), len(ms)))
    for cmd, med, lo, hi, k in rows:
        c.note('%-28s median %.1f ms  min %.1f  max %.1f  (n=%d)' % (cmd, med, lo, hi, k))
    if rows:
        worst = max(r[3] for r in rows)
        meas = [r[1] for r in rows if r[0].startswith('MEAS')]
        c.finding(
            11,
            'slowest query seen %.0f ms; median MEASure query %.1f ms; a poll interval below that is pointless, '
            'and a plug timeout of 10x the slowest (%.0f ms) is generous'
            % (worst, statistics.median(meas) if meas else float('nan'), worst * 10),
        )
    c.block(
        '| query | median ms | min | max | n |\n|---|---|---|---|---|\n'
        + '\n'.join('| `%s` | %.1f | %.1f | %.1f | %d |' % r for r in rows)
    )


@experiment(6, 'status_registers', READ, (6,))
def exp_status(c: Ctx) -> None:
    """Status registers before and after invalid read-only queries.

    Open question 6 (Errors: no error-query command; which bits of `*ESR?` and
    `*STB?` are used, what `*TST?` = 0 means). `*TST?` runs only with
    --allow-selftest.
    """
    before = {r: c.q(r) for r in ('*ESE?', '*SRE?', '*ESR?', '*STB?')}
    c.note('baseline %r' % before)
    c.probe('FOOBar? CH1')
    after1 = {r: c.q(r) for r in ('*ESR?', '*STB?')}
    c.probe('VOLTage? CH5')
    after2 = {r: c.q(r) for r in ('*ESR?', '*STB?')}
    c.finding(
        6,
        'baseline *ESR?=%r *STB?=%r; after unknown query `FOOBar?`: %r; after `VOLTage? CH5`: %r'
        % (before['*ESR?'], before['*STB?'], after1, after2),
    )
    changed = after1 != {k: before[k] for k in after1} or after2 != {k: before[k] for k in after2}
    if before['*ESR?'] is None or before['*STB?'] is None:
        c.finding(
            6, '*ESR? or *STB? gave NO ANSWER at all: not implemented, or the socket is out of step'
        )
    else:
        c.finding(
            6,
            'status registers %s after invalid queries'
            % ('CHANGED' if changed else 'did not change'),
        )
    if c.args.allow_selftest:
        c.finding(6, '*TST? -> %r' % c.q('*TST?'))
    else:
        c.note('*TST? skipped (needs --allow-selftest)')


@experiment(7, 'vxi11', READ, (3,), flag='try_vxi11')
def exp_vxi11(c: Ctx) -> None:
    """Open the supply as TCPIP::<host>::INSTR (VXI-11) next to the socket session.

    Open question 3 (LAN: does the instrument expose VXI-11 / `TCPIP::<ip>::INSTR`,
    and may a second session coexist with the socket?). Needs a network path to
    the instrument's portmapper; a forwarded single port 5025 will not do.
    """
    if c.dry or c.args.fake:
        raise Skip('not available in --dry-run/--fake')
    host = os.environ.get('PSU_HOST') or ''
    if not host:
        raise Skip('PSU_HOST not set')
    import pyvisa

    rm = pyvisa.ResourceManager('@py')
    name = 'TCPIP::%s::INSTR' % host
    try:
        res = rm.open_resource(name, open_timeout=5000)
    except Exception as exc:
        c.finding(3, 'opening `TCPIP::<host>::INSTR` failed: %s: %s' % (type(exc).__name__, exc))
        return
    try:
        res.timeout = 3000
        link = Link(res, c.policy)
        reply = link.query('*IDN?')
        c.finding(3, 'VXI-11 `*IDN?` -> %r while the socket session was open' % reply)
    except Exception as exc:
        c.finding(3, 'VXI-11 session opened but *IDN? failed: %s: %s' % (type(exc).__name__, exc))
    finally:
        res.close()
        rm.close()


@experiment(8, 'plug_smoke', READ, (4,))
def exp_plug_smoke(c: Ctx) -> None:
    """Run the plug's read-only methods against the real instrument.

    Not an open question: it checks that the plug's assumptions (`# ASSUMPTION(hw)`
    in src/) survive contact with the instrument. Answers nothing new for
    section 8 but any exception here is a defect to fix in the plug or the fake
    (open question 4 is the closest: response parsing). Skipped when the package
    is not installed. Calls only getters; tearDown() is never called.
    """
    try:
        from siglent_spd_openhtf.plug import SiglentSpdPlug
    except Exception as exc:
        raise Skip('siglent_spd_openhtf not importable: %s' % exc) from exc
    plug = SiglentSpdPlug(resource=c.link, outputs_off_on_teardown=False, restore_state=False)
    n = c.ch
    calls: list[tuple[str, Callable[[], Any]]] = [
        ('idn()', plug.idn),
        ('snapshot()', plug.snapshot),
        ('track()', plug.track),
        ('sense(2)', lambda: plug.sense(2)),
        ('output(%d)' % n, lambda: plug.output(n)),
        ('voltage_setpoint(%d)' % n, lambda: plug.voltage_setpoint(n)),
        ('current_setpoint(%d)' % n, lambda: plug.current_setpoint(n)),
        ('ovp(%d)' % n, lambda: plug.ovp(n)),
        ('ocp(%d)' % n, lambda: plug.ocp(n)),
        ('ocp_enabled(%d)' % n, lambda: plug.ocp_enabled(n)),
        ('ocp_delay(%d)' % n, lambda: plug.ocp_delay(n)),
        ('protection_status(%d)' % n, lambda: plug.protection_status(n)),
        ('measure(%d)' % n, lambda: plug.measure(n)),
        ('run_mode(%d)' % n, lambda: plug.run_mode(n)),
        ('locked()', plug.locked),
        ('opc()', plug.opc),
    ]
    bad = []
    for name, fn in calls:
        try:
            c.note('plug.%s -> %r' % (name, fn()))
        except Exception as exc:
            bad.append(name)
            c.note('plug.%s RAISED %s: %s' % (name, type(exc).__name__, exc))
    c.note('plug.model -> %r' % (getattr(plug, 'model', None),))
    c.finding(
        4, 'plug read-only methods that raised against the real instrument: %s' % (bad or 'none')
    )


# ---------------------------------------------------------------------------
# Experiments: write tier (outputs stay off)
# ---------------------------------------------------------------------------


def _setpoint_experiment(
    c: Ctx, kind: str, steps: list[tuple[str, str]], limit: float | None = None
) -> dict[str, str]:
    """Shared body for the voltage/current setpoint experiments."""
    n = c.ch
    qcmd = '%s? CH%d' % (kind, n)
    prev = fnum(c.q(qcmd))
    out: dict[str, str] = {}
    for label, val in steps:
        requested = fnum(val)
        r = c.setq('%s CH%d,%s' % (kind, n, val), qcmd)
        verdict = classify_set(prev, requested, r, limit)
        out[label] = verdict
        c.note('%s: sent %s, %s' % (label, val, verdict))
        if fnum(r) is not None:
            prev = fnum(r)
    return out


@experiment(10, 'voltage_set', WRITE, (4, 9))
def exp_voltage_set(c: Ctx) -> None:
    """Voltage setpoint: resolution, above-rating, negative, keywords.

    Open question 9 (Parameter keywords: rounding/clamping vs error when a value
    is out of range, what MINimum/MAXimum/DEFault set) and 4 (Responses: how many
    decimals come back after a set). Output stays off.
    """
    c.require_outputs_off()
    c.require_independent()
    rating = c.rating
    vr = rating[0] if rating else None
    steps = [('1.000 V', '1.000'), ('1.2345 V (resolution)', '1.2345')]
    if vr:
        steps += [
            ('rating exactly (%g V)' % vr, '%g' % vr),
            ('125%% of rating (%g V)' % round(vr * 1.25, 3), '%g' % round(vr * 1.25, 3)),
        ]
    steps += [
        ('negative (-1 V)', '-1'),
        ('MINimum', 'MINimum'),
        ('MAXimum', 'MAXimum'),
        ('DEFault', 'DEFault'),
        ('0', '0'),
    ]
    out = _setpoint_experiment(c, 'VOLTage', steps, vr)
    c.finding(9, 'VOLTage CH%d: %s' % (c.ch, '; '.join('%s -> %s' % kv for kv in out.items())))
    c.finding(
        4, 'read-back of `VOLTage CH%d,1.2345` -> %s' % (c.ch, out.get('1.2345 V (resolution)'))
    )


@experiment(11, 'current_set', WRITE, (4, 9))
def exp_current_set(c: Ctx) -> None:
    """Current setpoint: resolution, above-rating, negative, keywords.

    Open question 9 (Parameter keywords: clamp vs error out of range, what the
    keywords set) and 4 (Responses: decimals). Output stays off.
    """
    c.require_outputs_off()
    c.require_independent()
    rating = c.rating
    ir = rating[1] if rating else None
    steps = [('0.100 A', '0.100'), ('0.1234 A (resolution)', '0.1234')]
    if ir:
        steps += [
            ('rating exactly (%g A)' % ir, '%g' % ir),
            ('125%% of rating (%g A)' % round(ir * 1.25, 3), '%g' % round(ir * 1.25, 3)),
        ]
    steps += [
        ('negative (-0.1 A)', '-0.1'),
        ('MINimum', 'MINimum'),
        ('MAXimum', 'MAXimum'),
        ('DEFault', 'DEFault'),
        ('0', '0'),
    ]
    out = _setpoint_experiment(c, 'CURRent', steps, ir)
    c.finding(9, 'CURRent CH%d: %s' % (c.ch, '; '.join('%s -> %s' % kv for kv in out.items())))


@experiment(12, 'ovp', WRITE, (9, 10))
def exp_ovp(c: Ctx) -> None:
    """OVP set/read-back, out-of-range values, interaction with the voltage setpoint.

    Open question 9 (clamping vs error for OVP outside 0.1-1.1 x rated, MIN/MAX/DEF)
    and 10 (Interaction: OVP below the set voltage, voltage above OVP). Output off.
    """
    c.require_outputs_off()
    c.require_independent()
    n = c.ch
    rating = c.rating
    if not rating:
        raise Skip('unknown model; no rating to derive test values from')
    vr = rating[0]
    steps = [
        ('0.5 x rated', '%g' % (0.5 * vr)),
        ('1.1 x rated', '%g' % round(1.1 * vr, 3)),
        ('1.2 x rated (above range)', '%g' % round(1.2 * vr, 3)),
        ('0.05 x rated (below range)', '%g' % round(0.05 * vr, 3)),
        ('MAXimum', 'MAXimum'),
        ('MINimum', 'MINimum'),
        ('DEFault', 'DEFault'),
    ]
    out = _setpoint_experiment(c, 'OVP', steps, round(1.1 * vr, 3))
    c.finding(9, 'OVP CH%d: %s' % (n, '; '.join('%s -> %s' % kv for kv in out.items())))
    # Interaction A: OVP below the current voltage setpoint.
    vhi, ovp_lo = '%g' % round(0.7 * vr, 3), '%g' % round(0.4 * vr, 3)
    c.w('OVP CH%d,MAXimum' % n)
    c.w('VOLTage CH%d,%s' % (n, vhi))
    r_ovp = c.setq('OVP CH%d,%s' % (n, ovp_lo), 'OVP? CH%d' % n)
    r_v = c.q('VOLTage? CH%d' % n)
    c.finding(
        10,
        'OVP set to %s while VOLTage=%s: OVP reads %r, VOLTage now %r' % (ovp_lo, vhi, r_ovp, r_v),
    )
    # Interaction B: voltage above a low OVP.
    c.w('VOLTage CH%d,0' % n)
    c.w('OVP CH%d,%s' % (n, ovp_lo))
    r_v2 = c.setq('VOLTage CH%d,%s' % (n, vhi), 'VOLTage? CH%d' % n)
    r_ovp2 = c.q('OVP? CH%d' % n)
    c.finding(
        10,
        'VOLTage %s requested while OVP=%s: VOLTage reads %r, OVP reads %r'
        % (vhi, ovp_lo, r_v2, r_ovp2),
    )


@experiment(13, 'ocp', WRITE, (5, 9, 10))
def exp_ocp(c: Ctx) -> None:
    """OCP set/read-back (format of the unprinted `OCP?` response), out-of-range, interaction.

    Open question 5 (Missing responses: `OCP?`), 9 (clamping vs error for OCP
    outside 0.1-1.1 x rated, MIN/MAX/DEF) and 10 (Interaction: OCP vs current
    setpoint). Output off.
    """
    if c.no_ocp:
        raise Skip(
            'OCP? gave no answer in the snapshot, so OCP could not be restored; OCP is never written (see Q5)'
        )
    c.require_outputs_off()
    c.require_independent()
    n = c.ch
    rating = c.rating
    if not rating:
        raise Skip('unknown model; no rating to derive test values from')
    ir = rating[1]
    steps = [
        ('0.5 x rated', '%g' % (0.5 * ir)),
        ('1.1 x rated', '%g' % round(1.1 * ir, 3)),
        ('1.2 x rated (above range)', '%g' % round(1.2 * ir, 3)),
        ('0.05 x rated (below range)', '%g' % round(0.05 * ir, 3)),
        ('MAXimum', 'MAXimum'),
        ('MINimum', 'MINimum'),
        ('DEFault', 'DEFault'),
    ]
    out = _setpoint_experiment(c, 'OCP', steps, round(1.1 * ir, 3))
    c.finding(9, 'OCP CH%d: %s' % (n, '; '.join('%s -> %s' % kv for kv in out.items())))
    c.finding(5, '`OCP? CH%d` reply format: %r' % (n, c.link.txns[-1].raw if c.link.txns else None))
    ihi, ocp_lo = '%g' % round(0.7 * ir, 3), '%g' % round(0.4 * ir, 3)
    c.w('OCP CH%d,MAXimum' % n)
    c.w('CURRent CH%d,%s' % (n, ihi))
    r_ocp = c.setq('OCP CH%d,%s' % (n, ocp_lo), 'OCP? CH%d' % n)
    r_i = c.q('CURRent? CH%d' % n)
    c.finding(
        10,
        'OCP set to %s while CURRent=%s: OCP reads %r, CURRent now %r' % (ocp_lo, ihi, r_ocp, r_i),
    )


@experiment(14, 'ocp_state_delay', WRITE, (4, 7, 9))
def exp_ocp_state_delay(c: Ctx) -> None:
    """OCP:STATe and OCP:DELay set/read-back, accepted spellings and ranges.

    Open question 4 (Responses: `1`/`0` and 6-decimal delay), 7 (Case/forms:
    `ON`/`OFF` words, space after the comma as in the manual's
    `OCP:STATe CH1, 1`) and 9 (delay outside 0-3600 s, MIN/MAX/DEF). Output off.
    """
    c.require_outputs_off()
    c.require_independent()
    n = c.ch
    out = []
    for label, cmd in [
        ('1', 'OCP:STATe CH%d,1'),
        ('0', 'OCP:STATe CH%d,0'),
        ('ON', 'OCP:STATe CH%d,ON'),
        ('OFF', 'OCP:STATe CH%d,OFF'),
        ('`1` with space after comma', 'OCP:STATe CH%d, 1'),
    ]:
        r = c.setq(cmd % n, 'OCP:STATe? CH%d' % n)
        out.append('%s -> %r' % (label, r))
    c.finding(7, 'OCP:STATe spellings (read-back): %s' % '; '.join(out))
    steps = [
        ('0.5 s', '0.5'),
        ('1.2345 s (resolution)', '1.2345'),
        ('3600 s', '3600'),
        ('3601 s (above range)', '3601'),
        ('-1 s', '-1'),
        ('MAXimum', 'MAXimum'),
        ('MINimum', 'MINimum'),
        ('DEFault', 'DEFault'),
        ('0', '0'),
    ]
    res = _setpoint_experiment(c, 'OCP:DELay', steps, 3600.0)
    c.finding(9, 'OCP:DELay CH%d: %s' % (n, '; '.join('%s -> %s' % kv for kv in res.items())))
    c.finding(4, 'OCP:DELay read-back of 1.2345 -> %s' % res.get('1.2345 s (resolution)'))


@experiment(15, 'track', WRITE, (10, 13, 14))
def exp_track(c: Ctx) -> None:
    """OUTPut:TRACK: words vs numbers, what the query returns, side effects on CH2/CH3.

    Open question 13 (`OUTPut:TRACK` mapping: 1 = series? 2 = parallel? query
    returns number or word), 10 (OVP/OCP re-initialised when switching
    series/parallel) and 14 (MAX voltage/current in series/parallel versus the
    rated table). Runs only while CH2 and CH3 outputs are off; restores the
    original mode with read-back.
    """
    c.require_outputs_off((2, 3))
    orig = c.q('OUTPut:TRACK?')
    if orig is None:
        raise Skip('OUTPut:TRACK? gave no answer')
    c.note('original track mode: %r' % orig)
    mapping: dict[str, str | None] = {}
    side: list[str] = []
    try:
        for word in ('SERIES', 'PARALLEL', 'INDEPENDENT'):
            r = c.setq('OUTPut:TRACK %s' % word, 'OUTPut:TRACK?')
            mapping[word] = r
            parts = []
            for n in (2, 3):
                parts.append(
                    'CH%d V=%s I=%s OVP=%s OCP=%s Vmax=%s Imax=%s'
                    % (
                        n,
                        c.q('VOLTage? CH%d' % n),
                        c.q('CURRent? CH%d' % n),
                        c.q('OVP? CH%d' % n),
                        c.q('OCP? CH%d' % n),
                        c.probe('VOLTage? CH%d,MAX' % n),
                        c.probe('CURRent? CH%d,MAX' % n),
                    )
                )
            side.append('after %s (reads %r): %s' % (word, r, ' | '.join(parts)))
        num: dict[str, str | None] = {}
        for k in ('1', '2', '0'):
            num[k] = c.setq('OUTPut:TRACK %s' % k, 'OUTPut:TRACK?')
    finally:
        try:
            c.w('OUTPut:TRACK %s' % orig)
            back = c.q('OUTPut:TRACK?')
            c.note('restored track mode, now reads %r (wanted %r)' % (back, orig))
        except Exception as exc:  # pragma: no cover - reported by the global restore too
            c.note('local track restore failed: %s' % exc)
    c.finding(13, 'OUTPut:TRACK word -> query reply: %s' % mapping)
    c.finding(13, 'OUTPut:TRACK number -> query reply: %s' % num)
    for line in side:
        c.finding(10, line)
    c.finding(
        14,
        'series/parallel MAX queries are in the lines above (manual: series 60 V/3.2 A, parallel 32 V/6.4 A on the SPD4323X)',
    )


@experiment(16, 'sense', WRITE, (13,))
def exp_sense(c: Ctx) -> None:
    """MODE CH2,4W / 2W and MODE? CH2.

    Open question 13 (`MODE` 0/1 versus 2W/4W mapping, what the query returns
    after setting with words). CH2 only, independent mode only, output off.
    """
    c.require_outputs_off((2, 3))
    t = c.q('OUTPut:TRACK?')
    if t is None or t.strip().upper() not in ('0', 'INDEPENDENT'):
        raise Skip('track mode is %r; 4W sense is not supported in series/parallel' % t)
    orig = c.q('MODE? CH2')
    if orig is None:
        raise Skip('MODE? CH2 gave no answer')
    res: dict[str, str | None] = {}
    try:
        for label, cmd in [
            ('4W', 'MODE CH2,4W'),
            ('2W', 'MODE CH2,2W'),
            ('1', 'MODE CH2,1'),
            ('0', 'MODE CH2,0'),
        ]:
            res[label] = c.setq(cmd, 'MODE? CH2')
    finally:
        c.w('MODE CH2,%s' % orig)
        c.note('restored sense mode, now reads %r (wanted %r)' % (c.q('MODE? CH2'), orig))
    c.finding(13, 'MODE CH2 argument -> `MODE? CH2` reply: %s (original %r)' % (res, orig))


@experiment(17, 'lock', WRITE, (12,))
def exp_lock(c: Ctx) -> None:
    """LOCK / LOCK? and whether remote writes still work while locked.

    Open question 12 (Remote lock: does the panel stay locked after the session,
    is LOCK 0 needed, does the lock interfere with OUTPut). The panel state must
    be looked at by a human: see the note printed at the end of the run.
    """
    c.require_outputs_off()
    c.require_independent()
    n = c.ch
    orig = c.q('LOCK?')
    c.finding(12, 'LOCK? at start of this experiment (after earlier remote traffic): %r' % orig)
    seq = {}
    seq['LOCK 1'] = c.setq('LOCK 1', 'LOCK?')
    seq['VOLTage while locked'] = c.setq('VOLTage CH%d,1.5' % n, 'VOLTage? CH%d' % n)
    seq['OUTPut? while locked'] = c.q('OUTPut? CH%d' % n)
    seq['LOCK 0'] = c.setq('LOCK 0', 'LOCK?')
    seq['LOCK ON'] = c.setq('LOCK ON', 'LOCK?')
    seq['LOCK OFF'] = c.setq('LOCK OFF', 'LOCK?')
    seq[':SOURce:LOCK:STATe 1'] = c.setq(':SOURce:LOCK:STATe 1', ':SOURce:LOCK:STATe?')
    seq['LOCK 0 again'] = c.setq('LOCK 0', 'LOCK?')
    c.finding(12, 'LOCK sequence (read-backs): %s' % seq)
    c.finding(
        12,
        'remote VOLTage write while locked: %s'
        % (
            'worked'
            if seq['VOLTage while locked'] and close_to(fnum(seq['VOLTage while locked']), 1.5)
            else 'did NOT take effect'
        ),
    )
    c.note(
        'ASK THE OWNER: after the run, is the front panel locked? (the tool restores LOCK to its original value last)'
    )


@experiment(18, 'opc_wai', WRITE, (1, 11))
def exp_opc_wai(c: Ctx) -> None:
    """*OPC?, *OPC, *WAI and set+query chains on one line.

    Open question 11 (Timing: is `*OPC?` meaningful, do `*WAI`/`*OPC` block) and
    1 (Termination: several commands on one line with `;`, set followed by query).
    Output off.
    """
    c.require_outputs_off()
    c.require_independent()
    n = c.ch
    r1 = c.q('*OPC?')
    c.finding(11, '`*OPC?` -> %r in %.1f ms (idle)' % (r1, c.link.last_ms))
    c.w('VOLTage CH%d,1.000' % n)
    r2 = c.q('*OPC?')
    c.finding(11, '`*OPC?` right after a VOLTage set -> %r in %.1f ms' % (r2, c.link.last_ms))
    c.w('*OPC')
    r3 = c.q('*ESR?')
    c.finding(
        11,
        '`*OPC` then `*ESR?` -> %r (bit 0 = operation complete if the register is implemented)'
        % r3,
    )
    c.w('*WAI')
    r4 = c.q('VOLTage? CH%d' % n)
    c.finding(11, '`*WAI` then `VOLTage?` -> %r in %.1f ms' % (r4, c.link.last_ms))
    r5 = c.q('VOLTage CH%d,1.250;VOLTage? CH%d' % (n, n))
    c.finding(1, '`VOLTage CHn,1.250;VOLTage? CHn` on one line -> reply %r' % r5)
    r6 = c.q('VOLTage CH%d,1.500;*OPC?' % n)
    c.finding(1, '`VOLTage CHn,1.500;*OPC?` on one line -> reply %r' % r6)
    c.note('voltage after the chains: %r' % c.q('VOLTage? CH%d' % n))


@experiment(19, 'error_reporting', WRITE, (6, 8))
def exp_errors(c: Ctx) -> None:
    """What *ESR?/*STB? show after deliberately invalid commands.

    Open question 6 (Errors: how are errors reported, which bits of `*ESR?` and
    `*STB?`) and 8 (Channel argument: what happens with `CH5`). Output off;
    `*CLS` is sent first so the registers start clean.
    """
    c.require_outputs_off()
    c.require_independent()
    n = c.ch
    vr = c.rating[0] if c.rating else None
    c.w('*CLS')
    base = (c.q('*ESR?'), c.q('*STB?'))
    c.w('VOLTage CH5,1')
    after_ch5 = (c.q('*ESR?'), c.q('*STB?'))
    c.w('*CLS')
    ok_before = (c.q('*ESR?'), c.q('*STB?'))
    c.w('VOLTage CH%d,abc' % n)
    after_arg = (c.q('*ESR?'), c.q('*STB?'))
    after_over = None
    if vr:
        c.w('*CLS')
        c.w('VOLTage CH%d,%g' % (n, round(vr * 1.25, 3)))
        after_over = (c.q('*ESR?'), c.q('*STB?'))
    c.w('*CLS')
    c.probe('FOOBar? CH1')
    after_unknown = (c.q('*ESR?'), c.q('*STB?'))
    c.finding(
        6,
        '(*ESR?, *STB?) after *CLS: %r; after `VOLTage CH5,1`: %r; after `VOLTage CHn,abc`: %r; after value 125%% of rating: %r; after unknown query `FOOBar?`: %r'
        % (base, after_ch5, after_arg, after_over, after_unknown),
    )
    changed = [
        name
        for name, v in [
            ('CH5', after_ch5),
            ('bad argument', after_arg),
            ('over-range', after_over),
            ('unknown query', after_unknown),
        ]
        if v and v != base
    ]
    if base[0] is None:
        c.finding(
            6, '*ESR? gave no answer after *CLS; no conclusion about error reporting possible'
        )
    else:
        c.finding(
            6,
            'invalid input changes the status registers: %s'
            % (changed or 'no, errors are silent as far as these registers go'),
        )
    if base[0] is not None:
        c.finding(
            8,
            '`VOLTage CH5,1` was %s by the status registers'
            % ('flagged' if after_ch5 != base else 'not flagged'),
        )
    c.note('ESR/STB after a plain *CLS: %r (reference for the above)' % (ok_before,))


@experiment(20, 'set_forms', WRITE, (7,))
def exp_set_forms(c: Ctx) -> None:
    """Spellings of the voltage SET command, verified by read-back.

    Open question 7 (Case/forms: leading colon, `:SOURce:` prefix, `:SET` node,
    short forms, lower case, space after the comma). Each form writes a distinct
    value after the setpoint was reset to 0.5 V. Output off. A command without a
    channel is deliberately not tried as a write: it might hit another channel.
    """
    c.require_outputs_off()
    c.require_independent()
    n = c.ch
    forms = [
        ':SOURce:VOLTage:SET CH{n},1.1',
        'SOURce:VOLTage CH{n},1.2',
        'VOLTage:SET CH{n},1.3',
        'VOLT CH{n},1.4',
        'volt ch{n},1.5',
        'VOLTage CH{n}, 1.6',
        'VOLT:SET CH{n},1.7',
        ':VOLTage CH{n},1.8',
        'VOLTage CH{n} ,1.9',
    ]
    res = []
    for form in forms:
        cmd = form.format(n=n)
        want = float(cmd.rsplit(',', 1)[1])
        c.w('VOLTage CH%d,0.5' % n)
        r = c.setq(cmd, 'VOLTage? CH%d' % n)
        res.append((cmd, 'ACCEPTED' if close_to(fnum(r), want) else 'NOT applied', r))
    c.finding(7, 'set forms: %s' % '; '.join('`%s` %s (%s)' % row for row in res))
    c.block(
        '| set command | result | read-back |\n|---|---|---|\n'
        + '\n'.join('| `%s` | %s | `%r` |' % row for row in res)
    )


# ---------------------------------------------------------------------------
# Experiment: output on (opt-in)
# ---------------------------------------------------------------------------


@experiment(30, 'output_settling', OUTPUT, (11,), flag='allow_output')
def exp_output_settling(c: Ctx) -> None:
    """Output ON at 1.0 V / 0.1 A, no load: settling curve, run mode, OFF.

    Open question 11 (Timing/settling: how long after `OUTPut CHn,1` until the
    output is at voltage, is `*OPC?` meaningful for output-on, measurement refresh
    when polled every 50 ms; what `MEASure:RUN:MODE?` returns). Only runs with
    --allow-output --confirm-no-load. Always followed by OUTPut off, a wait until
    OUTPut? reads 0 and the snapshot restore.
    """
    n = c.ch
    c.require_independent()
    if c.outputs_on((n,)):
        raise Skip('CH%d output is on or unreadable before the test' % n)
    c.require_outputs_off((2, 3) if n in (2, 3) else ())
    v_set, i_set = 1.0, 0.1
    c.w('VOLTage CH%d,%.3f' % (n, v_set))
    c.w('CURRent CH%d,%.3f' % (n, i_set))
    rv, ri = fnum(c.q('VOLTage? CH%d' % n)), fnum(c.q('CURRent? CH%d' % n))
    if not (close_to(rv, v_set, 5e-3) and close_to(ri, i_set, 5e-3)):
        raise Skip('setpoints did not read back (%r V, %r A); refusing to switch on' % (rv, ri))
    on_delay = c.q('OUTPut:ON:DELay? CH%d' % n)
    off_delay = c.q('OUTPut:OFF:DELay? CH%d' % n)
    c.note('ON delay %r, OFF delay %r (non-zero values distort the curve)' % (on_delay, off_delay))
    pre_v, pre_i = c.q('MEASure:VOLTage? CH%d' % n), c.q('MEASure:CURRent? CH%d' % n)
    c.note('before ON: V=%r I=%r mode=%r' % (pre_v, pre_i, c.q('MEASure:RUN:MODE? CH%d' % n)))
    curve: list[tuple[float, float | None]] = []
    off_curve: list[tuple[float, float | None]] = []
    c.policy.on_allowed = {n}
    try:
        t_on = c.now()
        c.w('OUTPut CH%d,1' % n)
        first = c.q('MEASure:VOLTage? CH%d' % n)
        first_ms = (c.now() - t_on) * 1000
        opc = c.q('*OPC?')
        opc_ms = c.link.last_ms
        out_state = c.q('OUTPut? CH%d' % n)
        c.finding(
            11,
            'first MEASure:VOLTage? after `OUTPut CHn,1`: %r after %.0f ms; `*OPC?` -> %r in %.1f ms; OUTPut? -> %r'
            % (first, first_ms, opc, opc_ms, out_state),
        )
        curve.append((first_ms / 1000, fnum(first)))
        nxt = c.now() - t_on
        stable = 0
        while True:
            nxt += 0.05
            c.sleep(nxt - (c.now() - t_on))
            t = c.now() - t_on
            v = fnum(c.q('MEASure:VOLTage? CH%d' % n))
            curve.append((t, v))
            stable = stable + 1 if close_to(v, v_set, 0.02) else 0
            if t >= 3.0 or stable >= 10:
                break
        i_meas = c.q('MEASure:CURRent? CH%d' % n)
        p_meas = c.q('MEASure:POWER? CH%d' % n)
        mode = c.q('MEASure:RUN:MODE? CH%d' % n)
        c.finding(
            11, 'while ON, no load: I=%r P=%r `MEASure:RUN:MODE?` -> %r' % (i_meas, p_meas, mode)
        )
    finally:
        try:
            c.w('OUTPut CH%d,0' % n)
        finally:
            c.policy.on_allowed = set()
            st = None
            t_off = c.now()
            for _ in range(40):
                st = c.q('OUTPut? CH%d' % n)
                if st is not None and st.strip() in ('0', 'OFF'):
                    break
                c.sleep(0.25)
            c.note(
                'OUTPut? after off command reads %r (%.1f s after the command)'
                % (st, c.now() - t_off)
            )
    nxt = 0.0
    t0 = c.now()
    while nxt <= 1.0:
        c.sleep(nxt - (c.now() - t0))
        off_curve.append((c.now() - t0, fnum(c.q('MEASure:VOLTage? CH%d' % n))))
        nxt += 0.05
    c.finding(
        11,
        'after OFF: V=%r, I=%r, `MEASure:RUN:MODE?` -> %r'
        % (
            c.q('MEASure:VOLTage? CH%d' % n),
            c.q('MEASure:CURRent? CH%d' % n),
            c.q('MEASure:RUN:MODE? CH%d' % n),
        ),
    )
    valid = [(t, v) for t, v in curve if v is not None]
    if valid:
        within = next((t for t, v in valid if close_to(v, v_set, 0.02)), None)
        stable_t = next(
            (
                t
                for i, (t, v) in enumerate(valid)
                if all(close_to(w, v_set, 0.02) for _, w in valid[i:])
            ),
            None,
        )
        c.finding(
            11,
            'ON curve: first sample within 20 mV of %.1f V at %s s; stays within from %s s; peak %.3f V; last %.3f V; %d samples'
            % (
                v_set,
                '%.3f' % within if within is not None else 'never',
                '%.3f' % stable_t if stable_t is not None else 'never',
                max(v for _, v in valid),
                valid[-1][1],
                len(valid),
            ),
        )
    valid_off = [(t, v) for t, v in off_curve if v is not None]
    if valid_off:
        zero = next((t for t, v in valid_off if v <= 0.02), None)
        c.finding(
            11,
            'OFF curve: first sample at or below 20 mV at %s s (starts %.3f V)'
            % ('%.3f' % zero if zero is not None else 'never', valid_off[0][1]),
        )
    c.block(
        'ON curve (t s, V):\n\n```\n'
        + '\n'.join('%.3f  %s' % (t, v) for t, v in curve)
        + '\n```\n\nOFF curve (t s, V):\n\n```\n'
        + '\n'.join('%.3f  %s' % (t, v) for t, v in off_curve)
        + '\n```'
    )


EXPERIMENTS.sort(key=lambda e: e.num)


# ---------------------------------------------------------------------------
# Selection, run, report
# ---------------------------------------------------------------------------


def parse_numlist(text: str | None) -> set[int]:
    return {int(x) for x in re.split(r'[,\s]+', text.strip()) if x} if text else set()


def selected(args: argparse.Namespace) -> list[tuple[Experiment, str]]:
    """(experiment, '' if enabled else reason it is disabled)."""
    only, skip = parse_numlist(args.only), parse_numlist(args.skip)
    out = []
    for e in EXPERIMENTS:
        reason = ''
        if only and e.num not in only:
            reason = 'not in --only'
        elif e.num in skip:
            reason = 'in --skip'
        elif e.tier == WRITE and args.read_only:
            reason = '--read-only'
        elif e.tier == OUTPUT and not (args.allow_output and args.confirm_no_load):
            reason = 'needs --allow-output and --confirm-no-load'
        elif e.flag and not getattr(args, e.flag, False):
            reason = 'needs --%s' % e.flag.replace('_', '-')
        out.append((e, reason))
    return out


def open_resource(args: argparse.Namespace, dry: bool) -> tuple[Any, Callable[[], None]]:
    if dry:
        return DryResource(), lambda: None
    if args.fake:
        from siglent_spd_openhtf.fake_resource import FakeSpdResource

        return FakeSpdResource(), lambda: None
    try:
        import pyvisa
    except ImportError as exc:
        raise SystemExit(
            'pyvisa is not installed (uv pip install -e .[dev]); --help and --dry-run work without it: %s'
            % exc
        ) from exc
    rm = pyvisa.ResourceManager('@py')
    res = rm.open_resource(args.resource, open_timeout=5000)
    res.timeout = args.timeout_ms
    res.read_termination = '\n'
    res.write_termination = args.term
    return res, rm.close


def parse_term(text: str) -> str:
    table = {'\\n': '\n', '\n': '\n', 'lf': '\n', '\\r\\n': '\r\n', '\r\n': '\r\n', 'crlf': '\r\n'}
    if text.lower() not in table and text not in table:
        raise argparse.ArgumentTypeError('use \\n or \\r\\n')
    return table.get(text, table.get(text.lower()))  # type: ignore[return-value]


def redact(text: str, secrets: list[str]) -> str:
    for s in sorted({x for x in secrets if x}, key=len, reverse=True):
        text = text.replace(s, '<redacted>')
    return text


def md_escape(text: str) -> str:
    return text.replace('|', '\\|').replace('\n', ' ')


def run_experiments(
    c: Ctx, plan: list[tuple[Experiment, str]], results: list[ExpResult], out: Callable[[str], None]
) -> None:
    for exp, reason in plan:
        res = ExpResult(exp)
        results.append(res)
        if reason:
            res.status = 'skipped'
            res.error = reason
            continue
        c.cur = res
        res.txn_range = (len(c.link.txns), len(c.link.txns))
        out('--- experiment %d: %s' % (exp.num, exp.title))
        try:
            exp.fn(c)
            res.status = 'done'
        except Skip as exc:
            res.status = 'skipped'
            res.error = str(exc)
            out('    skipped: %s' % exc)
        except SafetyViolation as exc:
            res.status = 'error'
            res.error = 'SAFETY POLICY REFUSED A COMMAND (tool bug): %s' % exc
            out('    !!! ' + res.error)
        except KeyboardInterrupt:
            res.status = 'error'
            res.error = 'interrupted'
            raise
        except Exception as exc:
            res.status = 'error'
            res.error = '%s: %s' % (type(exc).__name__, exc)
            res.notes.append('traceback: ' + traceback.format_exc().strip().splitlines()[-3:][0])
            out('    error: %s' % res.error)
        finally:
            res.txn_range = (res.txn_range[0], len(c.link.txns))
        if exp.tier in (WRITE, OUTPUT) and c.snapshot:
            # Put CH-level state back after every write experiment so the next one starts clean.
            try:
                chans = write_channels(c)
                items = restore_snapshot(c, c.snapshot, chans)
                failed = [i for i in items if i.status == 'FAILED']
                if failed:
                    res.notes.append(
                        'local restore FAILED for: '
                        + ', '.join(
                            '%s (wanted %r, now %r)' % (i.name, i.orig, i.now) for i in failed
                        )
                    )
                    out('    !!! could not restore: %s' % ', '.join(i.name for i in failed))
            except SafetyViolation:
                raise
            except Exception as exc:
                res.notes.append('local restore error: %s' % exc)


def write_channels(c: Ctx) -> list[int]:
    chans = {c.ch}
    chans |= {2, 3} if any(e.num in (15, 16) for e, r in selected(c.args) if not r) else set()
    return sorted(chans)


def render_report(
    c: Ctx, args: argparse.Namespace, results: list[ExpResult], safety: dict[str, Any]
) -> str:
    L: list[str] = []
    a = L.append
    a('# Hardware acceptance report')
    a('')
    a('- Generated: %s' % dt.datetime.now(dt.UTC).strftime('%Y-%m-%d %H:%M:%S UTC'))
    a(
        "- Tool: `tools/hw_acceptance.py`; resource `%s`; command terminator `%r`, read termination `'\\n'`"
        % ('<fake/dry-run>' if (c.dry or args.fake) else args.resource, args.term)
    )
    a('- Instrument: `%s`' % (c.idn or 'not identified'))
    a(
        '- Mode: %s'
        % (
            'no-output mode (the tool never sends output ON)'
            if not (args.allow_output and args.confirm_no_load)
            else 'output experiment enabled (CH%d, 1.0 V / 0.1 A, no load)' % c.ch
        )
    )
    a('- Target channel for write experiments: CH%d' % c.ch)
    a('- Plug package importable: %s' % safety.get('plug', 'unknown'))
    a(
        '- Redaction: host and serial number replaced by `<redacted>` (public repository); the `.local.` log keeps everything.'
    )
    a('')
    a('## Safety log')
    a('')
    for line in safety.get('lines', []):
        a('- ' + line)
    if safety.get('snapshot_table'):
        a('')
        a('Snapshot taken before the first write:')
        a('')
        a('```')
        L.extend(safety['snapshot_table'])
        a('```')
    if safety.get('restore'):
        a('')
        a('Restore at the end (`unchanged` = already equal, nothing written):')
        a('')
        a('| item | wanted | now | status |')
        a('|---|---|---|---|')
        for it in safety['restore']:
            a(
                '| %s | `%s` | `%s` | %s |'
                % (it.name, it.orig, it.now, ('**FAILED**' if it.status == 'FAILED' else it.status))
            )
    a('')
    a('## Experiment summary')
    a('')
    a('| # | experiment | tier | open questions | status | note |')
    a('|---|---|---|---|---|---|')
    for r in results:
        e = r.exp
        a(
            '| %d | %s | %s | %s | %s | %s |'
            % (
                e.num,
                md_escape(e.title),
                e.tier,
                ', '.join(map(str, e.questions)) or '-',
                r.status,
                md_escape(r.error),
            )
        )
    a('')
    a('## Findings by open question (docs/scpi_reference.md section 8)')
    a('')
    by_q: dict[int, list[tuple[int, str]]] = {}
    for r in results:
        for q, text in r.findings:
            by_q.setdefault(q, []).append((r.exp.num, text))
    ran = {r.exp.num for r in results if r.status == 'done'}
    for q in range(1, 20):
        a('### Q%d %s' % (q, Q_TITLES[q]))
        a('')
        covering = [e.num for e in EXPERIMENTS if q in e.questions]
        ran_cov = [n for n in covering if n in ran]
        if q in STATIC_COVERAGE:
            a('*Coverage: %s.*' % STATIC_COVERAGE[q])
            a('')
        a('Experiments: %s; ran: %s.' % (covering or 'none', ran_cov or 'none'))
        a('')
        for num, text in by_q.get(q, []):
            a('- (E%d) %s' % (num, text))
        if not by_q.get(q):
            a('- no finding recorded')
        a('')
    a('## Experiment details')
    a('')
    for r in results:
        e = r.exp
        a('### E%d %s (%s)' % (e.num, e.key, r.status))
        a('')
        a(e.doc)
        a('')
        if r.error:
            a('**%s**' % r.error)
            a('')
        for n in r.notes:
            a('- ' + n)
        if r.notes:
            a('')
        for b in r.blocks:
            a(b)
            a('')
        lo, hi = r.txn_range
        if hi > lo:
            a('Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):')
            a('')
            a('```')
            a('\n'.join(t.line() for t in c.link.txns[lo:hi]))
            a('```')
            a('')
    return redact('\n'.join(L) + '\n', c.secrets)


def print_plan(
    args: argparse.Namespace,
    plan: list[tuple[Experiment, str]],
    per_exp: dict[int, list[str]] | None,
) -> None:
    print('hw_acceptance --dry-run: nothing is connected, nothing is sent to an instrument.')
    host = os.environ.get('PSU_HOST', '<PSU_HOST unset>')
    print('resource : %s' % (args.resource or 'TCPIP::%s::%d::SOCKET' % (host, args.port)))
    print(
        'terminator: %r   timeout %d ms   report -> %s   snapshot -> %s'
        % (args.term, args.timeout_ms, args.report, args.snapshot_file)
    )
    print(
        'mode     : %s'
        % (
            'OUTPUT experiment enabled (CH%d)' % args.channel
            if args.allow_output and args.confirm_no_load
            else 'no-output mode (never sends OUTPut ON)'
        )
    )
    print('channel  : CH%d for write experiments' % args.channel)
    print('')
    print(
        'Preflight (always): *IDN? -> refuse unless SPD4xxx; OUTPut? CH1..CH4 + OUTPut:ALL? -> refuse if any is on;'
    )
    print(
        '                    read-only snapshot of all channels -> %s -> then writes are enabled.'
        % args.snapshot_file
    )
    print(
        'Finally  : any output this run switched on is switched off with read-back, the snapshot is restored with read-back,'
    )
    print('           failures are reported, outputs are queried once more.')
    print('')
    print('%-3s %-16s %-7s %-10s %s' % ('#', 'experiment', 'tier', 'questions', 'status / title'))
    for e, reason in plan:
        state = 'ENABLED ' if not reason else 'disabled (%s)' % reason
        print(
            '%-3d %-16s %-7s %-10s %s: %s'
            % (e.num, e.key, e.tier, ','.join(map(str, e.questions)) or '-', state, e.title)
        )
        if per_exp and e.num in per_exp:
            for line in per_exp[e.num]:
                print('        ' + line)
    print('')
    print(
        'Blocked for every string (SafetyPolicy): *RST, DEFault:RESET, FACTory:RESET, LAN/DHCP/GPIB, STORage, CALibrate, WAVE, LIST;'
    )
    print(
        "writes only with an allow-listed header; 'OUTPut:ALL 1' never; 'OUTPut CHn,1' only inside the output experiment."
    )


def dry_plan(args: argparse.Namespace) -> int:
    """Run every enabled experiment against DryResource to list the exact commands."""
    policy = SafetyPolicy()
    policy.allow_selftest = args.allow_selftest
    link = Link(DryResource(), policy, None)
    c = Ctx(link, args, policy, dry=True)
    c.model = 'SPD4323X'
    c.idn = 'Siglent Technologies,SPD4323X,SPD4XXXXXXXXXX,1.0.0.0'
    plan = selected(args)
    c.snapshot = take_snapshot(c)
    policy.writes_enabled = True
    results: list[ExpResult] = []
    sink: list[str] = []
    run_experiments(c, [(e, r) for e, r in plan], results, sink.append)
    per: dict[int, list[str]] = {}
    for r in results:
        if r.status == 'skipped' and r.error and r.exp.num in {e.num for e, rr in plan if not rr}:
            per[r.exp.num] = ['(would be skipped here: %s)' % r.error]
            continue
        lo, hi = r.txn_range
        lines: list[str] = []
        last, count = None, 0
        for t in link.txns[lo:hi]:
            if t.kind == 'LATE':
                continue
            cur = ('W ' if t.kind == 'W' else 'Q ') + t.cmd
            if cur == last:
                count += 1
                continue
            if last is not None:
                lines.append(last + (' (x%d)' % count if count > 1 else ''))
            last, count = cur, 1
        if last is not None:
            lines.append(last + (' (x%d)' % count if count > 1 else ''))
        cap = 6 if r.exp.tier == READ else 80
        per[r.exp.num] = lines[:cap] + (
            ['... %d more distinct commands' % (len(lines) - cap)] if len(lines) > cap else []
        )
    print_plan(args, plan, per)
    bad = [r for r in results if r.error.startswith('SAFETY')]
    print('')
    print(
        'policy check over all planned commands: %s'
        % ('FAILED in experiment(s) %s' % [r.exp.num for r in bad] if bad else 'passed')
    )
    return 1 if bad else 0


def emit(line: str) -> None:
    print(line, flush=True)


def main_run(args: argparse.Namespace) -> int:
    policy = SafetyPolicy()
    policy.allow_selftest = args.allow_selftest
    try:
        res, close_rm = open_resource(args, dry=False)
    except SystemExit:
        raise
    except Exception as exc:
        print('cannot open the resource: %s: %s' % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    link = Link(res, policy, args.log)
    c = Ctx(link, args, policy)
    host = os.environ.get('PSU_HOST', '')
    c.secrets = [host]
    results: list[ExpResult] = []
    safety: dict[str, Any] = {'lines': []}
    sl: list[str] = safety['lines']
    exit_code = 0
    plan = selected(args)
    try:
        plug_ok = True
        try:
            import siglent_spd_openhtf  # noqa: F401
        except Exception:
            plug_ok = False
        safety['plug'] = 'yes' if plug_ok else 'no (direct pyvisa only)'

        # --- preflight: identity -------------------------------------------
        emit('== preflight')
        try:
            idn = link.query('*IDN?')
        except QueryFailed as exc:
            print(
                "no answer to *IDN?: %s\nCheck PSU_HOST/port forward and try --term '\\r\\n'."
                % exc,
                file=sys.stderr,
            )
            return 2
        c.idn = idn
        parts = [p.strip() for p in idn.split(',')]
        c.model = parts[1].upper() if len(parts) > 1 else None
        c.serial = parts[2] if len(parts) > 2 else ''
        c.secrets.append(c.serial)
        c.idn = redact(idn, [c.serial])
        emit('   instrument: %s' % idn)
        if not (c.model or '').startswith('SPD4'):
            msg = 'refusing: *IDN? does not name an SPD4xxx model (%r)' % c.model
            sl.append(msg)
            emit('   ' + msg)
            return 3
        if c.model not in RATINGS:
            sl.append(
                'model %s not in the local rating table: above-rating tests are skipped' % c.model
            )
        # --- preflight: outputs --------------------------------------------
        states = {n: link_q(c, 'OUTPut? CH%d' % n) for n in (1, 2, 3, 4)}
        all_state = link_q(c, 'OUTPut:ALL?')
        sl.append('output states at start: %s; OUTPut:ALL? -> %r' % (states, all_state))
        emit('   outputs at start: %s, OUTPut:ALL? -> %r' % (states, all_state))
        on = [n for n, s in states.items() if s is None or s.strip() not in ('0', 'OFF')]
        if on and not args.i_know_outputs_are_on:
            msg = (
                'REFUSING TO CONTINUE: output of CH%s is on or could not be read. Switch it off at the instrument, or '
                'pass --i-know-outputs-are-on if that is intended.' % ','.join(map(str, on))
            )
            sl.append(msg)
            emit('   ' + msg)
            return 3
        if on:
            sl.append(
                'WARNING: --i-know-outputs-are-on given; outputs on: CH%s' % ','.join(map(str, on))
            )

        # --- snapshot --------------------------------------------------------
        needs_write = any(not r and e.tier in (WRITE, OUTPUT) for e, r in plan)
        if needs_write:
            emit('== snapshot (read-only)')
            existing = None
            if os.path.exists(args.snapshot_file):
                try:
                    existing = json.load(open(args.snapshot_file, encoding='utf-8'))
                except Exception:
                    existing = {'status': 'unreadable'}
            if existing and existing.get('status') != 'restored' and not args.overwrite_snapshot:
                msg = (
                    'REFUSING: %s exists and its status is %r, i.e. an earlier run did not finish restoring. It holds the original '
                    "values. Run 'hw_acceptance.py --restore-snapshot' first (or pass --overwrite-snapshot)."
                    % (args.snapshot_file, existing.get('status'))
                )
                sl.append(msg)
                emit('   ' + msg)
                return 3
            c.snapshot = take_snapshot(c)
            for line in snapshot_table(c.snapshot):
                emit('   ' + line)
            chans = write_channels(c)
            c.no_ocp = any(c.snapshot['channels'][str(n)].get('ocp') is None for n in chans)
            if c.no_ocp:
                sl.append(
                    'OCP? CHn gave no answer: OCP cannot be read back or restored, so it is never written (experiment 13 disabled)'
                )
            missing = [
                (n, f)
                for n in chans
                for f in CORE_FIELDS
                if f != 'ocp' and c.snapshot['channels'][str(n)].get(f) is None
            ]
            if missing:
                msg = 'REFUSING: cannot snapshot %s; would not be able to restore' % missing
                sl.append(msg)
                emit('   ' + msg)
                return 3
            save_json(
                args.snapshot_file,
                {
                    'status': 'taken',
                    'taken_at': dt.datetime.now().isoformat(timespec='seconds'),
                    'model': c.model,
                    'channels_written': chans,
                    **c.snapshot,
                },
            )
            sl.append(
                'snapshot saved to %s before the first write (channels that may be written: %s)'
                % (args.snapshot_file, chans)
            )
            safety['snapshot_table'] = snapshot_table(c.snapshot)
            policy.writes_enabled = True

        emit('== experiments')
        try:
            run_experiments(c, plan, results, emit)
        except KeyboardInterrupt:
            sl.append('INTERRUPTED by the user; restoring')
            emit('interrupted, restoring')
        except BaseException:
            sl.append(
                'unexpected failure in the runner, restoring: '
                + traceback.format_exc().strip().splitlines()[-1]
            )
            raise
        finally:
            exit_code = shutdown(c, args, safety, results)
        errors = [r for r in results if r.status == 'error']
        if errors and exit_code == 0:
            exit_code = 1
    finally:
        report_text = render_report(c, args, results, safety)
        try:
            Path(args.report).write_text(report_text, encoding='utf-8')
            emit('report written to %s' % args.report)
        except OSError as exc:
            emit('could not write the report: %s' % exc)
        link.close()
        close_rm()
    emit('')
    emit('FINISHED. Look at the instrument front panel now: is it locked? (open question 12)')
    return exit_code


def link_q(c: Ctx, cmd: str) -> str | None:
    return c.q(cmd)


def shutdown(
    c: Ctx, args: argparse.Namespace, safety: dict[str, Any], results: list[ExpResult]
) -> int:
    """Outputs off, restore snapshot, final output check. Never raises."""
    sl = safety['lines']
    code = 0
    emit('== shutdown: outputs off, restore')
    c.policy.on_allowed = set()
    for n in sorted(c.policy.turned_on):
        try:
            c.link.write('OUTPut CH%d,0' % n)
            ok = False
            for _ in range(40):
                s = c.q('OUTPut? CH%d' % n)
                if s is not None and s.strip() in ('0', 'OFF'):
                    ok = True
                    break
                c.sleep(0.25)
            sl.append(
                'CH%d was switched on by this run; output off %s'
                % (n, 'confirmed' if ok else 'NOT CONFIRMED')
            )
            if not ok:
                code = 4
        except Exception as exc:
            sl.append('CH%d: could not confirm output off: %s' % (n, exc))
            code = 4
    if c.snapshot:
        try:
            items = restore_snapshot(c, c.snapshot, write_channels(c))
            safety['restore'] = items
            failed = [i for i in items if i.status == 'FAILED']
            ok = not failed
            sl.append(
                'restore: %d items, %d written back, %d unchanged, %d skipped (not snapshotted), %d FAILED'
                % (
                    len(items),
                    sum(i.status == 'restored' for i in items),
                    sum(i.status == 'unchanged' for i in items),
                    sum(i.status == 'skipped' for i in items),
                    len(failed),
                )
            )
            for i in failed:
                msg = 'COULD NOT RESTORE %s: wanted %r, instrument reads %r' % (
                    i.name,
                    i.orig,
                    i.now,
                )
                sl.append(msg)
                emit('   !!! ' + msg)
            if failed:
                code = 4
            try:
                save_json(
                    args.snapshot_file,
                    {
                        **json.load(open(args.snapshot_file, encoding='utf-8')),
                        'status': 'restored' if ok else 'restore-incomplete',
                        'restored_at': dt.datetime.now().isoformat(timespec='seconds'),
                        'failed': [i.name for i in failed],
                    },
                )
            except Exception as exc:
                sl.append('could not update the snapshot file: %s' % exc)
        except Exception as exc:
            sl.append(
                'RESTORE RAISED %s: %s; the snapshot file %s still holds the original values'
                % (type(exc).__name__, exc, args.snapshot_file)
            )
            emit('   !!! restore failed: %s' % exc)
            code = 4
    final = {n: c.q('OUTPut? CH%d' % n) for n in (1, 2, 3, 4)}
    sl.append('output states at the end: %s' % final)
    emit('   outputs at the end: %s' % final)
    if c.policy.turned_on and any(
        s is None or s.strip() not in ('0', 'OFF')
        for n, s in final.items()
        if n in c.policy.turned_on
    ):
        sl.append(
            '!!! AN OUTPUT SWITCHED ON BY THIS RUN IS NOT CONFIRMED OFF: switch it off at the instrument'
        )
        emit('   !!! an output switched on by this run is not confirmed off')
        code = 4
    return code


def restore_mode(args: argparse.Namespace) -> int:
    """--restore-snapshot: put the values from the snapshot file back."""
    if not os.path.exists(args.snapshot_file):
        print('no snapshot file %s' % args.snapshot_file, file=sys.stderr)
        return 2
    data = json.load(open(args.snapshot_file, encoding='utf-8'))
    policy = SafetyPolicy()
    res, close_rm = open_resource(args, dry=False)
    link = Link(res, policy, args.log)
    c = Ctx(link, args, policy)
    try:
        if not args.i_know_outputs_are_on:
            on = c.outputs_on()
            if on:
                print(
                    'refusing: output of CH%s is on or unreadable (--i-know-outputs-are-on overrides)'
                    % on,
                    file=sys.stderr,
                )
                return 3
        policy.writes_enabled = True
        snap = {k: data[k] for k in ('channels', 'sense', 'track', 'lock')}
        chans = data.get('channels_written') or [1]
        items = restore_snapshot(c, snap, chans)
        for i in items:
            print('%-22s wanted %-12r now %-12r %s' % (i.name, i.orig, i.now, i.status))
        failed = [i for i in items if i.status == 'FAILED']
        data['status'] = 'restored' if not failed else 'restore-incomplete'
        save_json(args.snapshot_file, data)
        return 4 if failed else 0
    finally:
        link.close()
        close_rm()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description='Hardware acceptance run for the Siglent SPD4000X; writes a Markdown report. '
        'Default: no output mode (never switches an output on).',
        epilog='Environment: PSU_HOST = address of the supply (documentation example: 192.0.2.10).',
    )
    ap.add_argument(
        '--resource', default=None, help='VISA resource (default: TCPIP::$PSU_HOST::5025::SOCKET)'
    )
    ap.add_argument(
        '--port',
        type=int,
        default=PORT,
        help='socket port used to build the default resource (5025)',
    )
    ap.add_argument(
        '--term',
        type=parse_term,
        default='\n',
        help='write termination: \\n (default) or \\r\\n; reads always end at \\n',
    )
    ap.add_argument(
        '--timeout-ms',
        type=int,
        default=3000,
        help='VISA timeout for normal queries (default 3000)',
    )
    ap.add_argument(
        '--probe-timeout-ms',
        type=int,
        default=1500,
        help='timeout for probes that may never be answered (default 1500)',
    )
    ap.add_argument(
        '--channel',
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help='channel for write experiments (default 1; SPD4323X CH1 is 6 V / 3.2 A)',
    )
    ap.add_argument(
        '--report',
        default=DEFAULT_REPORT,
        help='Markdown report path (default ./%s)' % DEFAULT_REPORT,
    )
    ap.add_argument(
        '--snapshot-file',
        default=DEFAULT_SNAPSHOT,
        help='pre-write snapshot (default ./%s, git-ignored)' % DEFAULT_SNAPSHOT,
    )
    ap.add_argument(
        '--log',
        default=DEFAULT_LOG,
        help='raw transaction log, flushed per command (default ./%s, git-ignored)' % DEFAULT_LOG,
    )
    ap.add_argument(
        '--read-only',
        action='store_true',
        help='run only the read-only experiments (no writes at all)',
    )
    ap.add_argument('--only', help='comma-separated experiment numbers to run')
    ap.add_argument('--skip', help='comma-separated experiment numbers to skip')
    ap.add_argument(
        '--allow-output',
        action='store_true',
        help='enable experiment 30 (output ON, CH1 1.0 V / 0.1 A); needs --confirm-no-load',
    )
    ap.add_argument(
        '--confirm-no-load',
        action='store_true',
        help='you confirm NOTHING is connected to the output terminals',
    )
    ap.add_argument(
        '--i-know-outputs-are-on',
        action='store_true',
        help='continue although an output is on (writes then affect a live supply)',
    )
    ap.add_argument(
        '--allow-selftest',
        action='store_true',
        help='also send *TST? (runs the instrument self-test)',
    )
    ap.add_argument(
        '--try-vxi11',
        action='store_true',
        help='experiment 7: also open TCPIP::$PSU_HOST::INSTR (needs a direct LAN path)',
    )
    ap.add_argument(
        '--overwrite-snapshot',
        action='store_true',
        help='replace a snapshot file whose restore never completed (the original values are lost)',
    )
    ap.add_argument(
        '--restore-snapshot',
        action='store_true',
        help='only restore the values saved in the snapshot file, then exit',
    )
    ap.add_argument(
        '--fake',
        action='store_true',
        help='use siglent_spd_openhtf.fake_resource.FakeSpdResource instead of hardware',
    )
    ap.add_argument(
        '--dry-run',
        action='store_true',
        help='print the planned experiments and their commands; no connection',
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.allow_output and not args.confirm_no_load:
        ap.error(
            '--allow-output requires --confirm-no-load (nothing may be connected to the outputs)'
        )
    if args.confirm_no_load and not args.allow_output:
        print('note: --confirm-no-load has no effect without --allow-output', file=sys.stderr)
    if args.channel != 1:
        print('note: write experiments will use CH%d (default CH1)' % args.channel, file=sys.stderr)
    if args.dry_run:
        return dry_plan(args)
    if not args.resource:
        host = os.environ.get('PSU_HOST')
        if not host and not args.fake:
            ap.error('set PSU_HOST (e.g. export PSU_HOST=192.0.2.10) or pass --resource')
        args.resource = 'fake' if args.fake else 'TCPIP::%s::%d::SOCKET' % (host, args.port)
    if args.restore_snapshot:
        return restore_mode(args)
    return main_run(args)


if __name__ == '__main__':
    sys.exit(main())
