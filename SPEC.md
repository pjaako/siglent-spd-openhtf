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

### Identity and state

| method | SCPI (exactly as written) | returns |
|---|---|---|
| `idn()` | `*IDN?` | `Identity`, split on `,`, 4 fields; fewer fields -> `RuntimeError` |
| `opc()` | `*OPC?` | `str` |
| `snapshot()` | per channel: `VOLTage? CHn`, `CURRent? CHn`, `OVP? CHn`, `OCP? CHn`, `OCP:STATe? CHn`, `OCP:DELay? CHn`, `OUTPut? CHn`; plus `OUTPut:TRACK?` | `dict` |
| `restore(snapshot)` | writes back setpoints, OVP, OCP, OCP state, OCP delay and track mode with read-back; **never writes `OUTPut CHn,1`**; collects every failure and raises one `RuntimeError` listing them at the end | `None` |

### Output

| method | SCPI | notes |
|---|---|---|
| `set_voltage(ch, volts)` | `VOLTage CHn,<v>` then `VOLTage? CHn` | `ValueError` if `volts < 0` or above the channel rating when the model is known (see guard rule) |
| `voltage_setpoint(ch)` | `VOLTage? CHn` | `float` |
| `set_current(ch, amps)` | `CURRent CHn,<a>` then `CURRent? CHn` | same guard |
| `current_setpoint(ch)` | `CURRent? CHn` | `float` |
| `set_output(ch, on: bool)` | `OUTPut CHn,1` / `OUTPut CHn,0` then `OUTPut? CHn` | |
| `output(ch)` | `OUTPut? CHn` | `bool` from `0`/`1` |
| `set_all_outputs(on)` | `OUTPut:ALL 1` / `OUTPut:ALL 0` then `OUTPut? CHn` for every channel | verification is per channel: the all-channel query format is undocumented |
| `all_outputs_off()` | `set_all_outputs(False)` | |
| `set_output_delay(ch, on_s=None, off_s=None)` | `OUTPut:ON:DELay CHn,<s>` / `OUTPut:OFF:DELay CHn,<s>` with read-back | 0..3600 else `ValueError` |
| `configure_channel(ch, *, voltage=None, current=None, ovp=None, ocp=None, ocp_enabled=None, ocp_delay=None)` | the corresponding setters, in this order: ovp, ocp, ocp_delay, ocp_enabled, voltage, current | attempts all items, raises one `RuntimeError` listing every failure |

Guard rule: when `self.model` is known and the channel is CH1 or CH4, or the
track mode last read is INDEPENDENT, the setter rejects values above the
independent rating with `ValueError` before anything is sent. For CH2/CH3 in
series or parallel mode use the series/parallel rating. The plug caches the
track mode from `track()`/`set_track()` and reads it once lazily when needed.

### Protection

| method | SCPI | notes |
|---|---|---|
| `set_ovp(ch, volts)` / `ovp(ch)` | `OVP CHn,<v>` with `OVP? CHn` | |
| `set_ocp(ch, amps)` / `ocp(ch)` | `OCP CHn,<a>` with `OCP? CHn` | |
| `set_ocp_enabled(ch, on)` / `ocp_enabled(ch)` | `OCP:STATe CHn,1|0` with `OCP:STATe? CHn` | |
| `set_ocp_delay(ch, s)` / `ocp_delay(ch)` | `OCP:DELay CHn,<s>` with `OCP:DELay? CHn` | 0..3600 |
| `protection_status(ch)` | `OVP:PROTect:STATe? CHn`, `OCP:PROTect:STATe? CHn` | `ProtectionStatus`; `1` = tripped `# ASSUMPTION(hw)` |
| `clear_protection(ch)` | `RESET:PROTect CHn` | no read-back possible; afterwards query `protection_status` and raise `RuntimeError` if still tripped |

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
| `set_track(mode: TrackMode)` | `OUTPut:TRACK <WORD>` (send the word, not the number) then `OUTPut:TRACK?` | the query returns a number; map `0`->INDEPENDENT, `1`->SERIES, `2`->PARALLEL `# ASSUMPTION(hw): track numbering`; also accept the words. Raise `RuntimeError` if any of CH2/CH3 output is on (query first). |
| `track()` | `OUTPut:TRACK?` | `TrackMode` |
| `set_sense(ch, mode: SenseMode)` | `MODE CHn,2W|4W` then `MODE? CHn` | CH2/CH3 only else `ValueError`; query returns a number; map `0`->2W, `1`->4W `# ASSUMPTION(hw): sense numbering`; also accept words |
| `sense(ch)` | `MODE? CHn` | `SenseMode` |

### Lock and teardown

| method | SCPI |
|---|---|
| `set_lock(on)` / `locked()` | `LOCK 1|0` with `LOCK?` |
| `tearDown()` | see below |

`tearDown()`:
1. If `outputs_off_on_teardown`: `all_outputs_off()`.
2. If `restore_state` and a snapshot exists: `restore(snapshot)`.
3. `set_lock(False)` (the panel locks itself under remote control; hand the
   front panel back). `# ASSUMPTION(hw): needed`.
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
  Initial values follow the manual's "Default Settings" (section 4 of the
  reference): V and I 0, OVP and OCP at the rated maximum, OCP off, delay 0,
  outputs off, track 0, sense 0, lock 0.
- Parsing: strip the optional leading `:` and optional `SOURce:`/`SOUR:`
  prefix, accept long and short forms of every keyword used by the plug
  (`VOLTage`/`VOLT`, `CURRent`/`CURR`, `OUTPut`/`OUTP`, `MEASure`/`MEAS`,
  `PROTect`/`PROT`, `STATe`/`STAT`, `DELay`/`DEL`, `RESet`?? - **no**: the
  manual prints `RESET:PROTect`; accept `RESET` only), case-insensitively.
  Channel parameter `CH1`..`CH4`; `CH5` or a missing channel queues nothing and
  the query raises `FakeTimeout` (subclass of `Exception`) to mimic an
  instrument that never answers. An unknown header behaves the same way on
  query and is ignored on write (recorded in `log`).
- Response formats as printed in the manual: scalars `f'{x:.6f}'`, booleans
  `'1'`/`'0'`, `OUTPut:TRACK?` and `MODE?` return the number, `MEASure:RUN:MODE?`
  returns `CV` or `CC`, `*IDN?` returns `Siglent Technologies,<model>,<serial>,<firmware>`,
  `*OPC?` returns `1`.
- Setting a voltage/current/OVP/OCP above the rating of the channel (per
  `models.py`, honoring track mode for CH2/CH3) **clamps to the rating**
  (`# ASSUMPTION(hw): clamping`), negative values clamp to 0, so that a plug
  without read-back verification would silently pass.
- `loads`: `dict[int, float | None]` ohms per channel, default `None` = open
  circuit. Measurement model when output is on: open circuit -> V = setpoint,
  I = 0, mode CV; with load R: I = V/R; if I > current setpoint then CC with
  I = Iset and V = Iset*R. Output off -> V = 0, I = 0. P = V*I. If OCP is
  enabled and I >= OCP value, set `ocp_tripped` and turn the output off
  (ignore the delay). If measured V > OVP, set `ovp_tripped` and turn the
  output off. `RESET:PROTect` clears both flags.
- `OUTPut:TRACK <x>` accepts `0|1|2|INDEPENDENT|SERIES|PARALLEL`.
  `MODE CH2|CH3,<0|1|2W|4W>`; `MODE CH1,...` is ignored and `MODE? CH1` times out.
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

Usage snippet first (10 lines), then: supported models table with a clear
"tested only on SPD4323X" statement, install (`uv venv` + `uv pip install -e .[dev]`),
transport/resource-name examples with RFC 5737 addresses (`192.0.2.10`),
teardown policy and CONF keys, running tests and `--fake`, a "Things the manual
does not tell you" section that is empty until hardware acceptance fills it,
links to `docs/scpi_reference.md`, `SPEC.md`, `AGENTS.md`, licence.

## Done means

- `ruff check .`, `ruff format --check .`, `mypy src` and `pytest -q` pass locally.
- `python example_test.py --fake` exits 0.
- Every SCPI string in `src/` appears in `docs/scpi_reference.md`
  (`grep` each one; a reviewer will).
- Every `# ASSUMPTION(hw)` in the spec is present in the source at the place
  where the assumption is made.
- README written as in section 7.
- No real VISA resource was opened.
