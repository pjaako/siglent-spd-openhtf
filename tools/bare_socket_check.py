#!/usr/bin/env python3
# ruff: noqa: UP031, E501  (percent-format and long message lines are deliberate in this operator tool)
"""Raw-socket sanity check for a Siglent SPD4000X on TCP port 5025 (stdlib only).

Run this FIRST, before tools/hw_acceptance.py. It uses no VISA layer, so what it
prints is exactly what the instrument put on the wire.

READ-ONLY BY CONSTRUCTION: every string is passed through ``assert_query``,
which refuses anything whose command header does not end in '?'. No set
command, no *RST, no *CLS, nothing under LAN/GPIB/STORage/CALibrate/WAVE/LIST
is ever sent. The only side effect on the instrument is the one the manual
announces: it may lock its front panel while it is remotely controlled.

Open questions of docs/scpi_reference.md section 8 that this tool answers (as
far as read-only queries allow):

  1 Termination       --term / --sweep-terms, ';' multi-command probe
  3 LAN               second concurrent connection test; --probe-ports (TCP
                      connect only) for web server / telnet / VXI-11 portmapper
  4 Responses         raw bytes of every query, decimals, units, '\\s', terminator
  5 Missing responses OCP? (the manual prints no response)
  6 Errors            *ESR? / *STB? before and after invalid queries (read-only)
  7 Case/forms        leading ':', ':SOURce:', short forms, bad abbreviations
  8 Channel argument  query without channel, CH0, CH5, bare '1'
  9 Keywords          'VOLTage? CH1,MAX' style queries (MIN, MAX, DEFault)
 14 Rated table       the same MAX queries on CH1..CH4

Usage:
  export PSU_HOST=192.0.2.10
  python3 tools/bare_socket_check.py --sweep-terms
  python3 tools/bare_socket_check.py --dry-run          # list queries, no network
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import sys
import time
from dataclasses import dataclass

DEFAULT_PORT = 5025
DEFAULT_LOG = 'bare_socket_check.local.log'  # '*.local.*' is git-ignored

TERM_ALIASES = {
    '\\n': '\n',
    '\n': '\n',
    'lf': '\n',
    '\\r\\n': '\r\n',
    '\r\n': '\r\n',
    'crlf': '\r\n',
    '\\r': '\r',
    '\r': '\r',
    'cr': '\r',
}


def parse_term(text: str) -> str:
    key = text.lower() if text.lower() in ('lf', 'crlf', 'cr') else text
    if key not in TERM_ALIASES:
        raise argparse.ArgumentTypeError('use \\n, \\r\\n (or lf, crlf); got %r' % text)
    return TERM_ALIASES[key]


def term_name(term: str) -> str:
    return {'\n': 'LF', '\r\n': 'CRLF', '\r': 'CR'}.get(term, repr(term))


# ---------------------------------------------------------------------------
# Read-only guard
# ---------------------------------------------------------------------------


class NotAQuery(Exception):
    """Raised before anything is sent when a string is not a pure query."""


def assert_query(cmd: str) -> None:
    """Refuse everything that is not a (possibly ';'-chained) query.

    Every ';'-separated segment must have a first token containing '?'. A set
    command such as 'VOLTage CH1,1' has no '?' in its header and is refused.
    """
    if '\n' in cmd or '\r' in cmd:
        raise NotAQuery('embedded line break in %r' % cmd)
    segments = [s.strip() for s in cmd.split(';')]
    if not cmd.strip() or any(not s for s in segments):
        raise NotAQuery('empty command or segment in %r' % cmd)
    for seg in segments:
        header = seg.split()[0]
        if '?' not in header:
            raise NotAQuery('refusing to send non-query %r (read-only tool)' % seg)
        if header.upper().startswith('*RST'):
            raise NotAQuery('refusing %r' % seg)


# ---------------------------------------------------------------------------
# Probe tables (all queries; edit with care, assert_query backs this up)
# ---------------------------------------------------------------------------

# (command, what it is)
CORE: list[tuple[str, str]] = [
    ('*IDN?', "identity (Q4: '\\s' on the wire, 4 fields)"),
    ('OUTPut? CH1', 'output state CH1'),
    ('OUTPut? CH2', 'output state CH2'),
    ('OUTPut? CH3', 'output state CH3'),
    ('OUTPut? CH4', 'output state CH4'),
    ('OUTPut:ALL?', 'all-channel output state (Q4: format undocumented)'),
    ('VOLTage? CH1', 'voltage setpoint'),
    ('CURRent? CH1', 'current setpoint'),
    ('OVP? CH1', 'OVP value'),
    ('OCP? CH1', 'OCP value (Q5: manual prints no response)'),
    ('OCP:STATe? CH1', 'OCP switch'),
    ('OCP:DELay? CH1', 'OCP delay'),
    ('OVP:PROTect:STATe? CH1', 'OVP tripped?'),
    ('OCP:PROTect:STATe? CH1', 'OCP tripped?'),
    ('MEASure:VOLTage? CH1', 'measured voltage'),
    ('MEASure:CURRent? CH1', 'measured current'),
    ('MEASure:POWER? CH1', 'measured power'),
    ('MEASure:RUN:MODE? CH1', 'CV/CC state'),
    ('OUTPut:TRACK?', 'CH2/CH3 coupling (number or word?)'),
    ('MODE? CH2', 'CH2 sense mode (number or word?)'),
    ('LOCK?', 'front panel lock'),
    ('*OPC?', 'operation complete'),
    ('*ESE?', 'event status enable'),
    ('*SRE?', 'service request enable'),
]

# Status registers are queried before and after the invalid probes (Q6).
STATUS_QUERIES = ['*ESR?', '*STB?']

# (label, command, reference core command or None, what the manual implies)
# manual: 'accept' = manual says valid, 'reject' = manual says error, '?' = unknown
FORMS: list[tuple[str, str, str | None, str]] = [
    ('leading colon', ':VOLTage? CH1', 'VOLTage? CH1', '?'),
    ('SOURce: prefix', 'SOURce:VOLTage? CH1', 'VOLTage? CH1', 'accept'),
    (':SOURce: prefix', ':SOURce:VOLTage? CH1', 'VOLTage? CH1', 'accept'),
    ('SOUR: short prefix', 'SOUR:VOLT? CH1', 'VOLTage? CH1', '?'),
    ('manual example :SOURce:VOLTage:SET?', ':SOURce:VOLTage:SET? CH1', 'VOLTage? CH1', 'accept'),
    ('VOLTage:SET? w/o SOURce', 'VOLTage:SET? CH1', 'VOLTage? CH1', 'accept'),
    ('short VOLT', 'VOLT? CH1', 'VOLTage? CH1', 'accept'),
    ('short VOLT:SET', 'VOLT:SET? CH1', 'VOLTage? CH1', 'accept'),
    ('lower case incl. ch1', 'volt? ch1', 'VOLTage? CH1', 'accept'),
    ('mixed case keyword', 'VolTaGe? CH1', 'VOLTage? CH1', 'accept'),
    ('bad abbreviation VOL', 'VOL? CH1', None, 'reject'),
    ('bad abbreviation VOLTAG', 'VOLTAG? CH1', None, 'reject'),
    ('short CURR', 'CURR? CH1', 'CURRent? CH1', 'accept'),
    ('short OUTP', 'OUTP? CH1', 'OUTPut? CH1', 'accept'),
    ('OUTPut:STATe', 'OUTPut:STATe? CH1', 'OUTPut? CH1', 'accept'),
    ('OUTP:STAT', 'OUTP:STAT? CH1', 'OUTPut? CH1', 'accept'),
    ('OCP:STAT', 'OCP:STAT? CH1', 'OCP:STATe? CH1', 'accept'),
    ('OCP:DEL', 'OCP:DEL? CH1', 'OCP:DELay? CH1', 'accept'),
    ('OVP:PROT:STAT', 'OVP:PROT:STAT? CH1', 'OVP:PROTect:STATe? CH1', 'accept'),
    ('MEAS:VOLT', 'MEAS:VOLT? CH1', 'MEASure:VOLTage? CH1', 'accept'),
    ('MEAS:CURR', 'MEAS:CURR? CH1', 'MEASure:CURRent? CH1', 'accept'),
    ('MEAS:POW (no short form printed)', 'MEAS:POW? CH1', 'MEASure:POWER? CH1', '?'),
    ('MEASure:POWer (mixed case)', 'MEASure:POWer? CH1', 'MEASure:POWER? CH1', '?'),
    ('MEAS:RUN:MODE', 'MEAS:RUN:MODE? CH1', 'MEASure:RUN:MODE? CH1', 'accept'),
    ('MEAS:MODE ([:RUN] omitted)', 'MEASure:MODE? CH1', 'MEASure:RUN:MODE? CH1', 'accept'),
    ('OUTP:TRAC (short TRACK?)', 'OUTP:TRAC?', 'OUTPut:TRACK?', '?'),
    ('LOCK:STATe', 'LOCK:STATe?', 'LOCK?', 'accept'),
    (':SOURce:LOCK:STATe (manual example)', ':SOURce:LOCK:STATe?', 'LOCK?', 'accept'),
    ('*IDN? lower case', '*idn?', '*IDN?', '?'),
    ('no space before channel', 'VOLTage?CH1', 'VOLTage? CH1', '?'),
    ('literal [:SET] brackets', 'VOLTage[:SET]? CH1', None, 'reject'),
    ("no channel (Q8: 'current channel'?)", 'VOLTage?', None, '?'),
    ('channel CH0 (Q8)', 'VOLTage? CH0', None, '?'),
    ('channel CH5 (Q8)', 'VOLTage? CH5', None, '?'),
    ("bare channel number '1' (Q8)", 'VOLTage? 1', None, '?'),
    ('parenthesised (CH1) (Q8)', 'VOLTage? (CH1)', None, '?'),
    ('channel arg on OUTPut:TRACK? (Q8)', 'OUTPut:TRACK? CH1', None, '?'),
    ('MODE? CH1 (manual: CH2/CH3 only)', 'MODE? CH1', None, 'reject'),
    ("two queries with ';' (Q1)", '*IDN?;*OPC?', None, '?'),
]

# Parameter keywords as queries (Q9, Q14). Not set commands.
PARAMS: list[tuple[str, str]] = [
    ('VOLTage? CH1,MAX', "implied by '{<value>|MINimum|MAXimum|DEFault}'"),
    ('VOLTage? CH1,MIN', ''),
    ('VOLTage? CH1,DEFault', ''),
    ('VOLTage? CH1,MAXimum', 'long keyword'),
    ('VOLTage? CH1, MAX', 'space after comma'),
    ('CURRent? CH1,MAX', ''),
    ('CURRent? CH1,MIN', ''),
    ('OVP? CH1,MAX', ''),
    ('OCP? CH1,MAX', ''),
    ('OCP:DELay? CH1,MAX', ''),
    ('OUTPut:ON:DELay? CH1,MAX', ''),
    ('VOLTage? CH2,MAX', 'CH2 rating (series/parallel changes it)'),
    ('CURRent? CH2,MAX', ''),
    ('VOLTage? CH3,MAX', ''),
    ('VOLTage? CH4,MAX', ''),
    ('CURRent? CH4,MAX', 'SPD4306X CH4 typo question (Q14)'),
]

PORTS = [
    (80, 'HTTP web server (Q3)'),
    (23, 'telnet (Q3)'),
    (111, 'ONC-RPC portmapper, used by VXI-11 (Q3)'),
    (5025, 'SCPI raw socket, in manual'),
]


# ---------------------------------------------------------------------------
# Output helper (stdout + log file)
# ---------------------------------------------------------------------------


class Out:
    def __init__(self, log_path: str | None):
        self.fh = open(log_path, 'a', encoding='utf-8') if log_path else None
        if self.fh:
            self.fh.write(
                '\n===== bare_socket_check %s =====\n' % time.strftime('%Y-%m-%d %H:%M:%S')
            )

    def p(self, text: str = '') -> None:
        print(text, flush=True)
        if self.fh:
            self.fh.write(text + '\n')
            self.fh.flush()

    def close(self) -> None:
        if self.fh:
            self.fh.close()


# ---------------------------------------------------------------------------
# Raw connection
# ---------------------------------------------------------------------------


@dataclass
class Result:
    cmd: str
    term: str
    sent: bytes
    received: bytes
    status: str  # ok | partial | timeout | closed | error
    t_first_ms: float | None
    t_done_ms: float
    late: bytes = b''
    error: str = ''

    @property
    def answered(self) -> bool:
        return bool(self.received)

    def line(self) -> str:
        if self.status == 'ok':
            tm = 'first=%.1fms done=%.1fms' % (self.t_first_ms or 0.0, self.t_done_ms)
        elif self.received:
            tm = 'first=%.1fms %s' % (self.t_first_ms or 0.0, self.status.upper())
        else:
            tm = '%s after %.0fms' % (self.status.upper(), self.t_done_ms)
        extra = '  late=%r' % self.late if self.late else ''
        err = '  (%s)' % self.error if self.error else ''
        return 'sent=%r  recv=%r  %s%s%s' % (self.sent, self.received, tm, extra, err)


class Connection:
    def __init__(self, host: str, port: int, term: str, grace: float, connect_timeout: float = 5.0):
        self.host, self.port, self.term, self.grace = host, port, term, grace
        self.sock = socket.create_connection((host, port), timeout=connect_timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _drain(self, quiet: float = 0.25) -> bytes:
        """Collect bytes that arrive late after a miss, so streams stay in step."""
        got = b''
        end = time.monotonic() + quiet
        while True:
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            self.sock.settimeout(remaining)
            try:
                chunk = self.sock.recv(4096)
            except (TimeoutError, OSError):
                break
            if not chunk:
                break
            got += chunk
            end = time.monotonic() + quiet
        return got

    def query(self, cmd: str, timeout: float, term: str | None = None) -> Result:
        assert_query(cmd)
        term = self.term if term is None else term
        sent = (cmd + term).encode('ascii')
        t0 = time.monotonic()
        buf = b''
        t_first: float | None = None
        t_last = t0
        status = 'timeout'
        error = ''
        try:
            self.sock.settimeout(timeout)
            self.sock.sendall(sent)
        except OSError as exc:
            return Result(cmd, term, sent, b'', 'error', None, 0.0, error=repr(exc))
        deadline = t0 + timeout
        complete_at: float | None = None
        while True:
            now = time.monotonic()
            limit = deadline if complete_at is None else min(deadline, complete_at + self.grace)
            if limit - now <= 0:
                break
            self.sock.settimeout(limit - now)
            try:
                chunk = self.sock.recv(4096)
            except TimeoutError:
                break
            except OSError as exc:
                status, error = 'error', repr(exc)
                break
            t_last = time.monotonic()
            if not chunk:
                status, error = 'closed', 'connection closed by peer'
                break
            if t_first is None:
                t_first = (t_last - t0) * 1000
            buf += chunk
            complete_at = t_last if buf.endswith(b'\n') else None
        if buf.endswith(b'\n'):
            status = 'ok'
        elif buf and status == 'timeout':
            status = 'partial'
        late = b''
        if status != 'ok':
            late = self._drain()
        t_done = ((t_last if buf else time.monotonic()) - t0) * 1000
        return Result(cmd, term, sent, buf, status, t_first, t_done, late, error)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_INT = re.compile(r'[-+]?\d+')
_DEC = re.compile(r'[-+]?\d*\.(\d+)(?:[eE][-+]?\d+)?')
_UNIT = re.compile(r'[-+]?\d*\.?\d+\s*[A-Za-z%]+')


def terminator_of(raw: bytes) -> str:
    if raw.endswith(b'\r\n'):
        return 'CRLF'
    if raw.endswith(b'\n'):
        return 'LF'
    if raw.endswith(b'\r'):
        return 'CR'
    return 'none'


def classify(raw: bytes) -> str:
    if not raw:
        return 'no reply'
    text = raw.decode('ascii', 'replace').strip()
    notes = []
    if '\\s' in text:
        notes.append('LITERAL backslash-s')
    body = text.splitlines()[0] if text.splitlines() else text
    if _INT.fullmatch(body):
        kind = 'integer'
    elif _DEC.fullmatch(body):
        kind = 'decimal, %d places' % len(_DEC.fullmatch(body).group(1))  # type: ignore[union-attr]
    elif _UNIT.fullmatch(body):
        kind = 'number WITH UNIT suffix'
    elif ',' in body:
        kind = 'comma list, %d fields' % (body.count(',') + 1)
    else:
        kind = 'text'
    if len(text.splitlines()) > 1:
        kind += ', %d lines' % len(text.splitlines())
    return '; '.join([kind] + notes)


def numbers_close(a: bytes, b: bytes) -> bool:
    if a == b:
        return True
    try:
        return abs(float(a.decode().strip()) - float(b.decode().strip())) <= 0.01
    except ValueError:
        return False


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    fmt = '  '.join('%%-%ds' % w for w in widths)
    out = [fmt % tuple(headers), fmt % tuple('-' * w for w in widths)]
    out += [fmt % tuple(r) for r in rows]
    return out


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def run_core(out: Out, conn: Connection, timeout: float, term: str) -> dict[str, Result]:
    out.p('')
    out.p('== Core queries, terminator %s ==' % term_name(term))
    results: dict[str, Result] = {}
    for cmd, _why in CORE:
        res = conn.query(cmd, timeout, term)
        results[cmd] = res
        out.p('%-26s %s' % (cmd, res.line()))
    return results


def run_status(out: Out, conn: Connection, timeout: float, label: str) -> dict[str, Result]:
    results = {}
    for cmd in STATUS_QUERIES:
        res = conn.query(cmd, timeout)
        results[cmd] = res
        out.p('[%s] %-8s %s' % (label, cmd, res.line()))
    return results


def run_forms(
    out: Out, conn: Connection, timeout: float, core: dict[str, Result]
) -> list[tuple[str, str, str, str, str]]:
    out.p('')
    out.p('== Forms (Q1, Q7, Q8): read-only queries, probe timeout %.1fs ==' % timeout)
    rows = []
    for label, cmd, ref, manual in FORMS:
        res = conn.query(cmd, timeout)
        out.p('%-34s %-26s %s' % (label, cmd, res.line()))
        if not res.answered:
            observed = 'SILENT'
        elif ref and ref in core and core[ref].answered:
            observed = (
                'OK, same as %s' % ref
                if numbers_close(res.received, core[ref].received)
                else 'OK, DIFFERENT'
            )
        else:
            observed = 'OK'
        rows.append((label, cmd, manual, observed, repr(res.received)))
    return rows


def run_params(out: Out, conn: Connection, timeout: float) -> list[tuple[str, str, str]]:
    out.p('')
    out.p('== Parameter keywords as queries (Q9, Q14), probe timeout %.1fs ==' % timeout)
    rows = []
    for cmd, _why in PARAMS:
        res = conn.query(cmd, timeout)
        out.p('%-28s %s' % (cmd, res.line()))
        rows.append((cmd, 'SILENT' if not res.answered else 'OK', repr(res.received)))
    return rows


def run_concurrency(
    out: Out, host: str, port: int, conn_a: Connection, timeout: float, term: str, grace: float
) -> tuple[str, list[str]]:
    """Q3: is a second simultaneous connection served?"""
    out.p('')
    out.p('== Second concurrent connection (Q3) ==')
    steps: list[str] = []

    def log(msg: str) -> None:
        steps.append(msg)
        out.p('  ' + msg)

    a1 = conn_a.query('*IDN?', timeout)
    log('A *IDN? before B opens: %s' % a1.status)
    try:
        conn_b = Connection(host, port, term, grace)
    except OSError as exc:
        log('B connect failed: %r' % exc)
        return 'second connection REFUSED while the first is open (single connection only)', steps
    b1 = conn_b.query('*IDN?', timeout)
    log('B *IDN? while A open: %s %r' % (b1.status, b1.received))
    a2 = conn_a.query('*IDN?', timeout)
    log('A *IDN? after B queried: %s %r' % (a2.status, a2.received))
    b2 = conn_b.query('*IDN?', timeout) if b1.answered else None
    if b2 is not None:
        log('B *IDN? again: %s' % b2.status)
    conn_b.close()
    a3 = conn_a.query('*IDN?', timeout)
    log('A *IDN? after B closed: %s' % a3.status)
    if b1.answered and a2.answered and (b2 is None or b2.answered):
        return 'MULTIPLE simultaneous connections work (both answered)', steps
    if b1.answered and not a2.answered:
        return 'second connection TAKES OVER: B answered, A went silent/closed', steps
    # B accepted but silent: does a fresh connection work once A is closed?
    conn_a.close()
    try:
        conn_c = Connection(host, port, term, grace)
    except OSError as exc:
        log('C connect after A closed failed: %r' % exc)
        return 'B accepted at TCP level but not served; reconnect after close FAILED', steps
    c1 = conn_c.query('*IDN?', timeout)
    log('C *IDN? after A closed: %s' % c1.status)
    conn_c.close()
    if c1.answered:
        return (
            'ONE client at a time: B accepted by TCP but not served while A open; served after A closed',
            steps,
        )
    return (
        'B accepted but not served, and C silent too: instrument may need a power cycle of the LAN stack',
        steps,
    )


def probe_ports(out: Out, host: str, ports: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    """TCP connect only, nothing is sent."""
    out.p('')
    out.p('== TCP connect probes (nothing is sent) ==')
    rows = []
    for port, why in ports:
        try:
            s = socket.create_connection((host, port), timeout=2.0)
            s.close()
            state = 'open'
        except OSError as exc:
            state = 'closed/filtered (%s)' % type(exc).__name__
        out.p('  %5d %-48s %s' % (port, why, state))
        rows.append((port, why, state))
    return rows


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


def dry_run(args: argparse.Namespace) -> int:
    out = Out(None)
    terms = [args.term] if not args.sweep_terms else ['\n', '\r\n']
    out.p('bare_socket_check --dry-run: nothing is opened, nothing is sent.')
    out.p(
        'target: %s:%d (PSU_HOST=%s)'
        % (args.host or '<unset>', args.port, os.environ.get('PSU_HOST', '<unset>'))
    )
    out.p(
        'terminator(s): %s; per-query timeout %.1fs; probe timeout %.1fs'
        % (', '.join(term_name(t) for t in terms), args.timeout, args.probe_timeout)
    )
    groups: list[tuple[str, list[str]]] = [
        ('core queries (once per terminator)', [c for c, _ in CORE]),
        ('status registers (before and after the invalid probes)', STATUS_QUERIES),
        ('forms', [c for _, c, _, _ in FORMS]),
        ('parameter keywords', [c for c, _ in PARAMS]),
        (
            'concurrency (Q3)',
            [
                'A: *IDN?',
                'B: connect + *IDN?',
                'A: *IDN?',
                'B: *IDN? again',
                'close B, A: *IDN?',
                '(only if B silent) close A, C: connect + *IDN?',
            ],
        ),
    ]
    total = 0
    for title, cmds in groups:
        out.p('')
        out.p('-- %s (%d)' % (title, len(cmds)))
        for c in cmds:
            out.p('   ' + c)
        total += len(cmds)
    if args.probe_ports:
        out.p('')
        out.p('-- TCP connect only: ' + ', '.join(str(p) for p, _ in PORTS))
    bad = [c for g in groups[:4] for c in g[1] if _checked(c) is False]
    out.p('')
    out.p(
        '%d planned queries; read-only check of every string: %s'
        % (total, 'FAILED %r' % bad if bad else 'passed')
    )
    return 1 if bad else 0


def _checked(cmd: str) -> bool:
    try:
        assert_query(cmd)
        return True
    except NotAQuery:
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description='Read-only raw-socket check of a Siglent SPD4000X on port 5025 (stdlib only).',
        epilog='Environment: PSU_HOST = address of the supply (documentation example: 192.0.2.10).',
    )
    ap.add_argument('--host', default=os.environ.get('PSU_HOST'), help='default: $PSU_HOST')
    ap.add_argument('--port', type=int, default=DEFAULT_PORT, help='default 5025')
    ap.add_argument(
        '--term',
        type=parse_term,
        default='\n',
        help='command terminator: \\n (default) or \\r\\n (also lf, crlf, cr)',
    )
    ap.add_argument(
        '--sweep-terms',
        action='store_true',
        help='run the core queries once with \\n and once with \\r\\n (Q1), each on a fresh connection',
    )
    ap.add_argument(
        '--timeout',
        type=float,
        default=2.0,
        help='per-query timeout in s for core queries (default 2.0)',
    )
    ap.add_argument(
        '--probe-timeout',
        type=float,
        default=1.0,
        help='per-query timeout in s for the forms/parameter probes (default 1.0)',
    )
    ap.add_argument(
        '--grace',
        type=float,
        default=0.10,
        help='seconds to keep listening after a complete line, to catch trailing bytes (default 0.10)',
    )
    ap.add_argument(
        '--probe-ports',
        action='store_true',
        help='also TCP-connect (nothing sent) to ports 80, 23, 111 for Q3',
    )
    ap.add_argument(
        '--skip-concurrency', action='store_true', help='do not open a second connection'
    )
    ap.add_argument(
        '--log',
        default=DEFAULT_LOG,
        help='append everything printed to this file (default %(default)s)',
    )
    ap.add_argument(
        '--dry-run',
        action='store_true',
        help='print the planned queries and exit; no network access',
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dry_run:
        return dry_run(args)
    if not args.host:
        print(
            'error: set PSU_HOST (e.g. export PSU_HOST=192.0.2.10) or pass --host', file=sys.stderr
        )
        return 2
    out = Out(args.log)
    try:
        return session(args, out)
    finally:
        out.close()


def session(args: argparse.Namespace, out: Out) -> int:
    out.p(
        'bare_socket_check: READ-ONLY. Target %s:%d, primary terminator %s, log %s'
        % (args.host, args.port, term_name(args.term), args.log)
    )
    terms = [args.term]
    if args.sweep_terms:
        terms = ['\n', '\r\n']
        if args.term not in terms:
            terms.insert(0, args.term)
    all_core: dict[str, dict[str, Result]] = {}
    try:
        conn = Connection(args.host, args.port, terms[0], args.grace)
    except OSError as exc:
        out.p('cannot connect: %r' % exc)
        return 2

    # Core queries per terminator (fresh connection for each after the first).
    for i, term in enumerate(terms):
        if i > 0:
            conn.close()
            try:
                conn = Connection(args.host, args.port, term, args.grace)
            except OSError as exc:
                out.p('reconnect for terminator %s failed: %r' % (term_name(term), exc))
                break
        all_core[term_name(term)] = run_core(out, conn, args.timeout, term)

    primary = term_name(terms[0])
    core = all_core.get(primary, {})
    if not core or not core.get('*IDN?', None) or not core['*IDN?'].answered:
        out.p('')
        out.p(
            '*IDN? got no answer with %s; skipping the probes that need a working terminator.'
            % primary
        )
        # still summarise what we have
    # Forms/params use the primary-terminator connection, so reconnect with it if the sweep moved on.
    if terms[-1] != terms[0]:
        conn.close()
        try:
            conn = Connection(args.host, args.port, terms[0], args.grace)
        except OSError as exc:
            out.p('reconnect failed: %r' % exc)
            return 2

    out.p('')
    out.p('== Status registers before invalid probes (Q6; *ESR? clears on read) ==')
    st_before = run_status(out, conn, args.timeout, 'before')
    form_rows = run_forms(out, conn, args.probe_timeout, core)
    param_rows = run_params(out, conn, args.probe_timeout)
    out.p('')
    out.p('== Status registers after invalid probes (Q6) ==')
    st_after = run_status(out, conn, args.timeout, 'after')

    verdict3, steps3 = ('not run', [])
    if not args.skip_concurrency:
        verdict3, steps3 = run_concurrency(
            out, args.host, args.port, conn, args.timeout, terms[0], args.grace
        )
    conn.close()
    port_rows = probe_ports(out, args.host, PORTS) if args.probe_ports else []

    summary(
        out, args, terms, all_core, form_rows, param_rows, st_before, st_after, verdict3, port_rows
    )
    idn = core.get('*IDN?')
    return 0 if idn is not None and idn.answered else 1


def summary(
    out: Out,
    args: argparse.Namespace,
    terms: list[str],
    all_core: dict[str, dict[str, Result]],
    form_rows: list[tuple[str, str, str, str, str]],
    param_rows: list[tuple[str, str, str]],
    st_before: dict[str, Result],
    st_after: dict[str, Result],
    verdict3: str,
    port_rows: list[tuple[int, str, str]],
) -> None:
    out.p('')
    out.p('=' * 78)
    out.p('SUMMARY (answers as far as read-only queries allow; paste into the acceptance report)')
    out.p('=' * 78)

    # Q1
    out.p('')
    out.p('Q1 Terminator (raw socket)')
    rows = []
    for name, res in all_core.items():
        ok = sum(1 for r in res.values() if r.status == 'ok')
        rows.append(
            [
                name,
                '%d/%d' % (ok, len(res)),
                '*IDN? ' + (res['*IDN?'].status if '*IDN?' in res else '-'),
            ]
        )
    out.p('\n'.join(table(['terminator', 'answered', 'identity'], rows)))
    multi = next((r for r in form_rows if r[1] == '*IDN?;*OPC?'), None)
    if multi:
        out.p("  ';' two queries on one line: %s  recv=%s" % (multi[3], multi[4]))
    for name, res in all_core.items():
        idn = res.get('*IDN?')
        if idn and idn.answered:
            out.p('  response terminator seen with %s: %s' % (name, terminator_of(idn.received)))
    out.p('  USB terminator: needs USB (not testable here)')

    # Q3
    out.p('')
    out.p('Q3 Socket behaviour / LAN')
    out.p('  second concurrent connection: ' + verdict3)
    for pt, why, state in port_rows:
        out.p('  port %d (%s): %s' % (pt, why, state))
    if not port_rows:
        out.p('  web/telnet/VXI-11 ports: not probed (use --probe-ports on a direct LAN path)')

    # Q4 (+Q5)
    primary = term_name(terms[0])
    core = all_core.get(primary, {})
    out.p('')
    out.p('Q4 Response formats (terminator %s)' % primary)
    rows = []
    for cmd, _ in CORE:
        r = core.get(cmd)
        if r is None:
            continue
        rows.append(
            [
                cmd,
                repr(r.received) if r.received else r.status.upper(),
                terminator_of(r.received),
                classify(r.received),
            ]
        )
    out.p('\n'.join(table(['query', 'raw reply', 'term', 'format'], rows)))
    r5 = core.get('OCP? CH1')
    out.p('Q5 OCP? CH1 (manual prints no response): %s' % (repr(r5.received) if r5 else 'n/a'))
    out.p('   (LAN/GPIB/STORage queries are deliberately not sent by this tool)')

    # Q6
    out.p('')
    out.p('Q6 Status registers (read-only evidence)')
    for reg in STATUS_QUERIES:
        b, a = st_before.get(reg), st_after.get(reg)
        out.p(
            '  %-6s before=%s  after invalid probes=%s'
            % (reg, repr(b.received) if b else 'n/a', repr(a.received) if a else 'n/a')
        )
    out.p(
        '  (a change after the invalid probes means errors are visible there; same value = unknown or silent)'
    )

    # Q7/Q8
    out.p('')
    out.p('Q7/Q8 Forms (manual column: what 10.2 implies)')
    mism = []
    rows = []
    for label, cmd, manual, observed, _raw in form_rows:
        flag = ''
        if manual == 'accept' and observed == 'SILENT':
            flag = '<-- manual says valid'
        if manual == 'reject' and observed != 'SILENT':
            flag = '<-- manual says error'
        if flag:
            mism.append(label)
        rows.append([label, cmd, manual, observed, flag])
    out.p('\n'.join(table(['form', 'command', 'manual', 'observed', ''], rows)))
    out.p('  differences from the manual: %s' % (', '.join(mism) if mism else 'none'))

    # Q9/Q14
    out.p('')
    out.p('Q9/Q14 Parameter keywords as queries')
    out.p('\n'.join(table(['query', 'result', 'raw reply'], [list(r) for r in param_rows])))
    out.p('')
    out.p(
        'Not answerable here: Q2 (needs USB), Q10-Q13 (need writes: tools/hw_acceptance.py), Q15-Q19 (out of scope).'
    )
    out.p('Log appended to %s' % args.log)


if __name__ == '__main__':
    sys.exit(main())
