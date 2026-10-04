# SPEC: OpenHTF plug for Siglent SPD4000X programmable DC power supplies

Target instrument: Siglent **SPD4323X** (4 channels; CH1 6 V/3.2 A, CH2 32 V/3.2 A,
CH3 32 V/3.2 A, CH4 6 V/3.2 A). The plug must also accept the other two models of
the family, SPD4121X and SPD4306X, using the rating table in `docs/scpi_reference.md`
section 6, and the README must state that only the SPD4323X has been tested.

Control is SCPI over **PyVISA** (`pyvisa` with the `pyvisa-py` backend). The same
code works over USB (USBTMC), VXI-11 (`TCPIP::<ip>::INSTR`) and the raw socket
(`TCPIP::<ip>::5025::SOCKET`, port 5025 is the one named in the manual). Do not
write your own USBTMC or socket transport.

**The only permitted source of SCPI commands is `docs/scpi_reference.md`**, a
transcription of chapter 10 of the SPD4000X user manual in `docs/`. Do not use a
command, parameter or response format that is not in that file. Where that file
flags something as unverified (⚠ manual note) the code must work with either
reading and the fake must implement the assumption named in this spec, marked
`# ASSUMPTION(hw): ...` in the source so hardware acceptance can find it.

**The real power supply is NOT available to coder agents.** Never open a real
VISA resource in tests. Everything you run must use `FakeSpdResource`.

Python 3.13. Runtime dependencies: `openhtf>=1.6.1`, `pyvisa>=1.14`,
`pyvisa-py>=0.7`. Optional extras: `usb` (`pyusb`), `dev` (`pytest`, `ruff`,
`mypy`). Nothing else.

## Files

```
pyproject.toml                       package `siglent-spd-openhtf`, src layout, ruff + mypy config
src/siglent_spd_openhtf/__init__.py  re-exports SiglentSpdPlug, FakeSpdResource, Channel, TrackMode, SenseMode, Reading, Identity, ProtectionStatus, MODELS
src/siglent_spd_openhtf/plug.py      the plug
src/siglent_spd_openhtf/models.py    rating table and model lookup
src/siglent_spd_openhtf/fake_resource.py  FakeSpdResource, no pyvisa import
src/siglent_spd_openhtf/py.typed
tests/test_plug.py                   plug behaviour against the fake, asserts on fake.log
tests/test_fake.py                   fake self-tests
tests/test_models.py
tests/test_openhtf.py                real openhtf.Test execution with the fake
tests/test_scripts.py                runs example_test.py --fake in a subprocess
example_test.py                      minimal OpenHTF test, --fake flag, exit 0/1 by outcome
.github/workflows/ci.yml             ruff, mypy, pytest on ubuntu / Python 3.13
README.md
```

Module and file names mirror `rigol-dho-openhtf` (same owner) on purpose: an
agent moving between the two repos must find the same things in the same places.

## 1. `models.py`

```python
class ChannelRating(NamedTuple): voltage: float; current: float
class Model(NamedTuple):
    name: str                       # 'SPD4323X'
    channels: tuple[ChannelRating, ChannelRating, ChannelRating, ChannelRating]
    series: ChannelRating           # CH2+CH3 in series
    parallel: ChannelRating         # CH2+CH3 in parallel
    total_power_w: float
    tested: bool                    # True only for SPD4323X
MODELS: dict[str, Model]            # keyed by name, values from docs/scpi_reference.md section 6
def model_from_idn(idn: str) -> Model | None   # second comma-separated field, upper-cased, exact key match
```

SPD4306X CH4 is `15 V / 1 A` as printed; keep it as printed and add a comment
pointing at the manual note.

## 2. Enums and records (in `plug.py`)

```python
class Channel(IntEnum): CH1 = 1; CH2 = 2; CH3 = 3; CH4 = 4      # str(Channel.CH1) -> 'CH1' via __str__
class TrackMode(str, Enum): INDEPENDENT = 'INDEPENDENT'; SERIES = 'SERIES'; PARALLEL = 'PARALLEL'
class SenseMode(str, Enum): TWO_WIRE = '2W'; FOUR_WIRE = '4W'
class Identity(NamedTuple): vendor: str; model: str; serial: str; firmware: str
class Reading(NamedTuple): voltage: float; current: float; power: float; mode: str   # mode: 'CV', 'CC' or whatever the instrument returns
class ProtectionStatus(NamedTuple): ovp_tripped: bool; ocp_tripped: bool
```

Any method taking `channel` accepts an `int` 1..4 or a `Channel`; anything else
raises `ValueError`. On the wire the channel is always written `CH<n>`.

## 3. `SiglentSpdPlug(BasePlug)`

```python
CONF.declare('siglent_spd_resource', default_value='',
    description='VISA resource name of the supply; empty = first USB instrument whose *IDN? names an SPD4xxx')
CONF.declare('siglent_spd_outputs_off_on_teardown', default_value=True,
    description='Turn all outputs off in tearDown()')
CONF.declare('siglent_spd_restore_state', default_value=False,
    description='Restore setpoints and protection values captured at connect in tearDown(); never re-enables outputs')
```

`auto_placeholder = True`.

`__init__(self, resource=None, outputs_off_on_teardown=None, restore_state=None)`
- `resource`: any object with `write(str)`, `query(str) -> str`, `close()` and the
  attributes `timeout`, `read_termination`, `write_termination`. Tests pass a
  `FakeSpdResource`. Define this as a `typing.Protocol` named `ScpiResource`.
- `None` arguments fall back to the CONF keys.
- If `resource is None`: import `pyvisa` lazily, open `pyvisa.ResourceManager('@py')`.
  Use `CONF.siglent_spd_resource` if non-empty. Otherwise iterate
  `rm.list_resources('USB?*::INSTR')`, open each, query `*IDN?`, keep the first
  whose model field starts with `SPD4`, close the others. Raise `RuntimeError`
  with a message naming the CONF key if nothing is found. The manual does not
  give a USB vendor id, so do not filter on one.
- After obtaining the resource: `timeout = 5000` ms, `read_termination = '\n'`,
  `write_termination = '\n'`. `# ASSUMPTION(hw): terminator`.
- Then: `self.identity = self.idn()`, `self.model = model_from_idn(...)` (may be
  `None`; log a warning, limits then come only from read-back), and if
  `restore_state` take `self._snapshot = self.snapshot()`.
- Never send `*RST`, `DEFAult:RESET` or `FACTory:RESET` from the plug.
  `FACTory:RESET` also resets the LAN settings and must not exist in this code base.

### Low-level

| method | behaviour |
|---|---|
| `write(cmd)` | `resource.write(cmd)`; log at DEBUG |
| `query(cmd) -> str` | `resource.query(cmd).strip()` |
| `write_verified(cmd, query_cmd, expected)` | write, then query and compare with `_values_match`; on mismatch raise `RuntimeError` naming command, expected and actual. Any exception from the query (timeouts included) is re-raised as `RuntimeError` naming the command. |
| `_values_match(expected, actual)` | bool vs `0/1/ON/OFF`; numbers with `math.isclose(rel_tol=1e-6, abs_tol=5e-4)` (instrument resolution is 1 mV / 1 mA, read-back prints 6 decimals); strings case-insensitively |
| `_fmt(x: float) -> str` | `format(x, '.9G')` (avoids `0.00019999999999999998`-style floats) |

Read-back after every set is mandatory. The manual defines no error query, so a
clamped or ignored value is only detectable by reading it back.

Command-form rule: send every command in the exact form the manual prints in
its *example* for that command (leading colon, `SOURce` prefix, `:SET` node and
keyword spelling included). Hardware acceptance (SPD4323X, fw 4.1.2.9R1,
2026-10-05, raw socket; `docs/hardware_findings.md` Q7/Q20) verified that the
verbatim forms and the short forms both work and that the channel argument is
always honoured; the verbatim forms are kept to avoid churn. Where the manual
prints no example for a form (e.g. a query), derive it from the printed example
of the paired set form. Never chain commands with `;` (replies are concatenated
without a separator).

Timing (measured): a query right after a write is held for up to about 330 ms
until the write is applied; otherwise replies take 1-5 ms. Read-back needs no
sleep and no `*OPC?`. The 5000 ms timeout stays. An invalid command is never
answered, so an unknown-header mistake costs one full timeout.

### Identity and state

| method | SCPI (exactly as written) | returns |
|---|---|---|
| `idn()` | `*IDN?` | `Identity`, split on `,`, 4 fields; fewer fields -> `RuntimeError` |
| `opc()` | `*OPC?` | `str` |
| `snapshot()` | per channel: voltage, current, OVP, OCP, OCP state, OCP delay, ON delay, OFF delay, output state; plus track mode | `dict` |
| `restore(snapshot)` | writes back track mode first (only if it differs), then per channel setpoints, OVP, OCP, OCP state, OCP delay, ON/OFF delays, each read first and written only if it differs (a write costs ~250 ms), with read-back; **never writes `OUTPut CHn,1`**; **skips every channel whose output is currently on** and, if the track restore failed, also CH2 and CH3, naming the skipped channels in the error; collects every failure and raises one `RuntimeError` listing them at the end | `None` |

### Output

| method | SCPI | notes |
|---|---|---|
| `set_voltage(ch, volts)` | `:SOURce:VOLTage:SET CHn,<v>` then `:SOURce:VOLTage:SET? CHn` | `ValueError` if `volts < 0` or above the channel rating when the model is known (see guard rule) |
| `voltage_setpoint(ch)` | `:SOURce:VOLTage:SET? CHn` | `float` |
| `set_current(ch, amps)` | `:SOURce:CURRent:SET CHn,<a>` then `:SOURce:CURRent:SET? CHn` | same guard |
| `current_setpoint(ch)` | `:SOURce:CURRent:SET? CHn` | `float` |
| `set_output(ch, on: bool)` | `OUTPut CHn,1` / `OUTPut CHn,0` then `OUTPut? CHn` | `on` must be a `bool` (or the ints 0/1); any other type or value raises `ValueError` before anything is sent. Same for every other boolean setter. |
| `output(ch)` | `OUTPut? CHn` | `bool` from `0`/`1` |
| `set_all_outputs(on)` | `OUTPut:ALL 1` / `OUTPut:ALL 0` then `OUTPut? CHn` for every channel | verification is per channel: the all-channel query format is undocumented |
| `all_outputs_off()` | `set_all_outputs(False)` | |
| `set_output_delay(ch, on_s=None, off_s=None)` | `OUTPut:ON:DELay CHn,<s>` / `OUTPut:OFF:DELay CHn,<s>` with read-back | 0..3600 else `ValueError` |
| `configure_channel(ch, *, voltage=None, current=None, ovp=None, ocp=None, ocp_enabled=None, ocp_delay=None)` | the corresponding setters, in this order: ovp, ocp, ocp_delay, ocp_enabled, voltage, current | attempts all items, raises one `RuntimeError` listing every failure |

Guard rule: when `self.model` is known, `set_voltage`/`set_current` reject
values above the channel's **rated** value with `ValueError` before anything is
sent. The instrument itself accepts up to 1.01 x rating (`VOLTage? CHn,MAX`)
and clamps silently beyond; that 1 % is headroom, not a specification, so the
guard stays at the rating. The one exception is the combined CH2 write of
the coupled modes (see below), whose guard is the model's series/parallel rating.
The plug caches the track mode from
`track()`/`set_track()` and reads it once lazily when needed.

Coupled modes (open question 21, verified on SPD4323X, firmware 4.1.2.9R1,
2026-10-04, `docs/hardware_findings.md` run 2): a setpoint written to CH2 is the
**combined** value (SERIES: `VOLTage CH2,20` reads back 20 on CH2 and 10 on
CH3; PARALLEL: `CURRent CH2,5` reads back 5 on CH2 and 2.5 on CH3). While the
cached track mode is SERIES or PARALLEL the plug therefore allows exactly two
setpoint writes on CH2/CH3, with the usual read-back: the **voltage of CH2 in
SERIES** and the **current of CH2 in PARALLEL**; their guard is the model's
`series.voltage` (SERIES) or `parallel.current` (PARALLEL) rating. Every other
voltage or current write on CH2 or CH3 in a coupled mode (CH3, the current of
CH2 in SERIES, the voltage of CH2 in PARALLEL), whether through `set_voltage`,
`set_current` or `configure_channel`, raises `RuntimeError` naming question 21
before anything is sent: nobody has tried them on hardware. `configure_channel`
checks its `voltage`/`current` items up front; OVP/OCP items are not affected.
`restore()` restores the allowed quantity and skips the rest (reporting it).
Not yet tried (open): the upper limit of a numeric combined write (5 A was
accepted in PARALLEL although `MAX` is 3.232 A; the `MAXimum` keyword stays
per channel) and everything listed above as refused.

`max_voltage(ch)` / `max_current(ch)` query `:SOURce:VOLTage:SET? CHn,MAXimum` /
`:SOURce:CURRent:SET? CHn,MAXimum` (verified) and return the float.

### Protection

| method | SCPI | notes |
|---|---|---|
| `set_ovp(ch, volts)` / `ovp(ch)` | `:SOURce:OVP CHn,<v>` with `:SOURce:OVP? CHn` | |
| `set_ocp(ch, amps)` / `ocp(ch)` | `:SOURce:OCP CHn,<a>` with `:SOURce:OCP? CHn` | |
| `set_ocp_enabled(ch, on)` / `ocp_enabled(ch)` | `:SOURce:OCP:STATe CHn,1|0` with `:SOURce:OCP:STATe? CHn` | the manual example has a space after the comma (`CH1, 1`); send without the space, mark `# ASSUMPTION(hw): no space` |
| `set_ocp_delay(ch, s)` / `ocp_delay(ch)` | `OCP:DELay CHn,<s>` with `OCP:DELay? CHn` | 0..3600 |
| `protection_status(ch)` | `:SOURce:OVP:PROTect:STATe? CHn`, `:SOURce:OCP:PROTect:STATe? CHn` | `ProtectionStatus`; `1` = tripped `# ASSUMPTION(hw)` (untripped reads `0`, verified; a trip not yet provoked) |
| `clear_protection(ch)` | `:SOURce:RESET:PROTect CHn` | no read-back possible; afterwards query `protection_status` and raise `RuntimeError` if still tripped |

There is no OVP enable command in the manual; do not invent one.

### Measurement

| method | SCPI | returns |
|---|---|---|
| `measure_voltage(ch)` | `MEASure:VOLTage? CHn` | `float` |
| `measure_current(ch)` | `MEASure:CURRent? CHn` | `float` |
| `measure_power(ch)` | `MEASure:POWER? CHn` | `float` |
| `run_mode(ch)` | `MEASure:RUN:MODE? CHn` | `str` as returned (`CV` in the manual example) |
| `measure(ch)` | the four above | `Reading` |
| `wait_for_voltage(ch, target, tol=0.05, timeout=5.0, interval=0.1)` | polls `measure_voltage` | returns the reading once `abs(v - target) <= tol`; `TimeoutError` otherwise; uses `time.monotonic`, no fixed sleeps elsewhere in the plug |

### CH2/CH3 coupling and sense

| method | SCPI | notes |
|---|---|---|
| `set_track(mode: TrackMode)` | `OUTPut:TRACK <WORD>` (send the word, not the number) then `OUTPut:TRACK?` | the query returns a number; `0`->INDEPENDENT, `1`->SERIES, `2`->PARALLEL (verified); also accept the words. Raise `RuntimeError` if any of CH2/CH3 output is on (query first). Entering SERIES or PARALLEL copies CH2's voltage and current setpoints into CH3, and CH3 keeps them after returning to INDEPENDENT (verified): read CH3 voltage/current before and after and `logger.warning` naming both values when they changed. |
| `track()` | `OUTPut:TRACK?` | `TrackMode` |
| `set_sense(ch, mode: SenseMode)` | `MODE CHn,2W|4W` then `MODE? CHn` | CH2/CH3 only else `ValueError` (the `0` that `MODE? CH1` returns on hardware means nothing); query returns a number; `0`->2W, `1`->4W (verified); also accept words |
| `sense(ch)` | `MODE? CHn` | `SenseMode` |

### Lock and teardown

| method | SCPI |
|---|---|
| `set_lock(on)` / `locked()` | `:SOURce:LOCK:STATe ON|OFF` with `:SOURce:LOCK:STATe?` |
| `tearDown()` | see below |

`tearDown()`:
1. If `outputs_off_on_teardown`: for every channel whose output is on, query the
   OFF delay and, if it is not 0, write `OUTPut:OFF:DELay CHn,0` with read-back
   and log a warning (a delayed switch-off would leave the DUT powered after the
   test ends). Then `all_outputs_off()`; if `OUTPut:ALL 0` fails, fall back to
   `OUTPut CHn,0` per channel. If this step failed with a transport error, skip
   step 2 (each restore write would wait for its own timeout).
   (Verified, run 2: `OUTPut:ALL 0` honours a pending OFF delay, so zeroing it
   first is necessary, and writing the delay 0 switches a pending output off at
   once.)
2. If `restore_state` and a snapshot exists: `restore(snapshot)`.
3. `set_lock(False)`: any remote write sets `LOCK` to 1 (verified), so this must
   stay the **last** write of the session; nothing may be written after it.
4. Each of the steps above is wrapped so that a failure is logged with
   `self.logger.warning` and never prevents the next step or `resource.close()`.
5. Close the resource, and the ResourceManager if the plug created it.

LIST, WAVE, STORAGE and CALIBRATE subsystems are out of scope for this phase.
Do not add methods for them.

## 4. `fake_resource.py` - `FakeSpdResource`

No `pyvisa` import. Constructor:
`FakeSpdResource(model='SPD4323X', serial='SPD4XXXXXXXXXX', firmware='1.0.0.0', loads=None, reject=None)`.

- `log: list[str]` records every string passed to `write` and `query`, in order.
- Attributes `timeout`, `read_termination`, `write_termination` exist and are
  settable. `close()` sets `closed = True`; a write or query after close raises
  `RuntimeError`.
- Per-channel state: `voltage`, `current`, `ovp`, `ocp`, `ocp_enabled`,
  `ocp_delay`, `output`, `on_delay`, `off_delay`, `ovp_tripped`, `ocp_tripped`.
  Instrument state: `track` (0/1/2), `sense` for CH2/CH3 (0/1), `lock`.
  Initial values as observed on hardware: V and I 0, OVP = 1.1 x rated voltage
  and OCP = 1.1 x rated current on every channel, OCP off, delays 0, outputs
  off, track 0, sense 0, lock 0. Every scalar is stored as float32 and answered
  as `f'{x:.6f}'` of that value (`OVP? CH2` -> `35.200001`).
- Parsing: strip the optional leading `:` and optional `SOURce:`/`SOUR:`
  prefix, accept long and short forms of every keyword used by the plug
  (`VOLTage`/`VOLT`, `CURRent`/`CURR`, `OUTPut`/`OUTP`, `MEASure`/`MEAS`,
  `PROTect`/`PROT`, `STATe`/`STAT`, `DELay`/`DEL`; the manual prints
  `RESET:PROTect` with no short form, so accept `RESET` only), case-insensitively.
  Channel parameter `CH1`..`CH4`; `CH5` or a missing channel queues nothing and
  the query raises `FakeTimeout` (subclass of `Exception`) to mimic an
  instrument that never answers. An unknown header behaves the same way on
  query and is ignored on write (recorded in `log`).
- Response formats as printed in the manual: scalars `f'{x:.6f}'`, booleans
  `'1'`/`'0'`, `OUTPut:TRACK?` and `MODE?` return the number, `MEASure:RUN:MODE?`
  returns `CV` or `CC`, `*IDN?` returns `Siglent Technologies,<model>,<serial>,<firmware>`,
  `*OPC?` returns `1`.
- Clamping as observed: voltage/current clamp to **1.01 x rating** (`MAX`,
  e.g. 6.060000 / 32.320000 / 3.232000 on the SPD4323X) and to 0 below; OVP/OCP
  clamp to 0.1 x .. 1.1 x rating; OCP delay clamps to 0..3600 s; ON/OFF delays
  the same (`# ASSUMPTION(hw): same as OCP:DELay`; writes of 0, 0.5 and 2 s were
  accepted on hardware, the clamps were not tried). Nothing is ever reported, so
  a plug without read-back verification would silently pass. `MINimum`/`MAXimum`/
  `DEFault` (and `MIN`/`MAX`/`DEF`) work in set commands for V, I, OVP, OCP and
  delays (DEFault = 0 for V/I/delays, 1.1 x rating for OVP/OCP) and as query
  arguments only for `VOLTage?`/`CURRent?` (any keyword on `OVP?`, `OCP?` or the
  delay queries gets no answer). `MAX` is per channel and ignores the track mode.
- Every accepted write other than the lock command sets `lock = 1` (queries
  never do); `LOCK 0` clears it.
- Status: `*ESR?` returns 32 after an unknown header or an unanswered query,
  clears on read; `*CLS` clears; `*STB?`, `*ESE?`, `*SRE?` answer `0`; `*OPC`
  sets bit 0; invalid channel, non-numeric value and clamping set nothing.
- `;` chaining: split, execute in order, answer the query replies concatenated
  without separator.
- A query that takes no channel but gets one (`OUTPut:TRACK? CH1`) gets no
  answer; a channel query without channel (`VOLTage?`) answers CH1
  (`# ASSUMPTION(hw): CH1 or the panel-selected channel`).
- Track change: entering SERIES/PARALLEL copies CH2's voltage and current
  setpoints to CH3 (kept after INDEPENDENT); store per-half values; in SERIES
  `VOLT? CH2` answers 2 x, in PARALLEL `CURR? CH2` answers 2 x; CH3 answers its
  own stored value; OVP/OCP are not changed by a track change. A write to CH2's
  combined quantity (voltage in SERIES, current in PARALLEL) is the combined
  value (verified): each half stores half of it and **CH3 follows CH2**; the
  `MAXimum`/`MINimum`/`DEFault` keywords are per channel and used as the combined
  value (32.32 V resp. 3.232 A for MAXimum, verified); a numeric value is
  clamped to 0..2 x MAX (`# ASSUMPTION(hw)`: the upper limit was not tried, 5 A
  above the 3.232 A MAX was accepted). Other writes in a coupled mode (CH3, the
  other quantity of CH2) are stored per channel (not tried).
- OFF delay (verified, run 2, Q22): switching an output off with a non-zero OFF
  delay, by `OUTPut CHn,0` or `OUTPut:ALL 0`, keeps it on (`OUTPut?` answers 1,
  measurements unchanged) until the delay has elapsed (`advance()`); writing the
  OFF delay 0 while the switch-off is pending switches the output off at once.
- `loads`: `dict[int, float | None]` ohms per channel, default `None` = open
  circuit. Measurement model when output is on: open circuit -> V = setpoint,
  I = 0, mode CV; with load R: I = V/R; if I > current setpoint then CC with
  I = Iset and V = Iset*R. Output off -> V = 0, I = 0. P = V*I. If OCP is
  enabled and I >= OCP value (including OCP value 0 with I = 0), set `ocp_tripped` and turn the output off
  (ignore the delay). If measured V > OVP, set `ovp_tripped` and turn the
  output off. `RESET:PROTect` clears both flags.
- `OUTPut:TRACK <x>` accepts `0|1|2|INDEPENDENT|SERIES|PARALLEL`.
  `MODE CH2|CH3,<0|1|2W|4W>`; `MODE? CH1` answers `0` (observed); `MODE? CH4`
  and `MODE CH1|CH4,<x>` keep no answer / ignored (`# ASSUMPTION(hw): not tried`).
- `reject: dict[str, str]`: header prefix -> if a write starts with it, ignore
  the write (state unchanged) so read-back verification catches it.
- Helpers for tests: `set_load(ch, ohms)`, `trip_ovp(ch)`, `trip_ocp(ch)`.

## 5. Tests

pytest, no mocks of the plug, no hardware. Build plugs with
`SiglentSpdPlug(resource=FakeSpdResource(...), outputs_off_on_teardown=False)` via
a `_plug()` helper. Cover at least:
- every public method sends exactly the command strings in section 3 (assert on `fake.log`),
- read-back verification raises on `reject`ed writes and on clamped values,
- the guard rule per model and per track mode, including the untested models,
- `tearDown` turns outputs off, unlocks, closes, and continues after a failing step,
- `restore` never turns an output on,
- `set_track` refuses while CH2/CH3 output is on,
- `wait_for_voltage` success and `TimeoutError` (use a tiny timeout, not sleeps),
- CV/CC transition with a load and OCP trip in the fake,
- `tests/test_openhtf.py`: an `openhtf.Test` with `@htf.plug(psu=...)` and
  `htf.Measurement('v_ch1').with_units(units.VOLT).in_range(...)` executes with
  outcome PASS using a fake-injecting subclass,
- `tests/test_scripts.py`: `python example_test.py --fake` exits 0.

## 6. `example_test.py`

Phases: `configure` (CH1 to 3.3 V / 0.5 A, OVP 4 V, OCP 1 A enabled),
`power_on` (output on, `wait_for_voltage`), `measure` (records `v_ch1`, `i_ch1`,
`p_ch1`, `mode_ch1` measurements with units), `power_off`. `--fake` injects a
`FakeSpdResource(loads={1: 10.0})`. `--resource <VISA name>` sets
`CONF.siglent_spd_resource` after importing the plug module. Exit code 0 on
PASS, 1 otherwise.

## 7. README.md

Usage snippet first (10 lines), then: supported models table stating that the
SPD4323X is the target and the only tested model ("tested over LAN (raw
socket), firmware 4.1.2.9R1" since `docs/acceptance.md` has been run; the other
two models "not started"), never stating an unverified transport or behaviour
as fact (USBTMC and VXI-11 are unverified; the raw socket on port 5025 and the
unlock step are verified), install (`uv venv` + `uv pip install -e .[dev]`),
transport/resource-name examples with RFC 5737 addresses (`192.0.2.10`),
teardown policy and CONF keys, running tests and `--fake`, a "Things the manual
does not tell you" section filled from the acceptance findings (dated, with
the raw reply),
links to `docs/scpi_reference.md`, `SPEC.md`, `AGENTS.md`, licence.

## Done means

- `ruff check .`, `ruff format --check .`, `mypy src` and `pytest -q` pass locally.
- `python example_test.py --fake` exits 0.
- Every SCPI string in `src/` appears in `docs/scpi_reference.md`
  (`grep` each one; a reviewer will).
- Every `# ASSUMPTION(hw)` in the spec is present in the source at the place
  where the assumption is made.
- CI runs on every Python version the README claims (3.11 and 3.13).
- `HANDOFF.md` updated.
- The fake reproduces every reply quoted in `docs/hardware_findings.md` for the
  commands the plug uses.
- `models.tested` is `True` for the SPD4323X only (experiments 21, the plug write
  smoke, and 30, output on, both passed on 2026-10-04); the README model table
  says "tested over LAN (raw socket), firmware 4.1.2.9R1". It stays `False` for
  the SPD4121X and SPD4306X.
- README written as in section 7.
- No real VISA resource was opened.
