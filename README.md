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

The **SPD4323X is the target** of this plug and the only model that has been tested: two
hardware acceptance runs on one unit (firmware 4.1.2.9R1, LAN raw socket; run 1 with all outputs
off, run 2 with the plug's write path and `tearDown()`, and one output switched on with nothing
connected) are analysed in [`docs/hardware_findings.md`](docs/hardware_findings.md), and
`models.tested` is `True` for it. USB, VXI-11, a real protection trip and a load were not
tested. The other two models of the family are accepted using the rating table from the
manual (`docs/scpi_reference.md` section 6) and have not been seen at all.

| Model | CH1 | CH2 / CH3 | CH4 | CH2+CH3 series | CH2+CH3 parallel | Power | Hardware acceptance |
|---|---|---|---|---|---|---|---|
| SPD4323X | 6 V / 3.2 A | 32 V / 3.2 A | 6 V / 3.2 A | 60 V / 3.2 A | 32 V / 6.4 A | 240 W tested over LAN (raw socket), firmware 4.1.2.9R1 |
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
- **Series/parallel: write CH2, CH3 follows.** While the track mode is SERIES or PARALLEL, a
  voltage or current written to **CH2** is verified by read-back as usual. On the SPD4323X the
  voltage in SERIES and the current in PARALLEL are the *combined* value (CH3 follows with half;
  the guard is the model's series 60 V / parallel 6.4 A rating), the current in SERIES and the
  voltage in PARALLEL are per channel (guard: the channel rating). A voltage or current written
  to **CH3** in a coupled mode is ignored by the instrument, so `set_voltage`, `set_current` and
  `configure_channel` raise `RuntimeError` before sending it. The CH2 writes need a model marked
  `tested` (the SPD4323X; an unknown or untested model refuses them too), and every CH2/CH3
  voltage or current setter reads `OUTPut:TRACK?` fresh first, since the track mode can be
  changed from the panel behind the plug's back. `restore()` writes CH2 and leaves CH3 to
  follow; it reports a CH3 item only if it still differs.
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
| LAN, raw socket | `TCPIP::192.0.2.10::5025::SOCKET` | verified 2026-10-04/05 (SPD4323X, firmware 4.1.2.9R1, PyVISA `@py`, LF terminators) |
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
off: `OUTPut:ALL 0` honours the delay, see below), restore the captured state (if enabled; skipped after a transport error while
switching off), unlock the front panel, close the connection. The unlock is needed and must
stay the last write: any remote write sets `LOCK` to 1 and `LOCK 0` clears it (observed
through `LOCK?` on 2026-10-05; the front panel was seen unlocked after the plug's
`tearDown()` on 2026-10-04). A failing step is logged as a
warning and never stops the next one. The plug never turns an output on in
`tearDown()` or `restore()`, and it never sends `*RST`, `DEFAult:RESET` or `FACTory:RESET`.

Each constructor argument (`resource`, `outputs_off_on_teardown`, `restore_state`)
overrides the matching CONF key. Passing a `resource` object (anything with `write`,
`query`, `close`, `timeout`, `read_termination` and `write_termination`) is how the tests
inject the fake.

## Running without hardware

`FakeSpdResource` models the supply as observed on 2026-10-04/05 (channel state stored as
float32, silent clamping, MIN/MAX/DEF keywords, auto-lock on every write, status registers,
`;` chaining, the CH2 to CH3 copy of a track change, combined CH2 writes in series/parallel,
the OFF delay, CV/CC with a resistive load, OVP/OCP trips, track mode, sense, lock) and logs every command in `fake.log`. Nothing in the tests
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

Found on an SPD4323X, firmware 4.1.2.9R1 (the manual's example shows 4.1.2.4), over the LAN
raw socket: items 1-15 on 2026-10-05 with all outputs off, items 16-20 on 2026-10-04 (run 2:
one output switched on with nothing connected). Details and line references:
[`docs/hardware_findings.md`](docs/hardware_findings.md). Other models, USB, VXI-11, loads and
protection trips are not covered.

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
    queries ignore the coupling (`32.320000` / `3.232000`). A *write* is the combined value
    too, see item 18. In SERIES `CURRent? CH3` shows CH2's current plus 0.1 A (3 A -> `3.100000`),
    a display rule: nothing is stored.
11. Any remote write locks the front panel (`LOCK?` -> `1`); `LOCK 0` unlocks and the write
    itself does not re-lock; queries never lock.
12. One socket client at a time: a second connection is accepted but gets no reply while
    the first is open.
13. A query right after a write waits about 250 ms (up to 330 ms) until the write has been
    applied, so a read-back needs no sleep; otherwise replies take 1-5 ms.
14. `MODE? CH1` answers `0` although the manual limits `MODE` to CH2 and CH3.
15. `;` chains work, but the replies of chained queries are concatenated with no separator
    (`*IDN?;*OPC?` -> `...4.1.2.9R11`).

16. Output on, nothing connected: the first `MEASure:VOLTage? CH1` after `OUTPut CH1,1` (1.0 V)
    already reads `0.999164` (it is held about 295 ms for the write); no ramp is visible.
    After `OUTPut CH1,0` the open output decays below 20 mV within about 0.7 s.
17. OFF delay: with `OUTPut:OFF:DELay CH1,2`, both `OUTPut CH1,0` and `OUTPut:ALL 0` leave
    `OUTPut? CH1` at `1` and the voltage at 1.0 V for 2.0 s, then it switches off; writing the
    delay `0` while the switch-off is pending switches the output off at once (`OUTPut?` -> `0`
    46 ms later). Hence `tearDown()` zeroes a pending OFF delay before `OUTPut:ALL 0`.
18. A setpoint written to CH2 in a coupled mode is the combined value: in SERIES
    `VOLTage CH2,20` reads back `20.000000` and CH3 reads `10.000000`; in PARALLEL
    `CURRent CH2,5` reads back `5.000000` (above the per-channel `MAX` of 3.232 A) and CH3
    reads `2.500000`. The `MAXimum` keyword still means the per-channel value (`32.320000` V
    combined in SERIES, `3.232000` A in PARALLEL). Both halves keep their value after going
    back to INDEPENDENT. OVP and OCP stay per channel. The combined value is limited to 60 V in
    SERIES (`VOLTage CH2,70` and `,200` read back `60.000000`) and to 6.464 A in PARALLEL
    (`CURRent CH2,7` and `,20` read back `6.464000`). The current of CH2 in SERIES and the voltage
    of CH2 in PARALLEL are per channel (the voltage then applies to CH3 as well). Writes to CH3 in
    a coupled mode are ignored (both channels read back unchanged).
19. `VOLTage CH5,1` and `VOLTage CH0,1` are ignored: CH1 to CH4 stay as they were (CH4 read back
    before and after, and `0 V / 0 A` seen on the panel); `*ESR?` stays 0 for them.
20. The bit-5 behaviour of `*ESR?` is not explained by an "empty error list": after `*CLS`,
    repeated unknown queries set it every time (`32`, `32`, `32`), while two unknown queries in
    the read-only phase did not. Read-back stays the only error check.

21. The ON and OFF delay writes clamp like `OCP:DELay`: `3601` -> `3600.000000`, `-1` -> `0.000000`,
    `MAXimum` 3600, `MINimum` and `DEFault` 0.
22. `MODE? CH4` answers `0` like `MODE? CH1`; `MODE CH1,1` and `MODE CH4,1` are accepted and
    ignored (the query still answers `0`).
23. `VOLTage?` without a channel answers CH1's value (`5.000000`), also with CH2 selected on the
    front panel.

Items 21-23 and the extra items of 18 were found in the second visit of 2026-10-04 (outputs off,
experiment 22).

Still unknown: USB (identity, terminator) and VXI-11, protection trips (`1` = tripped is
assumed), `OUTPut:TRACK` with an output on, `OUTPut:ALL?` with mixed channel states, whether
an ignored write locks the panel, and the other two models. Open questions:
`docs/scpi_reference.md` section 8.

## More

- [`docs/scpi_reference.md`](docs/scpi_reference.md): the only source of SCPI commands for this project
- [`SPEC.md`](SPEC.md): the contract for the implementation
- [`AGENTS.md`](AGENTS.md): rules for agents working on this repository
- [`LICENSE`](LICENSE): MIT
