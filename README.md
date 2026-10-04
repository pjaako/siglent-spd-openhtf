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
it (the manual defines no error query). When the test ends, `tearDown()` turns all
outputs off, hands the front panel back and closes the connection. See
`example_test.py` for a complete test.

## Supported models

**Only the SPD4323X has been tested.** The other two models of the family are accepted
using the rating table from the manual (`docs/scpi_reference.md` section 6), but nothing
about them has been verified on hardware.

| Model | CH1 | CH2 / CH3 | CH4 | CH2+CH3 series | CH2+CH3 parallel | Power | Tested |
|---|---|---|---|---|---|---|---|
| SPD4323X | 6 V / 3.2 A | 32 V / 3.2 A | 6 V / 3.2 A | 60 V / 3.2 A | 32 V / 6.4 A | 240 W | yes |
| SPD4121X | 15 V / 1.5 A | 12 V / 10 A | 15 V / 1.5 A | 24 V / 10 A | 12 V / 20 A | 285 W | no |
| SPD4306X | 15 V / 1.5 A | 30 V / 6 A | 15 V / 1 A (as printed) | 60 V / 6 A | 30 V / 12 A | 400 W | no |

The SPD4306X CH4 rating is printed as 15 V / 1 A in the manual, while CH1 of the same
model is 15 V / 1.5 A; it is kept as printed. With an unknown model the plug logs a
warning and only the read-back after each setter protects against out-of-range values.

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

| Transport | Resource name |
|---|---|
| USB (USBTMC) | `USB0::...::INSTR`; leave the resource empty to pick the first USB instrument whose `*IDN?` names an SPD4xxx |
| LAN, VXI-11 | `TCPIP::192.0.2.10::INSTR` |
| LAN, raw socket | `TCPIP::192.0.2.10::5025::SOCKET` (port 5025 is the one named in the manual) |

The addresses are documentation examples (RFC 5737). Choose the resource with the CONF
key `siglent_spd_resource` (set it after importing the plug module):

```python
from siglent_spd_openhtf.plug import CONF
CONF.load(siglent_spd_resource='TCPIP::192.0.2.10::INSTR')
```

or `python example_test.py --resource TCPIP::192.0.2.10::INSTR`.

## Teardown policy and CONF keys

| CONF key | Default | Meaning |
|---|---|---|
| `siglent_spd_resource` | `''` | VISA resource name; empty = first USB instrument whose `*IDN?` names an SPD4xxx |
| `siglent_spd_outputs_off_on_teardown` | `True` | turn all outputs off in `tearDown()` |
| `siglent_spd_restore_state` | `False` | capture setpoints and protection values at connect and write them back in `tearDown()`; never re-enables outputs |

`tearDown()` runs these steps in order: all outputs off (if enabled), restore the
captured state (if enabled), unlock the front panel, close the connection. A failing step
is logged as a warning and never stops the next one. The plug never turns an output on in
`tearDown()` or `restore()`, and it never sends `*RST`, `DEFAult:RESET` or `FACTory:RESET`.

Each constructor argument (`resource`, `outputs_off_on_teardown`, `restore_state`)
overrides the matching CONF key. Passing a `resource` object (anything with `write`,
`query`, `close`, `timeout`, `read_termination` and `write_termination`) is how the tests
inject the fake.

## Running without hardware

`FakeSpdResource` models the supply from the manual (channel state, ratings with clamping,
CV/CC with a resistive load, OVP/OCP trips, track mode, sense, lock) and logs every
command in `fake.log`. Nothing in the tests opens a real VISA resource.

```
.venv/bin/pytest -q
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy src
.venv/bin/python example_test.py --fake
```

A fake only knows what the manual told us, so hardware acceptance is still required
before a feature counts as done. Assumptions the manual leaves open are marked
`# ASSUMPTION(hw)` in the source.

## Things the manual does not tell you

Nothing yet. This section is filled in during hardware acceptance, one finding at a time
(open questions: `docs/scpi_reference.md` section 8).

## More

- [`docs/scpi_reference.md`](docs/scpi_reference.md): the only source of SCPI commands for this project
- [`SPEC.md`](SPEC.md): the contract for the implementation
- [`AGENTS.md`](AGENTS.md): rules for agents working on this repository
- [`LICENSE`](LICENSE): MIT
