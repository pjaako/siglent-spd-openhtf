# Hardware findings: SPD4323X acceptance run 1

| item | value |
|---|---|
| instrument | Siglent SPD4323X, serial `SPD43XXXXXXXXX` (placeholder) |
| firmware | `4.1.2.9R1` (from `*IDN?`; note the `R1` suffix, not a purely numeric version as in the manual's `4.1.2.4`) |
| date | 2026-10-05 (local time of the logs 01:48 to 01:51) |
| address | `192.0.2.10` in this document (documentation example; the real address stays out of git) |
| `tools/bare_socket_check.py --sweep-terms` | raw TCP socket, port 5025, Python standard library, read-only; log `bare_socket_check.local.log` (249 lines) |
| `tools/hw_acceptance.py` (default write mode, outputs off) | PyVISA `@py` (pyvisa-py), resource `TCPIP::192.0.2.10::5025::SOCKET`, write termination LF, timeout 3000 ms, probe timeout 1500 ms; log `hw_acceptance.local.log` (1018 lines) |
| experiments that ran | 1, 2, 3, 4, 5, 6, 8 (read tier); 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 (write tier). Write experiments on **CH1 only**; 15 and 16 on CH2/CH3 with their outputs off. |
| experiments that did not run | **30 (output on) did not run**: no output was switched on in this session and **no `OUTPut CHn,<x>` or `OUTPut:ALL <x>` write was sent at all**. 7 (VXI-11) not run (no direct LAN path). `*TST?` not sent. **USB not tested.** Web/telnet ports not probed. |
| state before / after | all four outputs off before and after (`OUTPut? CHn` -> `0`, acc 4-8 and 1015-1018); CH1-CH3 setpoints, OVP/OCP, OCP state/delay, ON/OFF delays and track/sense restored and read back (acc 987-1013); `LOCK?` -> `0` at the end (acc 1014). CH4 was not written and not re-read at the end (see Q8). |

Line references: "acc N" is line N of `hw_acceptance.local.log`, "bare N" is line N of
`bare_socket_check.local.log` (both local, git-ignored, held by the project owner). Quoted
replies are the raw bytes as logged; the serial number in `*IDN?` replies is replaced by the
placeholder. Times are the logged round-trip times.

Timing summary used below (computed over the whole acceptance log):

| situation | n | min | median | 90 % | max |
|---|---|---|---|---|---|
| query after a query | 741 | 0.5 ms | 2.1 ms | 4.1 ms | 368.7 ms (a `LOCK?`) |
| first query after a write (any write) | 109 | 7.2 ms | 250.5 ms | 261.7 ms | 325.2 ms |
| `LOCK?` after a query | 19 | 1.6 ms | 5.7 ms | 288.5 ms | 368.7 ms |
| `LOCK?` after a `LOCK` write | 17 | 157.7 ms | 217.8 ms | 284.7 ms | 325.2 ms |
| unanswered query (no reply at all) | - | - | - | - | full timeout (1509 ms at a 1500 ms probe timeout) |

---

## Answers to open questions (docs/scpi_reference.md section 8)

### Q1 Termination; several commands per line
**Status: answered for the raw socket; USB not tested.**
LF and CRLF are both accepted on input (24/24 queries each); every reply ends in a single LF,
never CRLF. `;` chains work for writes and queries, but the replies of several queries on one
line are **concatenated with no separator** and one LF at the end.

```
bare 6    *IDN?\n         -> b'Siglent Technologies,SPD4323X,SPD43XXXXXXXXX,4.1.2.9R1\n'  104.9 ms
bare 32   *IDN?\r\n       -> b'Siglent Technologies,SPD4323X,SPD43XXXXXXXXX,4.1.2.9R1\n'  106.1 ms
bare 138  LF 24/24 answered, CRLF 24/24 answered; reply terminator LF in both cases
bare 100  *IDN?;*OPC?\n   -> b'Siglent Technologies,SPD4323X,SPD43XXXXXXXXX,4.1.2.9R11\n'  4.8 ms
acc 172   '*IDN?;*OPC?'   -> VisaIOError VI_ERROR_TMO  1521.3 ms
acc 833   'VOLTage CH1,1.250;VOLTage? CH1' -> b'1.250000\n'  3.0 ms
acc 834   'VOLTage CH1,1.500;*OPC?'        -> b'1\n'         4.8 ms
acc 835   'VOLTage? CH1'                   -> b'1.500000\n'  5.3 ms
```

The `*IDN?;*OPC?` reply is the identity string immediately followed by `1` (`...4.1.2.9R1` +
`1` = `...4.1.2.9R11`). IEEE 488.2 would put `;` between the two responses; this instrument
does not, so a chained numeric reply cannot be split reliably.

**The PyVISA timeout on `*IDN?;*OPC?` (acc 172) is a defect of `hw_acceptance.py`, not of the
instrument.** `Link.query` counts the `?` segments (`n_lines = 2`) and calls `read_raw()` twice;
the instrument sends one line, so the first read got everything and the second waited for a
line that never came. On the error path the bytes of the first read are discarded, and
`drain()` found nothing late (the log has no `LATE` line, and the next query, acc 173, got its
own correct reply). Fix in the tool: read one line per command line, whatever the number of
queries in it.

Side observation: a write and a query in one line are fast (acc 833: 3.0 ms) while a query sent
as a separate line after a write waits about 250 ms (see Q11). The plug should still not chain
(verbatim-form rule, and concatenated replies are ambiguous).

### Q2 USB identity (VID/PID, resource string, USBTMC)
**Status: not tested.** Needs a USB connection.

### Q3 LAN: VXI-11, simultaneous connections, web, telnet
**Status: partially answered.** The socket on port 5025 serves **one client at a time**. A
second TCP connection is accepted by the TCP stack but its queries get no reply while the first
connection is open; after the first connection closes, a new connection is served. VXI-11, web
(80) and telnet (23) were not probed (only port 5025 was reachable).

```
bare 125  A *IDN? before B opens: ok
bare 126  B *IDN? while A open: error b''
bare 127  A *IDN? after B queried: ok
bare 128  A *IDN? after B closed: ok
bare 129  C *IDN? after A closed: ok
bare 146  second concurrent connection: ONE client at a time
```

Consequence: while an OpenHTF station holds the plug open, no other socket client (acceptance
tool, a second script) can talk to the supply; a crashed station that does not close its socket
blocks the supply until the TCP connection dies. `tearDown()` must always close (it does).

### Q4 Response formats, units, decimals, `\s`, terminators, `*IDN?`
**Status: answered for every query the plug uses.**
- No units in any reply. Scalars (V, A, W, s) are plain decimals with **6 places**; booleans and
  modes are bare integers (`0`/`1`, track `0`/`1`/`2`); `MEASure:RUN:MODE?` is a word (`CV`).
- `*IDN?` is `Siglent Technologies,SPD4323X,<serial>,4.1.2.9R1`: the manual's `\s` is a plain
  space; 4 comma-separated fields; the firmware field is not purely numeric.
- `*ESE?`, `*ESR?`, `*OPC?`, `*SRE?`, `*STB?` all end in LF like everything else.
- **Values are stored as 32-bit floats**: `OVP? CH2` answers `35.200001` (1.1 x 32 V), not
  `35.200000`. Every observed value matches `f'{float32(x):.6f}'` (checked: 35.2 -> 35.200001,
  6.6 -> 6.600000, 3.52 -> 3.520000, 6.06 -> 6.060000, 32.32 -> 32.320000, 3.232 -> 3.232000,
  1.2345 -> 1.234500).
- With the outputs off, the measurements show small offsets, not zero, and `CV`.

```
acc 3     '*IDN?'               -> b'Siglent Technologies,SPD4323X,SPD43XXXXXXXXX,4.1.2.9R1\n'  5.6 ms
acc 20    'OVP? CH2'            -> b'35.200001\n'   3.5 ms
acc 12    'OCP? CH1'            -> b'3.520000\n'    3.1 ms
acc 60-63 MEASure:VOLTage? CH1 -> b'0.000557\n'; MEASure:CURRent? CH1 -> b'0.000560\n';
          MEASure:POWER? CH1 -> b'0.000000\n'; MEASure:RUN:MODE? CH1 -> b'CV\n'  (output off)
acc 116-120 *OPC? -> b'1\n'; *ESE? -> b'0\n'; *ESR? -> b'0\n'; *SRE? -> b'0\n'; *STB? -> b'0\n'
bare 152-175  Q4 table: every reply LF-terminated, decimals with 6 places, integers bare
```

`OUTPut:ALL?` answers `0` with all outputs off (acc 8); its format with mixed channel states is
still unknown (needs outputs on).

### Q5 Missing responses (`OCP?`, LAN, GPIB, STORage)
**Status: answered for `OCP?`; the rest not tested (blocked by the safety policy).**
`OCP? CHn` answers a plain number like `OVP?`.

```
bare 15   OCP? CH1 -> b'3.520000\n'  1.1 ms
acc 21    'OCP? CH2' -> b'3.520000\n'  2.5 ms
```

### Q6 Error reporting; `*ESR?`/`*STB?`; `*TST?`
**Status: partially answered.** There is no error reply: an invalid query is simply never
answered (the caller times out). `*ESR?` bit 5 (value 32, command error) is set by unknown
headers / malformed queries, `*ESR?` clears on read, `*CLS` clears it, `*OPC` sets bit 0.
**Not flagged at all** (ESR stays 0): an invalid channel in a write (`VOLTage CH5,1`), a
non-numeric value (`VOLTage CH1,abc`) and an out-of-range value that gets clamped
(`VOLTage CH1,7.5`). `*STB?` was 0 throughout (`*ESE?` and `*SRE?` are 0, so nothing is
summarised there). `*TST?` not sent.

```
bare 58   [before] *ESR? -> b'0\n'
bare 121  [after invalid probes] *ESR? -> b'32\n'   *STB? -> b'0\n'
acc 278   '*ESR?' -> b'32\n'    (after the invalid probes of experiments 3 and 4)
acc 280   'FOOBar? CH1' -> VI_ERROR_TMO 1509.0 ms
acc 281   '*ESR?' -> b'0\n'     <-- unknown header did NOT set bit 5 here
acc 283   'VOLTage? CH5' -> VI_ERROR_TMO;  acc 284 '*ESR?' -> b'0\n'
acc 829   W '*OPC';             acc 830 '*ESR?' -> b'1\n'   34.6 ms
acc 872   W '*CLS';             acc 873 '*ESR?' -> b'0\n'
acc 875   W 'VOLTage CH5,1';    acc 876 '*ESR?' -> b'0\n'
acc 881   W 'VOLTage CH1,abc';  acc 882 '*ESR?' -> b'0\n'
acc 885   W 'VOLTage CH1,7.5';  acc 886 '*ESR?' -> b'0\n'
acc 888   W '*CLS'; acc 889 'FOOBar? CH1' -> VI_ERROR_TMO; acc 890 '*ESR?' -> b'32\n'
```

The same unknown query `FOOBar? CH1` set bit 5 after a `*CLS` (acc 888-890) but not after a
plain `*ESR?` read (acc 278-281). A consistent explanation, not yet proven: bit 5 is raised only
when an error enters an empty error list; `*ESR?` clears the register but not the list; only
`*CLS` empties the list (the manual says `*CLS` "clear[s] the error list"). Either way **`*ESR?`
is not a reliable error channel; read-back stays the only reliable check**, as SPEC.md already
assumes.

### Q7 Case and forms
**Status: answered.** Everything the grammar allows works, for queries and for writes:
leading `:` optional, `SOURce:`/`SOUR:` optional, `:SET` optional, `:STATe` optional,
`[:RUN]` optional, long and short keywords, any case (including `ch1`), no space before the
channel (`VOLTage?CH1`), a space after the comma (`CH1, 1`) and before it (`CH1 ,1.9`).
Rejected (no reply): wrong abbreviations (`VOL`, `VOLTAG`), literal brackets (`VOLTage[:SET]?`),
`MEAS:POW?` (so `POWER` has no short form) and `OUTP:TRAC?` (so `TRACK` has no short form).

```
bare 62-71   :VOLTage? / SOURce:VOLTage? / :SOURce:VOLTage? / SOUR:VOLT? / :SOURce:VOLTage:SET? /
             VOLTage:SET? / VOLT? / VOLT:SET? / volt? ch1 / VolTaGe? CH1  -> all b'5.000000\n'
bare 72-73   VOL? CH1, VOLTAG? CH1      -> b''  TIMEOUT
bare 83      MEAS:POW? CH1              -> b''  TIMEOUT
bare 84      MEASure:POWer? CH1         -> b'0.000000\n'
bare 86      MEASure:MODE? CH1          -> b'CV\n'
bare 87      OUTP:TRAC?                 -> b''  TIMEOUT
bare 91      VOLTage?CH1                -> b'5.000000\n'
bare 92      VOLTage[:SET]? CH1         -> b''  TIMEOUT
acc 929-954  writes, each after 'VOLTage CH1,0.5', read back with 'VOLTage? CH1':
             ':SOURce:VOLTage:SET CH1,1.1' -> 1.100000   'SOURce:VOLTage CH1,1.2' -> 1.200000
             'VOLTage:SET CH1,1.3' -> 1.300000          'VOLT CH1,1.4' -> 1.400000
             'volt ch1,1.5' -> 1.500000                 'VOLTage CH1, 1.6' -> 1.600000
             'VOLT:SET CH1,1.7' -> 1.700000             ':VOLTage CH1,1.8' -> 1.800000
             'VOLTage CH1 ,1.9' -> 1.900000
acc 586-587  W 'OCP:STATe CH1, 1' (manual's spacing) -> 'OCP:STATe? CH1' -> b'1\n'
```

### Q8 Channel argument: optional? invalid? on `OUTPut:TRACK`/`LOCK`?
**Status: mostly answered.**
- **Query without channel**: `VOLTage?` answers `5.000000`, which is CH1's setpoint (CH2 14,
  CH3 12, CH4 0 at the time). Whether that is "CH1" or "the channel selected on the panel"
  (which may have been CH1) cannot be told from this run. The plug never omits the channel.
- **Invalid channel** in a query (`CH0`, `CH5`, bare `1`, `(CH1)`): no reply.
- **Extra argument on a channel-less query**: `OUTPut:TRACK? CH1` gets **no reply**.
- `MODE? CH1` **answers `0`**, although the manual lists CH2/CH3 only (CH4 not tried).
- Invalid channel in a write (`VOLTage CH5,1`) raises no ESR bit; CH1-CH3 were unchanged
  afterwards (acc 899-918; CH1 shows the clamped 6.06 V of the following `7.5` write).
  **CH4 was not read back after it**, so whether it hit CH4 or the "current channel" is unknown.

```
bare 93   VOLTage?            -> b'5.000000\n'  2.7 ms        (acc 165 same)
bare 94-97 VOLTage? CH0 / CH5 / 1 / (CH1) -> b''  TIMEOUT
bare 98   OUTPut:TRACK? CH1   -> b''  TIMEOUT
bare 99   MODE? CH1           -> b'0\n'  4.0 ms               (acc 114, acc 171 same)
acc 9/18/27/36  VOLTage? CH1..CH4 -> 5.000000 / 14.000000 / 12.000000 / 0.000000
```

### Q9 MIN/MAX/DEF; rounding vs clamping vs error
**Status: answered for CH1 (write experiments ran on CH1 only).** Out-of-range values are
**clamped silently, never rejected and never flagged** (ESR stays 0). No rounding to the
documented 1 mV / 1 mA / 0.01 s resolution is visible in the read-back: 4 decimals are stored.

| write (CH1, rating 6 V / 3.2 A) | read-back | meaning |
|---|---|---|
| `VOLTage CH1,1.2345` | `1.234500` (acc 350-351, 14.8 ms) | no rounding to 1 mV in the stored value |
| `VOLTage CH1,6` | `6.000000` (acc 352-353) | |
| `VOLTage CH1,7.5` | `6.060000` (acc 354-355, 26.4 ms) | clamped to **1.01 x rating** |
| `VOLTage CH1,-1` | `0.000000` (acc 356-357) | clamped to 0 (previous value 6.06 V was overwritten, not kept) |
| `VOLTage CH1,MINimum` / `MAXimum` / `DEFault` | `0.000000` / `6.060000` / `0.000000` (acc 358-363) | |
| `CURRent CH1,0.1234` | `0.123400` (acc 405-406) | |
| `CURRent CH1,3.2` / `4` / `-0.1` | `3.200000` / `3.232000` / `0.000000` (acc 407-412) | clamp to 1.01 x 3.2 A, and to 0 |
| `CURRent CH1,MINimum` / `MAXimum` / `DEFault` | `0.000000` / `3.232000` / `0.000000` (acc 413-418) | |
| `OVP CH1,3` / `6.6` | `3.000000` / `6.600000` (acc 458-461) | |
| `OVP CH1,7.2` | `6.600000` (acc 462-463) | clamped to 1.1 x 6 V |
| `OVP CH1,0.3` | `0.600000` (acc 464-465) | clamped to 0.1 x 6 V |
| `OVP CH1,MAXimum` / `MINimum` / `DEFault` | `6.600000` / `0.600000` / `6.600000` (acc 466-471) | DEFault = max |
| `OCP CH1,1.6` / `3.52` | `1.600000` / `3.520000` (acc 521-524) | |
| `OCP CH1,3.84` | `3.520000` (acc 525-526) | clamped to 1.1 x 3.2 A |
| `OCP CH1,0.16` | `0.320000` (acc 527-528) | clamped to 0.1 x 3.2 A |
| `OCP CH1,MAXimum` / `MINimum` / `DEFault` | `3.520000` / `0.320000` / `3.520000` (acc 529-534) | DEFault = max |
| `OCP:DELay CH1,0.5` / `1.2345` / `3600` | `0.500000` / `1.234500` / `3600.000000` (acc 589-594) | no rounding to 0.01 s |
| `OCP:DELay CH1,3601` / `-1` | `3600.000000` / `0.000000` (acc 595-598) | clamped to 0..3600 |
| `OCP:DELay CH1,MAXimum` / `MINimum` / `DEFault` | `3600.000000` / `0.000000` / `0.000000` (acc 599-604) | |

As **queries**, the keywords work only for `VOLTage?` and `CURRent?` (`MAX`, `MAXimum`, `MIN`,
`DEF`, `DEFault`, with or without a space after the comma). `OVP?`, `OCP?`, `OCP:DELay?` and
`OUTPut:ON:DELay?` with any keyword get **no reply** on every channel.

```
bare 103  VOLTage? CH1,MAX     -> b'6.060000\n'      bare 108 CURRent? CH1,MAX -> b'3.232000\n'
bare 104  VOLTage? CH1,MIN     -> b'0.000000\n'      bare 105 VOLTage? CH1,DEFault -> b'0.000000\n'
bare 107  VOLTage? CH1, MAX    -> b'6.060000\n'
bare 110-113 OVP? CH1,MAX / OCP? CH1,MAX / OCP:DELay? CH1,MAX / OUTPut:ON:DELay? CH1,MAX -> b'' TIMEOUT
acc 191-225 OVP?/OCP? CHn,MIN|MAX|DEF on CH1..CH4 -> all VI_ERROR_TMO
```

The `OUTPut:ON:DELay` / `OUTPut:OFF:DELay` **writes** were not exercised (only their queries).

### Q10 Interaction of OVP/OCP with other settings
**Status: partially answered (outputs off only).**
- **No mutual limiting** between OVP and the voltage setpoint, or OCP and the current setpoint,
  while the output is off: an OVP below the setpoint is accepted, a setpoint above the OVP is
  accepted, both values are kept as written.
- Switching SERIES/PARALLEL does **not** rescale OVP or OCP (CH2 OVP stays 35.2 V in SERIES,
  CH2 OCP stays 3.52 A in PARALLEL).
- Not tested (needs outputs on / a load): what happens when such an output is switched on,
  state after a trip, after `RESET:PROTect`, `OUTPut?` while tripped.

```
acc 472-476  W 'OVP CH1,MAXimum'; W 'VOLTage CH1,4.2'; W 'OVP CH1,2.4'
             'OVP? CH1' -> b'2.400000\n' 273.4 ms;  'VOLTage? CH1' -> b'4.200000\n'
acc 477-481  W 'VOLTage CH1,0'; W 'OVP CH1,2.4'; W 'VOLTage CH1,4.2'
             'VOLTage? CH1' -> b'4.200000\n' 245.2 ms;  'OVP? CH1' -> b'2.400000\n'
acc 535-539  W 'OCP CH1,MAXimum'; W 'CURRent CH1,2.24'; W 'OCP CH1,1.28'
             'OCP? CH1' -> b'1.280000\n' 270.6 ms;  'CURRent? CH1' -> b'2.240000\n'
acc 646      (SERIES)   'OVP? CH2' -> b'35.200001\n'
acc 661      (PARALLEL) 'OCP? CH2' -> b'3.520000\n'
```

Three writes sent back to back without a query in between were all applied (acc 472-481), so
writes are not dropped while an earlier write is still being processed.

### Q11 Timing, settling, `*OPC?`, `*WAI`
**Status: partially answered; settling after output on not tested (experiment 30 did not run).**
- Query after query: median 2.1 ms, 90 % 4.1 ms. `*OPC?` and `*ESE?` 0.5-1 ms.
- **First query after any write: median 250 ms, max 325 ms** (109 cases; minimum 7 ms). The
  spread (7-325 ms) looks like writes being applied on an internal cycle of about 260 ms. The
  query is held until the write has been applied: **in every one of the 109 cases the read-back
  showed the new (or clamped) value**; no stale read-back was ever seen. Read-back therefore
  needs no sleep and no `*OPC?`.
- `*OPC?` returns `1`; right after a write it is held for the same ~220 ms as any other query, so
  it adds nothing over a read-back. `*OPC` sets ESR bit 0. `*WAI` is accepted, no visible effect.
- `LOCK?` is the slowest query: up to 368.7 ms even after only queries (acc 865), apparently while
  the auto-lock from a preceding write is pending (see Q12).
- First query on a **fresh** raw-socket connection took about 105 ms (bare 6, 32, 58); in the
  PyVISA session the first `*IDN?` took 5.6 ms (acc 3).
- Measurements repeat the identical value for 5 queries within 10 ms (acc 251-255
  `0.000047` x 5), so the measurement refresh is slower than the query rate; the actual refresh
  interval needs an output on (experiment 30).

```
acc 348-349  W 'VOLTage CH1,1.000';  'VOLTage? CH1' -> b'1.000000\n'  210.2 ms
acc 827-828  W 'VOLTage CH1,1.000';  '*OPC?' -> b'1\n'  218.5 ms
acc 829-830  W '*OPC';               '*ESR?' -> b'1\n'  34.6 ms
acc 831-832  W '*WAI';               'VOLTage? CH1' -> b'1.000000\n'  259.7 ms
acc 865      'LOCK?' -> b'1\n'  368.7 ms  (slowest reply of the run)
acc 780-781  W 'LOCK 0';  'LOCK?' -> b'0\n'  325.2 ms  (slowest reply after a write)
```

### Q12 Remote lock
**Status: answered at the SCPI level; front panel view not reported.**
- Queries alone never lock (`LOCK?` stays `0` through the whole read-only tier, acc 48, 115,
  132, 341).
- **Any write locks the panel**: the first `LOCK?` after the first write experiment answers `1`
  (acc 395), and so does every `LOCK?` after every later write experiment (acc 450, 513, 571,
  636, 723, 767, 819, 865, 921, 984).
- `LOCK 0` unlocks (`LOCK?` -> `0`) and the `LOCK 0` write itself does not re-lock. `LOCK ON`,
  `LOCK OFF`, `LOCK 1`, `:SOURce:LOCK:STATe 1` all work.
- Remote writes still work while locked (`VOLTage CH1,1.5` applied with LOCK = 1).
- `LOCK?` = 0 at the end of the run (acc 1014). Whether the panel was visibly unlocked (lock icon,
  keys usable) was not reported: ask the user to look after the next run.

```
acc 395-397  'LOCK?' -> b'1\n' 61.3 ms;  W 'LOCK 0';  'LOCK?' -> b'0\n' 159.9 ms
acc 774-779  'LOCK?' -> b'0\n';  W 'LOCK 1';  'LOCK?' -> b'1\n' 220.8 ms;
             W 'VOLTage CH1,1.5';  'VOLTage? CH1' -> b'1.500000\n' 23.5 ms
acc 782-789  W 'LOCK ON' -> b'1\n';  W 'LOCK OFF' -> b'0\n';
             W ':SOURce:LOCK:STATe 1';  ':SOURce:LOCK:STATe?' -> b'1\n' 284.7 ms;  W 'LOCK 0' -> b'0\n'
acc 1014     'LOCK?' -> b'0\n'  (end of run)
```

### Q13 `OUTPut:TRACK` and `MODE` mappings
**Status: answered (rejection of `OUTPut:TRACK` while an output is on not tested).**
- `OUTPut:TRACK` takes the words and the numbers; **the query always answers the number**:
  0 = INDEPENDENT, 1 = SERIES, 2 = PARALLEL.
- `MODE CH2,<x>` takes `2W`/`4W` and `0`/`1`; **the query answers the number**: 0 = 2W,
  1 = 4W. CH3 was not written; `MODE? CH3` answers `0` (default).

```
acc 642-643  W 'OUTPut:TRACK SERIES'      -> 'OUTPut:TRACK?' -> b'1\n'  239.4 ms
acc 656-657  W 'OUTPut:TRACK PARALLEL'    -> b'2\n'
acc 670-671  W 'OUTPut:TRACK INDEPENDENT' -> b'0\n'
acc 684-691  W 'OUTPut:TRACK 1' -> b'1\n';  '2' -> b'2\n';  '0' -> b'0\n';  '0' -> b'0\n'
acc 730-739  W 'MODE CH2,4W' -> 'MODE? CH2' -> b'1\n';  '2W' -> b'0\n';  '1' -> b'1\n';  '0' -> b'0\n'
```

**Side effect found (safety-relevant): entering SERIES or PARALLEL copies CH2's setpoints into
CH3, and CH3 keeps them after returning to INDEPENDENT.** Before: CH2 14 V / 3 A, CH3 12 V / 2 A
(acc 383-392). After SERIES -> PARALLEL -> INDEPENDENT: CH3 14 V / 3 A (acc 678-679). The tool
restored CH3 afterwards (acc 716-720). A CH3 DUT switched on after such a round trip gets CH2's
voltage.

### Q14 Rated table; real limits via `...? CHn,MAX`
**Status: answered for the SPD4323X.** `MAX` is **1.01 x the rated value** for voltage and
current on every channel; OVP and OCP range is 0.1 x .. 1.1 x rating, and both the values
found on the supply and the `DEFault` values of OVP/OCP are the 1.1 x maximum on every channel. In SERIES and PARALLEL the `MAX`
queries still answer the per-channel values (32.32 V / 3.232 A), not the series/parallel
ratings. SPD4306X CH4 (`15/1`) not testable here.

```
bare 103/117 VOLTage? CH1,MAX / CH4,MAX -> 6.060000      (6 V x 1.01)
bare 114/116 VOLTage? CH2,MAX / CH3,MAX -> 32.320000     (32 V x 1.01)
bare 108/115/118 CURRent? CH1/CH2/CH4,MAX -> 3.232000    (3.2 A x 1.01);  acc 208 CH3 same
acc 11/20/29/38  OVP? CH1..CH4 -> 6.600000 / 35.200001 / 35.200001 / 6.600000  (1.1 x)
acc 12/21/30/39  OCP? CH1..CH4 -> 3.520000 (all)                               (1.1 x)
acc 648-649  (SERIES)   VOLTage? CH2,MAX -> 32.320000;  CURRent? CH2,MAX -> 3.232000
acc 662-663  (PARALLEL) VOLTage? CH2,MAX -> 32.320000;  CURRent? CH2,MAX -> 3.232000
```

### Q15 LIST, Q16 WAVE, Q17 STORAGE
**Status: not tested** (out of scope; blocked by the tools' safety policy).

### Q18 `*RST`
**Status: not tested.** `*RST` is never sent by the tools or the plug.

### Q19 Programming examples
**Status: not applicable.** The manual contains none; the tools themselves are the validated
examples for the raw socket via PyVISA (`TCPIP::<ip>::5025::SOCKET`, LF terminator).

### Q20 Channel addressing with optional nodes
**Status: answered.** A command **without** `:SET` / `SOURce` honours its channel argument;
there is no "current channel" effect when a channel is given.
- Queries: `VOLTage? CHn` (no `:SET`) answers each channel's own value (CH1 5, CH2 14, CH3 12,
  CH4 0), identical to the verbatim `:SOURce:VOLTage:SET? CHn` (acc 288-315).
- Writes: `VOLTage CH1,<v>` changed CH1 only (dozens of times), and `VOLTage CH3,12.000000` /
  `CURRent CH3,2.000000` (no `:SET`) changed CH3 only, with CH1 unchanged before and after
  (acc 715-720, 747-748). At most one of CH1 and CH3 can be the panel-selected channel, so the
  argument is honoured.
- Without any channel, `VOLTage?` answers CH1's value (see Q8): never omit the channel.

### Q21 Series/parallel setpoint meaning
**Status: partially answered (read side only). Safety-relevant gap on the write side.**
- SERIES: `VOLTage? CH2` answers **28.000000 = 2 x 14 V** (CH2 was 14 V), i.e. the combined
  voltage; `VOLTage? CH3` answers 14. PARALLEL: `CURRent? CH2` answers **6.000000 = 2 x 3 A**,
  i.e. the combined current; `CURRent? CH3` answers 3.
- In SERIES `CURRent? CH3` answered **3.100000** while CH2 was 3 A (unexplained; possibly CH3 is
  set slightly above CH2 so that CH2 governs CC).
- `MAX` queries are not mode-aware (32.32 V / 3.232 A in all modes, Q14).
- **No setpoint was written while in SERIES or PARALLEL.** Whether `VOLTage CH2,20` in SERIES
  means 20 V combined (read-back 20) or 20 V per half (read-back 40, i.e. 40 V on the
  terminals) is unknown. If it is per half, writing back a value read in SERIES doubles the
  output voltage; the plug's read-back would detect it, but only after the instrument has
  applied it.

```
acc 643-655  (SERIES)   'VOLTage? CH2' -> b'28.000000\n';  'CURRent? CH2' -> b'3.000000\n';
                        'VOLTage? CH3' -> b'14.000000\n';  'CURRent? CH3' -> b'3.100000\n'
acc 657-669  (PARALLEL) 'VOLTage? CH2' -> b'14.000000\n';  'CURRent? CH2' -> b'6.000000\n';
                        'VOLTage? CH3' -> b'14.000000\n';  'CURRent? CH3' -> b'3.000000\n'
acc 671-683  (INDEPENDENT again) CH2 14/3, CH3 14/3 (CH3 was 12/2 before)
```

### Q22 Output OFF delay semantics
**Status: not tested.** Needs an output on with a non-zero OFF delay. Experiment 30 does not
cover it either (it runs with whatever delays are set and only records them); a new experiment
is needed (see "Still open").

---

## Verdict on every `ASSUMPTION(hw)` marker

| marker (text) | file:line | verdict | evidence |
|---|---|---|---|
| track numbering (`0` independent, `1` series, `2` parallel; words also accepted) | plug.py:166 | **confirmed** | acc 642-691: words and numbers accepted, query answers `0`/`1`/`2` |
| sense numbering (`0` = 2W, `1` = 4W) | plug.py:179 | **confirmed** (CH2; CH3 not written) | acc 730-739 |
| channel addressing / optional nodes (verbatim forms) | plug.py:201 | **confirmed**: verbatim forms work, and short forms address the named channel too | Q7, Q20; E8 plug getters acc 286-342 all answered |
| no space in `:SOURce:OCP:STATe CHn,1` | plug.py:247 | **confirmed** (with and without the space both work) | acc 578-587 |
| terminator `\n` both directions | plug.py:368 | **confirmed for the raw socket**; USB still open | bare 135-142 |
| series/parallel setpoint is the combined value on CH2 (guard uses series/parallel rating) | plug.py:611 | **partially confirmed, still open**: the read-back on CH2 is combined; the write side and the limit are untested | acc 643-669 |
| `OCP?` answers a plain number | plug.py:760 | **confirmed** | bare 15, acc 12 |
| protection state `1` = tripped | plug.py:783 | **still open** (only `0` ever seen) | acc 58-59, 73-74, 88-89, 103-104 |
| unlock in `tearDown()` needed | plug.py:942 | **confirmed at SCPI level** (writes set LOCK = 1, `LOCK 0` clears it); panel view still open | acc 395-397, 774-789, 1014 |
| terminator (fake answers without terminator) | fake_resource.py:90 | **confirmed** (PyVISA strips the single LF) | bare 141-142 |
| series/parallel setpoint combined; rating follows track mode | fake_resource.py:233 | **partially confirmed, still open**; the fake also lacks the CH2 -> CH3 copy on track change | acc 643-683 |
| clamping: V/I to the rating, negative to 0, OVP/OCP to 0.1x..1.1x | fake_resource.py:244 | **refuted in part**: V/I clamp to **1.01 x** rating (not 1.0 x); negative -> 0 confirmed; OVP/OCP 0.1x..1.1x confirmed; OCP delay clamps to 0..3600 (fake has no upper clamp); track-aware clamping untested | acc 352-363, 407-418, 462-469, 525-532, 593-598 |
| `OUTPut?` keeps answering 1 during an OFF delay | fake_resource.py:343 | **still open** (Q22) | - |
| track numbering (query answers the number) | fake_resource.py:362 | **confirmed**; but `OUTPut:TRACK?` with an argument must not answer | acc 643-691, bare 98 |
| "needed": the fake never locks the panel by itself | fake_resource.py:366 | **refuted**: the instrument sets LOCK = 1 on every write (not on queries) | acc 341 vs 395 |
| sense numbering (query answers 0/1) | fake_resource.py:379 | **confirmed**; but `MODE? CH1` answers `0` instead of timing out | acc 731-739, bare 99 |
| `OCP?` answers a plain number | fake_resource.py:399 | **confirmed** | bare 15 |
| protection state queries answer `1` when tripped | fake_resource.py:402 | **still open** | - |

Assumptions in SPEC.md that are not marked in the source but were tested:

| SPEC statement | verdict | evidence |
|---|---|---|
| fake initial OVP/OCP "at the rated maximum" (fake uses 1.0 x rating) | **refuted**: the maximum and the DEFault value is **1.1 x** rating (6.6 V, 35.2 V, 3.52 A) | acc 11-39, 470-471, 533-534 |
| fake: `MODE? CH1` times out | **refuted**: answers `0` | bare 99, acc 114 |
| fake: scalars `f'{x:.6f}'` | **refined**: values are float32, so `f'{float32(x):.6f}'` (`35.200001`) | acc 20 |
| "a clamped or ignored value is only detectable by reading it back" | **confirmed**: clamping and invalid writes leave `*ESR?` at 0 | acc 875-887 |
| plug timeout 5000 ms | **adequate**: slowest reply 368.7 ms (13 x margin) | timing table |

---

## Required code changes

For a coder (Sonnet class); the owner amends SPEC.md first (item 1) so the coder works from the
contract. Every change keeps the safety rules of AGENTS.md (read-back on every setter, no
output on in `tearDown()`/`restore()`, outputs off by default in `tearDown()`).

1. **SPEC.md (owner)**
   1. Command-form rule (section 3): state that hardware acceptance (2026-10-05, fw 4.1.2.9R1,
      raw socket) verified both the verbatim and the short forms, with the channel argument
      honoured; keep the verbatim forms (no reason to churn strings and tests), drop the
      "until hardware acceptance verifies channel addressing" clause.
   2. Timeout: keep 5000 ms (slowest reply 369 ms). Add: "the first query after a write is held
      for up to ~330 ms until the write is applied; read-back needs no sleep and no `*OPC?`".
   3. Guard rule: **keep the guard at the rated value** (6 V / 32 V / 3.2 A), not the
      instrument's 1.01 x `MAX`; the 1 % above rating is headroom, not a specification. Note
      that the instrument itself accepts up to 1.01 x and clamps beyond. Consequence to document:
      `restore()` of a snapshot taken while the panel held a value between 1.0 x and 1.01 x
      rating fails that item with `ValueError` (reported in the restore error, nothing sent).
   4. **SERIES/PARALLEL setpoints (decision needed).** Recommended: until a run has written
      setpoints in SERIES and PARALLEL with outputs off (see "Still open"), `set_voltage` /
      `set_current` on CH2 or CH3 while the cached track mode is not INDEPENDENT raise
      `RuntimeError` naming open question 21, and `restore()` skips CH2/CH3 setpoints in that
      case (reporting them). Reason: the read side is combined, the write side unknown, and a
      per-half write would double the terminal voltage before the read-back can object.
   5. `set_track()`: document that entering SERIES or PARALLEL copies CH2's voltage and current
      setpoints into CH3, and that CH3 keeps them after returning to INDEPENDENT. Require
      `set_track()` to read CH3 voltage/current before and after and log a warning naming both
      values when they changed.
   6. `sense()` / `set_sense()`: keep `ValueError` for CH1/CH4 (the manual limits `MODE` to
      CH2/CH3; the `0` that `MODE? CH1` returns means nothing).
   7. Section 4 (fake): replace the clamping and default paragraphs by the observed behaviour
      in item 3 below; replace "`MODE? CH1` times out" by "answers `0`".
   8. `models.tested`: decide whether a partial acceptance (raw socket, outputs off) is enough to
      set `tested=True` for the SPD4323X. Recommended: keep `False` until experiment 30 and the
      plug write smoke (item 9) have run; README then says "tested over LAN (raw socket),
      firmware 4.1.2.9R1".
   9. Add a line to "Done means": the fake reproduces every reply quoted in
      `docs/hardware_findings.md` for the commands the plug uses.

2. **plug.py**
   1. Replace the markers that are now confirmed by plain comments of the form
      `# verified on SPD4323X, firmware 4.1.2.9R1, 2026-10-05 (docs/hardware_findings.md Qn)`:
      track numbering (166), sense numbering (179), channel addressing / optional nodes (201),
      no space (247), terminator (368, but keep a note "USB not verified"), `OCP?` format (760).
   2. Keep as `# ASSUMPTION(hw)`: series/parallel setpoint (611, update the text: read side
      confirmed combined, write side open), protection `1` = tripped (783), and "needed" for the
      unlock (942, update the text: SCPI level confirmed, panel view open).
   3. Implement SPEC items 1.4 and 1.5 once the owner has decided.
   4. Add to the `tearDown()` docstring/comment: the unlock must stay the **last** write; any
      later write re-locks the panel (writes set LOCK = 1).
   5. No change to the timeout (5000 ms), the terminators, `_values_match` (abs_tol 5e-4 covers
      the float32 artefact `35.200001`) or the command strings.
   6. Optional, owner's call: `restore()` reads each value first and writes only those that
      differ (as `hw_acceptance.py` does). Each write costs about 250 ms; a full 4-channel
      restore is 32 writes, i.e. about 8 s.

3. **fake_resource.py** (each item with a test in `tests/test_fake.py`)
   1. Store every scalar as float32 and answer `f'{x:.6f}'` of that value
      (`struct.unpack('<f', struct.pack('<f', x))[0]`; standard library only), so that
      `OVP? CH2` answers `35.200001`.
   2. Initial OVP = 1.1 x rated voltage, initial OCP = 1.1 x rated current on every channel
      (6.600000 / 35.200001 / 3.520000 for the SPD4323X).
   3. Voltage and current clamp to **1.01 x rating** (6.060000, 32.320000, 3.232000) and to 0
      below; OVP/OCP clamp to 0.1 x .. 1.1 x rating (unchanged); OCP delay clamps to 0..3600
      (add the upper clamp); ON/OFF delay writes clamp the same way, marked
      `# ASSUMPTION(hw): same as OCP:DELay` (not exercised on hardware).
   4. Keywords: `MINimum`/`MIN`, `MAXimum`/`MAX`, `DEFault`/`DEF` in set commands for VOLT,
      CURR, OVP, OCP, OCP:DEL (and ON/OFF delays, same assumption). DEFault = 0 for V, I and
      delays, = 1.1 x rating for OVP/OCP. As query arguments (`VOLTage? CH1,MAX`) only for
      `VOLT?` and `CURR?` (answering 0, 1.01 x rating, 0); any keyword on `OVP?`, `OCP?`,
      `OCP:DEL?`, `OUTP:ON:DEL?`, `OUTP:OFF:DEL?` -> no answer (`FakeTimeout`). `MAX` is not
      track-aware (per-channel value in every mode).
   5. Lock: every accepted write other than `LOCK`/`LOCK:STATe` sets `lock = 1` (queries never
      do). Replace the "needed" marker at line 366 by a comment citing this document. Add a test
      that a plug write followed by `tearDown()` leaves `lock == 0`, and that `fake.lock == 1`
      after a setter.
   6. `MODE? CH1` answers `'0'` (observed). `MODE? CH4` and `MODE CH1|CH4,<x>` writes: keep
      the current behaviour (no answer / ignored) with `# ASSUMPTION(hw): not tried`.
   7. A query that takes no channel but gets an argument (`OUTPut:TRACK? CH1`) gets no answer.
   8. A channel query without channel (`VOLTage?`) answers CH1's value,
      `# ASSUMPTION(hw): CH1 or the panel-selected channel`. Keep `CH0`, `CH5`, `1`, `(CH1)` ->
      no answer, and invalid-channel writes ignored.
   9. Track change: entering SERIES or PARALLEL copies CH2's voltage and current setpoints to
      CH3 (kept after returning to INDEPENDENT). Store per-half values; in SERIES `VOLT? CH2`
      answers 2 x the stored CH2 voltage, in PARALLEL `CURR? CH2` answers 2 x the stored CH2
      current; CH3 answers its own stored value. Writes to CH2 in SERIES/PARALLEL: keep the
      current assumption (combined value, i.e. store value / 2) marked
      `# ASSUMPTION(hw): write side of question 21`. Do not model the 3.1 A oddity. OVP/OCP are
      not changed by a track change (observed).
   10. Status registers: `*ESR?` (bit 5 = 32 set by an unknown header or a query that gets no
       answer; bit 0 set by `*OPC`; cleared on read), `*CLS` (clears), `*STB?` -> `'0'`,
       `*ESE?` -> `'0'`, `*SRE?` -> `'0'`, `*WAI` accepted. Invalid channel, non-numeric value
       and clamping do not set any bit. The "only on an empty error list" quirk (Q6) is not
       modelled; note it as open.
   11. `;` chaining: split a line on `;`, execute the segments in order, answer the
       concatenation of the query replies with no separator (`'...R1' + '1'`). The plug never
       chains; this is for tools and tests that do.
   12. Keep the single-client limitation as a docstring note only (a fake object has no
       connections).
   13. Remove the clamping marker text that is now refuted and replace it by
       `# verified on SPD4323X ...` for the confirmed parts.

4. **models.py**: no change to the rating table (rated values stay the reference). Add two
   documented constants used by the fake (and available to the plug):
   `SETPOINT_MAX_FACTOR = 1.01` (instrument `MAX` for V and I) and
   `PROTECTION_RANGE = (0.1, 1.1)` (OVP/OCP range and 1.1 x default), each with a comment
   citing this document. `tested` per SPEC item 1.8.

5. **tests**
   1. `tests/test_fake.py`: update `test_out_of_range_values_are_clamped_silently` (6.060000,
      32.320000, 3.232000), `test_clamping_honours_track_mode` (mark the series/parallel part
      as assumption, `MAX` queries not track-aware), `test_sense_on_ch2_and_ch3_only`
      (`MODE? CH1` -> `'0'`); add tests for float32 formatting (`35.200001`), initial
      OVP/OCP 1.1 x, keywords in sets and queries, OCP delay clamp at 3600, auto-lock,
      `OUTPut:TRACK? CH1` no answer, `VOLTage?` -> CH1, CH2 -> CH3 copy on track change,
      `*ESR?`/`*CLS`/`*OPC`, `;` chaining.
   2. `tests/test_plug.py`: setting 6.05 V on CH1 is refused by the guard before sending
      (rating 6 V), while the fake would accept it (proves the guard, not the fake, refuses);
      a value above 6.06 V sent through `write_verified` directly raises on the clamped
      read-back; `set_track()` logs the CH3 change; if SPEC 1.4 is adopted, CH2/CH3 setters
      raise in SERIES/PARALLEL; `tearDown()` leaves `fake.lock == 0` after writes.
   3. Re-run `pytest -q`, `python example_test.py --fake`, `ruff check .`,
      `ruff format --check .`, `mypy src`.

6. **README.md "Things the manual does not tell you"** (dated 2026-10-05, SPD4323X firmware
   4.1.2.9R1, raw socket; one line each with the raw reply):
   1. Commands end in LF (CRLF also accepted); replies end in a single LF.
   2. `MAX` is 1.01 x the rating for voltage and current (`VOLTage? CH1,MAX` -> `6.060000`);
      OVP/OCP range 0.1 x .. 1.1 x rating; default OVP/OCP = 1.1 x (`OVP? CH2` -> `35.200001`).
   3. Out-of-range values are clamped silently (`VOLTage CH1,7.5` -> `6.060000`,
      `OVP CH1,0.3` -> `0.600000`), never reported.
   4. Values are float32 (`35.200001`).
   5. `OCP? CHn` answers like `OVP?` (`3.520000`).
   6. An invalid query is never answered (wait for the timeout); there is no error reply, and
      `*ESR?` bit 5 is not dependable.
   7. Short forms and omitted `SOURce`/`:SET` work and honour the channel; `VOLTage?` without a
      channel answers CH1; `POWER` and `TRACK` have no short form.
   8. Track and sense queries answer numbers: 0/1/2 = independent/series/parallel, 0/1 = 2W/4W.
   9. Entering series/parallel copies CH2's setpoints to CH3 permanently.
   10. In series `VOLTage? CH2` is the combined voltage, in parallel `CURRent? CH2` the combined
       current; `MAX` queries ignore the coupling.
   11. Any remote write locks the front panel (`LOCK?` -> `1`); `LOCK 0` unlocks; queries do
       not lock.
   12. One socket client at a time; a second connection is accepted but not served.
   13. A query right after a write waits about 250 ms (until the write is applied); otherwise
       replies take 1-5 ms.
   14. `MODE? CH1` answers `0` although the manual limits `MODE` to CH2/CH3.
   15. `;` chains work, but chained query replies are concatenated without separator.
   Also update the transport table: raw socket "verified (2026-10-05)", VXI-11 and USBTMC
   still "unverified"; model table: SPD4323X "LAN raw socket verified, outputs-on pending"
   (per SPEC 1.8).

7. **docs/scpi_reference.md**: do not rewrite the transcription. Append under each affected
   command a line `Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): ...` with the
   observed reply/behaviour, at least for `*IDN?`, `*ESR?`, `*OPC`/`*OPC?`, `*STB?`, VOLTage,
   CURRent, OVP, OCP (response format), OCP:STATe (space accepted), OCP:DELay (range and no
   0.01 s rounding), OUTPut:TRACK, MODE (`MODE? CH1`), LOCK, the MEASure queries, and the
   grammar section (forms, `;`, terminator). In section 8, annotate each question with its
   status and a link to the matching heading of this document (do not delete the question).

8. **HANDOFF.md**: record acceptance run 1 (what ran, what did not), the open items below, and
   the tool defects in item 9.

9. **tools/hw_acceptance.py** (defects and gaps found in this run)
   1. `Link.query`: read one line per command line, not one per `?` segment (cause of the
      false timeout on `*IDN?;*OPC?`); on any failure keep and log the bytes already received.
   2. Experiment 15 writes no setpoint while in SERIES/PARALLEL: add, with outputs off,
      `OUTPut:TRACK SERIES`, `VOLTage CH2,20`, `VOLTage? CH2`, `VOLTage? CH3`,
      `VOLTage CH2,MAXimum`, `VOLTage? CH2`, `OVP CH2,MAXimum`, `OVP? CH2`; the same for
      `CURRent`/`OCP` in PARALLEL; then INDEPENDENT and restore CH2/CH3. Answers Q21's write side
      without switching anything on.
   3. Experiment 19 writes `VOLTage CH5,1` but never reads CH4 back: read all four channels
      before and after every invalid-channel write. Add the Q6 sequence
      `*CLS`, `VOL? CH1`, `*ESR?`, `VOL? CH1`, `*ESR?`, `*CLS`, `VOL? CH1`, `*ESR?` to test the
      "empty error list" hypothesis.
   4. No experiment writes `OUTPut CHn,0`, `OUTPut:ALL 0` or the ON/OFF delays, so the plug's
      `tearDown()` path has never run on hardware. Add an outputs-off "plug write smoke"
      experiment: construct `SiglentSpdPlug(resource=<link>, outputs_off_on_teardown=True,
      restore_state=True)`, run `configure_channel(1, ...)`, `set_output_delay(1, on_s=0.5,
      off_s=0.5)`, `set_sense(2, ...)` and back, then `tearDown()` (sends `OUTPut:ALL 0`, per
      channel `OUTPut?`, restore, `:SOURce:LOCK:STATe OFF`). All these writes are already on the
      tool's allow list (OFF only).
   5. Restore and the final check cover CH1-CH3 only; include CH4.

---

## Still open / needs another hardware run

| question / marker | needs | how |
|---|---|---|
| Q11 settling after output on, measurement refresh, `*OPC?` after output on, `OUTPut:ALL?` with mixed states | output on, nothing connected | experiment 30 (command below) |
| `OUTPut CHn,0`, `OUTPut:ALL 0`, ON/OFF delay writes, `:SOURce:LOCK:STATe OFF` verbatim, i.e. the plug's `tearDown()` | outputs off is enough | new "plug write smoke" experiment (tool item 9.4) |
| Q21 write side: is a setpoint written to CH2 in SERIES/PARALLEL combined or per half; CH3 writes in coupled modes; OVP/OCP limits in coupled modes | outputs off is enough | extended experiment 15 (tool item 9.2) |
| Q22 `OUTPut?` during an OFF delay; `OUTPut:ALL 0` and delays; delay set to 0 while pending | output on, nothing connected | new experiment: CH1 1.0 V / 0.1 A, `OUTPut:OFF:DELay CH1,2`, `OUTPut CH1,1`, `OUTPut CH1,0`, poll `OUTPut? CH1` and `MEASure:VOLTage? CH1` every 100 ms for 3 s; repeat with `OUTPut:ALL 0`; repeat setting the delay to 0 while pending; finally delay 0 and output off with read-back |
| Q13 `OUTPut:TRACK` rejected while an output is on | output on | owner decides (it changes the coupling of a live output): nothing connected, CH2 on at 1 V / 0.1 A, `OUTPut:TRACK SERIES`, `OUTPut:TRACK?`, back to `0`, CH2 off with read-back |
| protection state `1` = tripped (plug.py:783, fake 402); Q10 state after trip and `RESET:PROTect` | a trip: an output on with OVP/OCP below what the output delivers | a deliberate OCP trip needs a load; an OVP trip without load is possible (OVP below setpoint, output on) but is a deliberate fault: owner decides, nothing connected |
| Q12 panel visibly unlocked after a session | someone at the front panel | user looks after the next run |
| Q6 error-list hypothesis | outputs off | tool item 9.3 |
| Q8 effect of `VOLTage CH5,1` on CH4 | outputs off | tool item 9.3; meanwhile ask the user to check CH4's setpoint on the panel (it was 0.000 V / 0.000 A before the run) |
| Q2 USB identity, USB terminator | USB cable | `python3 -c "import pyvisa; print(pyvisa.ResourceManager('@py').list_resources())"`, then `python3 tools/hw_acceptance.py --read-only --resource 'USB0::...::INSTR'` |
| Q3 VXI-11, web, telnet | a direct LAN path | `python3 tools/bare_socket_check.py --probe-ports`; `python3 tools/hw_acceptance.py --read-only --only 7 --try-vxi11` |
| Q14 SPD4306X CH4, Q15-Q19 | other model / out of scope | - |

Command line for the output-on run (experiment 30; the selector is the number, `--only 30`,
not `E30`; nothing may be connected to any output terminal; all outputs off at the start):

```bash
export PSU_HOST=192.0.2.10
python3 tools/hw_acceptance.py --only 30 --allow-output --confirm-no-load \
    --report acceptance_report_output.local.md
```

Experiment 30 switches on CH1 only, at 1.0 V / 0.1 A, records the settling curve every 50 ms for
up to 3 s, switches off with read-back, and restores the snapshot. It does not cover Q22; the
new experiments above should be added to the tool before the next session so that one visit
answers everything that needs an output on.


---
---

# Hardware findings: SPD4323X acceptance run 2

| item | value |
|---|---|
| instrument | Siglent SPD4323X, serial `SPD43XXXXXXXXX` (placeholder) |
| firmware | `4.1.2.9R1` |
| date | 2026-10-04 (log times 20:34 to 20:36 for step a, 21:21 for step b; the owner was at the instrument). Run 1 is dated 2026-10-05 in its own section (the clock of the machine that ran it), so run 2 carries the earlier date although it happened later |
| address | `192.0.2.10` in this document |
| transport | PyVISA `@py`, `TCPIP::192.0.2.10::5025::SOCKET`, LF terminators, timeout 3000 ms, probe timeout 1500 ms |
| step (a) | `tools/hw_acceptance.py --report run2.local.md`: experiments 1-6, 8, 10-21 (write tier, outputs off), exit clean, restore `36 items, 0 written back, 36 unchanged, 0 FAILED`, snapshot status `restored`, outputs `{1: 0, 2: 0, 3: 0, 4: 0}` at the end |
| step (b) | `tools/hw_acceptance.py --only 30,31 --allow-output --confirm-no-load --report run2_output.local.md`: experiments 30 and 31 (CH1 on at 1.0 V / 0.1 A, nothing connected), `CH1 was switched on by this run; output off confirmed`, restore `36 items, 1 written back, 35 unchanged, 0 FAILED`, outputs all `0` at the end |
| step (c), the owner at the front panel | panel **unlocked**; CH4 **0 V / 0 A**; CH3 back at **12 V / 2 A**, off |
| not run | experiment 7 (VXI-11), `*TST?`, USB, web/telnet, protection trip, `OUTPut:TRACK` with an output on, `OUTPut:ALL?` with mixed states |
| change outside the tool | at the owner's request the key sound was switched off (`SOUNd:KEY 0`, read back `0`; before: key sound `1`, alarm sound `1`, alarm sound untouched). This is a persistent instrument setting that neither the tool's snapshot nor the plug covers. It was sent with a one-off script, not by `tools/hw_acceptance.py` |

Line references: "acc N" is line N of `hw_acceptance.local.log` of this visit (a single file: step (a) is
lines 1-1432, step (b) lines 1433-1882; run 1's log is a different file, so "acc" numbers of run 1 and
run 2 are not comparable). Quoted replies are the raw bytes as logged, the serial number replaced by the
placeholder. The two reports are `run2.local.md` and `run2_output.local.md` (local, git-ignored).

Timing summary (whole log, queries only, timeouts excluded):

| situation | n | min | median | 90 % | max |
|---|---|---|---|---|---|
| query after a query | 1481 | 1.4 ms | 4.1 ms | 5.6 ms | 455.3 ms (a `LOCK?`) |
| first query after a write | 167 | 5.0 ms | 258.7 ms | 294.9 ms | 412.3 ms |
| `LOCK?` after a query | 22 | 2.5 ms | 33.4 ms | 246.3 ms | 455.3 ms |
| `LOCK?` after a write | 19 | 164.4 ms | 261.4 ms | 329.2 ms | 391.0 ms |

Same picture as run 1; the 5000 ms plug timeout keeps a factor 11 over the slowest reply. No `LATE` bytes.

## Answers to the open questions

### Q21 Series/parallel setpoint meaning (write side): answered

**A setpoint written to CH2 is the combined value, and CH3 follows with half of it.** In SERIES the
voltage written to CH2 is read back unchanged from CH2 (combined) and CH3 reads half; in PARALLEL the
same for the current. A numeric combined value above the per-channel `MAX` is accepted (5 A written to
CH2 in PARALLEL reads back 5 A although `MAX` is 3.232 A), while the `MAXimum` **keyword** still answers
the per-channel value (32.32 V resp. 3.232 A, taken as the combined value). OVP and OCP are untouched by
every write. Both halves keep their value after returning to INDEPENDENT.

```
acc 684-685   W 'OUTPut:TRACK SERIES' -> 'OUTPut:TRACK?' -> b'1\n'
acc 686-687   (SERIES) 'VOLTage? CH2' -> b'28.000000\n'  (CH2 was 14 V)   'CURRent? CH2' -> b'3.000000\n'
acc 692-693   (SERIES) 'VOLTage? CH3' -> b'14.000000\n'                    'CURRent? CH3' -> b'3.100000\n'
acc 742-744   W ':SOURce:VOLTage:SET CH2,20' -> ':SOURce:VOLTage:SET? CH2' -> b'20.000000\n'  216.3 ms
                                                ':SOURce:VOLTage:SET? CH3' -> b'10.000000\n'
acc 745-747   W ':SOURce:VOLTage:SET CH2,MAXimum' -> CH2 b'32.320000\n'  CH3 b'16.160000\n'
acc 748-750   W ':SOURce:OVP CH2,MAXimum' -> ':SOURce:OVP? CH2' -> b'35.200001\n'  ':SOURce:OVP? CH3' -> b'35.200001\n'
acc 759-762   W 'OUTPut:TRACK PARALLEL' -> b'2\n';  (PARALLEL) CH2 V b'16.160000\n' (the half kept from SERIES)
              'CURRent? CH2' -> b'6.000000\n' (2 x 3 A)   'CURRent? CH3' -> b'3.000000\n'
acc 769-771   W ':SOURce:CURRent:SET CH2,5' -> ':SOURce:CURRent:SET? CH2' -> b'5.000000\n'
                                               ':SOURce:CURRent:SET? CH3' -> b'2.500000\n'
acc 772-774   W ':SOURce:CURRent:SET CH2,MAXimum' -> CH2 b'3.232000\n'  CH3 b'1.616000\n'
acc 775-777   W ':SOURce:OCP CH2,MAXimum' -> CH2 b'3.520000\n'  CH3 b'3.520000\n'
acc 786-790   (after INDEPENDENT) CH2 V b'16.160000\n' I b'1.616000\n'; CH3 V b'16.160000\n' I b'1.616000\n'
              (the tool then wrote CH2 14 V / 3 A and CH3 12 V / 2 A back, each read back)
```

(Log times `20:35:34.4` to `20:35:38.9`.)

Conclusions:
- The write side is the **combined value**, so the guess in SPEC.md (and in the fake) was right: the
  read-back of a CH2 write in SERIES equals what was written. A per-half interpretation would have read
  back 40 for `VOLTage CH2,20`.
- The `MAXimum` keyword is **not mode-aware**: it writes the per-channel maximum as the combined value,
  32.32 V in SERIES (16.16 V per half) and 3.232 A in PARALLEL (1.616 A per half), the same finding as for
  the `MAX` queries (Q14). A **numeric** write is not limited to that: `CURRent CH2,5` in PARALLEL
  (acc 769-771) read back `5.000000` with CH3 at `2.500000`. The upper limit of a numeric combined write
  (probably twice `MAX`, i.e. 64.64 V / 6.464 A) and the behaviour of a numeric write above the series
  rating of the manual (60 V) were **not** tried.
- **CH3's reading in a coupled mode is the per-half value of CH2's write**; a write to CH3 in SERIES or
  PARALLEL, the voltage of CH2 in PARALLEL and the current of CH2 in SERIES were **not** written. Those stay
  open (the plug keeps refusing them).
- The `3.100000` that `CURRent? CH3` shows in SERIES while CH2 is 3 A reproduced (acc 693). It
  is not an effect of the write (it is there before any write); the fake does not model it.
- The half values persist: after the sequence CH2 and CH3 both read 16.16 V and 1.616 A in INDEPENDENT.
  The tool restored CH2 and CH3 to 14 V / 3 A and 12 V / 2 A with read-back (acc 791-806 and the
  restore summary); the owner confirmed CH3 at 12 V / 2 A on the panel.

### Q22 Output OFF delay semantics: answered

With a non-zero OFF delay (2 s) **`OUTPut? CHn` keeps answering `1` and the output keeps delivering
voltage until the delay has elapsed**, for `OUTPut CHn,0` and for `OUTPut:ALL 0` alike. Setting the delay
to 0 while the switch-off is pending turns the output off at once. Times relative to the OFF command:

| case (delay 2 s, CH1 1.0 V, no load) | `OUTPut? CH1` | `MEASure:VOLTage? CH1` |
|---|---|---|
| A `OUTPut CH1,0` | `1` until 1.91 s, `0` from 2.009 s | 0.999 V until 2.01 s, 0.862 V at 2.12 s, below 0.1 V at 2.60 s |
| B `OUTPut:ALL 0` | `1` until ~1.9 s, `0` from 2.008 s | 0.999 V until ~2.0 s, 0.770 V at the first sample after, below 0.1 V at 2.60 s |
| C `OUTPut CH1,0`, then `OUTPut:OFF:DELay CH1,0` at 0.50 s | `1` until 0.50 s, `0` at 0.547 s (46 ms after the write) | 0.999 V, 0.663 V from 0.55 s, below 0.1 V at 1.10 s |

```
acc 1582-1584  W 'OUTPut:OFF:DELay CH1,2';  W 'OUTPut CH1,1'
acc 1588-1629  W 'OUTPut CH1,0' (21:21:16.032) -> 'OUTPut? CH1' b'1\n' at 16.046 ... b'1\n' at 17.94 (line 1627), b'0\n' at 18.041 (line 1629)
acc 1654-1699  W 'OUTPut CH1,1';  W 'OUTPut:ALL 0' (21:21:20.480, line 1658) -> 'OUTPut? CH1' b'1\n' at 20.730 ... b'0\n' at 22.488 (line 1699)
acc 1728-1740  W 'OUTPut CH1,0' (21:21:24.873) -> b'1\n' at 24.897;  W 'OUTPut:OFF:DELay CH1,0' (line 1739, 25.374) -> 'OUTPut? CH1' -> b'0\n' at 25.420 (46.1 ms)
```

Consequences for the plug: the order in `tearDown()` (zero a non-zero OFF delay of every channel that is
on, then `OUTPut:ALL 0`) is **necessary**: without it `OUTPut:ALL 0` leaves the DUT powered for the delay
time and the per-channel read-back would find `1`. Zeroing the delay while the switch-off is pending
(case C) is also a valid way out. No code change; the assumption of the fake is confirmed.

### Q11 Timing, settling, `*OPC?` after output on: answered (no load)

- First `MEASure:VOLTage? CH1` after `OUTPut CH1,1` (V set 1.0 V, I 0.1 A): `0.999164` after **294.9 ms**
  (the query is held for the write, like every query after a write); there was **no ramp to observe** at
  that resolution: all 11 samples are within 1 mV of the final value. `*OPC?` -> `1` in 2.3 ms,
  `OUTPut? CH1` -> `1`. Run mode `CV`; current `0.000230`, power `0.000229` (offsets, nothing connected).
- The reading is a flickering plateau (`0.998909` / `0.999164`, one 0.25 mV step), i.e. the ADC noise at
  the 0.25 mV level; the measurement repeats the identical value for several 50 ms samples, so it
  refreshes slower than the query rate (every 50 to 100 ms in the OFF decay, where values repeat in pairs).
- Switching off without a delay: `OUTPut? CH1` -> `0` after 182.6 ms (query held for the write); the
  voltage of the open output decays through `0.961716`, `0.363061`, `0.268550` ... to `0.006416` in about
  1 s (the output stage discharging, no load): below 20 mV at 0.70 s.
- `OUTPut:ALL?` with mixed states was **not** queried (only the all-off `0` at the start). Still open.

```
acc 1490-1493  W 'OUTPut CH1,1' -> 'MEASure:VOLTage? CH1' -> b'0.999164\n' 294.9 ms; '*OPC?' -> b'1\n' 2.3 ms; 'OUTPut? CH1' -> b'1\n'
acc 1504-1506  'MEASure:CURRent? CH1' -> b'0.000230\n';  'MEASure:POWER? CH1' -> b'0.000229\n';  'MEASure:RUN:MODE? CH1' -> b'CV\n'
acc 1507-1510  W 'OUTPut CH1,0' -> 'OUTPut? CH1' -> b'0\n' 182.6 ms; 'MEASure:VOLTage? CH1' -> b'0.961716\n', b'0.363061\n'
```

`wait_for_voltage` defaults (tolerance 0.05 V, timeout 5 s, interval 0.1 s) are adequate for an
unloaded output; a capacitive DUT is the DUT's business.

### Q6 Error reporting: the "empty error list" hypothesis is not supported

The sequence `*CLS`, `VOL? CH1`, `*ESR?`, `VOL? CH1`, `*ESR?`, `*CLS`, `VOL? CH1`, `*ESR?` answered
`32`, `32`, `32`: bit 5 is set by **every** unanswered unknown header in this phase, also the second one
without a `*CLS` in between (acc 1072-1078). So the explanation of run 1 (bit 5 only for an empty error
list) does not hold. What remains unexplained: in the read-only tier an unknown query raised no bit twice
(acc 280-285: `FOOBar? CH1` -> `*ESR?` `0`; `VOLTage? CH5` -> `0`), right after an `*ESR?` that read `32`
(acc 278), the same pattern as in run 1. Invalid-channel writes, a non-numeric value and a clamped value
still raise nothing (`VOLTage CH5,1`, `VOLTage CH0,1`, `VOLTage CH1,abc`, 125 % of the rating: `*ESR?` `0`,
`*STB?` `0` each, acc 1026-1066). **`*ESR?` stays unusable as an error channel; read-back stays the only
check.** No code change: the fake already sets bit 5 on every unknown or unanswered query.

```
acc 1068-1070  'FOOBar? CH1' -> VI_ERROR_TMO;  '*ESR?' -> b'32\n';  '*STB?' -> b'0\n'
acc 1072-1078  'VOL? CH1' -> TMO;  '*ESR?' -> b'32\n';  'VOL? CH1' -> TMO;  '*ESR?' -> b'32\n';  *CLS;  'VOL? CH1' -> TMO;  '*ESR?' -> b'32\n'
acc 278-285    '*ESR?' -> b'32\n';  'FOOBar? CH1' -> TMO;  '*ESR?' -> b'0\n';  'VOLTage? CH5' -> TMO;  '*ESR?' -> b'0\n'
```

### Q8 Invalid channel write and CH4: answered

`VOLTage CH5,1` and `VOLTage CH0,1` change **none of the four channels**; CH4 was read back before and
after (voltage and current, `0.000000` each) and the owner saw 0 V / 0 A on the panel afterwards. The
write is silently ignored. `VOLTage?` without a channel answered `5.000000` again, which is CH1's value
(CH1 5 V, CH2 14 V, CH3 12 V, CH4 0 V); still not decidable whether that is "CH1" or the panel-selected channel.
`MODE? CH1` -> `0`, `MODE? CH4` and `MODE CH1|CH4,<x>` were not tried.

### Q12 Remote lock and the plug's tearDown(): answered

- The plug's `tearDown()` against the real supply (experiment 21, outputs off, `restore_state=True`):
  per channel `OUTPut? CHn` -> `0`, `OUTPut:ALL 0` (acc 1261) -> all four channels read `0`, the changed
  values were restored with read-back, `:SOURce:LOCK:STATe OFF` (acc 1315) -> `:SOURce:LOCK:STATe?` -> `0`
  (269.0 ms), `LOCK?` -> `0`. **The owner confirmed the front panel unlocked** afterwards (no lock icon,
  keys usable). Same after the tool's own `LOCK 0` at the end of every experiment (acc 1572-1573).
- The write path of the plug ran as written: `OUTPut:ON:DELay CH1,0.5` -> `OUTPut:ON:DELay? CH1` ->
  `0.500000`; `OUTPut:OFF:DELay CH1,0.5` -> `0.500000`; `MODE CH2,4W` -> `1`; `MODE CH2,2W` -> `0`; delays
  back to `0.000000` (acc 1245-1255). No exception, nothing left over, CH1-CH4 equal to the snapshot.

```
acc 1245-1253  W 'OUTPut:ON:DELay CH1,0.5' -> b'0.500000\n' 260.2 ms;  W 'OUTPut:OFF:DELay CH1,0.5' -> b'0.500000\n';
               W 'MODE CH2,4W' -> 'MODE? CH2' -> b'1\n';  W 'MODE CH2,2W' -> b'0\n'
acc 1261-1264  W 'OUTPut:ALL 0' -> 'OUTPut? CH1' -> b'0\n' 271.6 ms ... CH4 b'0\n'
acc 1315-1316  W ':SOURce:LOCK:STATe OFF' -> ':SOURce:LOCK:STATe?' -> b'0\n' 269.0 ms
```

### Q9 (rest): ON/OFF delay writes

`OUTPut:ON:DELay` and `OUTPut:OFF:DELay` writes accept `0.5`, `2` and `0` and read back `0.500000`,
`2.000000`, `0.000000`. Whether they clamp at 3600 s and at 0 like `OCP:DELay` was **not** tried (marker
stays, text narrowed).

### Q13 `OUTPut:TRACK` with an output on: not tested

Needs an output on while changing the coupling (a live output); not done. Open, owner's decision.

### Q10 protection trip: not tested

No trip was provoked (nothing connected, no deliberate OVP/OCP fault). `1` = tripped stays an assumption.

### Other observations
- Run 1's findings reproduced without exception: forms (E3, E20), clamping (E10-E14), track/sense numbers
  (E15, E16), `LOCK` behaviour (E17), `*IDN?;*OPC?` now answered as one line `...4.1.2.9R11` by the fixed
  `Link.query` (acc 172-174 equivalent: no timeout), the `;` chains in E18.
- The `LOCK?` after the `LOCK 0` write still takes 164-391 ms; irrelevant for the plug.
- The owner found the beeping annoying and asked for it to be switched off (`SOUNd:KEY 0`, see the header
  table). Whether the beeps came from remote writes or from keys was not established. It is a bench
  convenience, not something the plug should do.

## Verdict on every remaining `ASSUMPTION(hw)` marker

| marker | where | verdict | evidence |
|---|---|---|---|
| write side of question 21 | plug `_require_independent`, `restore()`; fake `_do_write` | **answered**: CH2's write is the combined value, CH3 follows half; the `MAXimum` keyword is per channel, a numeric value may exceed it. CH3 writes, CH2 current in SERIES, CH2 voltage in PARALLEL and the upper limit of a numeric combined write **still untested** | acc 742-777 |
| `OUTPut?` during OFF delay | fake `_set_output` | **confirmed** (also for `OUTPut:ALL 0`); plus: delay 0 while pending switches off at once, which the fake lacked | cases A, B, C |
| unlock needed / panel visibly unlocked | plug `tearDown()` | **confirmed** (SCPI and panel) | acc 1315-1316, owner |
| protection state `1` = tripped | plug `protection_status`; fake | **still open** (no trip) | - |
| same as `OCP:DELay` (ON/OFF delay clamp) | fake `_limits` | **still open** (0.5, 2, 0 accepted; clamps untried) | acc 1245-1255 |
| `MODE` on CH1/CH4 not tried | fake | **still open** | - |
| CH1 or the panel-selected channel (`VOLTage?`) | fake | **still open** | acc `VOLTage?` -> `5.000000` |

## Required code changes

1. **plug.py**
   1. Replace `_require_independent` by a check that allows, in a coupled mode, exactly the two verified
      writes: CH2 voltage in SERIES, CH2 current in PARALLEL (combined value, read-back verified; the guard
      is the series rating 60 V resp. the parallel rating 6.4 A of the model, every other guard stays at
      the per-channel rating). Everything else on CH2/CH3 in a coupled mode keeps raising `RuntimeError`
      (message names question 21 and says which combination is untested). `configure_channel` applies the
      same check per item; `restore()` restores the verified quantity and reports the rest as skipped.
   2. Resolve the unlock marker in `tearDown()`; add the OFF-delay evidence to the `tearDown()` comment.
   3. `models.SPD4323X.tested = True` (experiments 21 and 30 passed).
2. **fake_resource.py** (each with a test)
   1. Coupled write of the combined quantity: store half in CH2 **and CH3** (CH3 follows); the keywords
      `MINimum`/`MAXimum`/`DEFault` give the per-channel value as the combined one (then halved); a numeric
      value is clamped to `[0, 2 x MAX]` (`# ASSUMPTION(hw)`, upper limit untried).
   2. Setting the OFF delay to 0 while a switch-off is pending switches the output off at once.
   3. Replace the OFF-delay and unlock markers by `verified ...` comments; narrow the delay-clamp marker.
3. **tests**: coupled writes in SERIES/PARALLEL through plug and fake (combined read-back, CH3 half, clamp,
   keywords), remaining refusals, restore in a coupled mode, `OUTPut:ALL 0` with an OFF delay,
   delay 0 while pending, `models.tested`.
4. **docs**: SPEC.md (coupled modes, fake paragraph, `tested`, Done-means), README ("Things the manual does
   not tell you", model table), `docs/scpi_reference.md` annotations, HANDOFF.md.

## Still open after run 2

| item | needs |
|---|---|
| USB identity and USB terminator (Q2) | a USB cable |
| VXI-11, web, telnet (Q3) | a direct LAN path |
| protection state `1` = tripped, state after a trip and after `RESET:PROTect` (Q10) | a real trip (OCP needs a load; OVP trip without a load is a deliberate fault) |
| `OUTPut:TRACK` while an output is on (Q13) | owner's decision (live output) |
| `OUTPut:ALL?` with mixed channel states | two outputs on, nothing connected |
| CH3 writes in a coupled mode, CH2 current in SERIES, CH2 voltage in PARALLEL, the upper limit of a numeric combined write (`VOLTage CH2,40` in SERIES, `CURRent CH2,7` in PARALLEL) | outputs off is enough: a small extension of experiment 15 |
| ON/OFF delay clamp at 3600 s | outputs off is enough |
| `MODE` on CH1/CH4, `VOLTage?` without channel (CH1 vs panel channel) | outputs off, panel state |
| SPD4121X, SPD4306X (Q14) | other models |
