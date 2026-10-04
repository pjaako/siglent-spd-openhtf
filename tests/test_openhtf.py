"""Real openhtf.Test executions with the fake supply injected through a plug subclass."""

from __future__ import annotations

from typing import ClassVar

import openhtf as htf
from openhtf.util import units

from siglent_spd_openhtf import FakeSpdResource, SiglentSpdPlug


class FakePsu(SiglentSpdPlug):
    instances: ClassVar[list[FakePsu]] = []

    def __init__(self) -> None:
        self.fake = FakeSpdResource(loads={1: 10.0})
        super().__init__(resource=self.fake, outputs_off_on_teardown=False)
        FakePsu.instances.append(self)


class TearingDownFakePsu(SiglentSpdPlug):
    """Keeps the default teardown policy: all outputs off."""

    instances: ClassVar[list[TearingDownFakePsu]] = []

    def __init__(self) -> None:
        self.fake = FakeSpdResource(loads={1: 10.0})
        super().__init__(resource=self.fake)
        TearingDownFakePsu.instances.append(self)


@htf.measures(htf.Measurement('v_ch1').with_units(units.VOLT).in_range(3.2, 3.4))
@htf.plug(psu=FakePsu)
def measure_ch1(test: htf.TestApi, psu: FakePsu) -> None:
    psu.configure_channel(1, voltage=3.3, current=0.5)
    psu.set_output(1, True)
    test.measurements.v_ch1 = psu.wait_for_voltage(1, 3.3)


@htf.measures(htf.Measurement('v_ch1').with_units(units.VOLT).in_range(3.2, 3.4))
@htf.plug(psu=FakePsu)
def measure_out_of_range(test: htf.TestApi, psu: FakePsu) -> None:
    psu.configure_channel(1, voltage=5, current=0.8)
    psu.set_output(1, True)
    test.measurements.v_ch1 = psu.measure_voltage(1)


@htf.plug(psu=TearingDownFakePsu)
def leave_output_on(test: htf.TestApi, psu: TearingDownFakePsu) -> None:
    psu.configure_channel(1, voltage=3, current=0.5)
    psu.set_output(1, True)


@htf.plug(psu=FakePsu)
def breaks(test: htf.TestApi, psu: FakePsu) -> None:
    psu.set_voltage(1, 7)  # above the 6 V rating of CH1: the guard raises ValueError


def test_openhtf_test_passes_with_the_fake_plug() -> None:
    FakePsu.instances.clear()
    test = htf.Test(measure_ch1, test_name='psu_pass')
    assert test.execute(test_start=lambda: 'dut') is True
    assert len(FakePsu.instances) == 1
    log = FakePsu.instances[0].fake.log
    assert 'VOLTage CH1,3.3' in log
    assert 'OUTPut CH1,1' in log


def test_openhtf_test_fails_when_the_measurement_is_out_of_range() -> None:
    test = htf.Test(measure_out_of_range, test_name='psu_fail')
    assert test.execute(test_start=lambda: 'dut') is False


def test_openhtf_test_does_not_pass_when_a_phase_raises() -> None:
    test = htf.Test(breaks, test_name='psu_error')
    assert test.execute(test_start=lambda: 'dut') is False


def test_openhtf_calls_teardown_which_turns_the_outputs_off_and_closes() -> None:
    TearingDownFakePsu.instances.clear()
    test = htf.Test(leave_output_on, test_name='psu_teardown')
    assert test.execute(test_start=lambda: 'dut') is True
    fake = TearingDownFakePsu.instances[0].fake
    assert fake.channels[1].output is False
    assert fake.closed
    assert 'OUTPut:ALL 0' in fake.log
    assert fake.log[-2:] == ['LOCK 0', 'LOCK?']


def test_openhtf_teardown_runs_after_a_failing_phase() -> None:
    TearingDownFakePsu.instances.clear()

    @htf.plug(psu=TearingDownFakePsu)
    def on_then_fail(test: htf.TestApi, psu: TearingDownFakePsu) -> None:
        psu.configure_channel(1, voltage=3, current=0.5)
        psu.set_output(1, True)
        raise RuntimeError('boom')

    assert htf.Test(on_then_fail, test_name='psu_boom').execute(test_start=lambda: 'dut') is False
    fake = TearingDownFakePsu.instances[0].fake
    assert fake.channels[1].output is False
    assert fake.closed
