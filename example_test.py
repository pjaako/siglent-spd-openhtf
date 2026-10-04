"""Minimal OpenHTF test for a Siglent SPD4000X power supply.

    python example_test.py --fake                      # no hardware, simulated supply
    python example_test.py --resource TCPIP::192.0.2.10::5025::SOCKET

Exit code 0 on PASS, 1 otherwise. The plug turns all outputs off when the test ends.
"""

from __future__ import annotations

import argparse
import sys

import openhtf as htf
from openhtf.util import units

from siglent_spd_openhtf import FakeSpdResource, SiglentSpdPlug
from siglent_spd_openhtf.plug import CONF

CH = 1
V_SET = 3.3
I_LIMIT = 0.5
LOAD_OHMS = 10.0  # only used by the fake supply


class FakeSiglentSpdPlug(SiglentSpdPlug):
    """The plug wired to a simulated supply with a 10 ohm load on CH1.

    It keeps the default teardown policy (all outputs off), like the real plug.
    """

    def __init__(self) -> None:
        super().__init__(resource=FakeSpdResource(loads={CH: LOAD_OHMS}))


@htf.plug(psu=SiglentSpdPlug)
def configure(test: htf.TestApi, psu: SiglentSpdPlug) -> None:
    psu.configure_channel(CH, voltage=V_SET, current=I_LIMIT, ovp=4.0, ocp=1.0, ocp_enabled=True)


@htf.plug(psu=SiglentSpdPlug)
def power_on(test: htf.TestApi, psu: SiglentSpdPlug) -> None:
    psu.set_output(CH, True)
    psu.wait_for_voltage(CH, V_SET, tol=0.05, timeout=5.0)


@htf.measures(
    htf.Measurement('v_ch1').with_units(units.VOLT).in_range(3.2, 3.4),
    htf.Measurement('i_ch1').with_units(units.AMPERE).in_range(0.0, I_LIMIT),
    htf.Measurement('p_ch1').with_units(units.WATT).in_range(0.0, V_SET * I_LIMIT),
    htf.Measurement('mode_ch1').equals('CV'),
)
@htf.plug(psu=SiglentSpdPlug)
def measure(test: htf.TestApi, psu: SiglentSpdPlug) -> None:
    reading = psu.measure(CH)
    test.measurements.v_ch1 = reading.voltage
    test.measurements.i_ch1 = reading.current
    test.measurements.p_ch1 = reading.power
    test.measurements.mode_ch1 = reading.mode


@htf.plug(psu=SiglentSpdPlug)
def power_off(test: htf.TestApi, psu: SiglentSpdPlug) -> None:
    psu.set_output(CH, False)


def build_test(fake: bool) -> htf.Test:
    phases = [configure, power_on, measure, power_off]
    if fake:
        phases = [phase.with_plugs(psu=FakeSiglentSpdPlug) for phase in phases]
    return htf.Test(*phases, test_name='siglent_spd_example')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument('--fake', action='store_true', help='use a simulated supply')
    parser.add_argument('--resource', default='', help='VISA resource name of the supply')
    args = parser.parse_args(argv)
    if args.resource:
        # After importing the plug module: CONF.load before the key is declared is lost.
        CONF.load(siglent_spd_resource=args.resource)
    passed = build_test(args.fake).execute(test_start=lambda: 'example_dut')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
