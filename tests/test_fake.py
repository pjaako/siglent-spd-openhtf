import subprocess
import sys

import pytest

from siglent_spd_openhtf.fake_resource import FakeSpdResource, FakeTimeout, to_float32


def test_idn_and_opc() -> None:
    fake = FakeSpdResource(model='SPD4306X', serial='SN1', firmware='9.9')
    assert fake.query('*IDN?') == 'Siglent Technologies,SPD4306X,SN1,9.9'
    assert fake.query('*OPC?') == '1'


def test_unknown_model_is_rejected() -> None:
    with pytest.raises(ValueError):
        FakeSpdResource(model='SPD9999X')


def test_defaults_follow_the_hardware() -> None:
    fake = FakeSpdResource()
    assert fake.query('VOLTage? CH1') == '0.000000'
    assert fake.query('CURRent? CH2') == '0.000000'
    assert fake.query('OVP? CH1') == '6.600000'
    assert fake.query('OVP? CH2') == '35.200001'
    assert fake.query('OCP? CH4') == '3.520000'
    assert fake.query('OCP:STATe? CH1') == '0'
    assert fake.query('OCP:DELay? CH1') == '0.000000'
    assert fake.query('OUTPut? CH3') == '0'
    assert fake.query('OUTPut:ON:DELay? CH1') == '0.000000'
    assert fake.query('OUTPut:OFF:DELay? CH1') == '0.000000'
    assert fake.query('OUTPut:TRACK?') == '0'
    assert fake.query('MODE? CH2') == '0'
    assert fake.query('LOCK?') == '0'
    assert fake.query('*ESR?') == '0'
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


@pytest.mark.parametrize(
    ('write', 'query', 'answer'),
    [
        (':SOURce:VOLTage:SET CH2,3', ':SOURce:VOLTage:SET? CH2', '3.000000'),
        (':SOURce:VOLTage:SET CH2,3', 'VOLT? CH2', '3.000000'),
        (':SOURce:CURRent:SET CH2,2', ':SOURce:CURRent:SET? CH2', '2.000000'),
        ('CURR:SET CH2,2', 'CURR? CH2', '2.000000'),
        ('CURR CH2,2', ':SOURce:CURRent:SET? CH2', '2.000000'),
        (':SOURce:LOCK:STATe ON', ':SOURce:LOCK:STATe?', '1'),
        (':SOURce:LOCK:STATe 1', 'LOCK?', '1'),
        ('LOCK ON', ':SOURce:LOCK:STATe?', '1'),
        ('LOCK:STAT ON', 'LOCK?', '1'),
        (':SOURce:OCP:STATe CH2,1', ':SOURce:OCP:STATe? CH2', '1'),
        (':SOURce:OCP:STATe CH2, 1', ':SOURce:OCP:STATe? CH2', '1'),
        ('OUTPut:STATe CH2,0', 'OUTPut? CH2', '0'),
        ('OUTPut:ALL:STATe 1', 'OUTPut? CH2', '1'),
    ],
)
def test_verbatim_and_short_forms_with_optional_nodes(write: str, query: str, answer: str) -> None:
    fake = FakeSpdResource()
    fake.write(write)
    assert fake.query(query) == answer


def test_verbatim_forms_address_the_named_channel() -> None:
    fake = FakeSpdResource()
    for n in (1, 2, 3, 4):
        fake.write(f':SOURce:CURRent:SET CH{n},{n / 10}')
    assert [fake.query(f':SOURce:CURRent:SET? CH{n}') for n in (1, 2, 3, 4)] == [
        '0.100000',
        '0.200000',
        '0.300000',
        '0.400000',
    ]


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


@pytest.mark.parametrize(
    'query', ['VOLTage? CH5', 'VOLTage? CH0', 'VOLTage? 1', 'VOLTage? (CH1)', 'MEASure:VOLTage? 2']
)
def test_invalid_channel_times_out(query: str) -> None:
    with pytest.raises(FakeTimeout):
        FakeSpdResource().query(query)


def test_voltage_query_without_a_channel_answers_ch1() -> None:
    # ASSUMPTION(hw): CH1 or the panel-selected channel (docs/hardware_findings.md Q8).
    fake = FakeSpdResource()
    fake.write('VOLTage CH1,5')
    fake.write('VOLTage CH2,14')
    assert fake.query('VOLTage?') == '5.000000'
    assert fake.query('VOLTage?CH2') == '14.000000'  # the space before the channel is optional


@pytest.mark.parametrize('query', ['OUTPut:TRACK? CH1', 'LOCK? CH1', 'OUTPut:ALL? CH1'])
def test_a_query_without_a_channel_gets_no_answer_when_given_one(query: str) -> None:
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
        ('VOLTage CH1,7.5', 'VOLTage? CH1', '6.060000'),
        ('VOLTage CH1,6', 'VOLTage? CH1', '6.000000'),
        ('VOLTage CH2,99', 'VOLTage? CH2', '32.320000'),
        ('CURRent CH1,4', 'CURRent? CH1', '3.232000'),
        ('CURRent CH1,3.2', 'CURRent? CH1', '3.200000'),
        ('OVP CH1,7.2', 'OVP? CH1', '6.600000'),
        ('OVP CH4,99', 'OVP? CH4', '6.600000'),
        ('OVP CH1,0.3', 'OVP? CH1', '0.600000'),
        ('OVP CH1,0', 'OVP? CH1', '0.600000'),
        ('OCP CH1,3.84', 'OCP? CH1', '3.520000'),
        ('OCP CH1,0.16', 'OCP? CH1', '0.320000'),
        ('OCP CH1,0', 'OCP? CH1', '0.320000'),
        ('OCP CH3,99', 'OCP? CH3', '3.520000'),
        ('VOLTage CH1,-1', 'VOLTage? CH1', '0.000000'),
        ('CURRent CH1,-1', 'CURRent? CH1', '0.000000'),
        ('OCP:DELay CH1,3601', 'OCP:DELay? CH1', '3600.000000'),
        ('OCP:DELay CH1,-1', 'OCP:DELay? CH1', '0.000000'),
        # ASSUMPTION(hw): same as OCP:DELay (the ON/OFF delay writes were not exercised)
        ('OUTPut:ON:DELay CH1,4000', 'OUTPut:ON:DELay? CH1', '3600.000000'),
        ('OUTPut:OFF:DELay CH1,-5', 'OUTPut:OFF:DELay? CH1', '0.000000'),
    ],
)
def test_out_of_range_values_are_clamped_silently(command: str, query: str, answer: str) -> None:
    fake = FakeSpdResource()
    fake.write(command)
    assert fake.query(query) == answer
    assert fake.query('*ESR?') == '0'  # nothing is ever reported


def test_clamping_follows_the_rating_of_each_model() -> None:
    fake = FakeSpdResource(model='SPD4121X')
    fake.write('VOLTage CH2,99')
    fake.write('CURRent CH2,99')
    fake.write('OVP CH1,99')
    assert fake.query('VOLTage? CH2') == '12.120000'
    assert fake.query('CURRent? CH2') == '10.100000'
    assert fake.query('OVP? CH1') == '16.500000'


@pytest.mark.parametrize(
    ('keyword', 'volt', 'curr', 'ovp', 'ocp', 'delay'),
    [
        ('MINimum', '0.000000', '0.000000', '0.600000', '0.320000', '0.000000'),
        ('MIN', '0.000000', '0.000000', '0.600000', '0.320000', '0.000000'),
        ('MAXimum', '6.060000', '3.232000', '6.600000', '3.520000', '3600.000000'),
        ('max', '6.060000', '3.232000', '6.600000', '3.520000', '3600.000000'),
        ('DEFault', '0.000000', '0.000000', '6.600000', '3.520000', '0.000000'),
        ('DEF', '0.000000', '0.000000', '6.600000', '3.520000', '0.000000'),
    ],
)
def test_keywords_in_set_commands(
    keyword: str, volt: str, curr: str, ovp: str, ocp: str, delay: str
) -> None:
    fake = FakeSpdResource()
    for command in ('VOLTage CH1,3', 'CURRent CH1,2', 'OVP CH1,3', 'OCP CH1,1', 'OCP:DELay CH1,5'):
        fake.write(command)
    fake.write(f'VOLTage CH1,{keyword}')
    fake.write(f'CURRent CH1,{keyword}')
    fake.write(f'OVP CH1,{keyword}')
    fake.write(f'OCP CH1,{keyword}')
    fake.write(f'OCP:DELay CH1,{keyword}')
    assert fake.query('VOLTage? CH1') == volt
    assert fake.query('CURRent? CH1') == curr
    assert fake.query('OVP? CH1') == ovp
    assert fake.query('OCP? CH1') == ocp
    assert fake.query('OCP:DELay? CH1') == delay


@pytest.mark.parametrize(
    ('query', 'answer'),
    [
        ('VOLTage? CH1,MAX', '6.060000'),
        ('VOLTage? CH1,MAXimum', '6.060000'),
        ('VOLTage? CH1, MAX', '6.060000'),
        (':SOURce:VOLTage:SET? CH2,MAXimum', '32.320000'),
        ('VOLTage? CH1,MIN', '0.000000'),
        ('VOLTage? CH1,DEFault', '0.000000'),
        ('CURRent? CH4,MAX', '3.232000'),
        ('CURRent? CH1,MIN', '0.000000'),
        ('CURRent? CH1,DEF', '0.000000'),
    ],
)
def test_keywords_as_query_arguments_for_voltage_and_current(query: str, answer: str) -> None:
    assert FakeSpdResource().query(query) == answer


@pytest.mark.parametrize(
    'query',
    [
        'OVP? CH1,MAX',
        'OCP? CH1,MAX',
        'OCP? CH2,MIN',
        'OCP:DELay? CH1,MAX',
        'OUTPut:ON:DELay? CH1,MAX',
        'OUTPut:OFF:DELay? CH1,DEF',
        'VOLTage? CH1,7',
    ],
)
def test_other_keyword_queries_get_no_answer(query: str) -> None:
    with pytest.raises(FakeTimeout):
        FakeSpdResource().query(query)


def test_max_is_per_channel_and_ignores_the_track_mode() -> None:
    fake = FakeSpdResource()
    for word in ('SERIES', 'PARALLEL', 'INDEPENDENT'):
        fake.write(f'OUTPut:TRACK {word}')
        assert fake.query('VOLTage? CH2,MAX') == '32.320000'
        assert fake.query('CURRent? CH2,MAX') == '3.232000'


def test_values_are_stored_as_float32() -> None:
    fake = FakeSpdResource()
    assert to_float32(35.2) != 35.2
    assert fake.query('OVP? CH2') == '35.200001'
    assert fake.query('OVP? CH3') == '35.200001'
    fake.write('VOLTage CH1,1.2345')
    assert fake.query('VOLTage? CH1') == '1.234500'
    assert fake.channels[1].voltage == to_float32(1.2345)
    fake.write('OVP CH1,6.6')
    assert fake.query('OVP? CH1') == '6.600000'


def test_non_numeric_values_and_invalid_channels_change_nothing() -> None:
    fake = FakeSpdResource()
    fake.write('VOLTage CH1,abc')
    fake.write('VOLTage CH1,nan')
    fake.write('CURRent CH1')
    assert fake.query('VOLTage? CH1') == '0.000000'
    assert fake.query('*ESR?') == '0'
    assert fake.lock == 0


def test_coupled_modes_report_the_combined_value_on_ch2() -> None:
    fake = FakeSpdResource()
    fake.write('VOLTage CH2,14')
    fake.write('CURRent CH2,3')
    fake.write('OUTPut:TRACK SERIES')
    assert fake.query('VOLTage? CH2') == '28.000000'  # verified: 2 x 14 V
    assert fake.query('CURRent? CH2') == '3.000000'
    assert fake.query('VOLTage? CH3') == '14.000000'
    fake.write('OUTPut:TRACK PARALLEL')
    assert fake.query('VOLTage? CH2') == '14.000000'
    assert fake.query('CURRent? CH2') == '6.000000'  # verified: 2 x 3 A
    assert fake.query('CURRent? CH3') == '3.000000'
    fake.write('OUTPut:TRACK INDEPENDENT')
    assert fake.query('VOLTage? CH2') == '14.000000'
    assert fake.query('CURRent? CH2') == '3.000000'


def test_writing_ch2_in_a_coupled_mode_is_the_combined_value_and_ch3_follows() -> None:
    # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md run 2, Q21)
    fake = FakeSpdResource()
    fake.write('VOLTage CH2,14')
    fake.write('CURRent CH2,3')
    fake.write('OUTPut:TRACK SERIES')
    assert fake.query('VOLTage? CH2') == '28.000000'
    fake.write('VOLTage CH2,20')
    assert fake.query('VOLTage? CH2') == '20.000000'
    assert fake.query('VOLTage? CH3') == '10.000000'
    fake.write('VOLTage CH2,MAXimum')  # clamped as a whole at the per-channel MAX
    assert fake.query('VOLTage? CH2') == '32.320000'
    assert fake.query('VOLTage? CH3') == '16.160000'
    fake.write('OVP CH2,MAXimum')  # OVP and OCP stay per channel
    assert (fake.query('OVP? CH2'), fake.query('OVP? CH3')) == ('35.200001', '35.200001')
    fake.write('OUTPut:TRACK PARALLEL')
    assert fake.query('VOLTage? CH2') == '16.160000'  # the half survives, not combined here
    assert fake.query('CURRent? CH2') == '6.000000'
    assert fake.query('CURRent? CH3') == '3.000000'
    fake.write('CURRent CH2,5')
    assert (fake.query('CURRent? CH2'), fake.query('CURRent? CH3')) == ('5.000000', '2.500000')
    fake.write('CURRent CH2,MAXimum')  # the keyword is the per-channel MAX, 5 A above was accepted
    assert (fake.query('CURRent? CH2'), fake.query('CURRent? CH3')) == ('3.232000', '1.616000')
    fake.write('OCP CH2,MAXimum')
    assert (fake.query('OCP? CH2'), fake.query('OCP? CH3')) == ('3.520000', '3.520000')
    fake.write('OUTPut:TRACK INDEPENDENT')  # both halves keep their value
    assert (fake.query('VOLTage? CH2'), fake.query('CURRent? CH2')) == ('16.160000', '1.616000')
    assert (fake.query('VOLTage? CH3'), fake.query('CURRent? CH3')) == ('16.160000', '1.616000')


def test_coupled_keywords_are_combined_too() -> None:
    # ASSUMPTION(hw): MINimum and DEFault were not tried in a coupled mode (MAXimum was).
    fake = FakeSpdResource()
    fake.write('OUTPut:TRACK SERIES')
    fake.write('VOLTage CH2,10')
    fake.write('VOLTage CH2,MINimum')
    assert (fake.query('VOLTage? CH2'), fake.query('VOLTage? CH3')) == ('0.000000', '0.000000')
    fake.write('VOLTage CH2,10')
    fake.write('VOLTage CH2,DEFault')
    assert fake.query('VOLTage? CH2') == '0.000000'
    fake.write('VOLTage CH2,-1')
    assert fake.query('VOLTage? CH3') == '0.000000'


def test_a_numeric_combined_write_may_exceed_the_per_channel_max() -> None:
    # verified: 5 A written to CH2 in PARALLEL read back 5 A (docs/hardware_findings.md run 2);
    # ASSUMPTION(hw): the numeric limit is twice MAX, which was not tried.
    fake = FakeSpdResource()
    fake.write('OUTPut:TRACK PARALLEL')
    fake.write('CURRent CH2,5')
    assert fake.query('CURRent? CH2') == '5.000000'
    fake.write('CURRent CH2,9')
    assert fake.query('CURRent? CH2') == '6.464000'
    assert fake.query('CURRent? CH3') == '3.232000'


def test_the_uncoupled_quantity_of_ch2_is_stored_per_channel() -> None:
    # not tried on hardware: the current of CH2 in SERIES, the voltage of CH2 in PARALLEL
    fake = FakeSpdResource()
    fake.write('OUTPut:TRACK SERIES')
    fake.write('CURRent CH2,2')
    assert fake.channels[2].current == 2.0
    assert fake.channels[3].current == 0.0


def test_setting_the_off_delay_to_zero_switches_a_pending_output_off_at_once() -> None:
    # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md run 2, Q22)
    fake = FakeSpdResource()
    fake.write('OUTPut:OFF:DELay CH1,2')
    fake.write('OUTPut CH1,1')
    fake.write('OUTPut CH1,0')
    assert fake.query('OUTPut? CH1') == '1'  # pending
    fake.write('OUTPut:OFF:DELay CH1,0')
    assert fake.query('OUTPut? CH1') == '0'
    assert fake.channels[1].off_remaining is None
    fake.advance(5)
    assert fake.query('OUTPut? CH1') == '0'


def test_all_off_honours_the_off_delay_like_a_single_channel() -> None:
    # verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-04 (docs/hardware_findings.md run 2, Q22)
    fake = FakeSpdResource()
    fake.write('OUTPut:OFF:DELay CH1,2')
    fake.write('OUTPut CH1,1')
    fake.write('OUTPut:ALL 0')
    assert fake.query('OUTPut? CH1') == '1'
    fake.advance(1.9)
    assert fake.query('OUTPut? CH1') == '1'
    fake.advance(0.2)
    assert fake.query('OUTPut? CH1') == '0'


def test_entering_a_coupled_mode_copies_ch2_setpoints_to_ch3_for_good() -> None:
    fake = FakeSpdResource()
    for command in ('VOLTage CH2,14', 'CURRent CH2,3', 'VOLTage CH3,12', 'CURRent CH3,2'):
        fake.write(command)
    fake.write('OVP CH3,20')
    fake.write('OUTPut:TRACK SERIES')
    assert (fake.query('VOLTage? CH3'), fake.query('CURRent? CH3')) == ('14.000000', '3.000000')
    fake.write('OUTPut:TRACK PARALLEL')
    fake.write('OUTPut:TRACK INDEPENDENT')
    assert (fake.query('VOLTage? CH3'), fake.query('CURRent? CH3')) == ('14.000000', '3.000000')
    assert fake.query('OVP? CH3') == '20.000000'  # OVP and OCP are not changed
    assert fake.query('OVP? CH2') == '35.200001'
    assert fake.query('OCP? CH2') == '3.520000'


def test_going_independent_does_not_copy() -> None:
    fake = FakeSpdResource()
    fake.write('VOLTage CH2,14')
    fake.write('VOLTage CH3,12')
    fake.write('OUTPut:TRACK INDEPENDENT')
    assert fake.query('VOLTage? CH3') == '12.000000'


def test_ovp_and_ocp_are_not_changed_by_the_track_mode() -> None:
    fake = FakeSpdResource()
    fake.write('OUTPut:TRACK SERIES')
    assert fake.query('OVP? CH2') == '35.200001'
    fake.write('OUTPut:TRACK PARALLEL')
    assert fake.query('OCP? CH2') == '3.520000'


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


def test_ocp_value_zero_trips_even_with_no_current() -> None:
    fake = FakeSpdResource()
    fake.write('VOLTage CH1,3')
    fake.write('OCP:STATe CH1,1')
    fake.channels[1].ocp = 0.0  # the panel range is 0.1x..1.1x, so only a test can set 0
    fake.write('OUTPut CH1,1')  # open circuit: I = 0 >= 0
    assert fake.query('OUTPut? CH1') == '0'
    assert fake.query('OCP:PROTect:STATe? CH1') == '1'


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


def test_output_off_with_an_off_delay_reads_on_until_the_time_has_passed() -> None:
    fake = FakeSpdResource(loads={1: 10.0})
    fake.write('VOLTage CH1,5')
    fake.write('CURRent CH1,1')
    fake.write('OUTPut CH1,1')
    fake.write('OUTPut:OFF:DELay CH1,2')
    fake.write('OUTPut CH1,0')
    assert fake.query('OUTPut? CH1') == '1'
    assert fake.query('MEASure:VOLTage? CH1') == '5.000000'  # still delivering power
    fake.advance(1.5)
    assert fake.query('OUTPut? CH1') == '1'
    fake.advance(0.5)
    assert fake.query('OUTPut? CH1') == '0'
    assert fake.query('MEASure:VOLTage? CH1') == '0.000000'


def test_switching_on_again_cancels_a_pending_switch_off_and_all_off_honours_delays() -> None:
    fake = FakeSpdResource()
    fake.write('OUTPut:OFF:DELay CH2,1')
    fake.write('OUTPut:ALL 1')
    fake.write('OUTPut:ALL 0')
    assert [fake.query(f'OUTPut? CH{n}') for n in (1, 2, 3, 4)] == ['0', '1', '0', '0']
    fake.write('OUTPut CH2,1')
    fake.advance(10)
    assert fake.query('OUTPut? CH2') == '1'


def test_off_delay_of_zero_switches_off_at_once() -> None:
    fake = FakeSpdResource()
    fake.write('OUTPut CH1,1')
    fake.write('OUTPut CH1,0')
    assert fake.query('OUTPut? CH1') == '0'


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
    fake.write('MODE CH4,4W')
    assert fake.query('MODE? CH1') == '0'  # verified: the supply answers 0 for CH1
    assert fake.sense == {2: 0, 3: 1}  # ASSUMPTION(hw): CH1/CH4 writes are ignored (not tried)
    with pytest.raises(FakeTimeout):
        fake.query('MODE? CH4')  # ASSUMPTION(hw): not tried


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


def test_every_accepted_write_locks_and_queries_never_do() -> None:
    fake = FakeSpdResource()
    for query in ('VOLTage? CH1', 'OUTPut:TRACK?', '*IDN?', 'MEASure:VOLTage? CH1', '*ESR?'):
        fake.query(query)
    assert fake.query('LOCK?') == '0'
    fake.write('VOLTage CH1,1')
    assert fake.lock == 1
    assert fake.query('LOCK?') == '1'
    fake.write('LOCK 0')
    assert fake.query('LOCK?') == '0'  # the LOCK write itself does not re-lock
    fake.write('OUTPut CH1,0')
    assert fake.lock == 1
    fake.write(':SOURce:LOCK:STATe OFF')
    assert fake.lock == 0
    fake.write('LOCK ON')
    assert fake.lock == 1


@pytest.mark.parametrize('command', ['VOLTage CH5,1', 'VOLTage CH1,abc', 'FOOBar CH1,1', 'LOCK 0'])
def test_ignored_writes_do_not_lock(command: str) -> None:
    fake = FakeSpdResource()
    fake.write(command)
    assert fake.lock == 0


def test_a_rejected_write_does_not_lock() -> None:
    fake = FakeSpdResource(reject={'VOLTage CH1': 'x'})
    fake.write('VOLTage CH1,1')
    assert fake.lock == 0


def test_esr_is_set_by_unknown_headers_and_unanswered_queries_and_clears_on_read() -> None:
    fake = FakeSpdResource()
    assert fake.query('*ESR?') == '0'
    fake.write('FOOBar CH1,1')
    assert fake.query('*ESR?') == '32'
    assert fake.query('*ESR?') == '0'  # reading clears
    with pytest.raises(FakeTimeout):
        fake.query('FOOBar? CH1')
    assert fake.query('*ESR?') == '32'
    with pytest.raises(FakeTimeout):
        fake.query('VOLTage? CH5')  # an unanswered query counts too
    fake.write('*CLS')
    assert fake.query('*ESR?') == '0'
    with pytest.raises(FakeTimeout):
        fake.query('OVP? CH1,MAX')
    fake.write('*CLS')
    assert fake.query('*ESR?') == '0'


def test_esr_ignores_invalid_channels_bad_values_and_clamping() -> None:
    fake = FakeSpdResource()
    fake.write('VOLTage CH5,1')
    fake.write('VOLTage CH1,abc')
    fake.write('VOLTage CH1,7.5')  # clamped
    assert fake.query('*ESR?') == '0'


def test_opc_sets_bit_0_and_the_other_status_queries_answer_zero() -> None:
    fake = FakeSpdResource()
    fake.write('*OPC')
    assert fake.query('*ESR?') == '1'
    assert [fake.query(q) for q in ('*STB?', '*ESE?', '*SRE?')] == ['0', '0', '0']
    fake.write('*WAI')  # accepted, no visible effect
    assert fake.query('*ESR?') == '0'
    assert fake.query('*OPC?') == '1'


def test_semicolon_chaining_concatenates_the_replies_without_a_separator() -> None:
    fake = FakeSpdResource(serial='SN1', firmware='4.1.2.9R1')
    assert fake.query('*IDN?;*OPC?') == 'Siglent Technologies,SPD4323X,SN1,4.1.2.9R11'
    assert fake.query('VOLTage CH1,1.25;VOLTage? CH1') == '1.250000'
    assert fake.query('VOLTage CH1,1.5;*OPC?') == '1'
    assert fake.query('VOLTage? CH1;CURRent? CH1') == '1.5000000.000000'
    fake.write('VOLTage CH2,2;CURRent CH2,0.5')
    assert (fake.query('VOLTage? CH2'), fake.query('CURRent? CH2')) == ('2.000000', '0.500000')
    assert fake.log[0] == '*IDN?;*OPC?'  # one log entry per line sent
    with pytest.raises(FakeTimeout):
        fake.query('VOLTage CH1,1;VOLTage CH1,2')  # no query in the line


def test_set_load_validates_channel() -> None:
    with pytest.raises(ValueError):
        FakeSpdResource().set_load(5, 1.0)


def test_package_import_does_not_import_pyvisa() -> None:
    code = (
        'import sys, siglent_spd_openhtf.fake_resource, siglent_spd_openhtf.plug;'
        "sys.exit(1 if 'pyvisa' in sys.modules else 0)"
    )
    assert subprocess.run([sys.executable, '-c', code], check=False).returncode == 0
