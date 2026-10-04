# siglent-spd-openhtf

OpenHTF plug for Siglent SPD4000X programmable DC power supplies, over SCPI with PyVISA.

```python
import openhtf as htf
from openhtf.util import units
from siglent_spd_openhtf import SiglentSpdPlug

@htf.measures(htf.Measurement('v_ch1').with_units(units.VOLT).in_range(3.2, 3.4))
@htf.plug(psu=SiglentSpdPlug)
def power_up(test, psu):
    psu.configure_channel(1, voltage=3.3, current=0.5, ovp=4.0, ocp=1.0, ocp_enabled=True)
    psu.set_output(1, True)
    test.measurements.v_ch1 = psu.wait_for_voltage(1, 3.3)
```

Every setter reads its value back and raises `RuntimeError` if the supply did not take
it (the manual defines no error query). Boolean arguments must be `True`/`False` or the
ints `0`/`1`; anything else (for example the string `'off'`) raises `ValueError` before
anything is sent. When the test ends, `tearDown()` turns all
outputs off, hands the front panel back and closes the connection. See
`example_test.py` for a complete test.

## Supported models

The **SPD4323X is the target** of this plug. A first hardware acceptance run on an
SPD4323X (firmware 4.1.2.9R1, 2026-10-05, LAN raw socket, all outputs off, nothing
connected) is analysed in [`docs/hardware_findings.md`](docs/hardware_findings.md). **Output-on
acceptance is still pending**, so no model is marked "tested" (`models.tested` stays
`False`; the README will say "tested over LAN (raw socket), firmware 4.1.2.9R1" once
experiment 30 and the plug write smoke have run). The other two models of the family are
accepted using the rating table from the manual (`docs/scpi_reference.md` section 6) and
have not been seen at all.

| Model | CH1 | CH2 / CH3 | CH4 | CH2+CH3 series | CH2+CH3 parallel | Power | Hardware acceptance |
|---|---|---|---|---|---|---|---|
| SPD4323X | 6 V / 3.2 A | 32 V / 3.2 A | 6 V / 3.2 A | 60 V / 3.2 A | 32 V / 6.4 A | 240 W | LAN raw socket verified with outputs off (2026-10-05, firmware 4.1.2.9R1); output-on acceptance pending |
| SPD4121X | 15 V / 1.5 A | 12 V / 10 A | 15 V / 1.5 A | 24 V / 10 A | 12 V / 20 A | 285 W | not started |
| SPD4306X | 15 V / 1.5 A | 30 V / 6 A | 15 V / 1 A (as printed) | 60 V / 6 A | 30 V / 12 A | 400 W | not started |

The SPD4306X CH4 rating is printed as 15 V / 1 A in the manual, while CH1 of the same
model is 15 V / 1.5 A; it is kept as printed. With an unknown model the plug logs a
warning and only the read-back after each setter protects against out-of-range values.

## API notes

- **Guard at the rating.** `set_voltage` / `set_current` raise `ValueError` before anything
  is sent for a value above the channel's *rated* value (6 V / 32 V / 3.2 A on the SPD4323X).
  The supply itself accepts up to 1.01 x the rating and clamps silently beyond that; the
  extra 1 % is headroom, not a specification. `max_voltage(ch)` / `max_current(ch)` return
  what the supply reports as its own limit (`:SOURce:VOLTage:SET? CHn,MAXimum`, for example
  6.06 V on CH1) for information; the guard does not use them. A `restore()` of a value that
  sat between the rating and that limit fails that item with `ValueError` and is reported.
- **Series/parallel is write-protected for now.** While the track mode is SERIES or PARALLEL,
  `set_voltage`, `set_current` and `configure_channel` on CH2 or CH3 raise `RuntimeError`
  naming open question 21 before anything is sent, and `restore()` skips CH2/CH3 voltage and
  current and reports them. Reading is fine: in SERIES `VOLTage? CH2` is the combined voltage.
  What a setpoint *written* in a coupled mode means (combined or per half) has not been
  tried on hardware, and a per-half write would double the terminal voltage before the
  read-back could object.
- **`set_track()` changes CH3.** Entering SERIES or PARALLEL copies CH2's voltage and current
  setpoints into CH3, and CH3 keeps them after going back to INDEPENDENT. `set_track()` reads
  CH3's setpoints before and after and logs a warning naming both values when they changed.
  It refuses while the output of CH2 or CH3 is on.
- **`restore()`** reads each value first and writes only what differs (a write costs about
  250 ms on the supply); it never turns an output on and skips channels whose output is on.
- **`tearDown()`** ends with the unlock because any remote write locks the front panel;
  nothing may be written after it.

LIST, WAVE, STORAGE and CALIBRATE are not implemented.

## Install

```
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e '.[dev]'
```

Add the `usb` extra (`-e '.[dev,usb]'`) for USB access through pyusb. Python 3.11 or
newer works; development is on 3.13.

## Connecting

The plug uses PyVISA with the `pyvisa-py` (`@py`) backend; there is no custom transport.
The manual documents only the raw socket on port 5025. It was verified on an SPD4323X on
2026-10-05; the other two transports below are **unverified**. The supply serves **one
socket client at a time**: while the plug holds the connection, no other tool can talk to it.

| Transport | Resource name | Status |
|---|---|---|
| LAN, raw socket | `TCPIP::192.0.2.10::5025::SOCKET` | verified 2026-10-05 (SPD4323X, firmware 4.1.2.9R1, PyVISA `@py`, LF terminators) |
| LAN, VXI-11 | `TCPIP::192.0.2.10::INSTR` | unverified: the manual does not mention VXI-11, and it was not tried |
| USB (USBTMC) | `USB0::...::INSTR`; leave the resource empty to pick the first USB instrument whose `*IDN?` names an SPD4xxx | unverified: the manual does not mention USBTMC or give a vendor id, and USB was not tried |

The addresses are documentation examples (RFC 5737). Choose the resource with the CONF
key `siglent_spd_resource` (set it after importing the plug module):

```python
from siglent_spd_openhtf.plug import CONF
CONF.load(siglent_spd_resource='TCPIP::192.0.2.10::5025::SOCKET')
```

or `python example_test.py --resource TCPIP::192.0.2.10::5025::SOCKET`.

## Teardown policy and CONF keys

| CONF key | Default | Meaning |
|---|---|---|
| `siglent_spd_resource` | `''` | VISA resource name; empty = first USB instrument whose `*IDN?` names an SPD4xxx |
| `siglent_spd_outputs_off_on_teardown` | `True` | turn all outputs off in `tearDown()` |
| `siglent_spd_restore_state` | `False` | capture setpoints, protection values and ON/OFF delays at connect and write them back in `tearDown()`; never re-enables outputs, and skips a channel whose output is on |

`tearDown()` runs these steps in order: all outputs off (if enabled; a non-zero OFF delay
of a channel that is on is first set to 0 with a warning, so the output really switches
off), restore the captured state (if enabled; skipped after a transport error while
switching off), unlock the front panel, close the connection. The unlock is needed and must
stay the last write: any remote write sets `LOCK` to 1 and `LOCK 0` clears it (observed
through `LOCK?` on 2026-10-05). Whether the panel is then visibly unlocked (lock icon, keys
usable) has not been checked (`# ASSUMPTION(hw)`). A failing step is logged as a
warning and never stops the next one. The plug never turns an output on in
`tearDown()` or `restore()`, and it never sends `*RST`, `DEFAult:RESET` or `FACTory:RESET`.

Each constructor argument (`resource`, `outputs_off_on_teardown`, `restore_state`)
overrides the matching CONF key. Passing a `resource` object (anything with `write`,
`query`, `close`, `timeout`, `read_termination` and `write_termination`) is how the tests
inject the fake.

## Running without hardware

`FakeSpdResource` models the supply as observed on 2026-10-05 (channel state stored as
float32, silent clamping, MIN/MAX/DEF keywords, auto-lock on every write, status registers,
`;` chaining, the CH2 to CH3 copy of a track change, CV/CC with a resistive load, OVP/OCP
trips, track mode, sense, lock) and logs every command in `fake.log`. Nothing in the tests
opens a real VISA resource.

```
.venv/bin/pytest -q
.venv/bin/ruff check src tests example_test.py && .venv/bin/ruff format --check src tests example_test.py
.venv/bin/mypy src
.venv/bin/python example_test.py --fake
```

A fake only knows what we told it, so hardware acceptance is still required before a
feature counts as done. Assumptions that are still open are marked `# ASSUMPTION(hw)` in
the source; answers found on hardware are marked `# verified on SPD4323X ...`.

## Things the manual does not tell you

Found on 2026-10-05 on an SPD4323X, firmware 4.1.2.9R1 (the manual's example shows 4.1.2.4),
over the LAN raw socket, all outputs off (details and line references:
[`docs/hardware_findings.md`](docs/hardware_findings.md)). Other models, USB, VXI-11 and
everything that needs an output switched on are not covered.

1. Commands end in LF (CRLF is also accepted); every reply ends in a single LF.
2. `MAX` is 1.01 x the rating for voltage and current (`VOLTage? CH1,MAX` -> `6.060000`);
   OVP and OCP accept 0.1 x .. 1.1 x the rating, and the default is 1.1 x
   (`OVP? CH2` -> `35.200001`).
3. Out-of-range values are clamped silently and never reported
   (`VOLTage CH1,7.5` -> read-back `6.060000`, `OVP CH1,0.3` -> `0.600000`), and `*ESR?` stays 0.
4. Values are 32-bit floats: `OVP? CH2` answers `35.200001`, not `35.200000`.
5. `OCP? CHn` answers a plain number like `OVP?` (`3.520000`).
6. An invalid query is never answered, so the caller waits for the full timeout; there is no
   error reply, and `*ESR?` bit 5 (32) is not dependable (set after `FOOBar? CH1` in one
   sequence and not in another).
7. Short forms and omitted `SOURce` / `:SET` work and honour the channel argument;
   `VOLTage?` without a channel answers CH1's value (`5.000000`); `POWER` and `TRACK`
   have no short form (`MEAS:POW? CH1` and `OUTP:TRAC?` get no answer).
8. Track and sense queries answer numbers: `OUTPut:TRACK?` -> `0`/`1`/`2` for
   independent/series/parallel, `MODE? CH2` -> `0`/`1` for 2W/4W.
9. Entering series or parallel copies CH2's voltage and current setpoints into CH3, and CH3
   keeps them (CH3 12 V / 2 A became 14 V / 3 A after a round trip).
10. In series `VOLTage? CH2` is the combined voltage (`28.000000` with 14 V per half), in
    parallel `CURRent? CH2` the combined current (`6.000000` with 3 A per half); the `MAX`
    queries ignore the coupling (`32.320000` / `3.232000`). What a *write* means is unknown.
11. Any remote write locks the front panel (`LOCK?` -> `1`); `LOCK 0` unlocks and the write
    itself does not re-lock; queries never lock.
12. One socket client at a time: a second connection is accepted but gets no reply while
    the first is open.
13. A query right after a write waits about 250 ms (up to 330 ms) until the write has been
    applied, so a read-back needs no sleep; otherwise replies take 1-5 ms.
14. `MODE? CH1` answers `0` although the manual limits `MODE` to CH2 and CH3.
15. `;` chains work, but the replies of chained queries are concatenated with no separator
    (`*IDN?;*OPC?` -> `...4.1.2.9R11`).

Still unknown (needs an output on, or another interface): settling time after switching on,
the state during an OFF delay, protection trips (`1` = tripped is assumed), the meaning of a
setpoint written in series/parallel, USB and VXI-11. Open questions:
`docs/scpi_reference.md` section 8.

## More

- [`docs/scpi_reference.md`](docs/scpi_reference.md): the only source of SCPI commands for this project
- [`SPEC.md`](SPEC.md): the contract for the implementation
- [`AGENTS.md`](AGENTS.md): rules for agents working on this repository
- [`LICENSE`](LICENSE): MIT
