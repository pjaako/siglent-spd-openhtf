# Hardware acceptance report

- Generated: 2026-10-04 19:21:29 UTC
- Tool: `tools/hw_acceptance.py`; resource `TCPIP::<redacted>::5025::SOCKET`; command terminator `'\n'`, read termination `'\n'`
- Instrument: `Siglent Technologies,SPD4323X,<redacted>,4.1.2.9R1`
- Mode: output experiment enabled (CH1, 1.0 V / 0.1 A, no load)
- Target channel for write experiments: CH1
- Plug package importable: yes
- Redaction: host and serial number replaced by `<redacted>` (public repository); the `.local.` log keeps everything.

## Safety log

- output states at start: {1: '0', 2: '0', 3: '0', 4: '0'}; OUTPut:ALL? -> '0'
- snapshot saved to acceptance_snapshot.local.json before the first write (channels that may be written: [1, 2, 3, 4])
- CH1 was switched on by this run; output off confirmed
- restore: 36 items, 1 written back, 35 unchanged, 0 skipped (not snapshotted), 0 FAILED
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
| lock | `0` | `0` | restored |

## Experiment summary

| # | experiment | tier | open questions | status | note |
|---|---|---|---|---|---|
| 1 | Identity string and raw reply shape. | read | 1, 4 | skipped | not in --only |
| 2 | Raw reply of every read-only query, every channel. | read | 4, 5, 8 | skipped | not in --only |
| 3 | Syntax forms as read-only queries (same table as bare_socket_check.py). | read | 1, 7, 8 | skipped | not in --only |
| 4 | MINimum / MAXimum / DEFault as queries (`VOLTage? CH1,MAX`). | read | 9, 14 | skipped | not in --only |
| 5 | Round-trip time per query, median of 5. | read | 11 | skipped | not in --only |
| 6 | Status registers before and after invalid read-only queries. | read | 6 | skipped | not in --only |
| 7 | Open the supply as TCPIP::<host>::INSTR (VXI-11) next to the socket session. | read | 3 | skipped | not in --only |
| 8 | Run the plug's read-only methods against the real instrument. | read | 4 | skipped | not in --only |
| 10 | Voltage setpoint: resolution, above-rating, negative, keywords. | write | 4, 9 | skipped | not in --only |
| 11 | Current setpoint: resolution, above-rating, negative, keywords. | write | 4, 9 | skipped | not in --only |
| 12 | OVP set/read-back, out-of-range values, interaction with the voltage setpoint. | write | 9, 10 | skipped | not in --only |
| 13 | OCP set/read-back (format of the unprinted `OCP?` response), out-of-range, interaction. | write | 5, 9, 10 | skipped | not in --only |
| 14 | OCP:STATe and OCP:DELay set/read-back, accepted spellings and ranges. | write | 4, 7, 9 | skipped | not in --only |
| 15 | OUTPut:TRACK: words vs numbers, what the query returns, side effects, setpoint writes while coupled. | write | 10, 13, 14, 21 | skipped | not in --only |
| 16 | MODE CH2,4W / 2W and MODE? CH2. | write | 13 | skipped | not in --only |
| 17 | LOCK / LOCK? and whether remote writes still work while locked. | write | 12 | skipped | not in --only |
| 18 | *OPC?, *OPC, *WAI and set+query chains on one line. | write | 1, 11 | skipped | not in --only |
| 19 | What *ESR?/*STB? show after deliberately invalid commands; where an invalid-channel write lands. | write | 6, 8 | skipped | not in --only |
| 20 | Spellings of the voltage SET command, verified by read-back. | write | 7 | skipped | not in --only |
| 21 | The plug's write path and tearDown() against the instrument, outputs off. | write | 9, 12 | skipped | not in --only |
| 30 | Output ON at 1.0 V / 0.1 A, no load: settling curve, run mode, OFF. | output | 11 | done |  |
| 31 | OUTPut:OFF:DELay semantics with the output on (no load): CH1 1.0 V / 0.1 A, OFF delay 2 s. | output | 11, 22 | done |  |

## Findings by open question (docs/scpi_reference.md section 8)

### Q1 Termination (commands, multi-command lines)

Experiments: [1, 3, 18]; ran: none.

- no finding recorded

### Q2 USB identity

*Coverage: needs USB (this tool uses the LAN socket).*

Experiments: none; ran: none.

- no finding recorded

### Q3 LAN (VXI-11, simultaneous connections, web, telnet)

*Coverage: partly: second connection is in bare_socket_check.py; VXI-11 here only with --try-vxi11; web/telnet via bare_socket_check.py --probe-ports.*

Experiments: [7]; ran: none.

- no finding recorded

### Q4 Response formats

Experiments: [1, 2, 8, 10, 11, 14]; ran: none.

- no finding recorded

### Q5 Missing responses

*Coverage: partly: OCP? covered; LAN/GPIB/STORage queries are out of scope and blocked by the safety policy.*

Experiments: [2, 13]; ran: none.

- no finding recorded

### Q6 Error reporting

Experiments: [6, 19]; ran: none.

- no finding recorded

### Q7 Case / forms (leading colon, SOURce, short forms, spacing)

Experiments: [3, 14, 20]; ran: none.

- no finding recorded

### Q8 Channel argument (optional? invalid channel?)

Experiments: [2, 3, 19]; ran: none.

- no finding recorded

### Q9 Parameter keywords and out-of-range behaviour

Experiments: [4, 10, 11, 12, 13, 14, 21]; ran: none.

- no finding recorded

### Q10 OVP/OCP interaction with other settings

*Coverage: partly: output state after a trip and after RESET:PROTect needs a load that trips protection (out of scope).*

Experiments: [12, 13, 15]; ran: none.

- no finding recorded

### Q11 Timing / settling / *OPC

Experiments: [5, 18, 30, 31]; ran: [30, 31].

- (E30) first MEASure:VOLTage? after `OUTPut CHn,1`: '0.999164' after 295 ms; `*OPC?` -> '1' in 2.3 ms; OUTPut? -> '1'
- (E30) while ON, no load: I='0.000230' P='0.000229' `MEASure:RUN:MODE?` -> 'CV'
- (E30) after OFF: V='0.006416', I='0.000119', `MEASure:RUN:MODE?` -> 'CV'
- (E30) ON curve: first sample within 20 mV of 1.0 V at 0.295 s; stays within from 0.295 s; peak 0.999 V; last 0.999 V; 11 samples
- (E30) OFF curve: first sample at or below 20 mV at 0.700 s (starts 0.962 V)

### Q12 Remote lock

Experiments: [17, 21]; ran: none.

- no finding recorded

### Q13 OUTPut:TRACK and MODE mappings

*Coverage: partly: rejection of OUTPut:TRACK while outputs are on is not tested (would need an output on).*

Experiments: [15, 16]; ran: none.

- no finding recorded

### Q14 Rated table / MAX queries

*Coverage: partly: SPD4306X CH4 needs that model (out of scope).*

Experiments: [4, 15]; ran: none.

- no finding recorded

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

Experiments: [15]; ran: none.

- no finding recorded

### Q22 Output OFF delay semantics

Experiments: [31]; ran: [31].

- (E31) A. OUTPut CHn,0 with a pending delay (delay 2 s, V while on 0.998909): `OUTPut CH1,0` -> OUTPut? replies: 1 from t=0.00 s, 0 from t=2.00 s; MEASure:VOLTage? first sample at or below 0.1 V: t=2.60 s (peak 0.999164 V); 31 samples
- (E31) B. OUTPut:ALL 0 with a pending delay (delay 2 s, V while on 0.999164): `OUTPut:ALL 0` -> OUTPut? replies: 1 from t=0.00 s, 0 from t=2.00 s; MEASure:VOLTage? first sample at or below 0.1 V: t=2.60 s (peak 0.999164 V); 31 samples
- (E31) C. delay set to 0 while the switch-off is pending (delay 2 s, V while on 0.998909): `OUTPut CH1,0` then at ~0.5 s `OUTPut:OFF:DELay CH1,0` -> OUTPut? replies: 1 from t=0.00 s, 0 from t=0.50 s; MEASure:VOLTage? first sample at or below 0.1 V: t=1.10 s (peak 0.999164 V); 31 samples

## Experiment details

### E1 identity (skipped)

Identity string and raw reply shape.

Open question 1 (Termination: which terminator the instrument expects and
sends) and 4 (Responses: what the literal `\s` in the *IDN? example looks
like on the wire, actual *IDN? string, `\n` after every reply).

**not in --only**

### E2 formats (skipped)

Raw reply of every read-only query, every channel.

Open question 4 (Responses: decimals, units, `0`/`1`, `CV`, number vs word
for OUTPut:TRACK? and MODE?), 5 (Missing responses: `OCP?` has no printed
response) and 8 (Channel argument: MODE? CH1, which the manual says is
CH2/CH3 only).

**not in --only**

### E3 forms (skipped)

Syntax forms as read-only queries (same table as bare_socket_check.py).

Open question 7 (Case/forms: leading colon, `[:SOURce]`, short forms,
literal brackets, spacing), 8 (Channel argument: no channel, CH0, CH5,
bare number) and 1 (Termination: two queries on one line separated by `;`).

**not in --only**

### E4 min_max (skipped)

MINimum / MAXimum / DEFault as queries (`VOLTage? CH1,MAX`).

Open question 9 (Parameter keywords: do they work, what do they return) and
14 (Rated table: real limits returned by `VOLT? CHn,MAX` / `CURR? CHn,MAX`).
Queries only; nothing is set.

**not in --only**

### E5 timing (skipped)

Round-trip time per query, median of 5.

Open question 11 (Timing: response time of MEASure, measurement refresh
rate); the numbers size the plug's timeouts and polling interval.

**not in --only**

### E6 status_registers (skipped)

Status registers before and after invalid read-only queries.

Open question 6 (Errors: no error-query command; which bits of `*ESR?` and
`*STB?` are used, what `*TST?` = 0 means). `*TST?` runs only with
--allow-selftest.

**not in --only**

### E7 vxi11 (skipped)

Open the supply as TCPIP::<host>::INSTR (VXI-11) next to the socket session.

Open question 3 (LAN: does the instrument expose VXI-11 / `TCPIP::<ip>::INSTR`,
and may a second session coexist with the socket?). Needs a network path to
the instrument's portmapper; a forwarded single port 5025 will not do.

**not in --only**

### E8 plug_smoke (skipped)

Run the plug's read-only methods against the real instrument.

Not an open question: it checks that the plug's assumptions (`# ASSUMPTION(hw)`
in src/) survive contact with the instrument. Answers nothing new for
section 8 but any exception here is a defect to fix in the plug or the fake
(open question 4 is the closest: response parsing). Skipped when the package
is not installed. Calls only getters; tearDown() is never called.

**not in --only**

### E10 voltage_set (skipped)

Voltage setpoint: resolution, above-rating, negative, keywords.

Open question 9 (Parameter keywords: rounding/clamping vs error when a value
is out of range, what MINimum/MAXimum/DEFault set) and 4 (Responses: how many
decimals come back after a set). Output stays off.

**not in --only**

### E11 current_set (skipped)

Current setpoint: resolution, above-rating, negative, keywords.

Open question 9 (Parameter keywords: clamp vs error out of range, what the
keywords set) and 4 (Responses: decimals). Output stays off.

**not in --only**

### E12 ovp (skipped)

OVP set/read-back, out-of-range values, interaction with the voltage setpoint.

Open question 9 (clamping vs error for OVP outside 0.1-1.1 x rated, MIN/MAX/DEF)
and 10 (Interaction: OVP below the set voltage, voltage above OVP). Output off.

**not in --only**

### E13 ocp (skipped)

OCP set/read-back (format of the unprinted `OCP?` response), out-of-range, interaction.

Open question 5 (Missing responses: `OCP?`), 9 (clamping vs error for OCP
outside 0.1-1.1 x rated, MIN/MAX/DEF) and 10 (Interaction: OCP vs current
setpoint). Output off.

**not in --only**

### E14 ocp_state_delay (skipped)

OCP:STATe and OCP:DELay set/read-back, accepted spellings and ranges.

Open question 4 (Responses: `1`/`0` and 6-decimal delay), 7 (Case/forms:
`ON`/`OFF` words, space after the comma as in the manual's
`OCP:STATe CH1, 1`) and 9 (delay outside 0-3600 s, MIN/MAX/DEF). Output off.

**not in --only**

### E15 track (skipped)

OUTPut:TRACK: words vs numbers, what the query returns, side effects, setpoint writes while coupled.

Open question 13 (`OUTPut:TRACK` mapping: 1 = series? 2 = parallel? query
returns number or word), 10 (OVP/OCP re-initialised when switching
series/parallel), 14 (MAX voltage/current in series/parallel versus the
rated table) and 21 (write side: is `VOLTage CH2,20` in SERIES the combined
value or per half; same for `CURRent` in PARALLEL; `MAXimum` and OVP/OCP in
both modes). Runs only while ALL outputs are off (enforced, the
--i-know-outputs-are-on override does not apply); restores the CH2 and CH3
setpoints, OVP and OCP from the snapshot and the original mode, with read-back.

**not in --only**

### E16 sense (skipped)

MODE CH2,4W / 2W and MODE? CH2.

Open question 13 (`MODE` 0/1 versus 2W/4W mapping, what the query returns
after setting with words). CH2 only, independent mode only, output off.

**not in --only**

### E17 lock (skipped)

LOCK / LOCK? and whether remote writes still work while locked.

Open question 12 (Remote lock: does the panel stay locked after the session,
is LOCK 0 needed, does the lock interfere with OUTPut). The panel state must
be looked at by a human: see the note printed at the end of the run.

**not in --only**

### E18 opc_wai (skipped)

*OPC?, *OPC, *WAI and set+query chains on one line.

Open question 11 (Timing: is `*OPC?` meaningful, do `*WAI`/`*OPC` block) and
1 (Termination: several commands on one line with `;`, set followed by query).
Output off.

**not in --only**

### E19 error_reporting (skipped)

What *ESR?/*STB? show after deliberately invalid commands; where an invalid-channel write lands.

Open question 6 (Errors: how are errors reported, which bits of `*ESR?` and
`*STB?`; hypothesis: `*ESR?` bit 5 is raised only when an error enters an
EMPTY error list, which only `*CLS` empties) and 8 (Channel argument: what
happens with `CH5` and `CH0`; all four channels' voltage and current are read
before and after every invalid-channel write, CH4 included). Output off;
`*CLS` is sent first so the registers start clean.

**not in --only**

### E20 set_forms (skipped)

Spellings of the voltage SET command, verified by read-back.

Open question 7 (Case/forms: leading colon, `:SOURce:` prefix, `:SET` node,
short forms, lower case, space after the comma). Each form writes a distinct
value after the setpoint was reset to 0.5 V. Output off. A command without a
channel is deliberately not tried as a write: it might hit another channel.

**not in --only**

### E21 plug_write_smoke (skipped)

The plug's write path and tearDown() against the instrument, outputs off.

Constructs SiglentSpdPlug on the tool's own link (every exchange lands in the
transcript), runs configure_channel(1, ...), set_output_delay(1, ...),
set_sense(2, 4W) and back to 2W, set_output_delay(1, 0, 0) and then tearDown(),
which sends `OUTPut:ALL 0`, one `OUTPut? CHn` per channel, the restore writes
and `:SOURce:LOCK:STATe OFF` last. Run 1 never sent `OUTPut CHn,0`,
`OUTPut:ALL 0` or the ON/OFF delay writes, so this path had never run on
hardware. Afterwards raw queries check: all outputs 0, LOCK? 0, every snapshot value back.
Open question 9 (ON/OFF delay writes and read-back) and 12 (unlock stays the last write).

**not in --only**

### E30 output_settling (done)

Output ON at 1.0 V / 0.1 A, no load: settling curve, run mode, OFF.

Open question 11 (Timing/settling: how long after `OUTPut CHn,1` until the
output is at voltage, is `*OPC?` meaningful for output-on, measurement refresh
when polled every 50 ms; what `MEASure:RUN:MODE?` returns). Only runs with
--allow-output --confirm-no-load. Always followed by OUTPut off, a wait until
OUTPut? reads 0 and the snapshot restore.

- ON delay '0.000000', OFF delay '0.000000' (non-zero values distort the curve)
- before ON: V='0.000302' I='0.000230' mode='CV'
- OUTPut? after off command reads '0' (0.2 s after the command)

ON curve (t s, V):

```
0.295  0.999164
0.357  0.999164
0.406  0.999164
0.457  0.999164
0.506  0.999164
0.554  0.999164
0.605  0.999164
0.657  0.999164
0.704  0.999164
0.758  0.999164
0.808  0.999164
```

OFF curve (t s, V):

```
0.000  0.961716
0.050  0.363061
0.104  0.26855
0.151  0.216327
0.200  0.216327
0.251  0.133789
0.300  0.108824
0.352  0.078764
0.400  0.078764
0.450  0.049723
0.504  0.040043
0.553  0.03291
0.600  0.029598
0.650  0.029598
0.700  0.017115
0.751  0.014568
0.801  0.011766
0.851  0.011766
0.900  0.00718
0.954  0.006416
```

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.9 ms
 W  'VOLTage CH1,1.000'                          0.1 ms
 W  'CURRent CH1,0.100'                          0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.000000\n'                        138.6 ms
 Q  'CURRent? CH1'                           -> b'0.100000\n'                          2.4 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                          3.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                          2.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000302\n'                          4.3 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000230\n'                          5.8 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                4.2 ms
 W  'OUTPut CH1,1'                               0.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                        294.9 ms
 Q  '*OPC?'                                  -> b'1\n'                                 2.3 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          7.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          3.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          3.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.8 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000230\n'                          5.7 ms
 Q  'MEASure:POWER? CH1'                     -> b'0.000229\n'                          5.2 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                3.6 ms
 W  'OUTPut CH1,0'                               0.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                               182.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.961716\n'                          5.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.363061\n'                          4.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.268550\n'                          5.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.216327\n'                          3.9 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.216327\n'                          6.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.133789\n'                          5.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.108824\n'                          5.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.078764\n'                          4.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.078764\n'                          5.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.049723\n'                          4.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.040043\n'                          3.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.032910\n'                          5.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.029598\n'                          4.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.029598\n'                          3.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.017115\n'                          4.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.014568\n'                          5.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.011766\n'                          6.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.011766\n'                          5.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.007180\n'                          4.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.006416\n'                          4.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.006416\n'                          4.9 ms
 Q  'MEASure:CURRent? CH1'                   -> b'0.000119\n'                          5.5 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                3.2 ms
```

### E31 off_delay (done)

OUTPut:OFF:DELay semantics with the output on (no load): CH1 1.0 V / 0.1 A, OFF delay 2 s.

Open question 22: what does `OUTPut? CHn` return between `OUTPut CHn,0` and the
actual switch-off; does `OUTPut:ALL 0` honour the per-channel delay; does setting
the delay to 0 while a delayed switch-off is pending switch off immediately.
Three scenarios, each polled every 100 ms for 3 s with `OUTPut? CH1` and
`MEASure:VOLTage? CH1`. Only with --allow-output --confirm-no-load. The whole body is
in a try/finally that sets the delay to 0, forces `OUTPut CH1,0` and waits for
`OUTPut? CH1` = 0; the snapshot restore follows.

- A. OUTPut CHn,0 with a pending delay: OUTPut? settles at '0'
- B. OUTPut:ALL 0 with a pending delay: OUTPut? settles at '0'
- C. delay set to 0 while the switch-off is pending: OUTPut? settles at '0'
- final: OUTPut? CH1 reads '0' after the forced off

A. OUTPut CHn,0 with a pending delay: t s, OUTPut?, V

```
0.00  1  0.999164
0.10  1  0.999164
0.20  1  0.999164
0.30  1  0.999164
0.40  1  0.998909
0.50  1  0.998909
0.60  1  0.999164
0.70  1  0.998909
0.81  1  0.998909
0.90  1  0.999164
1.00  1  0.999164
1.10  1  0.999164
1.21  1  0.999164
1.30  1  0.998909
1.40  1  0.998909
1.50  1  0.998909
1.60  1  0.999164
1.70  1  0.998909
1.80  1  0.998909
1.90  1  0.999164
2.00  0  0.999164
2.11  0  0.861601
2.20  0  0.38497
2.30  0  0.307272
2.40  0  0.155443
2.50  0  0.113155
2.60  0  0.058894
2.70  0  0.0431
2.80  0  0.027815
2.91  0  0.015842
3.00  0  0.010747
```

B. OUTPut:ALL 0 with a pending delay: t s, OUTPut?, V

```
0.00  1  0.998909
0.26  1  0.999164
0.27  1  0.999164
0.30  1  0.998909
0.40  1  0.999164
0.50  1  0.999164
0.60  1  0.999164
0.70  1  0.998909
0.80  1  0.998909
0.90  1  0.999164
1.00  1  0.999164
1.10  1  0.998909
1.20  1  0.999164
1.30  1  0.999164
1.40  1  0.998909
1.50  1  0.998909
1.60  1  0.998909
1.70  1  0.998909
1.80  1  0.999164
1.90  1  0.998909
2.00  0  0.998909
2.10  0  0.770401
2.20  0  0.383441
2.30  0  0.275174
2.40  0  0.154933
2.50  0  0.113919
2.60  0  0.086916
2.70  0  0.03724
2.80  0  0.033674
2.90  0  0.016606
3.00  0  0.014058
```

C. delay set to 0 while the switch-off is pending: t s, OUTPut?, V

```
0.00  1  0.999164
0.10  1  0.998909
0.20  1  0.998909
0.30  1  0.998909
0.40  1  0.998909
0.50  sent: OUTPut:OFF:DELay CH1,0  
0.50  0  0.998909
0.60  0  0.663153
0.71  0  0.663153
0.80  0  0.663153
0.90  0  0.143979
1.00  0  0.115193
1.10  0  0.059913
1.20  0  0.044119
1.30  0  0.023739
1.40  0  0.016096
1.50  0  0.010492
1.60  0  0.007945
1.70  0  0.004888
1.80  0  0.004123
1.90  0  0.003869
2.00  0  0.00234
2.11  0  0.001831
2.20  0  0.001831
2.30  0  0.001576
2.40  0  0.001321
2.51  0  0.001321
2.61  0  0.001066
2.70  0  0.001066
2.80  0  0.000812
2.90  0  0.000812
3.01  0  0.000812
```

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.6 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.3 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 5.0 ms
 W  'VOLTage CH1,1.000'                          0.0 ms
 W  'CURRent CH1,0.100'                          0.0 ms
 Q  'VOLTage? CH1'                           -> b'1.000000\n'                        101.1 ms
 Q  'CURRent? CH1'                           -> b'0.100000\n'                          3.9 ms
 W  'OUTPut:OFF:DELay CH1,2'                     0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'2.000000\n'                        317.2 ms
 W  'OUTPut CH1,1'                               0.0 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                               206.9 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          7.3 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                6.0 ms
 W  'OUTPut CH1,0'                               0.1 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                13.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 4.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.7 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 4.9 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.6 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.6 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 3.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          4.7 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 3.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.2 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          4.6 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          6.0 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.6 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          3.4 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.7 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 3.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.7 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.4 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 4.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          3.4 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          3.5 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.7 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 4.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          3.9 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 4.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.5 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.7 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 3.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          3.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.9 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.9 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.861601\n'                          5.5 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.384970\n'                          3.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.307272\n'                          5.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.155443\n'                          4.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.113155\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.058894\n'                          3.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.043100\n'                          4.3 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.9 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.027815\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.015842\n'                          3.4 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.010747\n'                          3.6 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.7 ms
 W  'OUTPut:OFF:DELay CH1,2'                     0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'2.000000\n'                        122.6 ms
 W  'OUTPut CH1,1'                               0.1 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                               296.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          3.6 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                3.6 ms
 W  'OUTPut:ALL 0'                               0.1 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                               249.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 4.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          4.0 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          3.1 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          3.8 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 3.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.5 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          4.7 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          3.6 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          3.8 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.9 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 4.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.2 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 6.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          4.0 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 3.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          6.0 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          3.6 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 7.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          6.7 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 6.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          6.5 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 2.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.4 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 6.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.5 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          3.5 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 4.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          6.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.770401\n'                          6.0 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.383441\n'                          3.3 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.275174\n'                          5.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.154933\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.113919\n'                          6.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.086916\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.037240\n'                          3.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.033674\n'                          3.4 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.016606\n'                          5.9 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.014058\n'                          5.9 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.2 ms
 W  'OUTPut:OFF:DELay CH1,2'                     0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'2.000000\n'                         99.5 ms
 W  'OUTPut CH1,1'                               0.1 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                               260.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          6.1 ms
 Q  'MEASure:RUN:MODE? CH1'                  -> b'CV\n'                                6.4 ms
 W  'OUTPut CH1,0'                               0.1 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                24.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.999164\n'                          5.6 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 6.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.6 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 5.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 4.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.7 ms
 Q  'OUTPut? CH1'                            -> b'1\n'                                 3.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          3.1 ms
 W  'OUTPut:OFF:DELay CH1,0'                     0.2 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                46.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.998909\n'                          5.6 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.663153\n'                          5.9 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.663153\n'                          5.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.1 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.663153\n'                          5.4 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.143979\n'                          4.9 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.115193\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.059913\n'                          3.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.5 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.044119\n'                          5.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.023739\n'                          3.5 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.016096\n'                          5.6 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.010492\n'                          3.6 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.007945\n'                          6.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.2 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.004888\n'                          5.3 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.004123\n'                          5.5 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.003869\n'                          3.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.9 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.002340\n'                          6.6 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.001831\n'                          4.4 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.8 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.001831\n'                          3.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.9 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.001576\n'                          5.8 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 3.3 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.001321\n'                          3.0 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.7 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.001321\n'                          4.6 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.001066\n'                          4.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.9 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.001066\n'                          4.5 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 4.6 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000812\n'                          4.0 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.0 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000812\n'                          4.5 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 5.4 ms
 Q  'MEASure:VOLTage? CH1'                   -> b'0.000812\n'                          5.7 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.6 ms
 W  'OUTPut:OFF:DELay CH1,0'                     0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                        131.8 ms
 W  'OUTPut CH1,0'                               0.1 ms
 Q  'OUTPut? CH1'                            -> b'0\n'                               260.1 ms
```

