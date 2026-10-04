# Hardware acceptance report

- Generated: 2026-10-04 18:36:03 UTC
- Tool: `tools/hw_acceptance.py`; resource `TCPIP::<redacted>::5025::SOCKET`; command terminator `'\n'`, read termination `'\n'`
- Instrument: `Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1`
- Mode: no-output mode (the tool never sends output ON)
- Target channel for write experiments: CH1
- Plug package importable: yes
- Redaction: host and serial number replaced by `<redacted>` (public repository); the `.local.` log keeps everything.

## Safety log

- output states at start: {1: '0', 2: '0', 3: '0', 4: '0'}; OUTPut:ALL? -> '0'
- snapshot saved to acceptance_snapshot.local.json before the first write (channels that may be written: [1, 2, 3, 4])
- restore: 36 items, 0 written back, 36 unchanged, 0 skipped (not snapshotted), 0 FAILED
- output states at the end: {1: '0', 2: '0', 3: '0', 4: '0'}

Snapshot taken before the first write:

```
           CH        1 CH        2 CH        3 CH        4
voltage        5.000000    14.000000    12.000000     0.000000
current        2.000000     3.000000     2.000000     0.000000
ovp            6.600000    35.200001    35.200001     6.600000
ocp            3.520000     3.520000     3.520000     3.520000
ocp_state             0            0            0            0
ocp_delay      0.000000     0.000000     0.000000     0.000000
on_delay       0.000000     0.000000     0.000000     0.000000
off_delay      0.000000     0.000000     0.000000     0.000000
output                0            0            0            0
track='0'  sense CH2='0' CH3='0'  lock='0'
```

Restore at the end (`unchanged` = already equal, nothing written):

| item | wanted | now | status |
|---|---|---|---|
| track | `0` | `0` | unchanged |
| sense CH2 | `0` | `0` | unchanged |
| sense CH3 | `0` | `0` | unchanged |
| CH1 ovp | `6.600000` | `6.600000` | unchanged |
| CH1 ocp | `3.520000` | `3.520000` | unchanged |
| CH1 ocp_delay | `0.000000` | `0.000000` | unchanged |
| CH1 ocp_state | `0` | `0` | unchanged |
| CH1 voltage | `5.000000` | `5.000000` | unchanged |
| CH1 current | `2.000000` | `2.000000` | unchanged |
| CH1 on_delay | `0.000000` | `0.000000` | unchanged |
| CH1 off_delay | `0.000000` | `0.000000` | unchanged |
| CH2 ovp | `35.200001` | `35.200001` | unchanged |
| CH2 ocp | `3.520000` | `3.520000` | unchanged |
| CH2 ocp_delay | `0.000000` | `0.000000` | unchanged |
| CH2 ocp_state | `0` | `0` | unchanged |
| CH2 voltage | `14.000000` | `14.000000` | unchanged |
| CH2 current | `3.000000` | `3.000000` | unchanged |
| CH2 on_delay | `0.000000` | `0.000000` | unchanged |
| CH2 off_delay | `0.000000` | `0.000000` | unchanged |
| CH3 ovp | `35.200001` | `35.200001` | unchanged |
| CH3 ocp | `3.520000` | `3.520000` | unchanged |
| CH3 ocp_delay | `0.000000` | `0.000000` | unchanged |
| CH3 ocp_state | `0` | `0` | unchanged |
| CH3 voltage | `12.000000` | `12.000000` | unchanged |
| CH3 current | `2.000000` | `2.000000` | unchanged |
| CH3 on_delay | `0.000000` | `0.000000` | unchanged |
| CH3 off_delay | `0.000000` | `0.000000` | unchanged |
| CH4 ovp | `6.600000` | `6.600000` | unchanged |
| CH4 ocp | `3.520000` | `3.520000` | unchanged |
| CH4 ocp_delay | `0.000000` | `0.000000` | unchanged |
| CH4 ocp_state | `0` | `0` | unchanged |
| CH4 voltage | `0.000000` | `0.000000` | unchanged |
| CH4 current | `0.000000` | `0.000000` | unchanged |
| CH4 on_delay | `0.000000` | `0.000000` | unchanged |
| CH4 off_delay | `0.000000` | `0.000000` | unchanged |
| lock | `0` | `0` | unchanged |

## Experiment summary

| # | experiment | tier | open questions | status | note |
|---|---|---|---|---|---|
| 1 | Identity string and raw reply shape. | read | 1, 4 | done |  |
| 2 | Raw reply of every read-only query, every channel. | read | 4, 5, 8 | done |  |
| 3 | Syntax forms as read-only queries (same table as bare_socket_check.py). | read | 1, 7, 8 | done |  |
| 4 | MINimum / MAXimum / DEFault as queries (`VOLTage? CH1,MAX`). | read | 9, 14 | done |  |
| 5 | Round-trip time per query, median of 5. | read | 11 | done |  |
| 6 | Status registers before and after invalid read-only queries. | read | 6 | done |  |
| 7 | Open the supply as TCPIP::<host>::INSTR (VXI-11) next to the socket session. | read | 3 | skipped | needs --try-vxi11 |
| 8 | Run the plug's read-only methods against the real instrument. | read | 4 | done |  |
| 10 | Voltage setpoint: resolution, above-rating, negative, keywords. | write | 4, 9 | done |  |
| 11 | Current setpoint: resolution, above-rating, negative, keywords. | write | 4, 9 | done |  |
| 12 | OVP set/read-back, out-of-range values, interaction with the voltage setpoint. | write | 9, 10 | done |  |
| 13 | OCP set/read-back (format of the unprinted `OCP?` response), out-of-range, interaction. | write | 5, 9, 10 | done |  |
| 14 | OCP:STATe and OCP:DELay set/read-back, accepted spellings and ranges. | write | 4, 7, 9 | done |  |
| 15 | OUTPut:TRACK: words vs numbers, what the query returns, side effects, setpoint writes while coupled. | write | 10, 13, 14, 21 | done |  |
| 16 | MODE CH2,4W / 2W and MODE? CH2. | write | 13 | done |  |
| 17 | LOCK / LOCK? and whether remote writes still work while locked. | write | 12 | done |  |
| 18 | *OPC?, *OPC, *WAI and set+query chains on one line. | write | 1, 11 | done |  |
| 19 | What *ESR?/*STB? show after deliberately invalid commands; where an invalid-channel write lands. | write | 6, 8 | done |  |
| 20 | Spellings of the voltage SET command, verified by read-back. | write | 7 | done |  |
| 21 | The plug's write path and tearDown() against the instrument, outputs off. | write | 9, 12 | done |  |
| 30 | Output ON at 1.0 V / 0.1 A, no load: settling curve, run mode, OFF. | output | 11 | skipped | needs --allow-output and --confirm-no-load |
| 31 | OUTPut:OFF:DELay semantics with the output on (no load): CH1 1.0 V / 0.1 A, OFF delay 2 s. | output | 11, 22 | skipped | needs --allow-output and --confirm-no-load |

## Findings by open question (docs/scpi_reference.md section 8)

### Q1 Termination (commands, multi-command lines)

Experiments: [1, 3, 18]; ran: [1, 3, 18].

- (E1) reply terminator seen through pyvisa read_termination=\n: LF (command terminator used: '\n')
- (E3) `*IDN?;*OPC?` on one line -> both queries answered (reply 'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R11')
- (E18) `VOLTage CHn,1.250;VOLTage? CHn` on one line -> reply '1.250000'
- (E18) `VOLTage CHn,1.500;*OPC?` on one line -> reply '1'

### Q2 USB identity

*Coverage: needs USB (this tool uses the LAN socket).*

Experiments: none; ran: none.

- no finding recorded

### Q3 LAN (VXI-11, simultaneous connections, web, telnet)

*Coverage: partly: second connection is in bare_socket_check.py; VXI-11 here only with --try-vxi11; web/telnet via bare_socket_check.py --probe-ports.*

Experiments: [7]; ran: none.

- no finding recorded

### Q4 Response formats

Experiments: [1, 2, 8, 10, 11, 14]; ran: [1, 2, 8, 10, 11, 14].

- (E1) *IDN? raw reply b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'
- (E1) *IDN? has 4 comma-separated fields: ['Siglent Technologies', 'SPD4323X', '<redacted>', '4.1.2.9R1']
- (E1) the manual's `\s` is a plain space on the wire
- (E2) scalar V/A/W/s replies use [6] decimal places
- (E2) replies with a unit suffix: none
- (E2) OUTPut:ALL? -> '0', OUTPut:TRACK? -> '0', MODE? CH2 -> '0', MEASure:RUN:MODE? CH1 -> 'CV', LOCK? -> '0'
- (E8) plug read-only methods that raised against the real instrument: none
- (E10) read-back of `VOLTage CH1,1.2345` -> accepted as sent (read-back 1.234500)
- (E14) OCP:DELay read-back of 1.2345 -> accepted as sent (read-back 1.234500)

### Q5 Missing responses

*Coverage: partly: OCP? covered; LAN/GPIB/STORage queries are out of scope and blocked by the safety policy.*

Experiments: [2, 13]; ran: [2, 13].

- (E2) OCP? CH1 -> '3.520000' (CH2..4: ['3.520000', '3.520000', '3.520000'])
- (E13) `OCP? CH1` reply format: b'3.520000\n'

### Q6 Error reporting

Experiments: [6, 19]; ran: [6, 19].

- (E6) baseline *ESR?='32' *STB?='0'; after unknown query `FOOBar?`: {'*ESR?': '0', '*STB?': '0'}; after `VOLTage? CH5`: {'*ESR?': '0', '*STB?': '0'}
- (E6) status registers CHANGED after invalid queries
- (E19) (*ESR?, *STB?) after *CLS: ('0', '0'); after `VOLTage CH5,1`: ('0', '0'); after `VOLTage CH0,1`: ('0', '0'); after `VOLTage CHn,abc`: ('0', '0'); after value 125% of rating: ('0', '0'); after unknown query `FOOBar?`: ('32', '0')
- (E19) invalid input changes the status registers: ['unknown query']
- (E19) error-list hypothesis (`*CLS`, `VOL? CH1`, `*ESR?`, `VOL? CH1`, `*ESR?`, `*CLS`, `VOL? CH1`, `*ESR?`): 1st 32 (bit 5 set), 2nd (list not emptied) 32 (bit 5 set), 3rd (after *CLS) 32 (bit 5 set) -> hypothesis NOT supported as stated

### Q7 Case / forms (leading colon, SOURce, short forms, spacing)

Experiments: [3, 14, 20]; ran: [3, 14, 20].

- (E3) forms that differ from what the manual implies: ['MODE? CH1 (manual: CH2/CH3 only)']
- (E3) answered: [':VOLTage? CH1', 'SOURce:VOLTage? CH1', ':SOURce:VOLTage? CH1', 'SOUR:VOLT? CH1', ':SOURce:VOLTage:SET? CH1', 'VOLTage:SET? CH1', 'VOLT? CH1', 'VOLT:SET? CH1', 'volt? ch1', 'VolTaGe? CH1', 'CURR? CH1', 'OUTP? CH1', 'OUTPut:STATe? CH1', 'OUTP:STAT? CH1', 'OCP:STAT? CH1', 'OCP:DEL? CH1', 'OVP:PROT:STAT? CH1', 'MEAS:VOLT? CH1', 'MEAS:CURR? CH1', 'MEASure:POWer? CH1', 'MEAS:RUN:MODE? CH1', 'MEASure:MODE? CH1', 'LOCK:STATe?', ':SOURce:LOCK:STATe?', '*idn?', 'VOLTage?CH1', 'VOLTage?', 'MODE? CH1', '*IDN?;*OPC?']
- (E3) no answer: ['VOL? CH1', 'VOLTAG? CH1', 'MEAS:POW? CH1', 'OUTP:TRAC?', 'VOLTage[:SET]? CH1', 'VOLTage? CH0', 'VOLTage? CH5', 'VOLTage? 1', 'VOLTage? (CH1)', 'OUTPut:TRACK? CH1']
- (E14) OCP:STATe spellings (read-back): 1 -> '1'; 0 -> '0'; ON -> '1'; OFF -> '0'; `1` with space after comma -> '1'
- (E20) set forms: `:SOURce:VOLTage:SET CH1,1.1` ACCEPTED (1.100000); `SOURce:VOLTage CH1,1.2` ACCEPTED (1.200000); `VOLTage:SET CH1,1.3` ACCEPTED (1.300000); `VOLT CH1,1.4` ACCEPTED (1.400000); `volt ch1,1.5` ACCEPTED (1.500000); `VOLTage CH1, 1.6` ACCEPTED (1.600000); `VOLT:SET CH1,1.7` ACCEPTED (1.700000); `:VOLTage CH1,1.8` ACCEPTED (1.800000); `VOLTage CH1 ,1.9` ACCEPTED (1.900000)

### Q8 Channel argument (optional? invalid channel?)

Experiments: [2, 3, 19]; ran: [2, 3, 19].

- (E2) MODE? CH1 -> '0' (manual: CH2/CH3 only)
- (E3) `VOLTage?` without channel -> '5.000000'; CH0 -> None; CH5 -> None; `VOLTage? 1` -> None
- (E19) `VOLTage CH5,1`: (*ESR?, *STB?) ('0', '0'); setpoints of CH1-CH4 changed: no, all four channels unchanged
- (E19) `VOLTage CH0,1`: (*ESR?, *STB?) ('0', '0'); setpoints of CH1-CH4 changed: no, all four channels unchanged

### Q9 Parameter keywords and out-of-range behaviour

Experiments: [4, 10, 11, 12, 13, 14, 21]; ran: [4, 10, 11, 12, 13, 14, 21].

- (E4) `<query>? CHn,MAX|MIN|DEF` answered for: ['VOLTage? CH1,MAX', 'VOLTage? CH1,MIN', 'VOLTage? CH1,DEFault', 'VOLTage? CH1,MAXimum', 'VOLTage? CH1, MAX', 'CURRent? CH1,MAX', 'CURRent? CH1,MIN', 'VOLTage? CH2,MAX', 'CURRent? CH2,MAX', 'VOLTage? CH3,MAX', 'VOLTage? CH4,MAX', 'CURRent? CH4,MAX', 'VOLTage? CH1,DEF', 'CURRent? CH1,DEF', 'VOLTage? CH2,MIN', 'VOLTage? CH2,DEF', 'CURRent? CH2,MIN', 'CURRent? CH2,DEF', 'VOLTage? CH3,MIN', 'VOLTage? CH3,DEF', 'CURRent? CH3,MIN', 'CURRent? CH3,MAX', 'CURRent? CH3,DEF', 'VOLTage? CH4,MIN', 'VOLTage? CH4,DEF', 'CURRent? CH4,MIN', 'CURRent? CH4,DEF']
- (E4) no answer for: ['OVP? CH1,MAX', 'OCP? CH1,MAX', 'OCP:DELay? CH1,MAX', 'OUTPut:ON:DELay? CH1,MAX', 'OVP? CH1,MIN', 'OVP? CH1,DEF', 'OCP? CH1,MIN', 'OCP? CH1,DEF', 'OVP? CH2,MIN', 'OVP? CH2,MAX', 'OVP? CH2,DEF', 'OCP? CH2,MIN', 'OCP? CH2,MAX', 'OCP? CH2,DEF', 'OVP? CH3,MIN', 'OVP? CH3,MAX', 'OVP? CH3,DEF', 'OCP? CH3,MIN', 'OCP? CH3,MAX', 'OCP? CH3,DEF', 'OVP? CH4,MIN', 'OVP? CH4,MAX', 'OVP? CH4,DEF', 'OCP? CH4,MIN', 'OCP? CH4,MAX', 'OCP? CH4,DEF']
- (E10) VOLTage CH1: 1.000 V -> accepted as sent (read-back 1.000000); 1.2345 V (resolution) -> accepted as sent (read-back 1.234500); rating exactly (6 V) -> accepted as sent (read-back 6.000000); 125% of rating (7.5 V) -> CHANGED to 6.060000 (clamped or rounded); negative (-1 V) -> CHANGED to 0.000000 (clamped or rounded); MINimum -> keyword; read-back 0.000000; MAXimum -> keyword; read-back 6.060000; DEFault -> keyword; read-back 0.000000; 0 -> accepted as sent (read-back 0.000000)
- (E11) CURRent CH1: 0.100 A -> accepted as sent (read-back 0.100000); 0.1234 A (resolution) -> accepted as sent (read-back 0.123400); rating exactly (3.2 A) -> accepted as sent (read-back 3.200000); 125% of rating (4 A) -> CHANGED to 3.232000 (clamped or rounded); negative (-0.1 A) -> CHANGED to 0.000000 (clamped or rounded); MINimum -> keyword; read-back 0.000000; MAXimum -> keyword; read-back 3.232000; DEFault -> keyword; read-back 0.000000; 0 -> accepted as sent (read-back 0.000000)
- (E12) OVP CH1: 0.5 x rated -> accepted as sent (read-back 3.000000); 1.1 x rated -> accepted as sent (read-back 6.600000); 1.2 x rated (above range) -> CLAMPED to the limit 6.6 (read-back 6.600000); 0.05 x rated (below range) -> CHANGED to 0.600000 (clamped or rounded); MAXimum -> keyword; read-back 6.600000; MINimum -> keyword; read-back 0.600000; DEFault -> keyword; read-back 6.600000
- (E13) OCP CH1: 0.5 x rated -> accepted as sent (read-back 1.600000); 1.1 x rated -> accepted as sent (read-back 3.520000); 1.2 x rated (above range) -> CLAMPED to the limit 3.52 (read-back 3.520000); 0.05 x rated (below range) -> CHANGED to 0.320000 (clamped or rounded); MAXimum -> keyword; read-back 3.520000; MINimum -> keyword; read-back 0.320000; DEFault -> keyword; read-back 3.520000
- (E14) OCP:DELay CH1: 0.5 s -> accepted as sent (read-back 0.500000); 1.2345 s (resolution) -> accepted as sent (read-back 1.234500); 3600 s -> accepted as sent (read-back 3600.000000); 3601 s (above range) -> CLAMPED to the limit 3600 (read-back 3600.000000); -1 s -> CHANGED to 0.000000 (clamped or rounded); MAXimum -> keyword; read-back 3600.000000; MINimum -> keyword; read-back 0.000000; DEFault -> keyword; read-back 0.000000; 0 -> accepted as sent (read-back 0.000000)
- (E21) plug write path (configure_channel, ON/OFF delays, sense) raised: nothing; snapshot values not back after tearDown(): none, all restored

### Q10 OVP/OCP interaction with other settings

*Coverage: partly: output state after a trip and after RESET:PROTect needs a load that trips protection (out of scope).*

Experiments: [12, 13, 15]; ran: [12, 13, 15].

- (E12) OVP set to 2.4 while VOLTage=4.2: OVP reads '2.400000', VOLTage now '4.200000'
- (E12) VOLTage 4.2 requested while OVP=2.4: VOLTage reads '4.200000', OVP reads '2.400000'
- (E13) OCP set to 1.28 while CURRent=2.24: OCP reads '1.280000', CURRent now '2.240000'
- (E15) after SERIES (reads '1'): CH2 V=28.000000 I=3.000000 OVP=35.200001 OCP=3.520000 Vmax=32.320000 Imax=3.232000 | CH3 V=14.000000 I=3.100000 OVP=35.200001 OCP=3.520000 Vmax=32.320000 Imax=3.232000
- (E15) after PARALLEL (reads '2'): CH2 V=14.000000 I=6.000000 OVP=35.200001 OCP=3.520000 Vmax=32.320000 Imax=3.232000 | CH3 V=14.000000 I=3.000000 OVP=35.200001 OCP=3.520000 Vmax=32.320000 Imax=3.232000
- (E15) after INDEPENDENT (reads '0'): CH2 V=14.000000 I=3.000000 OVP=35.200001 OCP=3.520000 Vmax=32.320000 Imax=3.232000 | CH3 V=14.000000 I=3.000000 OVP=35.200001 OCP=3.520000 Vmax=32.320000 Imax=3.232000

### Q11 Timing / settling / *OPC

Experiments: [5, 18, 30, 31]; ran: [5, 18].

- (E5) slowest query seen 14 ms; median MEASure query 4.7 ms; a poll interval below that is pointless, and a plug timeout of 10x the slowest (137 ms) is generous
- (E18) `*OPC?` -> '1' in 3.9 ms (idle)
- (E18) `*OPC?` right after a VOLTage set -> '1' in 175.6 ms
- (E18) `*OPC` then `*ESR?` -> '1' (bit 0 = operation complete if the register is implemented)
- (E18) `*WAI` then `VOLTage?` -> '1.000000' in 260.2 ms

### Q12 Remote lock

Experiments: [17, 21]; ran: [17, 21].

- (E17) LOCK? at start of this experiment (after earlier remote traffic): '0'
- (E17) LOCK sequence (read-backs): {'LOCK 1': '1', 'VOLTage while locked': '1.500000', 'OUTPut? while locked': '0', 'LOCK 0': '0', 'LOCK ON': '1', 'LOCK OFF': '0', ':SOURce:LOCK:STATe 1': '1', 'LOCK 0 again': '0'}
- (E17) remote VOLTage write while locked: worked
- (E21) after plug.tearDown(): outputs all 0 ({1: '0', 2: '0', 3: '0', 4: '0'}); LOCK? -> '0' (wanted 0, the unlock is the last write)

### Q13 OUTPut:TRACK and MODE mappings

*Coverage: partly: rejection of OUTPut:TRACK while outputs are on is not tested (would need an output on).*

Experiments: [15, 16]; ran: [15, 16].

- (E15) OUTPut:TRACK word -> query reply: {'SERIES': '1', 'PARALLEL': '2', 'INDEPENDENT': '0'}
- (E15) OUTPut:TRACK number -> query reply: {'1': '1', '2': '2', '0': '0'}
- (E16) MODE CH2 argument -> `MODE? CH2` reply: {'4W': '1', '2W': '0', '1': '1', '0': '0'} (original '0')

### Q14 Rated table / MAX queries

*Coverage: partly: SPD4306X CH4 needs that model (out of scope).*

Experiments: [4, 15]; ran: [4, 15].

- (E4) CH1 MAX: voltage '6.060000', current '3.232000' (manual table: (6, 3.2))
- (E4) CH2 MAX: voltage '32.320000', current '3.232000' (manual table: (32, 3.2))
- (E4) CH3 MAX: voltage '32.320000', current '3.232000' (manual table: (32, 3.2))
- (E4) CH4 MAX: voltage '6.060000', current '3.232000' (manual table: (6, 3.2))
- (E15) series/parallel MAX queries are in the lines above (manual: series 60 V/3.2 A, parallel 32 V/6.4 A on the SPD4323X)

### Q15 LIST

*Coverage: out of scope (LIST blocked by the safety policy).*

Experiments: none; ran: none.

- no finding recorded

### Q16 WAVE

*Coverage: out of scope (WAVE blocked by the safety policy).*

Experiments: none; ran: none.

- no finding recorded

### Q17 STORAGE

*Coverage: out of scope (STORage blocked by the safety policy).*

Experiments: none; ran: none.

- no finding recorded

### Q18 *RST

*Coverage: out of scope (*RST is never sent).*

Experiments: none; ran: none.

- no finding recorded

### Q19 Programming examples

*Coverage: out of scope.*

Experiments: none; ran: none.

- no finding recorded

### Q20 Channel addressing with optional nodes

Experiments: none; ran: none.

- no finding recorded

### Q21 Series/parallel setpoint meaning (write side)

Experiments: [15]; ran: [15].

- (E15) SERIES `VOLTage CH2,20`: CH2 reads '20.000000', CH3 reads '10.000000' -> COMBINED: CH2 reads back the V written (20). `CH2,MAXimum`: CH2 '32.320000', CH3 '16.160000'. `OVP CH2,MAXimum`: `OVP? CH2` '35.200001', `OVP? CH3` '35.200001'
- (E15) PARALLEL `CURRent CH2,5`: CH2 reads '5.000000', CH3 reads '2.500000' -> COMBINED: CH2 reads back the I written (5). `CH2,MAXimum`: CH2 '3.232000', CH3 '1.616000'. `OCP CH2,MAXimum`: `OCP? CH2` '3.520000', `OCP? CH3` '3.520000'

### Q22 Output OFF delay semantics

Experiments: [31]; ran: none.

- no finding recorded

## Experiment details

### E1 identity (done)

Identity string and raw reply shape.

Open question 1 (Termination: which terminator the instrument expects and
sends) and 4 (Responses: what the literal `\s` in the *IDN? example looks
like on the wire, actual *IDN? string, `\n` after every reply).

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'     3.5 ms
```

### E2 formats (done)

Raw reply of every read-only query, every channel.

Open question 4 (Responses: decimals, units, `0`/`1`, `CV`, number vs word
for OUTPut:TRACK? and MODE?), 5 (Missing responses: `OCP?` has no printed
response) and 8 (Channel argument: MODE? CH1, which the manual says is
CH2/CH3 only).

- *OPC? raw b'1\n'
- *ESE? raw b'0\n'
- *ESR? raw b'0\n'
- *SRE? raw b'0\n'
- *STB? raw b'0\n'

| query | reply |
|---|---|
| `VOLTage? CH1` | `'5.000000'` |
| `CURRent? CH1` | `'2.000000'` |
| `OVP? CH1` | `'6.600000'` |
| `OCP? CH1` | `'3.520000'` |
| `OCP:STATe? CH1` | `'0'` |
| `OCP:DELay? CH1` | `'0.000000'` |
| `OUTPut:ON:DELay? CH1` | `'0.000000'` |
| `OUTPut:OFF:DELay? CH1` | `'0.000000'` |
| `OVP:PROTect:STATe? CH1` | `'0'` |
| `OCP:PROTect:STATe? CH1` | `'0'` |
| `MEASure:VOLTage? CH1` | `'0.000302'` |
| `MEASure:CURRent? CH1` | `'0.000230'` |
| `MEASure:POWER? CH1` | `'0.000000'` |
| `MEASure:RUN:MODE? CH1` | `'CV'` |
| `OUTPut? CH1` | `'0'` |
| `VOLTage? CH2` | `'14.000000'` |
| `CURRent? CH2` | `'3.000000'` |
| `OVP? CH2` | `'35.200001'` |
| `OCP? CH2` | `'3.520000'` |
| `OCP:STATe? CH2` | `'0'` |
| `OCP:DELay? CH2` | `'0.000000'` |
| `OUTPut:ON:DELay? CH2` | `'0.000000'` |
| `OUTPut:OFF:DELay? CH2` | `'0.000000'` |
| `OVP:PROTect:STATe? CH2` | `'0'` |
| `OCP:PROTect:STATe? CH2` | `'0'` |
| `MEASure:VOLTage? CH2` | `'0.000000'` |
| `MEASure:CURRent? CH2` | `'0.000000'` |
| `MEASure:POWER? CH2` | `'0.000000'` |
| `MEASure:RUN:MODE? CH2` | `'CV'` |
| `OUTPut? CH2` | `'0'` |
| `VOLTage? CH3` | `'12.000000'` |
| `CURRent? CH3` | `'2.000000'` |
| `OVP? CH3` | `'35.200001'` |
| `OCP? CH3` | `'3.520000'` |
| `OCP:STATe? CH3` | `'0'` |
| `OCP:DELay? CH3` | `'0.000000'` |
| `OUTPut:ON:DELay? CH3` | `'0.000000'` |
| `OUTPut:OFF:DELay? CH3` | `'0.000000'` |
| `OVP:PROTect:STATe? CH3` | `'0'` |
| `OCP:PROTect:STATe? CH3` | `'0'` |
| `MEASure:VOLTage? CH3` | `'0.000000'` |
| `MEASure:CURRent? CH3` | `'0.000196'` |
| `MEASure:POWER? CH3` | `'0.000000'` |
| `MEASure:RUN:MODE? CH3` | `'CV'` |
| `OUTPut? CH3` | `'0'` |
| `VOLTage? CH4` | `'0.000000'` |
| `CURRent? CH4` | `'0.000000'` |
| `OVP? CH4` | `'6.600000'` |
| `OCP? CH4` | `'3.520000'` |
| `OCP:STATe? CH4` | `'0'` |
| `OCP:DELay? CH4` | `'0.000000'` |
| `OUTPut:ON:DELay? CH4` | `'0.000000'` |
| `OUTPut:OFF:DELay? CH4` | `'0.000000'` |
| `OVP:PROTect:STATe? CH4` | `'0'` |
| `OCP:PROTect:STATe? CH4` | `'0'` |
| `MEASure:VOLTage? CH4` | `'0.000000'` |
| `MEASure:CURRent? CH4` | `'0.000434'` |
| `MEASure:POWER? CH4` | `'0.000000'` |
| `MEASure:RUN:MODE? CH4` | `'CV'` |
| `OUTPut? CH4` | `'0'` |
| `OUTPut:ALL?` | `'0'` |
| `OUTPut:TRACK?` | `'0'` |
| `MODE? CH2` | `'0'` |
| `MODE? CH3` | `'0'` |
| `MODE? CH1` | `'0'` |
| `LOCK?` | `'0'` |
| `*OPC?` | `'1'` |
| `*ESE?` | `'0'` |
| `*ESR?` | `'0'` |
| `*SRE?` | `'0'` |
| `*STB?` | `'0'` |

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          2.3 ms
 Q  'CURRent? CH1'                           -> b'2.000000\n'                          3.8 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                          3.6 ms
 Q  'OCP? CH1'                               -> b'3.520000\n'                          5.1 ms
 Q  'OCP:STATe? CH1'                         -> b'0\n'                                 2.0 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                          2.2 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                          2.4 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                          2.5 ms
 Q  'OVP:PROTect:STATe? CH1'                 -> b'0\n'                                 4.8 ms
 Q  'OCP:PROTect:STATe? CH1'                 -> b'0\n'                                 5.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000302\n'                          4.8 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000230\n'                          3.7 ms
 Q  'MEASure:POWER? CH1'                     -> b'0.000000\n'                          3.4 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                5.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.4 ms
 Q  'VOLTage? CH2'                           -> b'14.000000\n'                         5.0 ms
 Q  'CURRent? CH2'                           -> b'3.000000\n'                          2.2 ms
 Q  'OVP? CH2'                               -> b'35.200001\n'                         1.9 ms
 Q  'OCP? CH2'                               -> b'3.520000\n'                          2.0 ms
 Q  'OCP:STATe? CH2'                         -> b'0\n'                                 2.3 ms
 Q  'OCP:DELay? CH2'                         -> b'0.000000\n'                          3.5 ms
 Q  'OUTPut:ON:DELay? CH2'                   -> b'0.000000\n'                          4.9 ms
 Q  'OUTPut:OFF:DELay? CH2'                  -> b'0.000000\n'                          5.0 ms
 Q  'OVP:PROTect:STATe? CH2'                 -> b'0\n'                                 2.4 ms
 Q  'OCP:PROTect:STATe? CH2'                 -> b'0\n'                                 2.6 ms
 Q  'MEASure:VOLTage? CH2'                   -> b'0.000000\n'                          2.9 ms
 Q  'MEASure:CURRent? CH2'                   -> b'0.000000\n'                          4.1 ms
 Q  'MEASure:POWER? CH2'                     -> b'0.000000\n'                          5.8 ms
 Q  'MEASure:RUN:MODE? CH2'                  -> b'CV\n'                                5.0 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 4.6 ms
 Q  'VOLTage? CH3'                           -> b'12.000000\n'                         3.9 ms
 Q  'CURRent? CH3'                           -> b'2.000000\n'                          7.1 ms
 Q  'OVP? CH3'                               -> b'35.200001\n'                         4.8 ms
 Q  'OCP? CH3'                               -> b'3.520000\n'                          4.9 ms
 Q  'OCP:STATe? CH3'                         -> b'0\n'                                 2.7 ms
 Q  'OCP:DELay? CH3'                         -> b'0.000000\n'                          3.9 ms
 Q  'OUTPut:ON:DELay? CH3'                   -> b'0.000000\n'                          4.1 ms
 Q  'OUTPut:OFF:DELay? CH3'                  -> b'0.000000\n'                          3.0 ms
 Q  'OVP:PROTect:STATe? CH3'                 -> b'0\n'                                 2.5 ms
 Q  'OCP:PROTect:STATe? CH3'                 -> b'0\n'                                 4.0 ms
 Q  'MEASure:VOLTage? CH3'                   -> b'0.000000\n'                          4.7 ms
 Q  'MEASure:CURRent? CH3'                   -> b'0.000196\n'                          5.0 ms
 Q  'MEASure:POWER? CH3'                     -> b'0.000000\n'                          3.7 ms
 Q  'MEASure:RUN:MODE? CH3'                  -> b'CV\n'                                3.3 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 4.0 ms
 Q  'VOLTage? CH4'                           -> b'0.000000\n'                          4.1 ms
 Q  'CURRent? CH4'                           -> b'0.000000\n'                          2.9 ms
 Q  'OVP? CH4'                               -> b'6.600000\n'                          2.6 ms
 Q  'OCP? CH4'                               -> b'3.520000\n'                          2.1 ms
 Q  'OCP:STATe? CH4'                         -> b'0\n'                                 4.2 ms
 Q  'OCP:DELay? CH4'                         -> b'0.000000\n'                          5.3 ms
 Q  'OUTPut:ON:DELay? CH4'                   -> b'0.000000\n'                          4.1 ms
 Q  'OUTPut:OFF:DELay? CH4'                  -> b'0.000000\n'                          5.0 ms
 Q  'OVP:PROTect:STATe? CH4'                 -> b'0\n'                                 3.8 ms
 Q  'OCP:PROTect:STATe? CH4'                 -> b'0\n'                                 5.0 ms
 Q  'MEASure:VOLTage? CH4'                   -> b'0.000000\n'                          5.8 ms
 Q  'MEASure:CURRent? CH4'                   -> b'0.000434\n'                          5.7 ms
 Q  'MEASure:POWER? CH4'                     -> b'0.000000\n'                          5.4 ms
 Q  'MEASure:RUN:MODE? CH4'                  -> b'CV\n'                                5.7 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 2.3 ms
 Q  'OUTPut:ALL?'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 2.3 ms
 Q  'MODE? CH2'                              -> b'0\n'                                 2.4 ms
 Q  'MODE? CH3'                              -> b'0\n'                                 3.5 ms
 Q  'MODE? CH1'                              -> b'0\n'                                 4.9 ms
 Q  'LOCK?'                                  -> b'0\n'                                 4.9 ms
 Q  '*OPC?'                                  -> b'1\n'                                 1.7 ms
 Q  '*ESE?'                                  -> b'0\n'                                 1.8 ms
 Q  '*ESR?'                                  -> b'0\n'                                 1.9 ms
 Q  '*SRE?'                                  -> b'0\n'                                 1.9 ms
 Q  '*STB?'                                  -> b'0\n'                                 3.1 ms
```

### E3 forms (done)

Syntax forms as read-only queries (same table as bare_socket_check.py).

Open question 7 (Case/forms: leading colon, `[:SOURce]`, short forms,
literal brackets, spacing), 8 (Channel argument: no channel, CH0, CH5,
bare number) and 1 (Termination: two queries on one line separated by `;`).

- no answer to 'VOL? CH1' (timeout)
- no answer to 'VOLTAG? CH1' (timeout)
- no answer to 'MEAS:POW? CH1' (timeout)
- no answer to 'OUTP:TRAC?' (timeout)
- no answer to 'VOLTage[:SET]? CH1' (timeout)
- no answer to 'VOLTage? CH0' (timeout)
- no answer to 'VOLTage? CH5' (timeout)
- no answer to 'VOLTage? 1' (timeout)
- no answer to 'VOLTage? (CH1)' (timeout)
- no answer to 'OUTPut:TRACK? CH1' (timeout)

| form | command | manual | observed | reply |
|---|---|---|---|---|
| leading colon | `:VOLTage? CH1` | ? | same as `VOLTage? CH1` | `'5.000000'` |
| SOURce: prefix | `SOURce:VOLTage? CH1` | accept | same as `VOLTage? CH1` | `'5.000000'` |
| :SOURce: prefix | `:SOURce:VOLTage? CH1` | accept | same as `VOLTage? CH1` | `'5.000000'` |
| SOUR: short prefix | `SOUR:VOLT? CH1` | ? | same as `VOLTage? CH1` | `'5.000000'` |
| manual example :SOURce:VOLTage:SET? | `:SOURce:VOLTage:SET? CH1` | accept | same as `VOLTage? CH1` | `'5.000000'` |
| VOLTage:SET? w/o SOURce | `VOLTage:SET? CH1` | accept | same as `VOLTage? CH1` | `'5.000000'` |
| short VOLT | `VOLT? CH1` | accept | same as `VOLTage? CH1` | `'5.000000'` |
| short VOLT:SET | `VOLT:SET? CH1` | accept | same as `VOLTage? CH1` | `'5.000000'` |
| lower case incl. ch1 | `volt? ch1` | accept | same as `VOLTage? CH1` | `'5.000000'` |
| mixed case keyword | `VolTaGe? CH1` | accept | same as `VOLTage? CH1` | `'5.000000'` |
| bad abbreviation VOL | `VOL? CH1` | reject | SILENT | `None` |
| bad abbreviation VOLTAG | `VOLTAG? CH1` | reject | SILENT | `None` |
| short CURR | `CURR? CH1` | accept | same as `CURRent? CH1` | `'2.000000'` |
| short OUTP | `OUTP? CH1` | accept | same as `OUTPut? CH1` | `'0'` |
| OUTPut:STATe | `OUTPut:STATe? CH1` | accept | same as `OUTPut? CH1` | `'0'` |
| OUTP:STAT | `OUTP:STAT? CH1` | accept | same as `OUTPut? CH1` | `'0'` |
| OCP:STAT | `OCP:STAT? CH1` | accept | same as `OCP:STATe? CH1` | `'0'` |
| OCP:DEL | `OCP:DEL? CH1` | accept | same as `OCP:DELay? CH1` | `'0.000000'` |
| OVP:PROT:STAT | `OVP:PROT:STAT? CH1` | accept | same as `OVP:PROTect:STATe? CH1` | `'0'` |
| MEAS:VOLT | `MEAS:VOLT? CH1` | accept | same as `MEASure:VOLTage? CH1` | `'0.000302'` |
| MEAS:CURR | `MEAS:CURR? CH1` | accept | same as `MEASure:CURRent? CH1` | `'0.000230'` |
| MEAS:POW (no short form printed) | `MEAS:POW? CH1` | ? | SILENT | `None` |
| MEASure:POWer (mixed case) | `MEASure:POWer? CH1` | ? | same as `MEASure:POWER? CH1` | `'0.000000'` |
| MEAS:RUN:MODE | `MEAS:RUN:MODE? CH1` | accept | same as `MEASure:RUN:MODE? CH1` | `'CV'` |
| MEAS:MODE ([:RUN] omitted) | `MEASure:MODE? CH1` | accept | same as `MEASure:RUN:MODE? CH1` | `'CV'` |
| OUTP:TRAC (short TRACK?) | `OUTP:TRAC?` | ? | SILENT | `None` |
| LOCK:STATe | `LOCK:STATe?` | accept | same as `LOCK?` | `'0'` |
| :SOURce:LOCK:STATe (manual example) | `:SOURce:LOCK:STATe?` | accept | same as `LOCK?` | `'0'` |
| *IDN? lower case | `*idn?` | ? | same as `*IDN?` | `'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1'` |
| no space before channel | `VOLTage?CH1` | ? | same as `VOLTage? CH1` | `'5.000000'` |
| literal [:SET] brackets | `VOLTage[:SET]? CH1` | reject | SILENT | `None` |
| no channel (Q8: 'current channel'?) | `VOLTage?` | ? | answered | `'5.000000'` |
| channel CH0 (Q8) | `VOLTage? CH0` | ? | SILENT | `None` |
| channel CH5 (Q8) | `VOLTage? CH5` | ? | SILENT | `None` |
| bare channel number '1' (Q8) | `VOLTage? 1` | ? | SILENT | `None` |
| parenthesised (CH1) (Q8) | `VOLTage? (CH1)` | ? | SILENT | `None` |
| channel arg on OUTPut:TRACK? (Q8) | `OUTPut:TRACK? CH1` | ? | SILENT | `None` |
| MODE? CH1 (manual: CH2/CH3 only) | `MODE? CH1` | reject | answered | `'0'` |
| two queries with ';' (Q1) | `*IDN?;*OPC?` | ? | answered | `'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R11'` |

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          2.1 ms
 Q  'CURRent? CH1'                           -> b'2.000000\n'                          2.3 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.6 ms
 Q  'OCP:STATe? CH1'                         -> b'0\n'                                 4.9 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                          5.0 ms
 Q  'OVP:PROTect:STATe? CH1'                 -> b'0\n'                                 2.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000302\n'                          3.2 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000230\n'                          3.7 ms
 Q  'MEASure:POWER? CH1'                     -> b'0.000000\n'                          6.1 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                4.5 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 3.5 ms
 Q  'LOCK?'                                  -> b'0\n'                                 2.9 ms
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'     4.0 ms
 Q  ':VOLTage? CH1'                          -> b'5.000000\n'                          2.0 ms
 Q  'SOURce:VOLTage? CH1'                    -> b'5.000000\n'                          5.2 ms
 Q  ':SOURce:VOLTage? CH1'                   -> b'5.000000\n'                          5.1 ms
 Q  'SOUR:VOLT? CH1'                         -> b'5.000000\n'                          2.9 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'5.000000\n'                          3.9 ms
 Q  'VOLTage:SET? CH1'                       -> b'5.000000\n'                          3.8 ms
 Q  'VOLT? CH1'                              -> b'5.000000\n'                          5.9 ms
 Q  'VOLT:SET? CH1'                          -> b'5.000000\n'                          5.0 ms
 Q  'volt? ch1'                              -> b'5.000000\n'                          6.0 ms
 Q  'VolTaGe? CH1'                           -> b'5.000000\n'                          2.9 ms
 Q  'VOL? CH1'                               -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1514.3 ms
 Q  'VOLTAG? CH1'                            -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1506.1 ms
 Q  'CURR? CH1'                              -> b'2.000000\n'                          2.3 ms
 Q  'OUTP? CH1'                              -> b'0\n'                                 2.1 ms
 Q  'OUTPut:STATe? CH1'                      -> b'0\n'                                 2.1 ms
 Q  'OUTP:STAT? CH1'                         -> b'0\n'                                 5.5 ms
 Q  'OCP:STAT? CH1'                          -> b'0\n'                                 5.0 ms
 Q  'OCP:DEL? CH1'                           -> b'0.000000\n'                          3.5 ms
 Q  'OVP:PROT:STAT? CH1'                     -> b'0\n'                                 2.0 ms
 Q  'MEAS:VOLT? CH1'                         -> b'0.000302\n'                          3.0 ms
 Q  'MEAS:CURR? CH1'                         -> b'0.000230\n'                          2.9 ms
 Q  'MEAS:POW? CH1'                          -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1512.9 ms
 Q  'MEASure:POWer? CH1'                     -> b'0.000000\n'                          6.2 ms
 Q  'MEAS:RUN:MODE? CH1'                     -> b'CV\n'                                4.6 ms
 Q  'MEASure:MODE? CH1'                      -> b'CV\n'                                5.4 ms
 Q  'OUTP:TRAC?'                             -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1508.8 ms
 Q  'LOCK:STATe?'                            -> b'0\n'                                 5.0 ms
 Q  ':SOURce:LOCK:STATe?'                    -> b'0\n'                                 3.6 ms
 Q  '*idn?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'     3.5 ms
 Q  'VOLTage?CH1'                            -> b'5.000000\n'                          3.4 ms
 Q  'VOLTage[:SET]? CH1'                     -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1518.5 ms
 Q  'VOLTage?'                               -> b'5.000000\n'                          2.5 ms
 Q  'VOLTage? CH0'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1509.4 ms
 Q  'VOLTage? CH5'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1502.5 ms
 Q  'VOLTage? 1'                             -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1515.3 ms
 Q  'VOLTage? (CH1)'                         -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1507.5 ms
 Q  'OUTPut:TRACK? CH1'                      -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1508.5 ms
 Q  'MODE? CH1'                              -> b'0\n'                                 2.7 ms
 Q  '*IDN?;*OPC?'                            -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R11\n'    13.7 ms
```

### E4 min_max (done)

MINimum / MAXimum / DEFault as queries (`VOLTage? CH1,MAX`).

Open question 9 (Parameter keywords: do they work, what do they return) and
14 (Rated table: real limits returned by `VOLT? CHn,MAX` / `CURR? CHn,MAX`).
Queries only; nothing is set.

- no answer to 'OVP? CH1,MAX' (timeout)
- no answer to 'OCP? CH1,MAX' (timeout)
- no answer to 'OCP:DELay? CH1,MAX' (timeout)
- no answer to 'OUTPut:ON:DELay? CH1,MAX' (timeout)
- no answer to 'OVP? CH1,MIN' (timeout)
- no answer to 'OVP? CH1,DEF' (timeout)
- no answer to 'OCP? CH1,MIN' (timeout)
- no answer to 'OCP? CH1,DEF' (timeout)
- no answer to 'OVP? CH2,MIN' (timeout)
- no answer to 'OVP? CH2,MAX' (timeout)
- no answer to 'OVP? CH2,DEF' (timeout)
- no answer to 'OCP? CH2,MIN' (timeout)
- no answer to 'OCP? CH2,MAX' (timeout)
- no answer to 'OCP? CH2,DEF' (timeout)
- no answer to 'OVP? CH3,MIN' (timeout)
- no answer to 'OVP? CH3,MAX' (timeout)
- no answer to 'OVP? CH3,DEF' (timeout)
- no answer to 'OCP? CH3,MIN' (timeout)
- no answer to 'OCP? CH3,MAX' (timeout)
- no answer to 'OCP? CH3,DEF' (timeout)
- no answer to 'OVP? CH4,MIN' (timeout)
- no answer to 'OVP? CH4,MAX' (timeout)
- no answer to 'OVP? CH4,DEF' (timeout)
- no answer to 'OCP? CH4,MIN' (timeout)
- no answer to 'OCP? CH4,MAX' (timeout)
- no answer to 'OCP? CH4,DEF' (timeout)

| query | reply |
|---|---|
| `VOLTage? CH1,MAX` | `'6.060000'` |
| `VOLTage? CH1,MIN` | `'0.000000'` |
| `VOLTage? CH1,DEFault` | `'0.000000'` |
| `VOLTage? CH1,MAXimum` | `'6.060000'` |
| `VOLTage? CH1, MAX` | `'6.060000'` |
| `CURRent? CH1,MAX` | `'3.232000'` |
| `CURRent? CH1,MIN` | `'0.000000'` |
| `OVP? CH1,MAX` | `None` |
| `OCP? CH1,MAX` | `None` |
| `OCP:DELay? CH1,MAX` | `None` |
| `OUTPut:ON:DELay? CH1,MAX` | `None` |
| `VOLTage? CH2,MAX` | `'32.320000'` |
| `CURRent? CH2,MAX` | `'3.232000'` |
| `VOLTage? CH3,MAX` | `'32.320000'` |
| `VOLTage? CH4,MAX` | `'6.060000'` |
| `CURRent? CH4,MAX` | `'3.232000'` |
| `VOLTage? CH1,DEF` | `'0.000000'` |
| `CURRent? CH1,DEF` | `'0.000000'` |
| `OVP? CH1,MIN` | `None` |
| `OVP? CH1,DEF` | `None` |
| `OCP? CH1,MIN` | `None` |
| `OCP? CH1,DEF` | `None` |
| `VOLTage? CH2,MIN` | `'0.000000'` |
| `VOLTage? CH2,DEF` | `'0.000000'` |
| `CURRent? CH2,MIN` | `'0.000000'` |
| `CURRent? CH2,DEF` | `'0.000000'` |
| `OVP? CH2,MIN` | `None` |
| `OVP? CH2,MAX` | `None` |
| `OVP? CH2,DEF` | `None` |
| `OCP? CH2,MIN` | `None` |
| `OCP? CH2,MAX` | `None` |
| `OCP? CH2,DEF` | `None` |
| `VOLTage? CH3,MIN` | `'0.000000'` |
| `VOLTage? CH3,DEF` | `'0.000000'` |
| `CURRent? CH3,MIN` | `'0.000000'` |
| `CURRent? CH3,MAX` | `'3.232000'` |
| `CURRent? CH3,DEF` | `'0.000000'` |
| `OVP? CH3,MIN` | `None` |
| `OVP? CH3,MAX` | `None` |
| `OVP? CH3,DEF` | `None` |
| `OCP? CH3,MIN` | `None` |
| `OCP? CH3,MAX` | `None` |
| `OCP? CH3,DEF` | `None` |
| `VOLTage? CH4,MIN` | `'0.000000'` |
| `VOLTage? CH4,DEF` | `'0.000000'` |
| `CURRent? CH4,MIN` | `'0.000000'` |
| `CURRent? CH4,DEF` | `'0.000000'` |
| `OVP? CH4,MIN` | `None` |
| `OVP? CH4,MAX` | `None` |
| `OVP? CH4,DEF` | `None` |
| `OCP? CH4,MIN` | `None` |
| `OCP? CH4,MAX` | `None` |
| `OCP? CH4,DEF` | `None` |

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'VOLTage? CH1,MAX'                       -> b'6.060000\n'                          3.8 ms
 Q  'VOLTage? CH1,MIN'                       -> b'0.000000\n'                          5.0 ms
 Q  'VOLTage? CH1,DEFault'                   -> b'0.000000\n'                          4.8 ms
 Q  'VOLTage? CH1,MAXimum'                   -> b'6.060000\n'                          3.9 ms
 Q  'VOLTage? CH1, MAX'                      -> b'6.060000\n'                          4.0 ms
 Q  'CURRent? CH1,MAX'                       -> b'3.232000\n'                          4.7 ms
 Q  'CURRent? CH1,MIN'                       -> b'0.000000\n'                          3.6 ms
 Q  'OVP? CH1,MAX'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1513.0 ms
 Q  'OCP? CH1,MAX'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1509.3 ms
 Q  'OCP:DELay? CH1,MAX'                     -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1512.2 ms
 Q  'OUTPut:ON:DELay? CH1,MAX'               -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1515.1 ms
 Q  'VOLTage? CH2,MAX'                       -> b'32.320000\n'                         4.1 ms
 Q  'CURRent? CH2,MAX'                       -> b'3.232000\n'                          2.2 ms
 Q  'VOLTage? CH3,MAX'                       -> b'32.320000\n'                         5.3 ms
 Q  'VOLTage? CH4,MAX'                       -> b'6.060000\n'                          4.9 ms
 Q  'CURRent? CH4,MAX'                       -> b'3.232000\n'                          2.5 ms
 Q  'VOLTage? CH1,DEF'                       -> b'0.000000\n'                          2.1 ms
 Q  'CURRent? CH1,DEF'                       -> b'0.000000\n'                          2.0 ms
 Q  'OVP? CH1,MIN'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1514.7 ms
 Q  'OVP? CH1,DEF'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1518.5 ms
 Q  'OCP? CH1,MIN'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1513.8 ms
 Q  'OCP? CH1,DEF'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1506.4 ms
 Q  'VOLTage? CH2,MIN'                       -> b'0.000000\n'                          4.9 ms
 Q  'VOLTage? CH2,DEF'                       -> b'0.000000\n'                          3.1 ms
 Q  'CURRent? CH2,MIN'                       -> b'0.000000\n'                          3.2 ms
 Q  'CURRent? CH2,DEF'                       -> b'0.000000\n'                          5.2 ms
 Q  'OVP? CH2,MIN'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1509.6 ms
 Q  'OVP? CH2,MAX'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1511.0 ms
 Q  'OVP? CH2,DEF'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1511.5 ms
 Q  'OCP? CH2,MIN'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1515.3 ms
 Q  'OCP? CH2,MAX'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1512.6 ms
 Q  'OCP? CH2,DEF'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1514.8 ms
 Q  'VOLTage? CH3,MIN'                       -> b'0.000000\n'                          4.8 ms
 Q  'VOLTage? CH3,DEF'                       -> b'0.000000\n'                          4.9 ms
 Q  'CURRent? CH3,MIN'                       -> b'0.000000\n'                          5.3 ms
 Q  'CURRent? CH3,MAX'                       -> b'3.232000\n'                          5.1 ms
 Q  'CURRent? CH3,DEF'                       -> b'0.000000\n'                          4.8 ms
 Q  'OVP? CH3,MIN'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1509.3 ms
 Q  'OVP? CH3,MAX'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1514.5 ms
 Q  'OVP? CH3,DEF'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1512.8 ms
 Q  'OCP? CH3,MIN'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1507.2 ms
 Q  'OCP? CH3,MAX'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1512.9 ms
 Q  'OCP? CH3,DEF'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1502.2 ms
 Q  'VOLTage? CH4,MIN'                       -> b'0.000000\n'                          6.7 ms
 Q  'VOLTage? CH4,DEF'                       -> b'0.000000\n'                          3.9 ms
 Q  'CURRent? CH4,MIN'                       -> b'0.000000\n'                          2.8 ms
 Q  'CURRent? CH4,DEF'                       -> b'0.000000\n'                          5.8 ms
 Q  'OVP? CH4,MIN'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1502.3 ms
 Q  'OVP? CH4,MAX'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1511.9 ms
 Q  'OVP? CH4,DEF'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1501.0 ms
 Q  'OCP? CH4,MIN'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1513.8 ms
 Q  'OCP? CH4,MAX'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1505.9 ms
 Q  'OCP? CH4,DEF'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1507.5 ms
```

### E5 timing (done)

Round-trip time per query, median of 5.

Open question 11 (Timing: response time of MEASure, measurement refresh
rate); the numbers size the plug's timeouts and polling interval.

- *IDN?                        median 13.2 ms  min 3.9  max 13.7  (n=5)
- *OPC?                        median 2.0 ms  min 1.7  max 2.3  (n=5)
- OUTPut? CH1                  median 3.8 ms  min 2.5  max 4.8  (n=5)
- VOLTage? CH1                 median 4.3 ms  min 2.3  max 5.1  (n=5)
- OVP? CH1                     median 2.3 ms  min 2.0  max 5.4  (n=5)
- MEASure:VOLTage? CH1         median 4.6 ms  min 3.3  max 5.1  (n=5)
- MEASure:CURRent? CH1         median 6.0 ms  min 5.1  max 6.9  (n=5)
- MEASure:POWER? CH1           median 4.7 ms  min 3.6  max 5.3  (n=5)
- MEASure:RUN:MODE? CH1        median 4.7 ms  min 3.8  max 5.8  (n=5)
- OUTPut:TRACK?                median 3.4 ms  min 2.4  max 3.9  (n=5)

| query | median ms | min | max | n |
|---|---|---|---|---|
| `*IDN?` | 13.2 | 3.9 | 13.7 | 5 |
| `*OPC?` | 2.0 | 1.7 | 2.3 | 5 |
| `OUTPut? CH1` | 3.8 | 2.5 | 4.8 | 5 |
| `VOLTage? CH1` | 4.3 | 2.3 | 5.1 | 5 |
| `OVP? CH1` | 2.3 | 2.0 | 5.4 | 5 |
| `MEASure:VOLTage? CH1` | 4.6 | 3.3 | 5.1 | 5 |
| `MEASure:CURRent? CH1` | 6.0 | 5.1 | 6.9 | 5 |
| `MEASure:POWER? CH1` | 4.7 | 3.6 | 5.3 | 5 |
| `MEASure:RUN:MODE? CH1` | 4.7 | 3.8 | 5.8 | 5 |
| `OUTPut:TRACK?` | 3.4 | 2.4 | 3.9 | 5 |

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'    13.2 ms
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'    13.3 ms
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'     3.9 ms
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'     3.9 ms
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'    13.7 ms
 Q  '*OPC?'                                  -> b'1\n'                                 2.3 ms
 Q  '*OPC?'                                  -> b'1\n'                                 1.7 ms
 Q  '*OPC?'                                  -> b'1\n'                                 1.8 ms
 Q  '*OPC?'                                  -> b'1\n'                                 2.0 ms
 Q  '*OPC?'                                  -> b'1\n'                                 2.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.6 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.5 ms
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          2.4 ms
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          4.7 ms
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          5.1 ms
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          4.3 ms
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          2.3 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                          2.0 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                          2.2 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                          2.3 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                          3.4 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                          5.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000302\n'                          5.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000302\n'                          3.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000302\n'                          3.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000302\n'                          4.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000302\n'                          4.7 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000119\n'                          6.9 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000119\n'                          5.1 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000119\n'                          6.0 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000119\n'                          6.8 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000119\n'                          5.4 ms
 Q  'MEASure:POWER? CH1'                     -> b'0.000000\n'                          3.6 ms
 Q  'MEASure:POWER? CH1'                     -> b'0.000000\n'                          5.3 ms
 Q  'MEASure:POWER? CH1'                     -> b'0.000000\n'                          4.7 ms
 Q  'MEASure:POWER? CH1'                     -> b'0.000000\n'                          5.0 ms
 Q  'MEASure:POWER? CH1'                     -> b'0.000000\n'                          3.8 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                5.8 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                4.7 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                4.9 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                3.9 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                3.8 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 3.9 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 3.6 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 3.4 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 2.8 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 2.4 ms
```

### E6 status_registers (done)

Status registers before and after invalid read-only queries.

Open question 6 (Errors: no error-query command; which bits of `*ESR?` and
`*STB?` are used, what `*TST?` = 0 means). `*TST?` runs only with
--allow-selftest.

- baseline {'*ESE?': '0', '*SRE?': '0', '*ESR?': '32', '*STB?': '0'}
- no answer to 'FOOBar? CH1' (timeout)
- no answer to 'VOLTage? CH5' (timeout)
- *TST? skipped (needs --allow-selftest)

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  '*ESE?'                                  -> b'0\n'                                 1.4 ms
 Q  '*SRE?'                                  -> b'0\n'                                 2.9 ms
 Q  '*ESR?'                                  -> b'32\n'                                2.1 ms
 Q  '*STB?'                                  -> b'0\n'                                 2.9 ms
 Q  'FOOBar? CH1'                            -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1500.5 ms
 Q  '*ESR?'                                  -> b'0\n'                                 2.2 ms
 Q  '*STB?'                                  -> b'0\n'                                 1.6 ms
 Q  'VOLTage? CH5'                           -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1507.7 ms
 Q  '*ESR?'                                  -> b'0\n'                                 2.7 ms
 Q  '*STB?'                                  -> b'0\n'                                 1.8 ms
```

### E7 vxi11 (skipped)

Open the supply as TCPIP::<host>::INSTR (VXI-11) next to the socket session.

Open question 3 (LAN: does the instrument expose VXI-11 / `TCPIP::<ip>::INSTR`,
and may a second session coexist with the socket?). Needs a network path to
the instrument's portmapper; a forwarded single port 5025 will not do.

**needs --try-vxi11**

### E8 plug_smoke (done)

Run the plug's read-only methods against the real instrument.

Not an open question: it checks that the plug's assumptions (`# ASSUMPTION(hw)`
in src/) survive contact with the instrument. Answers nothing new for
section 8 but any exception here is a defect to fix in the plug or the fake
(open question 4 is the closest: response parsing). Skipped when the package
is not installed. Calls only getters; tearDown() is never called.

- plug.idn() -> Identity(vendor='Siglent Technologies', model='SPD4323X', serial='<redacted>', firmware='4.1.2.9R1')
- plug.snapshot() -> {'channels': {1: {'voltage': 5.0, 'current': 2.0, 'ovp': 6.6, 'ocp': 3.52, 'ocp_enabled': False, 'ocp_delay': 0.0, 'on_delay': 0.0, 'off_delay': 0.0, 'output': False}, 2: {'voltage': 14.0, 'current': 3.0, 'ovp': 35.200001, 'ocp': 3.52, 'ocp_enabled': False, 'ocp_delay': 0.0, 'on_delay': 0.0, 'off_delay': 0.0, 'output': False}, 3: {'voltage': 12.0, 'current': 2.0, 'ovp': 35.200001, 'ocp': 3.52, 'ocp_enabled': False, 'ocp_delay': 0.0, 'on_delay': 0.0, 'off_delay': 0.0, 'output': False}, 4: {'voltage': 0.0, 'current': 0.0, 'ovp': 6.6, 'ocp': 3.52, 'ocp_enabled': False, 'ocp_delay': 0.0, 'on_delay': 0.0, 'off_delay': 0.0, 'output': False}}, 'track': <TrackMode.INDEPENDENT: 'INDEPENDENT'>}
- plug.track() -> <TrackMode.INDEPENDENT: 'INDEPENDENT'>
- plug.sense(2) -> <SenseMode.TWO_WIRE: '2W'>
- plug.output(1) -> False
- plug.voltage_setpoint(1) -> 5.0
- plug.current_setpoint(1) -> 2.0
- plug.ovp(1) -> 6.6
- plug.ocp(1) -> 3.52
- plug.ocp_enabled(1) -> False
- plug.ocp_delay(1) -> 0.0
- plug.protection_status(1) -> ProtectionStatus(ovp_tripped=False, ocp_tripped=False)
- plug.measure(1) -> Reading(voltage=0.000302, current=0.00023, power=0.0, mode='CV')
- plug.run_mode(1) -> 'CV'
- plug.locked() -> False
- plug.opc() -> '1'
- plug.model -> Model(name='SPD4323X', channels=(ChannelRating(voltage=6, current=3.2), ChannelRating(voltage=32, current=3.2), ChannelRating(voltage=32, current=3.2), ChannelRating(voltage=6, current=3.2)), series=ChannelRating(voltage=60, current=3.2), parallel=ChannelRating(voltage=32, current=6.4), total_power_w=240, tested=False)

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'    14.1 ms
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'    13.5 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'5.000000\n'                          5.4 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'2.000000\n'                          4.0 ms
 Q  ':SOURce:OVP? CH1'                       -> b'6.600000\n'                          3.5 ms
 Q  ':SOURce:OCP? CH1'                       -> b'3.520000\n'                          4.1 ms
 Q  ':SOURce:OCP:STATe? CH1'                 -> b'0\n'                                 3.8 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                          4.2 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                          4.0 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                          5.2 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.9 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'14.000000\n'                         3.0 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          3.7 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         4.8 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          4.1 ms
 Q  ':SOURce:OCP:STATe? CH2'                 -> b'0\n'                                 2.4 ms
 Q  'OCP:DELay? CH2'                         -> b'0.000000\n'                          3.9 ms
 Q  'OUTPut:ON:DELay? CH2'                   -> b'0.000000\n'                          5.1 ms
 Q  'OUTPut:OFF:DELay? CH2'                  -> b'0.000000\n'                          4.5 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 3.8 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'12.000000\n'                         4.4 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.000000\n'                          5.5 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         4.6 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          4.9 ms
 Q  ':SOURce:OCP:STATe? CH3'                 -> b'0\n'                                 4.9 ms
 Q  'OCP:DELay? CH3'                         -> b'0.000000\n'                          5.3 ms
 Q  'OUTPut:ON:DELay? CH3'                   -> b'0.000000\n'                          5.8 ms
 Q  'OUTPut:OFF:DELay? CH3'                  -> b'0.000000\n'                          4.9 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 4.8 ms
 Q  ':SOURce:VOLTage:SET? CH4'               -> b'0.000000\n'                          2.1 ms
 Q  ':SOURce:CURRent:SET? CH4'               -> b'0.000000\n'                          2.1 ms
 Q  ':SOURce:OVP? CH4'                       -> b'6.600000\n'                          2.3 ms
 Q  ':SOURce:OCP? CH4'                       -> b'3.520000\n'                          2.3 ms
 Q  ':SOURce:OCP:STATe? CH4'                 -> b'0\n'                                 5.2 ms
 Q  'OCP:DELay? CH4'                         -> b'0.000000\n'                          5.0 ms
 Q  'OUTPut:ON:DELay? CH4'                   -> b'0.000000\n'                          4.7 ms
 Q  'OUTPut:OFF:DELay? CH4'                  -> b'0.000000\n'                          2.6 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 2.5 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 2.6 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 5.4 ms
 Q  'MODE? CH2'                              -> b'0\n'                                 5.0 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.7 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'5.000000\n'                          2.1 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'2.000000\n'                          2.4 ms
 Q  ':SOURce:OVP? CH1'                       -> b'6.600000\n'                          2.0 ms
 Q  ':SOURce:OCP? CH1'                       -> b'3.520000\n'                          2.1 ms
 Q  ':SOURce:OCP:STATe? CH1'                 -> b'0\n'                                 5.3 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                          4.8 ms
 Q  ':SOURce:OVP:PROTect:STATe? CH1'         -> b'0\n'                                 2.7 ms
 Q  ':SOURce:OCP:PROTect:STATe? CH1'         -> b'0\n'                                 2.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000302\n'                          3.2 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000230\n'                          3.2 ms
 Q  'MEASure:POWER? CH1'                     -> b'0.000000\n'                          5.7 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                5.4 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                4.0 ms
 Q  ':SOURce:LOCK:STATe?'                    -> b'0\n'                                 3.1 ms
 Q  '*OPC?'                                  -> b'1\n'                                 1.8 ms
```

### E10 voltage_set (done)

Voltage setpoint: resolution, above-rating, negative, keywords.

Open question 9 (Parameter keywords: rounding/clamping vs error when a value
is out of range, what MINimum/MAXimum/DEFault set) and 4 (Responses: how many
decimals come back after a set). Output stays off.

- 1.000 V: sent 1.000, accepted as sent (read-back 1.000000)
- 1.2345 V (resolution): sent 1.2345, accepted as sent (read-back 1.234500)
- rating exactly (6 V): sent 6, accepted as sent (read-back 6.000000)
- 125% of rating (7.5 V): sent 7.5, CHANGED to 6.060000 (clamped or rounded)
- negative (-1 V): sent -1, CHANGED to 0.000000 (clamped or rounded)
- MINimum: sent MINimum, keyword; read-back 0.000000
- MAXimum: sent MAXimum, keyword; read-back 6.060000
- DEFault: sent DEFault, keyword; read-back 0.000000
- 0: sent 0, accepted as sent (read-back 0.000000)

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.1 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 3.3 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 5.0 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 5.0 ms
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          3.2 ms
 W  'VOLTage CH1,1.000'                          0.1 ms
 Q  'VOLTage? CH1'                           -> b'1.000000\n'                        245.5 ms
 W  'VOLTage CH1,1.2345'                         0.2 ms
 Q  'VOLTage? CH1'                           -> b'1.234500\n'                        260.8 ms
 W  'VOLTage CH1,6'                              0.1 ms
 Q  'VOLTage? CH1'                           -> b'6.000000\n'                        259.9 ms
 W  'VOLTage CH1,7.5'                            0.0 ms
 Q  'VOLTage? CH1'                           -> b'6.060000\n'                        260.3 ms
 W  'VOLTage CH1,-1'                             0.1 ms
 Q  'VOLTage? CH1'                           -> b'0.000000\n'                        392.7 ms
 W  'VOLTage CH1,MINimum'                        0.1 ms
 Q  'VOLTage? CH1'                           -> b'0.000000\n'                        126.4 ms
 W  'VOLTage CH1,MAXimum'                        0.1 ms
 Q  'VOLTage? CH1'                           -> b'6.060000\n'                         10.5 ms
 W  'VOLTage CH1,DEFault'                        0.0 ms
 Q  'VOLTage? CH1'                           -> b'0.000000\n'                        317.7 ms
 W  'VOLTage CH1,0'                              0.2 ms
 Q  'VOLTage? CH1'                           -> b'0.000000\n'                        192.2 ms
```

### E11 current_set (done)

Current setpoint: resolution, above-rating, negative, keywords.

Open question 9 (Parameter keywords: clamp vs error out of range, what the
keywords set) and 4 (Responses: decimals). Output stays off.

- 0.100 A: sent 0.100, accepted as sent (read-back 0.100000)
- 0.1234 A (resolution): sent 0.1234, accepted as sent (read-back 0.123400)
- rating exactly (3.2 A): sent 3.2, accepted as sent (read-back 3.200000)
- 125% of rating (4 A): sent 4, CHANGED to 3.232000 (clamped or rounded)
- negative (-0.1 A): sent -0.1, CHANGED to 0.000000 (clamped or rounded)
- MINimum: sent MINimum, keyword; read-back 0.000000
- MAXimum: sent MAXimum, keyword; read-back 3.232000
- DEFault: sent DEFault, keyword; read-back 0.000000
- 0: sent 0, accepted as sent (read-back 0.000000)

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 1.8 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.0 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.1 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 2.0 ms
 Q  'CURRent? CH1'                           -> b'2.000000\n'                          3.4 ms
 W  'CURRent CH1,0.100'                          0.1 ms
 Q  'CURRent? CH1'                           -> b'0.100000\n'                        412.3 ms
 W  'CURRent CH1,0.1234'                         0.1 ms
 Q  'CURRent? CH1'                           -> b'0.123400\n'                         66.5 ms
 W  'CURRent CH1,3.2'                            0.1 ms
 Q  'CURRent? CH1'                           -> b'3.200000\n'                        258.7 ms
 W  'CURRent CH1,4'                              0.2 ms
 Q  'CURRent? CH1'                           -> b'3.232000\n'                        295.1 ms
 W  'CURRent CH1,-0.1'                           0.1 ms
 Q  'CURRent? CH1'                           -> b'0.000000\n'                        406.5 ms
 W  'CURRent CH1,MINimum'                        0.1 ms
 Q  'CURRent? CH1'                           -> b'0.000000\n'                         78.6 ms
 W  'CURRent CH1,MAXimum'                        0.1 ms
 Q  'CURRent? CH1'                           -> b'3.232000\n'                        258.7 ms
 W  'CURRent CH1,DEFault'                        0.1 ms
 Q  'CURRent? CH1'                           -> b'0.000000\n'                        276.8 ms
 W  'CURRent CH1,0'                              0.1 ms
 Q  'CURRent? CH1'                           -> b'0.000000\n'                        408.0 ms
```

### E12 ovp (done)

OVP set/read-back, out-of-range values, interaction with the voltage setpoint.

Open question 9 (clamping vs error for OVP outside 0.1-1.1 x rated, MIN/MAX/DEF)
and 10 (Interaction: OVP below the set voltage, voltage above OVP). Output off.

- 0.5 x rated: sent 3, accepted as sent (read-back 3.000000)
- 1.1 x rated: sent 6.6, accepted as sent (read-back 6.600000)
- 1.2 x rated (above range): sent 7.2, CLAMPED to the limit 6.6 (read-back 6.600000)
- 0.05 x rated (below range): sent 0.3, CHANGED to 0.600000 (clamped or rounded)
- MAXimum: sent MAXimum, keyword; read-back 6.600000
- MINimum: sent MINimum, keyword; read-back 0.600000
- DEFault: sent DEFault, keyword; read-back 6.600000

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.4 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.2 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.3 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 2.1 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                          4.7 ms
 W  'OVP CH1,3'                                  0.1 ms
 Q  'OVP? CH1'                               -> b'3.000000\n'                         93.3 ms
 W  'OVP CH1,6.6'                                0.1 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                        259.6 ms
 W  'OVP CH1,7.2'                                0.1 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                        261.1 ms
 W  'OVP CH1,0.3'                                0.1 ms
 Q  'OVP? CH1'                               -> b'0.600000\n'                        259.4 ms
 W  'OVP CH1,MAXimum'                            0.2 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                        261.5 ms
 W  'OVP CH1,MINimum'                            0.1 ms
 Q  'OVP? CH1'                               -> b'0.600000\n'                        258.9 ms
 W  'OVP CH1,DEFault'                            0.1 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                        259.4 ms
 W  'OVP CH1,MAXimum'                            0.1 ms
 W  'VOLTage CH1,4.2'                            0.0 ms
 W  'OVP CH1,2.4'                                0.0 ms
 Q  'OVP? CH1'                               -> b'2.400000\n'                        266.9 ms
 Q  'VOLTage? CH1'                           -> b'4.200000\n'                          2.9 ms
 W  'VOLTage CH1,0'                              0.1 ms
 W  'OVP CH1,2.4'                                0.0 ms
 W  'VOLTage CH1,4.2'                            0.0 ms
 Q  'VOLTage? CH1'                           -> b'4.200000\n'                        309.1 ms
 Q  'OVP? CH1'                               -> b'2.400000\n'                          5.0 ms
```

### E13 ocp (done)

OCP set/read-back (format of the unprinted `OCP?` response), out-of-range, interaction.

Open question 5 (Missing responses: `OCP?`), 9 (clamping vs error for OCP
outside 0.1-1.1 x rated, MIN/MAX/DEF) and 10 (Interaction: OCP vs current
setpoint). Output off.

- 0.5 x rated: sent 1.6, accepted as sent (read-back 1.600000)
- 1.1 x rated: sent 3.52, accepted as sent (read-back 3.520000)
- 1.2 x rated (above range): sent 3.84, CLAMPED to the limit 3.52 (read-back 3.520000)
- 0.05 x rated (below range): sent 0.16, CHANGED to 0.320000 (clamped or rounded)
- MAXimum: sent MAXimum, keyword; read-back 3.520000
- MINimum: sent MINimum, keyword; read-back 0.320000
- DEFault: sent DEFault, keyword; read-back 3.520000

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.2 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.0 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 2.1 ms
 Q  'OCP? CH1'                               -> b'3.520000\n'                          3.5 ms
 W  'OCP CH1,1.6'                                0.3 ms
 Q  'OCP? CH1'                               -> b'1.600000\n'                        125.3 ms
 W  'OCP CH1,3.52'                               0.1 ms
 Q  'OCP? CH1'                               -> b'3.520000\n'                        263.3 ms
 W  'OCP CH1,3.84'                               0.1 ms
 Q  'OCP? CH1'                               -> b'3.520000\n'                        255.9 ms
 W  'OCP CH1,0.16'                               0.1 ms
 Q  'OCP? CH1'                               -> b'0.320000\n'                        260.0 ms
 W  'OCP CH1,MAXimum'                            0.1 ms
 Q  'OCP? CH1'                               -> b'3.520000\n'                        260.3 ms
 W  'OCP CH1,MINimum'                            0.2 ms
 Q  'OCP? CH1'                               -> b'0.320000\n'                        261.7 ms
 W  'OCP CH1,DEFault'                            0.1 ms
 Q  'OCP? CH1'                               -> b'3.520000\n'                        259.1 ms
 W  'OCP CH1,MAXimum'                            0.1 ms
 W  'CURRent CH1,2.24'                           0.0 ms
 W  'OCP CH1,1.28'                               0.2 ms
 Q  'OCP? CH1'                               -> b'1.280000\n'                        273.1 ms
 Q  'CURRent? CH1'                           -> b'2.240000\n'                          6.0 ms
```

### E14 ocp_state_delay (done)

OCP:STATe and OCP:DELay set/read-back, accepted spellings and ranges.

Open question 4 (Responses: `1`/`0` and 6-decimal delay), 7 (Case/forms:
`ON`/`OFF` words, space after the comma as in the manual's
`OCP:STATe CH1, 1`) and 9 (delay outside 0-3600 s, MIN/MAX/DEF). Output off.

- 0.5 s: sent 0.5, accepted as sent (read-back 0.500000)
- 1.2345 s (resolution): sent 1.2345, accepted as sent (read-back 1.234500)
- 3600 s: sent 3600, accepted as sent (read-back 3600.000000)
- 3601 s (above range): sent 3601, CLAMPED to the limit 3600 (read-back 3600.000000)
- -1 s: sent -1, CHANGED to 0.000000 (clamped or rounded)
- MAXimum: sent MAXimum, keyword; read-back 3600.000000
- MINimum: sent MINimum, keyword; read-back 0.000000
- DEFault: sent DEFault, keyword; read-back 0.000000
- 0: sent 0, accepted as sent (read-back 0.000000)

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 5.3 ms
 W  'OCP:STATe CH1,1'                            0.1 ms
 Q  'OCP:STATe? CH1'                         -> b'1\n'                               179.3 ms
 W  'OCP:STATe CH1,0'                            0.1 ms
 Q  'OCP:STATe? CH1'                         -> b'0\n'                               259.1 ms
 W  'OCP:STATe CH1,ON'                           0.1 ms
 Q  'OCP:STATe? CH1'                         -> b'1\n'                               260.0 ms
 W  'OCP:STATe CH1,OFF'                          0.2 ms
 Q  'OCP:STATe? CH1'                         -> b'0\n'                               261.1 ms
 W  'OCP:STATe CH1, 1'                           0.1 ms
 Q  'OCP:STATe? CH1'                         -> b'1\n'                               259.9 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                          4.0 ms
 W  'OCP:DELay CH1,0.5'                          0.2 ms
 Q  'OCP:DELay? CH1'                         -> b'0.500000\n'                        254.7 ms
 W  'OCP:DELay CH1,1.2345'                       0.1 ms
 Q  'OCP:DELay? CH1'                         -> b'1.234500\n'                        262.7 ms
 W  'OCP:DELay CH1,3600'                         0.2 ms
 Q  'OCP:DELay? CH1'                         -> b'3600.000000\n'                     258.1 ms
 W  'OCP:DELay CH1,3601'                         0.2 ms
 Q  'OCP:DELay? CH1'                         -> b'3600.000000\n'                     259.8 ms
 W  'OCP:DELay CH1,-1'                           0.1 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                        260.0 ms
 W  'OCP:DELay CH1,MAXimum'                      0.2 ms
 Q  'OCP:DELay? CH1'                         -> b'3600.000000\n'                     258.5 ms
 W  'OCP:DELay CH1,MINimum'                      0.1 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                        260.3 ms
 W  'OCP:DELay CH1,DEFault'                      0.2 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                        258.5 ms
 W  'OCP:DELay CH1,0'                            0.1 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                        261.8 ms
```

### E15 track (done)

OUTPut:TRACK: words vs numbers, what the query returns, side effects, setpoint writes while coupled.

Open question 13 (`OUTPut:TRACK` mapping: 1 = series? 2 = parallel? query
returns number or word), 10 (OVP/OCP re-initialised when switching
series/parallel), 14 (MAX voltage/current in series/parallel versus the
rated table) and 21 (write side: is `VOLTage CH2,20` in SERIES the combined
value or per half; same for `CURRent` in PARALLEL; `MAXimum` and OVP/OCP in
both modes). Runs only while ALL outputs are off (enforced, the
--i-know-outputs-are-on override does not apply); restores the CH2 and CH3
setpoints, OVP and OCP from the snapshot and the original mode, with read-back.

- original track mode: '0'
- SERIES: track reads '1'; before the writes: CH2 V=28.000000 CH2 I=3.000000 CH2 OVP=35.200001 CH2 OCP=3.520000 CH3 V=14.000000 CH3 I=3.100000 CH3 OVP=35.200001 CH3 OCP=3.520000
- SERIES: after the writes: CH2 V=32.320000 CH2 I=3.000000 CH2 OVP=35.200001 CH2 OCP=3.520000 CH3 V=16.160000 CH3 I=3.100000 CH3 OVP=35.200001 CH3 OCP=3.520000
- PARALLEL: track reads '2'; before the writes: CH2 V=16.160000 CH2 I=6.000000 CH2 OVP=35.200001 CH2 OCP=3.520000 CH3 V=16.160000 CH3 I=3.000000 CH3 OVP=35.200001 CH3 OCP=3.520000
- PARALLEL: after the writes: CH2 V=16.160000 CH2 I=3.232000 CH2 OVP=35.200001 CH2 OCP=3.520000 CH3 V=16.160000 CH3 I=1.616000 CH3 OVP=35.200001 CH3 OCP=3.520000
- track back to INDEPENDENT, reads '0'
- local restore of CH2/CH3 setpoints, OVP, OCP: 8 items, FAILED: none
- restored track mode, now reads '0' (wanted '0')

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.5 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.4 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.7 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 3.6 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 5.1 ms
 W  'OUTPut:TRACK SERIES'                        0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'1\n'                                27.9 ms
 Q  'VOLTage? CH2'                           -> b'28.000000\n'                         5.2 ms
 Q  'CURRent? CH2'                           -> b'3.000000\n'                          3.8 ms
 Q  'OVP? CH2'                               -> b'35.200001\n'                         5.0 ms
 Q  'OCP? CH2'                               -> b'3.520000\n'                          5.0 ms
 Q  'VOLTage? CH2,MAX'                       -> b'32.320000\n'                         5.0 ms
 Q  'CURRent? CH2,MAX'                       -> b'3.232000\n'                          5.4 ms
 Q  'VOLTage? CH3'                           -> b'14.000000\n'                         3.9 ms
 Q  'CURRent? CH3'                           -> b'3.100000\n'                          4.9 ms
 Q  'OVP? CH3'                               -> b'35.200001\n'                         3.8 ms
 Q  'OCP? CH3'                               -> b'3.520000\n'                          5.1 ms
 Q  'VOLTage? CH3,MAX'                       -> b'32.320000\n'                         4.6 ms
 Q  'CURRent? CH3,MAX'                       -> b'3.232000\n'                          3.6 ms
 W  'OUTPut:TRACK PARALLEL'                      0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'2\n'                               201.7 ms
 Q  'VOLTage? CH2'                           -> b'14.000000\n'                         5.1 ms
 Q  'CURRent? CH2'                           -> b'6.000000\n'                          3.8 ms
 Q  'OVP? CH2'                               -> b'35.200001\n'                         4.8 ms
 Q  'OCP? CH2'                               -> b'3.520000\n'                          4.9 ms
 Q  'VOLTage? CH2,MAX'                       -> b'32.320000\n'                         3.2 ms
 Q  'CURRent? CH2,MAX'                       -> b'3.232000\n'                          5.0 ms
 Q  'VOLTage? CH3'                           -> b'14.000000\n'                         4.9 ms
 Q  'CURRent? CH3'                           -> b'3.000000\n'                          5.4 ms
 Q  'OVP? CH3'                               -> b'35.200001\n'                         5.2 ms
 Q  'OCP? CH3'                               -> b'3.520000\n'                          3.9 ms
 Q  'VOLTage? CH3,MAX'                       -> b'32.320000\n'                         5.2 ms
 Q  'CURRent? CH3,MAX'                       -> b'3.232000\n'                          5.0 ms
 W  'OUTPut:TRACK INDEPENDENT'                   0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                               200.9 ms
 Q  'VOLTage? CH2'                           -> b'14.000000\n'                         3.1 ms
 Q  'CURRent? CH2'                           -> b'3.000000\n'                          3.5 ms
 Q  'OVP? CH2'                               -> b'35.200001\n'                         3.9 ms
 Q  'OCP? CH2'                               -> b'3.520000\n'                          4.9 ms
 Q  'VOLTage? CH2,MAX'                       -> b'32.320000\n'                         3.8 ms
 Q  'CURRent? CH2,MAX'                       -> b'3.232000\n'                          3.8 ms
 Q  'VOLTage? CH3'                           -> b'14.000000\n'                         5.3 ms
 Q  'CURRent? CH3'                           -> b'3.000000\n'                          4.8 ms
 Q  'OVP? CH3'                               -> b'35.200001\n'                         5.2 ms
 Q  'OCP? CH3'                               -> b'3.520000\n'                          4.9 ms
 Q  'VOLTage? CH3,MAX'                       -> b'32.320000\n'                         5.2 ms
 Q  'CURRent? CH3,MAX'                       -> b'3.232000\n'                          5.0 ms
 W  'OUTPut:TRACK 1'                             0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'1\n'                               204.8 ms
 W  'OUTPut:TRACK 2'                             0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'2\n'                               259.9 ms
 W  'OUTPut:TRACK 0'                             0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                               259.9 ms
 W  'OUTPut:TRACK SERIES'                        0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'1\n'                               260.1 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'28.000000\n'                         5.1 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          4.0 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         4.3 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          4.8 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'14.000000\n'                         3.7 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'3.100000\n'                          8.3 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         6.0 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          4.1 ms
 W  ':SOURce:VOLTage:SET CH2,20'                 0.0 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'20.000000\n'                       216.3 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'10.000000\n'                         3.4 ms
 W  ':SOURce:VOLTage:SET CH2,MAXimum'            0.1 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'32.320000\n'                        12.9 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'16.160000\n'                         5.1 ms
 W  ':SOURce:OVP CH2,MAXimum'                    0.1 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                       237.9 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         5.0 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'32.320000\n'                         4.0 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          5.0 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         4.9 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          4.6 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'16.160000\n'                         3.6 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'3.100000\n'                          4.1 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         3.9 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          5.2 ms
 W  'OUTPut:TRACK PARALLEL'                      0.2 ms
 Q  'OUTPut:TRACK?'                          -> b'2\n'                               220.4 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'16.160000\n'                         5.1 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'6.000000\n'                          4.8 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         5.2 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          5.7 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'16.160000\n'                         5.6 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'3.000000\n'                          4.0 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         4.0 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          5.0 ms
 W  ':SOURce:CURRent:SET CH2,5'                  0.0 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'5.000000\n'                        219.2 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.500000\n'                          3.9 ms
 W  ':SOURce:CURRent:SET CH2,MAXimum'            0.0 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.232000\n'                        256.3 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'1.616000\n'                          3.8 ms
 W  ':SOURce:OCP CH2,MAXimum'                    0.1 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                        254.2 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          4.8 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'16.160000\n'                         2.6 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.232000\n'                          2.6 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         2.3 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          2.2 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'16.160000\n'                         5.3 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'1.616000\n'                          5.0 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         3.9 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          2.6 ms
 W  'OUTPut:TRACK INDEPENDENT'                   0.2 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                               228.0 ms
 Q  'OVP? CH2'                               -> b'35.200001\n'                         3.4 ms
 Q  'OCP? CH2'                               -> b'3.520000\n'                          4.1 ms
 Q  'VOLTage? CH2'                           -> b'16.160000\n'                         3.9 ms
 W  'VOLTage CH2,14.000000'                      0.1 ms
 Q  'VOLTage? CH2'                           -> b'14.000000\n'                       246.8 ms
 Q  'CURRent? CH2'                           -> b'1.616000\n'                          7.0 ms
 W  'CURRent CH2,3.000000'                       0.1 ms
 Q  'CURRent? CH2'                           -> b'3.000000\n'                        252.2 ms
 Q  'OVP? CH3'                               -> b'35.200001\n'                         5.2 ms
 Q  'OCP? CH3'                               -> b'3.520000\n'                          5.1 ms
 Q  'VOLTage? CH3'                           -> b'16.160000\n'                         5.1 ms
 W  'VOLTage CH3,12.000000'                      0.2 ms
 Q  'VOLTage? CH3'                           -> b'12.000000\n'                       243.7 ms
 Q  'CURRent? CH3'                           -> b'1.616000\n'                          3.6 ms
 W  'CURRent CH3,2.000000'                       0.1 ms
 Q  'CURRent? CH3'                           -> b'2.000000\n'                        257.0 ms
 W  'OUTPut:TRACK 0'                             0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                               260.5 ms
```

### E16 sense (done)

MODE CH2,4W / 2W and MODE? CH2.

Open question 13 (`MODE` 0/1 versus 2W/4W mapping, what the query returns
after setting with words). CH2 only, independent mode only, output off.

- restored sense mode, now reads '0' (wanted '0')

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.4 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.3 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 2.6 ms
 Q  'MODE? CH2'                              -> b'0\n'                                 5.1 ms
 W  'MODE CH2,4W'                                0.1 ms
 Q  'MODE? CH2'                              -> b'1\n'                                83.8 ms
 W  'MODE CH2,2W'                                0.1 ms
 Q  'MODE? CH2'                              -> b'0\n'                               262.3 ms
 W  'MODE CH2,1'                                 0.1 ms
 Q  'MODE? CH2'                              -> b'1\n'                               260.3 ms
 W  'MODE CH2,0'                                 0.1 ms
 Q  'MODE? CH2'                              -> b'0\n'                               259.9 ms
 W  'MODE CH2,0'                                 0.1 ms
 Q  'MODE? CH2'                              -> b'0\n'                               259.4 ms
```

### E17 lock (done)

LOCK / LOCK? and whether remote writes still work while locked.

Open question 12 (Remote lock: does the panel stay locked after the session,
is LOCK 0 needed, does the lock interfere with OUTPut). The panel state must
be looked at by a human: see the note printed at the end of the run.

- ASK THE OWNER: after the run, is the front panel locked? (the tool restores LOCK to its original value last)

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.0 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.2 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.4 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 2.3 ms
 Q  'LOCK?'                                  -> b'0\n'                                 5.3 ms
 W  'LOCK 1'                                     0.1 ms
 Q  'LOCK?'                                  -> b'1\n'                               212.3 ms
 W  'VOLTage CH1,1.5'                            0.2 ms
 Q  'VOLTage? CH1'                           -> b'1.500000\n'                        207.6 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.9 ms
 W  'LOCK 0'                                     0.2 ms
 Q  'LOCK?'                                  -> b'0\n'                               309.3 ms
 W  'LOCK ON'                                    0.2 ms
 Q  'LOCK?'                                  -> b'1\n'                               205.2 ms
 W  'LOCK OFF'                                   0.1 ms
 Q  'LOCK?'                                  -> b'0\n'                               329.2 ms
 W  ':SOURce:LOCK:STATe 1'                       0.0 ms
 Q  ':SOURce:LOCK:STATe?'                    -> b'1\n'                               262.8 ms
 W  'LOCK 0'                                     0.1 ms
 Q  'LOCK?'                                  -> b'0\n'                               188.6 ms
```

### E18 opc_wai (done)

*OPC?, *OPC, *WAI and set+query chains on one line.

Open question 11 (Timing: is `*OPC?` meaningful, do `*WAI`/`*OPC` block) and
1 (Termination: several commands on one line with `;`, set followed by query).
Output off.

- voltage after the chains: '1.500000'

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.3 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 3.9 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 4.5 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 5.1 ms
 Q  '*OPC?'                                  -> b'1\n'                                 3.9 ms
 W  'VOLTage CH1,1.000'                          0.0 ms
 Q  '*OPC?'                                  -> b'1\n'                               175.6 ms
 W  '*OPC'                                       0.1 ms
 Q  '*ESR?'                                  -> b'1\n'                               260.3 ms
 W  '*WAI'                                       0.1 ms
 Q  'VOLTage? CH1'                           -> b'1.000000\n'                        260.2 ms
 Q  'VOLTage CH1,1.250;VOLTage? CH1'         -> b'1.250000\n'                          6.4 ms
 Q  'VOLTage CH1,1.500;*OPC?'                -> b'1\n'                                 7.4 ms
 Q  'VOLTage? CH1'                           -> b'1.500000\n'                          2.7 ms
```

### E19 error_reporting (done)

What *ESR?/*STB? show after deliberately invalid commands; where an invalid-channel write lands.

Open question 6 (Errors: how are errors reported, which bits of `*ESR?` and
`*STB?`; hypothesis: `*ESR?` bit 5 is raised only when an error enters an
EMPTY error list, which only `*CLS` empties) and 8 (Channel argument: what
happens with `CH5` and `CH0`; all four channels' voltage and current are read
before and after every invalid-channel write, CH4 included). Output off;
`*CLS` is sent first so the registers start clean.

- no answer to 'FOOBar? CH1' (timeout)
- ESR/STB after a plain *CLS: ('0', '0') (reference for the above)
- no answer to 'VOL? CH1' (timeout)
- no answer to 'VOL? CH1' (timeout)
- no answer to 'VOL? CH1' (timeout)

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.4 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.5 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.3 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 5.4 ms
 W  '*CLS'                                       0.1 ms
 Q  '*ESR?'                                  -> b'0\n'                               136.3 ms
 Q  '*STB?'                                  -> b'0\n'                                 1.9 ms
 W  '*CLS'                                       0.1 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'5.000000\n'                        261.8 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'2.000000\n'                          4.8 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'14.000000\n'                         4.4 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          5.1 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'12.000000\n'                         3.9 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.000000\n'                          4.9 ms
 Q  ':SOURce:VOLTage:SET? CH4'               -> b'0.000000\n'                          5.5 ms
 Q  ':SOURce:CURRent:SET? CH4'               -> b'0.000000\n'                          4.5 ms
 W  'VOLTage CH5,1'                              0.1 ms
 Q  '*ESR?'                                  -> b'0\n'                               222.2 ms
 Q  '*STB?'                                  -> b'0\n'                                 2.0 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'5.000000\n'                          3.4 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'2.000000\n'                          2.6 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'14.000000\n'                         2.4 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          2.5 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'12.000000\n'                         2.3 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.000000\n'                          4.9 ms
 Q  ':SOURce:VOLTage:SET? CH4'               -> b'0.000000\n'                          5.1 ms
 Q  ':SOURce:CURRent:SET? CH4'               -> b'0.000000\n'                          4.5 ms
 W  '*CLS'                                       0.1 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'5.000000\n'                        231.4 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'2.000000\n'                          3.5 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'14.000000\n'                         3.9 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          3.5 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'12.000000\n'                         3.6 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.000000\n'                          3.7 ms
 Q  ':SOURce:VOLTage:SET? CH4'               -> b'0.000000\n'                          3.9 ms
 Q  ':SOURce:CURRent:SET? CH4'               -> b'0.000000\n'                          2.7 ms
 W  'VOLTage CH0,1'                              0.1 ms
 Q  '*ESR?'                                  -> b'0\n'                               231.9 ms
 Q  '*STB?'                                  -> b'0\n'                                 3.2 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'5.000000\n'                          4.8 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'2.000000\n'                          3.9 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'14.000000\n'                         4.9 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          4.8 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'12.000000\n'                         5.0 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.000000\n'                          4.9 ms
 Q  ':SOURce:VOLTage:SET? CH4'               -> b'0.000000\n'                          2.2 ms
 Q  ':SOURce:CURRent:SET? CH4'               -> b'0.000000\n'                          2.5 ms
 W  '*CLS'                                       0.1 ms
 Q  '*ESR?'                                  -> b'0\n'                               222.1 ms
 Q  '*STB?'                                  -> b'0\n'                                 2.1 ms
 W  'VOLTage CH1,abc'                            0.1 ms
 Q  '*ESR?'                                  -> b'0\n'                               257.3 ms
 Q  '*STB?'                                  -> b'0\n'                                 1.6 ms
 W  '*CLS'                                       0.1 ms
 W  'VOLTage CH1,7.5'                            0.0 ms
 Q  '*ESR?'                                  -> b'0\n'                               264.8 ms
 Q  '*STB?'                                  -> b'0\n'                                 2.8 ms
 W  '*CLS'                                       0.1 ms
 Q  'FOOBar? CH1'                            -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1517.7 ms
 Q  '*ESR?'                                  -> b'32\n'                                2.0 ms
 Q  '*STB?'                                  -> b'0\n'                                 1.6 ms
 W  '*CLS'                                       0.1 ms
 Q  'VOL? CH1'                               -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1502.2 ms
 Q  '*ESR?'                                  -> b'32\n'                                1.8 ms
 Q  'VOL? CH1'                               -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1515.9 ms
 Q  '*ESR?'                                  -> b'32\n'                                1.7 ms
 W  '*CLS'                                       0.1 ms
 Q  'VOL? CH1'                               -> VisaIOError: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.   1513.1 ms
 Q  '*ESR?'                                  -> b'32\n'                                1.9 ms
```

### E20 set_forms (done)

Spellings of the voltage SET command, verified by read-back.

Open question 7 (Case/forms: leading colon, `:SOURce:` prefix, `:SET` node,
short forms, lower case, space after the comma). Each form writes a distinct
value after the setpoint was reset to 0.5 V. Output off. A command without a
channel is deliberately not tried as a write: it might hit another channel.

| set command | result | read-back |
|---|---|---|
| `:SOURce:VOLTage:SET CH1,1.1` | ACCEPTED | `'1.100000'` |
| `SOURce:VOLTage CH1,1.2` | ACCEPTED | `'1.200000'` |
| `VOLTage:SET CH1,1.3` | ACCEPTED | `'1.300000'` |
| `VOLT CH1,1.4` | ACCEPTED | `'1.400000'` |
| `volt ch1,1.5` | ACCEPTED | `'1.500000'` |
| `VOLTage CH1, 1.6` | ACCEPTED | `'1.600000'` |
| `VOLT:SET CH1,1.7` | ACCEPTED | `'1.700000'` |
| `:VOLTage CH1,1.8` | ACCEPTED | `'1.800000'` |
| `VOLTage CH1 ,1.9` | ACCEPTED | `'1.900000'` |

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.3 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.5 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.0 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 1.9 ms
 W  'VOLTage CH1,0.5'                            0.2 ms
 W  ':SOURce:VOLTage:SET CH1,1.1'                0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.100000\n'                        229.1 ms
 W  'VOLTage CH1,0.5'                            0.2 ms
 W  'SOURce:VOLTage CH1,1.2'                     0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.200000\n'                        263.3 ms
 W  'VOLTage CH1,0.5'                            0.1 ms
 W  'VOLTage:SET CH1,1.3'                        0.1 ms
 Q  'VOLTage? CH1'                           -> b'1.300000\n'                        259.0 ms
 W  'VOLTage CH1,0.5'                            0.1 ms
 W  'VOLT CH1,1.4'                               0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.400000\n'                        258.0 ms
 W  'VOLTage CH1,0.5'                            0.1 ms
 W  'volt ch1,1.5'                               0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.500000\n'                        263.4 ms
 W  'VOLTage CH1,0.5'                            0.1 ms
 W  'VOLTage CH1, 1.6'                           0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.600000\n'                        312.0 ms
 W  'VOLTage CH1,0.5'                            0.1 ms
 W  'VOLT:SET CH1,1.7'                           0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.700000\n'                        202.6 ms
 W  'VOLTage CH1,0.5'                            0.1 ms
 W  ':VOLTage CH1,1.8'                           0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.800000\n'                        316.9 ms
 W  'VOLTage CH1,0.5'                            0.1 ms
 W  'VOLTage CH1 ,1.9'                           0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.900000\n'                        260.2 ms
```

### E21 plug_write_smoke (done)

The plug's write path and tearDown() against the instrument, outputs off.

Constructs SiglentSpdPlug on the tool's own link (every exchange lands in the
transcript), runs configure_channel(1, ...), set_output_delay(1, ...),
set_sense(2, 4W) and back to 2W, set_output_delay(1, 0, 0) and then tearDown(),
which sends `OUTPut:ALL 0`, one `OUTPut? CHn` per channel, the restore writes
and `:SOURce:LOCK:STATe OFF` last. Run 1 never sent `OUTPut CHn,0`,
`OUTPut:ALL 0` or the ON/OFF delay writes, so this path had never run on
hardware. Afterwards raw queries check: all outputs 0, LOCK? 0, every snapshot value back.
Open question 9 (ON/OFF delay writes and read-back) and 12 (unlock stays the last write).

- plug.configure_channel(1, ...): ok
- plug.set_output_delay(1, on_s=0.5, off_s=0.5): ok
- plug.set_sense(2, FOUR_WIRE): ok
- plug.set_sense(2, TWO_WIRE): ok
- plug.set_output_delay(1, on_s=0, off_s=0): ok
- plug.tearDown() follows (OUTPut:ALL 0, OUTPut? per channel, restore, unlock last)
- plug.tearDown(): returned; the tool's link was closed 1 time(s) by the plug and kept open

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.3 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.3 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.2 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 2.0 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 5.3 ms
 Q  '*IDN?'                                  -> b'Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1\n'     7.6 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'5.000000\n'                          1.8 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'2.000000\n'                          2.3 ms
 Q  ':SOURce:OVP? CH1'                       -> b'6.600000\n'                          1.9 ms
 Q  ':SOURce:OCP? CH1'                       -> b'3.520000\n'                          5.2 ms
 Q  ':SOURce:OCP:STATe? CH1'                 -> b'0\n'                                 5.2 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                          3.9 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                          3.0 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                          3.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 1.9 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'14.000000\n'                         3.8 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          4.5 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         5.0 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          2.2 ms
 Q  ':SOURce:OCP:STATe? CH2'                 -> b'0\n'                                 2.3 ms
 Q  'OCP:DELay? CH2'                         -> b'0.000000\n'                          2.4 ms
 Q  'OUTPut:ON:DELay? CH2'                   -> b'0.000000\n'                          2.6 ms
 Q  'OUTPut:OFF:DELay? CH2'                  -> b'0.000000\n'                          5.2 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 5.2 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'12.000000\n'                         2.8 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.000000\n'                          5.2 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         3.7 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          5.9 ms
 Q  ':SOURce:OCP:STATe? CH3'                 -> b'0\n'                                 6.6 ms
 Q  'OCP:DELay? CH3'                         -> b'0.000000\n'                          3.9 ms
 Q  'OUTPut:ON:DELay? CH3'                   -> b'0.000000\n'                          3.0 ms
 Q  'OUTPut:OFF:DELay? CH3'                  -> b'0.000000\n'                          5.1 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 3.6 ms
 Q  ':SOURce:VOLTage:SET? CH4'               -> b'0.000000\n'                          3.8 ms
 Q  ':SOURce:CURRent:SET? CH4'               -> b'0.000000\n'                          2.4 ms
 Q  ':SOURce:OVP? CH4'                       -> b'6.600000\n'                          2.5 ms
 Q  ':SOURce:OCP? CH4'                       -> b'3.520000\n'                          3.6 ms
 Q  ':SOURce:OCP:STATe? CH4'                 -> b'0\n'                                 3.1 ms
 Q  'OCP:DELay? CH4'                         -> b'0.000000\n'                          5.2 ms
 Q  'OUTPut:ON:DELay? CH4'                   -> b'0.000000\n'                          4.5 ms
 Q  'OUTPut:OFF:DELay? CH4'                  -> b'0.000000\n'                          5.1 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 4.7 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 2.8 ms
 W  ':SOURce:OVP CH1,2'                          0.1 ms
 Q  ':SOURce:OVP? CH1'                       -> b'2.000000\n'                         28.2 ms
 W  ':SOURce:OCP CH1,0.5'                        0.2 ms
 Q  ':SOURce:OCP? CH1'                       -> b'0.500000\n'                        260.1 ms
 W  'OCP:DELay CH1,0.5'                          0.2 ms
 Q  'OCP:DELay? CH1'                         -> b'0.500000\n'                        259.7 ms
 W  ':SOURce:OCP:STATe CH1,1'                    0.1 ms
 Q  ':SOURce:OCP:STATe? CH1'                 -> b'1\n'                               258.9 ms
 W  ':SOURce:VOLTage:SET CH1,1'                  0.1 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'1.000000\n'                        260.0 ms
 W  ':SOURce:CURRent:SET CH1,0.1'                0.1 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'0.100000\n'                        259.4 ms
 W  'OUTPut:ON:DELay CH1,0.5'                    0.2 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.500000\n'                        260.2 ms
 W  'OUTPut:OFF:DELay CH1,0.5'                   0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.500000\n'                          5.0 ms
 W  'MODE CH2,4W'                                0.1 ms
 Q  'MODE? CH2'                              -> b'1\n'                               256.2 ms
 W  'MODE CH2,2W'                                0.2 ms
 Q  'MODE? CH2'                              -> b'0\n'                               260.4 ms
 W  'OUTPut:ON:DELay CH1,0'                      0.2 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                        260.5 ms
 W  'OUTPut:OFF:DELay CH1,0'                     0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                        259.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.0 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 4.9 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 5.0 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 4.3 ms
 W  'OUTPut:ALL 0'                               0.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                               271.6 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.5 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 2.3 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 5.5 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.4 ms
 Q  ':SOURce:OVP? CH1'                       -> b'2.000000\n'                          4.6 ms
 W  ':SOURce:OVP CH1,6.6'                        0.1 ms
 Q  ':SOURce:OVP? CH1'                       -> b'6.600000\n'                        203.5 ms
 Q  ':SOURce:OCP? CH1'                       -> b'0.500000\n'                          3.7 ms
 W  ':SOURce:OCP CH1,3.52'                       0.1 ms
 Q  ':SOURce:OCP? CH1'                       -> b'3.520000\n'                        254.6 ms
 Q  'OCP:DELay? CH1'                         -> b'0.500000\n'                          4.7 ms
 W  'OCP:DELay CH1,0'                            0.1 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                        255.9 ms
 Q  ':SOURce:OCP:STATe? CH1'                 -> b'1\n'                                 4.5 ms
 W  ':SOURce:OCP:STATe CH1,0'                    0.0 ms
 Q  ':SOURce:OCP:STATe? CH1'                 -> b'0\n'                               254.1 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                          3.9 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                          4.3 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'1.000000\n'                          3.8 ms
 W  ':SOURce:VOLTage:SET CH1,5'                  0.2 ms
 Q  ':SOURce:VOLTage:SET? CH1'               -> b'5.000000\n'                        246.8 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'0.100000\n'                          5.6 ms
 W  ':SOURce:CURRent:SET CH1,2'                  0.1 ms
 Q  ':SOURce:CURRent:SET? CH1'               -> b'2.000000\n'                        255.2 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 3.9 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         3.8 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          5.0 ms
 Q  'OCP:DELay? CH2'                         -> b'0.000000\n'                          4.0 ms
 Q  ':SOURce:OCP:STATe? CH2'                 -> b'0\n'                                 3.7 ms
 Q  'OUTPut:ON:DELay? CH2'                   -> b'0.000000\n'                          5.2 ms
 Q  'OUTPut:OFF:DELay? CH2'                  -> b'0.000000\n'                          4.9 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'14.000000\n'                         4.8 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          3.8 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.3 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         2.2 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          2.3 ms
 Q  'OCP:DELay? CH3'                         -> b'0.000000\n'                          2.3 ms
 Q  ':SOURce:OCP:STATe? CH3'                 -> b'0\n'                                 4.9 ms
 Q  'OUTPut:ON:DELay? CH3'                   -> b'0.000000\n'                          5.1 ms
 Q  'OUTPut:OFF:DELay? CH3'                  -> b'0.000000\n'                          4.0 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'12.000000\n'                         2.5 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.000000\n'                          2.3 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 2.1 ms
 Q  ':SOURce:OVP? CH4'                       -> b'6.600000\n'                          1.8 ms
 Q  ':SOURce:OCP? CH4'                       -> b'3.520000\n'                          3.3 ms
 Q  'OCP:DELay? CH4'                         -> b'0.000000\n'                          4.8 ms
 Q  ':SOURce:OCP:STATe? CH4'                 -> b'0\n'                                 2.9 ms
 Q  'OUTPut:ON:DELay? CH4'                   -> b'0.000000\n'                          2.7 ms
 Q  'OUTPut:OFF:DELay? CH4'                  -> b'0.000000\n'                          4.8 ms
 Q  ':SOURce:VOLTage:SET? CH4'               -> b'0.000000\n'                          5.9 ms
 Q  ':SOURce:CURRent:SET? CH4'               -> b'0.000000\n'                          7.1 ms
 W  ':SOURce:LOCK:STATe OFF'                     0.1 ms
 Q  ':SOURce:LOCK:STATe?'                    -> b'0\n'                               269.0 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.5 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.5 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 3.5 ms
 Q  'LOCK?'                                  -> b'0\n'                                 5.3 ms
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          4.8 ms
 Q  'CURRent? CH1'                           -> b'2.000000\n'                          2.3 ms
 Q  'OVP? CH1'                               -> b'6.600000\n'                          2.3 ms
 Q  'OCP? CH1'                               -> b'3.520000\n'                          2.2 ms
 Q  'OCP:STATe? CH1'                         -> b'0\n'                                 2.6 ms
 Q  'OCP:DELay? CH1'                         -> b'0.000000\n'                          5.6 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                          5.2 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                          4.0 ms
 Q  'VOLTage? CH2'                           -> b'14.000000\n'                         2.3 ms
 Q  'CURRent? CH2'                           -> b'3.000000\n'                          2.0 ms
 Q  'OVP? CH2'                               -> b'35.200001\n'                         2.0 ms
 Q  'OCP? CH2'                               -> b'3.520000\n'                          2.3 ms
 Q  'OCP:STATe? CH2'                         -> b'0\n'                                 4.3 ms
 Q  'OCP:DELay? CH2'                         -> b'0.000000\n'                          5.1 ms
 Q  'OUTPut:ON:DELay? CH2'                   -> b'0.000000\n'                          4.7 ms
 Q  'OUTPut:OFF:DELay? CH2'                  -> b'0.000000\n'                          2.6 ms
 Q  'VOLTage? CH3'                           -> b'12.000000\n'                         2.3 ms
 Q  'CURRent? CH3'                           -> b'2.000000\n'                          2.0 ms
 Q  'OVP? CH3'                               -> b'35.200001\n'                         1.9 ms
 Q  'OCP? CH3'                               -> b'3.520000\n'                          3.5 ms
 Q  'OCP:STATe? CH3'                         -> b'0\n'                                 5.2 ms
 Q  'OCP:DELay? CH3'                         -> b'0.000000\n'                          4.5 ms
 Q  'OUTPut:ON:DELay? CH3'                   -> b'0.000000\n'                          5.5 ms
 Q  'OUTPut:OFF:DELay? CH3'                  -> b'0.000000\n'                          5.1 ms
 Q  'VOLTage? CH4'                           -> b'0.000000\n'                          5.5 ms
 Q  'CURRent? CH4'                           -> b'0.000000\n'                          6.5 ms
 Q  'OVP? CH4'                               -> b'6.600000\n'                          4.3 ms
 Q  'OCP? CH4'                               -> b'3.520000\n'                          4.8 ms
 Q  'OCP:STATe? CH4'                         -> b'0\n'                                 4.8 ms
 Q  'OCP:DELay? CH4'                         -> b'0.000000\n'                          3.8 ms
 Q  'OUTPut:ON:DELay? CH4'                   -> b'0.000000\n'                          3.2 ms
 Q  'OUTPut:OFF:DELay? CH4'                  -> b'0.000000\n'                          5.4 ms
 Q  'MODE? CH2'                              -> b'0\n'                                 3.6 ms
 Q  'MODE? CH3'                              -> b'0\n'                                 4.1 ms
```

### E30 output_settling (skipped)

Output ON at 1.0 V / 0.1 A, no load: settling curve, run mode, OFF.

Open question 11 (Timing/settling: how long after `OUTPut CHn,1` until the
output is at voltage, is `*OPC?` meaningful for output-on, measurement refresh
when polled every 50 ms; what `MEASure:RUN:MODE?` returns). Only runs with
--allow-output --confirm-no-load. Always followed by OUTPut off, a wait until
OUTPut? reads 0 and the snapshot restore.

**needs --allow-output and --confirm-no-load**

### E31 off_delay (skipped)

OUTPut:OFF:DELay semantics with the output on (no load): CH1 1.0 V / 0.1 A, OFF delay 2 s.

Open question 22: what does `OUTPut? CHn` return between `OUTPut CHn,0` and the
actual switch-off; does `OUTPut:ALL 0` honour the per-channel delay; does setting
the delay to 0 while a delayed switch-off is pending switch off immediately.
Three scenarios, each polled every 100 ms for 3 s with `OUTPut? CH1` and
`MEASure:VOLTage? CH1`. Only with --allow-output --confirm-no-load. The whole body is
in a try/finally that sets the delay to 0, forces `OUTPut CH1,0` and waits for
`OUTPut? CH1` = 0; the snapshot restore follows.

**needs --allow-output and --confirm-no-load**

