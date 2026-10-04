import subprocess
import sys

import pytest

from siglent_spd_openhtf.fake_resource import FakeSpdResource, FakeTimeout


def test_idn_and_opc() -> None:
    fake = FakeSpdResource(model='SPD4306X', serial='SN1', firmware='9.9')
    assert fake.query('*IDN?') == 'Siglent Technologies,SPD4306X,SN1,9.9'
    assert fake.query('*OPC?') == '1'


def test_unknown_model_is_rejected() -> None:
    with pytest.raises(ValueError):
        FakeSpdResource(model='SPD9999X')


def test_defaults_follow_the_manual() -> None:
    fake = FakeSpdResource()
    assert fake.query('VOLTage? CH1') == '0.000000'
    assert fake.query('CURRent? CH2') == '0.000000'
    assert fake.query('OVP? CH1') == '6.000000'
    assert fake.query('OVP? CH2') == '32.000000'
    assert fake.query('OCP? CH4') == '3.200000'
    assert fake.query('OCP:STATe? CH1') == '0'
    assert fake.query('OCP:DELay? CH1') == '0.000000'
    assert fake.query('OUTPut? CH3') == '0'
    assert fake.query('OUTPut:ON:DELay? CH1') == '0.000000'
    assert fake.query('OUTPut:OFF:DELay? CH1') == '0.000000'
    assert fake.query('OUTPut:TRACK?') == '0'
    assert fake.query('MODE? CH2') == '0'
    assert fake.query('LOCK?') == '0'
    assert fake.query('OVP:PROTect:STATe? CH1') == '0'
    assert fake.query('OCP:PROTect:STATe? CH1') == '0'


def test_log_records_writes_and_queries_in_order() -> None:
    fake = FakeSpdResource()
    fake.write('VOLTage CH1,3')
    fake.query('VOLTage? CH1')
    fake.write('NONSENSE')
    assert fake.log == ['VOLTage CH1,3', 'VOLTage? CH1', 'NONSENSE']


def test_attributes_are_settable_and_close_blocks_io() -> None:
    fake = FakeSpdResource()
    fake.timeout = 5000
    fake.read_termination = '\n'
    fake.write_termination = '\n'
    assert (fake.timeout, fake.read_termination, fake.write_termination) == (5000, '\n', '\n')
    fake.close()
    assert fake.closed
    with pytest.raises(RuntimeError):
        fake.write('OUTPut:ALL 0')
    with pytest.raises(RuntimeError):
        fake.query('*IDN?')


@pytest.mark.parametrize(
    'command',
    [
        'VOLTage CH1,3',
        'VOLT CH1,3',
        'volt ch1,3',
        ':VOLTage CH1,3',
        ':SOURce:VOLTage:SET CH1,3',
        'SOUR:VOLT:SET CH1,3',
        'SOURce:VOLTage CH1, 3',
    ],
)
def test_voltage_accepts_long_short_and_prefixed_forms(command: str) -> None:
    fake = FakeSpdResource()
    fake.write(command)
    assert fake.query('VOLT? CH1') == '3.000000'
    assert fake.query(':SOURce:VOLTage:SET? CH1') == '3.000000'


def test_other_short_forms() -> None:
    fake = FakeSpdResource(loads={1: 10.0})
    fake.write('CURR CH1,1')
    fake.write('OUTP CH1,1')
    fake.write('OUTP:ON:DEL CH1,2')
    fake.write('OCP:STAT CH1,1')
    fake.write('OCP:DEL CH1,0.5')
    assert fake.query('CURRent? CH1') == '1.000000'
    assert fake.query('OUTPut:STATe? CH1') == '1'
    assert fake.query('OUTPut:ON:DELay? CH1') == '2.000000'
    assert fake.query('OCP:STATe? CH1') == '1'
    assert fake.query('OCP:DEL? CH1') == '0.500000'
    assert fake.query('MEAS:CURR? CH1') == '0.000000'
    assert fake.query('MEAS:RUN:MODE? CH1') == 'CV'
    assert fake.query('MEAS:MODE? CH1') == 'CV'
    assert fake.query('OVP:PROT:STAT? CH1') == '0'


def test_partial_keywords_are_errors() -> None:
    fake = FakeSpdResource()
    fake.write('VOL CH1,3')
    assert fake.query('VOLT? CH1') == '0.000000'
    with pytest.raises(FakeTimeout):
        fake.query('VOLTAG? CH1')


def test_unknown_header_is_ignored_on_write_and_times_out_on_query() -> None:
    fake = FakeSpdResource()
    fake.write('FROBnicate CH1,1')
    with pytest.raises(FakeTimeout):
        fake.query('FROBnicate? CH1')
    assert fake.log == ['FROBnicate CH1,1', 'FROBnicate? CH1']


@pytest.mark.parametrize('query', ['VOLTage? CH5', 'VOLTage?', 'VOLTage? CH0', 'MEASure:VOLTage?'])
def test_invalid_or_missing_channel_times_out(query: str) -> None:
    with pytest.raises(FakeTimeout):
        FakeSpdResource().query(query)


def test_write_with_invalid_channel_is_ignored() -> None:
    fake = FakeSpdResource()
    fake.write('VOLTage CH5,3')
    fake.write('VOLTage 3')
    assert all(fake.query(f'VOLTage? CH{n}') == '0.000000' for n in (1, 2, 3, 4))


def test_a_set_command_used_as_query_times_out() -> None:
    with pytest.raises(FakeTimeout):
        FakeSpdResource().query('VOLTage CH1,3')


@pytest.mark.parametrize(
    ('command', 'query', 'answer'),
    [
        ('VOLTage CH1,99', 'VOLTage? CH1', '6.000000'),
        ('VOLTage CH2,99', 'VOLTage? CH2', '32.000000'),
        ('CURRent CH1,99', 'CURRent? CH1', '3.200000'),
        ('OVP CH4,99', 'OVP? CH4', '6.000000'),
        ('OCP CH3,99', 'OCP? CH3', '3.200000'),
        ('VOLTage CH1,-1', 'VOLTage? CH1', '0.000000'),
        ('CURRent CH1,-1', 'CURRent? CH1', '0.000000'),
    ],
)
def test_out_of_range_values_are_clamped_silently(command: str, query: str, answer: str) -> None:
    fake = FakeSpdResource()
    fake.write(command)
    assert fake.query(query) == answer


def test_clamping_honours_track_mode() -> None:
    fake = FakeSpdResource()
    fake.write('OUTPut:TRACK SERIES')
    fake.write('VOLTage CH2,99')
    fake.write('CURRent CH2,99')
    assert fake.query('VOLTage? CH2') == '60.000000'
    assert fake.query('CURRent? CH2') == '3.200000'
    fake.write('OUTPut:TRACK PARALLEL')
    fake.write('VOLTage CH2,99')
    fake.write('CURRent CH2,99')
    assert fake.query('VOLTage? CH2') == '32.000000'
    assert fake.query('CURRent? CH2') == '6.400000'
    fake.write('VOLTage CH1,99')  # CH1 never follows the track mode
    assert fake.query('VOLTage? CH1') == '6.000000'


def test_reject_ignores_matching_writes_only() -> None:
    fake = FakeSpdResource(reject={'VOLTage CH1': 'locked'})
    fake.write('VOLTage CH1,3')
    fake.write('VOLTage CH2,3')
    assert fake.query('VOLTage? CH1') == '0.000000'
    assert fake.query('VOLTage? CH2') == '3.000000'
    assert fake.rejected == ['VOLTage CH1,3']
    assert fake.log[0] == 'VOLTage CH1,3'


@pytest.mark.parametrize(
    ('value', 'answer'), [('1', '1'), ('ON', '1'), ('on', '1'), ('0', '0'), ('OFF', '0')]
)
def test_boolean_words(value: str, answer: str) -> None:
    fake = FakeSpdResource()
    fake.write('OUTPut CH1,1')
    fake.write(f'OUTPut CH1,{value}')
    assert fake.query('OUTPut? CH1') == answer


def test_output_all() -> None:
    fake = FakeSpdResource()
    fake.write('OUTPut:ALL 1')
    assert [fake.query(f'OUTPut? CH{n}') for n in (1, 2, 3, 4)] == ['1'] * 4
    fake.write('OUTPut:ALL OFF')
    assert [fake.query(f'OUTPut? CH{n}') for n in (1, 2, 3, 4)] == ['0'] * 4


def test_open_circuit_measurement() -> None:
    fake = FakeSpdResource()
    fake.write('VOLTage CH1,3')
    assert fake.query('MEASure:VOLTage? CH1') == '0.000000'  # output off
    fake.write('OUTPut CH1,1')
    assert fake.query('MEASure:VOLTage? CH1') == '3.000000'
    assert fake.query('MEASure:CURRent? CH1') == '0.000000'
    assert fake.query('MEASure:POWER? CH1') == '0.000000'
    assert fake.query('MEASure:RUN:MODE? CH1') == 'CV'


def test_cv_to_cc_transition_with_a_load() -> None:
    fake = FakeSpdResource(loads={2: 10.0})
    fake.write('VOLTage CH2,5')
    fake.write('CURRent CH2,1')
    fake.write('OUTPut CH2,1')
    assert fake.query('MEASure:CURRent? CH2') == '0.500000'
    assert fake.query('MEASure:POWER? CH2') == '2.500000'
    assert fake.query('MEASure:RUN:MODE? CH2') == 'CV'
    fake.write('CURRent CH2,0.2')
    assert fake.query('MEASure:CURRent? CH2') == '0.200000'
    assert fake.query('MEASure:VOLTage? CH2') == '2.000000'
    assert fake.query('MEASure:RUN:MODE? CH2') == 'CC'
    fake.set_load(2, None)
    assert fake.query('MEASure:RUN:MODE? CH2') == 'CV'


def test_ocp_trips_and_turns_the_output_off() -> None:
    fake = FakeSpdResource(loads={1: 5.0})
    for command in ('VOLTage CH1,5', 'CURRent CH1,3', 'OCP CH1,0.5', 'OCP:STATe CH1,1'):
        fake.write(command)
    fake.write('OUTPut CH1,1')  # 1 A > 0.5 A
    assert fake.query('OUTPut? CH1') == '0'
    assert fake.query('OCP:PROTect:STATe? CH1') == '1'
    assert fake.query('OVP:PROTect:STATe? CH1') == '0'
    assert fake.query('MEASure:VOLTage? CH1') == '0.000000'
    fake.write('RESET:PROTect CH1')
    assert fake.query('OCP:PROTect:STATe? CH1') == '0'


def test_ocp_does_not_trip_while_disabled() -> None:
    fake = FakeSpdResource(loads={1: 5.0})
    fake.write('VOLTage CH1,5')
    fake.write('CURRent CH1,3')
    fake.write('OCP CH1,0.5')
    fake.write('OUTPut CH1,1')
    assert fake.query('OUTPut? CH1') == '1'


def test_ovp_trips_and_turns_the_output_off() -> None:
    fake = FakeSpdResource()
    fake.write('OVP CH2,4')
    fake.write('VOLTage CH2,5')
    fake.write('OUTPut CH2,1')
    assert fake.query('OUTPut? CH2') == '0'
    assert fake.query('OVP:PROTect:STATe? CH2') == '1'
    fake.write('reset:prot CH2')
    assert fake.query('OVP:PROTect:STATe? CH2') == '0'


def test_trip_helpers() -> None:
    fake = FakeSpdResource()
    fake.write('OUTPut CH1,1')
    fake.trip_ovp(1)
    fake.trip_ocp(2)
    assert fake.query('OUTPut? CH1') == '0'
    assert fake.query('OVP:PROTect:STATe? CH1') == '1'
    assert fake.query('OCP:PROTect:STATe? CH2') == '1'


@pytest.mark.parametrize(
    ('word', 'number'), [('INDEPENDENT', '0'), ('SERIES', '1'), ('PARALLEL', '2'), ('2', '2')]
)
def test_track_accepts_words_and_numbers_and_returns_a_number(word: str, number: str) -> None:
    fake = FakeSpdResource()
    fake.write(f'OUTPut:TRACK {word}')
    assert fake.query('OUTPut:TRACK?') == number


def test_sense_on_ch2_and_ch3_only() -> None:
    fake = FakeSpdResource()
    fake.write('MODE CH2,4W')
    fake.write('MODE CH3,1')
    assert fake.query('MODE? CH2') == '1'
    assert fake.query('MODE? CH3') == '1'
    fake.write('MODE CH2,2W')
    assert fake.query('MODE? CH2') == '0'
    fake.write('MODE CH1,4W')
    with pytest.raises(FakeTimeout):
        fake.query('MODE? CH1')


def test_lock_and_delays() -> None:
    fake = FakeSpdResource()
    fake.write('LOCK 1')
    assert fake.query('LOCK?') == '1'
    fake.write(':SOURce:LOCK:STATe 0')
    assert fake.query('LOCK?') == '0'
    fake.write('OUTPut:ON:DELay CH1,3')
    fake.write('OUTPut:OFF:DELay CH1,1.5')
    assert fake.query('OUTPut:ON:DELay? CH1') == '3.000000'
    assert fake.query('OUTPut:OFF:DELay? CH1') == '1.500000'


def test_set_load_validates_channel() -> None:
    with pytest.raises(ValueError):
        FakeSpdResource().set_load(5, 1.0)


def test_package_import_does_not_import_pyvisa() -> None:
    code = (
        'import sys, siglent_spd_openhtf.fake_resource, siglent_spd_openhtf.plug;'
        "sys.exit(1 if 'pyvisa' in sys.modules else 0)"
    )
    assert subprocess.run([sys.executable, '-c', code], check=False).returncode == 0
