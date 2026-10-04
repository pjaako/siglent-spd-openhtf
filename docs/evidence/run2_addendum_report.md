# Hardware acceptance report

- Generated: 2026-10-04 20:35:39 UTC
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
| 22 | Run-2 leftovers, outputs off: coupled writes not yet tried, delay clamps, MODE on CH1/CH4, `VOLTage?` without channel. | write | 21, 9, 8 | done |  |
| 30 | Output ON at 1.0 V / 0.1 A, no load: settling curve, run mode, OFF. | output | 11 | skipped | not in --only |
| 31 | OUTPut:OFF:DELay semantics with the output on (no load): CH1 1.0 V / 0.1 A, OFF delay 2 s. | output | 11, 22 | skipped | not in --only |

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

Experiments: [2, 3, 19, 22]; ran: [22].

- (E22) `VOLTage?` -> '5.000000' and `CURRent?` -> '2.000000' without a channel; CH1..CH4 voltage ['5.000000', '14.000000', '12.000000', '0.000000'], current ['2.000000', '3.000000', '2.000000', '0.000000']. Compare with the channel the panel has selected (ask the owner)
- (E22) MODE on CH1/CH4 (originals {1: '0', 4: '0'}): `MODE CH1,1` -> '0'; `MODE CH1,0` -> '0'; `MODE CH4,1` -> '0'; `MODE CH4,0` -> '0'

### Q9 Parameter keywords and out-of-range behaviour

Experiments: [4, 10, 11, 12, 13, 14, 21, 22]; ran: [22].

- (E22) ON/OFF delay writes on CH1 (originals {'ON': '0.000000', 'OFF': '0.000000'}): `OUTPut:ON:DELay CH1,3601` -> '3600.000000'; `OUTPut:ON:DELay CH1,-1` -> '0.000000'; `OUTPut:ON:DELay CH1,MAXimum` -> '3600.000000'; `OUTPut:ON:DELay CH1,MINimum` -> '0.000000'; `OUTPut:ON:DELay CH1,DEFault` -> '0.000000'; `OUTPut:ON:DELay CH1,0` -> '0.000000'; `OUTPut:OFF:DELay CH1,3601` -> '3600.000000'; `OUTPut:OFF:DELay CH1,-1` -> '0.000000'; `OUTPut:OFF:DELay CH1,MAXimum` -> '3600.000000'; `OUTPut:OFF:DELay CH1,MINimum` -> '0.000000'; `OUTPut:OFF:DELay CH1,DEFault` -> '0.000000'; `OUTPut:OFF:DELay CH1,0` -> '0.000000'

### Q10 OVP/OCP interaction with other settings

*Coverage: partly: output state after a trip and after RESET:PROTect needs a load that trips protection (out of scope).*

Experiments: [12, 13, 15]; ran: none.

- no finding recorded

### Q11 Timing / settling / *OPC

Experiments: [5, 18, 30, 31]; ran: none.

- no finding recorded

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

Experiments: [15, 22]; ran: [22].

- (E22) coupled writes not tried before, SERIES: `:SOURce:VOLTage:SET CH2,40` -> '40.000000', '20.000000'; `:SOURce:VOLTage:SET CH2,70` -> '60.000000', '30.000000'; `:SOURce:VOLTage:SET CH2,200` -> '60.000000', '30.000000'; `:SOURce:CURRent:SET CH2,2` -> '2.000000', '2.100000'; `:SOURce:VOLTage:SET CH3,6` -> '60.000000', '30.000000'; `:SOURce:CURRent:SET CH3,1.5` -> '2.000000', '2.100000'
- (E22) coupled writes not tried before, PARALLEL: `:SOURce:CURRent:SET CH2,7` -> '6.464000', '3.232000'; `:SOURce:CURRent:SET CH2,20` -> '6.464000', '3.232000'; `:SOURce:VOLTage:SET CH2,10` -> '10.000000', '10.000000'; `:SOURce:VOLTage:SET CH3,8` -> '10.000000', '10.000000'; `:SOURce:CURRent:SET CH3,1` -> '6.464000', '3.232000'

### Q22 Output OFF delay semantics

Experiments: [31]; ran: none.

- no finding recorded

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

### E22 followups (done)

Run-2 leftovers, outputs off: coupled writes not yet tried, delay clamps, MODE on CH1/CH4, `VOLTage?` without channel.

Open question 21 (what a CH3 write, the current of CH2 in SERIES, the voltage of CH2 in
PARALLEL and a numeric combined value above `MAX` do), 9 (do the ON/OFF delay writes clamp
like `OCP:DELay`), 8 (does `VOLTage?` without a channel answer CH1 or the panel-selected
channel: ask the owner to select CH2 on the panel before the run; does `MODE` accept
CH1/CH4). Runs only while ALL outputs are off (enforced) and the track mode is INDEPENDENT.
CH2/CH3 setpoints, the delays of the channel, MODE of CH1/CH4 and the track mode are
restored with read-back.

- SERIES: track reads '1'; before the writes: CH2 V=28.000000 CH2 I=3.000000 CH2 OVP=35.200001 CH2 OCP=3.520000 CH3 V=14.000000 CH3 I=3.100000 CH3 OVP=35.200001 CH3 OCP=3.520000
- SERIES: after the writes: CH2 V=60.000000 CH2 I=2.000000 CH2 OVP=35.200001 CH2 OCP=3.520000 CH3 V=30.000000 CH3 I=2.100000 CH3 OVP=35.200001 CH3 OCP=3.520000
- PARALLEL: track reads '2'; before the writes: CH2 V=30.000000 CH2 I=4.000000 CH2 OVP=35.200001 CH2 OCP=3.520000 CH3 V=30.000000 CH3 I=2.000000 CH3 OVP=35.200001 CH3 OCP=3.520000
- PARALLEL: after the writes: CH2 V=10.000000 CH2 I=6.464000 CH2 OVP=35.200001 CH2 OCP=3.520000 CH3 V=10.000000 CH3 I=3.232000 CH3 OVP=35.200001 CH3 OCP=3.520000
- track back to INDEPENDENT, reads '0'
- local restore of CH2/CH3 setpoints, OVP, OCP and the delays of CH1: 10 items, FAILED: none
- MODE CH1 restored: now '0' (wanted '0')
- MODE CH4 restored: now '0' (wanted '0')

SERIES

| write | read-back |
|---|---|
| `:SOURce:VOLTage:SET CH2,40` | `:SOURce:VOLTage:SET? CH2` -> `40.000000`; `:SOURce:VOLTage:SET? CH3` -> `20.000000` |
| `:SOURce:VOLTage:SET CH2,70` | `:SOURce:VOLTage:SET? CH2` -> `60.000000`; `:SOURce:VOLTage:SET? CH3` -> `30.000000` |
| `:SOURce:VOLTage:SET CH2,200` | `:SOURce:VOLTage:SET? CH2` -> `60.000000`; `:SOURce:VOLTage:SET? CH3` -> `30.000000` |
| `:SOURce:CURRent:SET CH2,2` | `:SOURce:CURRent:SET? CH2` -> `2.000000`; `:SOURce:CURRent:SET? CH3` -> `2.100000` |
| `:SOURce:VOLTage:SET CH3,6` | `:SOURce:VOLTage:SET? CH2` -> `60.000000`; `:SOURce:VOLTage:SET? CH3` -> `30.000000` |
| `:SOURce:CURRent:SET CH3,1.5` | `:SOURce:CURRent:SET? CH2` -> `2.000000`; `:SOURce:CURRent:SET? CH3` -> `2.100000` |

PARALLEL

| write | read-back |
|---|---|
| `:SOURce:CURRent:SET CH2,7` | `:SOURce:CURRent:SET? CH2` -> `6.464000`; `:SOURce:CURRent:SET? CH3` -> `3.232000` |
| `:SOURce:CURRent:SET CH2,20` | `:SOURce:CURRent:SET? CH2` -> `6.464000`; `:SOURce:CURRent:SET? CH3` -> `3.232000` |
| `:SOURce:VOLTage:SET CH2,10` | `:SOURce:VOLTage:SET? CH2` -> `10.000000`; `:SOURce:VOLTage:SET? CH3` -> `10.000000` |
| `:SOURce:VOLTage:SET CH3,8` | `:SOURce:VOLTage:SET? CH2` -> `10.000000`; `:SOURce:VOLTage:SET? CH3` -> `10.000000` |
| `:SOURce:CURRent:SET CH3,1` | `:SOURce:CURRent:SET? CH2` -> `6.464000`; `:SOURce:CURRent:SET? CH3` -> `3.232000` |

ON/OFF delay clamps

| write | read-back |
|---|---|
| `OUTPut:ON:DELay CH1,3601` | `OUTPut:ON:DELay? CH1` -> `3600.000000` |
| `OUTPut:ON:DELay CH1,-1` | `OUTPut:ON:DELay? CH1` -> `0.000000` |
| `OUTPut:ON:DELay CH1,MAXimum` | `OUTPut:ON:DELay? CH1` -> `3600.000000` |
| `OUTPut:ON:DELay CH1,MINimum` | `OUTPut:ON:DELay? CH1` -> `0.000000` |
| `OUTPut:ON:DELay CH1,DEFault` | `OUTPut:ON:DELay? CH1` -> `0.000000` |
| `OUTPut:ON:DELay CH1,0` | `OUTPut:ON:DELay? CH1` -> `0.000000` |
| `OUTPut:OFF:DELay CH1,3601` | `OUTPut:OFF:DELay? CH1` -> `3600.000000` |
| `OUTPut:OFF:DELay CH1,-1` | `OUTPut:OFF:DELay? CH1` -> `0.000000` |
| `OUTPut:OFF:DELay CH1,MAXimum` | `OUTPut:OFF:DELay? CH1` -> `3600.000000` |
| `OUTPut:OFF:DELay CH1,MINimum` | `OUTPut:OFF:DELay? CH1` -> `0.000000` |
| `OUTPut:OFF:DELay CH1,DEFault` | `OUTPut:OFF:DELay? CH1` -> `0.000000` |
| `OUTPut:OFF:DELay CH1,0` | `OUTPut:OFF:DELay? CH1` -> `0.000000` |

MODE on CH1/CH4

| write | read-back |
|---|---|
| `MODE CH1,1` | `MODE? CH1` -> `0` |
| `MODE CH1,0` | `MODE? CH1` -> `0` |
| `MODE CH4,1` | `MODE? CH4` -> `0` |
| `MODE CH4,0` | `MODE? CH4` -> `0` |

Raw transcript (`W` write, `Q` query with raw reply bytes, time in ms):

```
 Q  'OUTPut? CH1'                            -> b'0\n'                                 2.2 ms
 Q  'OUTPut? CH2'                            -> b'0\n'                                 2.4 ms
 Q  'OUTPut? CH3'                            -> b'0\n'                                 2.2 ms
 Q  'OUTPut? CH4'                            -> b'0\n'                                 3.5 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                                 5.2 ms
 Q  'VOLTage?'                               -> b'5.000000\n'                          5.0 ms
 Q  'CURRent?'                               -> b'2.000000\n'                          2.4 ms
 Q  'VOLTage? CH1'                           -> b'5.000000\n'                          2.1 ms
 Q  'VOLTage? CH2'                           -> b'14.000000\n'                         2.0 ms
 Q  'VOLTage? CH3'                           -> b'12.000000\n'                         1.9 ms
 Q  'VOLTage? CH4'                           -> b'0.000000\n'                          3.4 ms
 Q  'CURRent? CH1'                           -> b'2.000000\n'                          3.5 ms
 Q  'CURRent? CH2'                           -> b'3.000000\n'                          3.1 ms
 Q  'CURRent? CH3'                           -> b'2.000000\n'                          4.0 ms
 Q  'CURRent? CH4'                           -> b'0.000000\n'                          1.7 ms
 Q  'MODE? CH1'                              -> b'0\n'                                 1.9 ms
 Q  'MODE? CH4'                              -> b'0\n'                                 2.0 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                          2.2 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                          5.1 ms
 W  'MODE CH1,1'                                 0.0 ms
 Q  'MODE? CH1'                              -> b'0\n'                                49.2 ms
 W  'MODE CH1,0'                                 0.1 ms
 Q  'MODE? CH1'                              -> b'0\n'                               260.7 ms
 W  'MODE CH4,1'                                 0.1 ms
 Q  'MODE? CH4'                              -> b'0\n'                               331.7 ms
 W  'MODE CH4,0'                                 0.2 ms
 Q  'MODE? CH4'                              -> b'0\n'                               205.4 ms
 W  'OUTPut:ON:DELay CH1,3601'                   0.0 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'3600.000000\n'                     407.6 ms
 W  'OUTPut:ON:DELay CH1,-1'                     0.0 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                         95.0 ms
 W  'OUTPut:ON:DELay CH1,MAXimum'                0.0 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'3600.000000\n'                     315.6 ms
 W  'OUTPut:ON:DELay CH1,MINimum'                0.0 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                        203.7 ms
 W  'OUTPut:ON:DELay CH1,DEFault'                0.1 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                        261.2 ms
 W  'OUTPut:ON:DELay CH1,0'                      0.0 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                        261.4 ms
 W  'OUTPut:OFF:DELay CH1,3601'                  0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'3600.000000\n'                     259.1 ms
 W  'OUTPut:OFF:DELay CH1,-1'                    0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                        259.5 ms
 W  'OUTPut:OFF:DELay CH1,MAXimum'               0.0 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'3600.000000\n'                     391.8 ms
 W  'OUTPut:OFF:DELay CH1,MINimum'               0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                        129.8 ms
 W  'OUTPut:OFF:DELay CH1,DEFault'               0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                        258.3 ms
 W  'OUTPut:OFF:DELay CH1,0'                     0.1 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                        261.3 ms
 W  'OUTPut:TRACK SERIES'                        0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'1\n'                               259.0 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'28.000000\n'                         4.3 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'3.000000\n'                          4.9 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         3.3 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          4.9 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'14.000000\n'                         5.1 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'3.100000\n'                          5.1 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         5.2 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          5.0 ms
 W  ':SOURce:VOLTage:SET CH2,40'                 0.0 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'40.000000\n'                       220.4 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'20.000000\n'                         5.0 ms
 W  ':SOURce:VOLTage:SET CH2,70'                 0.1 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'60.000000\n'                       254.6 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'30.000000\n'                         2.1 ms
 W  ':SOURce:VOLTage:SET CH2,200'                0.1 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'60.000000\n'                       259.6 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'30.000000\n'                         3.2 ms
 W  ':SOURce:CURRent:SET CH2,2'                  0.1 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'2.000000\n'                        328.8 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.100000\n'                          2.8 ms
 W  ':SOURce:VOLTage:SET CH3,6'                  0.1 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'60.000000\n'                       182.2 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'30.000000\n'                         5.2 ms
 W  ':SOURce:CURRent:SET CH3,1.5'                0.1 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'2.000000\n'                        256.8 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.100000\n'                          5.2 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'60.000000\n'                         3.6 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'2.000000\n'                          5.2 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         5.3 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          3.9 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'30.000000\n'                         4.5 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.100000\n'                          4.9 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         5.5 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          3.7 ms
 W  'OUTPut:TRACK PARALLEL'                      0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'2\n'                               214.5 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'30.000000\n'                         2.5 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'4.000000\n'                          5.3 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         4.9 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          4.3 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'30.000000\n'                         3.9 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'2.000000\n'                          4.2 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         7.1 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          6.0 ms
 W  ':SOURce:CURRent:SET CH2,7'                  0.1 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'6.464000\n'                        220.5 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'3.232000\n'                          4.7 ms
 W  ':SOURce:CURRent:SET CH2,20'                 0.1 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'6.464000\n'                        255.8 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'3.232000\n'                          5.1 ms
 W  ':SOURce:VOLTage:SET CH2,10'                 0.2 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'10.000000\n'                        12.3 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'10.000000\n'                         3.9 ms
 W  ':SOURce:VOLTage:SET CH3,8'                  0.2 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'10.000000\n'                       238.9 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'10.000000\n'                         5.1 ms
 W  ':SOURce:CURRent:SET CH3,1'                  0.2 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'6.464000\n'                        253.6 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'3.232000\n'                          3.8 ms
 Q  ':SOURce:VOLTage:SET? CH2'               -> b'10.000000\n'                         5.0 ms
 Q  ':SOURce:CURRent:SET? CH2'               -> b'6.464000\n'                          5.0 ms
 Q  ':SOURce:OVP? CH2'                       -> b'35.200001\n'                         4.9 ms
 Q  ':SOURce:OCP? CH2'                       -> b'3.520000\n'                          5.2 ms
 Q  ':SOURce:VOLTage:SET? CH3'               -> b'10.000000\n'                         2.6 ms
 Q  ':SOURce:CURRent:SET? CH3'               -> b'3.232000\n'                          2.0 ms
 Q  ':SOURce:OVP? CH3'                       -> b'35.200001\n'                         1.9 ms
 Q  ':SOURce:OCP? CH3'                       -> b'3.520000\n'                          2.2 ms
 W  'OUTPut:TRACK INDEPENDENT'                   0.1 ms
 Q  'OUTPut:TRACK?'                          -> b'0\n'                               226.7 ms
 Q  'OVP? CH2'                               -> b'35.200001\n'                         5.0 ms
 Q  'OCP? CH2'                               -> b'3.520000\n'                          5.0 ms
 Q  'VOLTage? CH2'                           -> b'10.000000\n'                         5.1 ms
 W  'VOLTage CH2,14.000000'                      0.1 ms
 Q  'VOLTage? CH2'                           -> b'14.000000\n'                       413.8 ms
 Q  'CURRent? CH2'                           -> b'3.232000\n'                          3.6 ms
 W  'CURRent CH2,3.000000'                       0.1 ms
 Q  'CURRent? CH2'                           -> b'3.000000\n'                         85.7 ms
 Q  'OVP? CH3'                               -> b'35.200001\n'                         3.9 ms
 Q  'OCP? CH3'                               -> b'3.520000\n'                          5.0 ms
 Q  'VOLTage? CH3'                           -> b'10.000000\n'                         4.0 ms
 W  'VOLTage CH3,12.000000'                      0.2 ms
 Q  'VOLTage? CH3'                           -> b'12.000000\n'                       245.2 ms
 Q  'CURRent? CH3'                           -> b'3.232000\n'                          3.1 ms
 W  'CURRent CH3,2.000000'                       0.1 ms
 Q  'CURRent? CH3'                           -> b'2.000000\n'                        258.0 ms
 Q  'OUTPut:ON:DELay? CH1'                   -> b'0.000000\n'                          3.8 ms
 Q  'OUTPut:OFF:DELay? CH1'                  -> b'0.000000\n'                          5.4 ms
 W  'MODE CH1,0'                                 0.0 ms
 Q  'MODE? CH1'                              -> b'0\n'                               420.2 ms
 W  'MODE CH4,0'                                 0.1 ms
 Q  'MODE? CH4'                              -> b'0\n'                                90.1 ms
```

### E30 output_settling (skipped)

Output ON at 1.0 V / 0.1 A, no load: settling curve, run mode, OFF.

Open question 11 (Timing/settling: how long after `OUTPut CHn,1` until the
output is at voltage, is `*OPC?` meaningful for output-on, measurement refresh
when polled every 50 ms; what `MEASure:RUN:MODE?` returns). Only runs with
--allow-output --confirm-no-load. Always followed by OUTPut off, a wait until
OUTPut? reads 0 and the snapshot restore.

**not in --only**

### E31 off_delay (skipped)

OUTPut:OFF:DELay semantics with the output on (no load): CH1 1.0 V / 0.1 A, OFF delay 2 s.

Open question 22: what does `OUTPut? CHn` return between `OUTPut CHn,0` and the
actual switch-off; does `OUTPut:ALL 0` honour the per-channel delay; does setting
the delay to 0 while a delayed switch-off is pending switch off immediately.
Three scenarios, each polled every 100 ms for 3 s with `OUTPut? CH1` and
`MEASure:VOLTage? CH1`. Only with --allow-output --confirm-no-load. The whole body is
in a try/finally that sets the delay to 0, forces `OUTPut CH1,0` and waits for
`OUTPut? CH1` = 0; the snapshot restore follows.

**not in --only**

