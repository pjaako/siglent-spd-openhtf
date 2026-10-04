# SPD4000X Remote-Control (SCPI) Reference

> **Source document:** `SPD4000X_UserManual_E01C.pdf` (SIGLENT "SPD4000X Series User Manual", Chapter 10 "Remote Control", printed pp. 51-77, plus related facts from chapters 4, 5, 7, 8, 9).
> **Status:** This file is a transcription for agents. It **MUST be the only source of truth for SCPI commands in this project.** Do **not** add commands from other Siglent models (SPD3303X, SPD4000X-other docs, etc.) or from general SCPI knowledge. If a command is not in this file, it is not known to exist on the SPD4000X.
> Conventions in this file: text in code blocks is copied verbatim from the manual (including its typos). Lines starting with `⚠ manual note:` mark ambiguities or apparent typos; they have NOT been silently corrected. `\n` in responses is the manual's own notation; `\s` in responses is the manual's own notation (apparently a space).

---

## 1. Transports (manual section 10.1 "Way to Control")

Chapter 10 intro (verbatim):

> The SPD4000X supports communication with a computer via USB and LAN interfaces using a SCPI (Standard Commands for Programmable Instruments) compliant command set.
> This chapter will introduce how to build a programming environment and explain the SCPI commands supported by the SPD4000X.

### 1.1 NI-VISA (USB or LAN)

> Users can develop remote control programs for the instrument by using NI-VISA of NI (National Instrument Corporation). Regarding NI-VISA, there is a complete and real-time version (Run-Time Engine version). The complete version includes NI device drivers and a tool called NI MAX. NI MAX is a user interface used to control the device. The real-time version is much smaller than the full version, and it only includes NI device drivers.
>
> After installing NI-VISA, use a USB cable to connect the SPD4000X (via the USB Device interface on the rear panel) to the computer, or use a network cable to connect the SPD4000X (via the LAN interface on the rear panel) to the local area network where the computer is located.
>
> Based on NI-VISA, users can remotely control SPD4000X in two ways, one is through web service; the other is by developing custom programming combined with SCPI commands. For more information, please refer to the programming examples.

Facts stated:
- USB: connect through the "USB Device interface on the rear panel" (the rear panel has multiple "USB ports", item 4 in the rear panel legend; a USB HOST port for U-disk also exists, see chapter 11 item 3).
- LAN: via the "LAN interface on the rear panel".
- Requirement stated: NI-VISA (full version with NI MAX, or Run-Time Engine).

⚠ manual note: The manual does **not** mention USBTMC, USB VID/PID, VISA resource-string format (e.g. `USB0::...::INSTR` or `TCPIP::...::INSTR`), VXI-11, HiSLIP, or telnet. None of those may be assumed from this document. Only the facts above and the raw socket (below) are documented.
⚠ manual note: The text says "please refer to the programming examples" but chapter 10 contains **no** programming examples.

### 1.2 Raw sockets (LAN)

> Users can also use Sockets to communicate with SPD4000X based on the TCP/IP protocol through the network port. Socket communication is a basic communication technology of computer networks, which allows applications to communicate through network hardware and standard network protocol mechanisms built into the operating system. This method requires two-way communication between the instrument and the computer network through an IP address and a fixed port number.
>
> **The port of SPD4000X for Socket communication is 5025.**
>
> After connecting the SPD4000X (via the LAN interface on the rear panel) to the local area network where the computer is located with a network cable, the user can combine SCPI commands for custom programming to realize remote control of the SPD4000X. For more information, please refer to the programming examples.

- TCP port: **5025**.
- Manual does not say whether the socket transport is TCP-only, multiple-connections, nor what line terminator the instrument expects on input (see Open Questions).
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): port 5025 serves **one client at a time**: a second connection is accepted by TCP but gets no reply while the first is open (docs/hardware_findings.md Q3). The input terminator is LF (CRLF also works), replies end in a single LF (Q1). VXI-11, web and telnet were not probed.

### 1.3 Web service (LAN) - section 10.5

> The SPD4000X can be remotely controlled through its embedded web control interface.

- Connection method 1 (direct PC-to-instrument with a network cable, "cross-over cable"): set the PC to a static IPv4 address that differs from the SPD's, with the same subnet mask and same gateway as the SPD; set the SPD manually (per "9.2.2 LAN Setting") to the same subnet mask/gateway and a different IP. (Manual text also says "Set the SPD3004X:" and "apply it to SPD3004X" in this section.)
- Connection method 2: SPD4000X and PC on the same network; set DHCP to "ON" in the LAN setting interface (or change the IP manually).
- Access: "open the Google browser on the PC and directly enter the IP address in the input field". No port number is given for the web server (default HTTP assumed by the manual's wording; not stated explicitly).
- Web UI pages named: main interface (voltage/current, "Submit"), "Configure" (needs "Submit"), "About" (device info), list operation (select channel, add steps, loop/cycles, "Download" per step, then turn on "Output" and "Submit"), list "Export"/"Import" as `.csv` (see 10.5.3 / 10.5.4).
⚠ manual note: "SPD3004X" appears in 10.5.1 and 10.5.4 - evident copy-paste leftover from another model's manual; read as SPD4000X.

### 1.4 LAN configuration (panel and SCPI)

From 9.2.2: the SPD4000X supports DHCP; with DHCP ON it sets IP/subnet/gateway automatically; with DHCP OFF the user sets IP, subnet mask and gateway manually. The factory settings (9.3.2) set DHCP to on and set IP, Subnet Mask, Gateway and GPIB address to 0. See SYSTEM subsystem (section 5.4) for the SCPI commands.

### 1.5 GPIB

Features list: "USB-GPIB module is optional". GPIB address is settable on the panel (Menu > Interface > GPIB) and via `GPIB:ADDRess`. The manual says nothing else about GPIB remote use.

### 1.6 Remote-control side effect (lock)

Front-panel button description (chapter 5, shortcut buttons): "Lock/Unlock: Enable/disable the lock function. Short press to lock, long press to release, **and the device will be automatically locked when remotely controlled.**"

---

## 2. Grammar (section 10.2 "Grammatical Conventions")

Verbatim:

> SCPI commands are a tree-like hierarchical structure, including multiple subsystems. Each subsystem is composed of a root keyword and one or several hierarchical keywords. Command keywords are separated by colons ' : ', keywords are followed by optional parameter settings, commands and parameters are separated by ' spaces ', for multiple parameters, parameters are separated by commas ' , '. A question mark ' ? ' is added after the command line, which means to query this function.
>
> Most SCPI commands are a mixture of upper and lower case letters. Capital letters indicate the abbreviations of commands, namely short commands. If you want better program readability, you can use long commands. E.g:
> `[:SOURce]:VOLTage[:SET]? CH1`
>
> Among them, the keyword VOLTage. You can enter VOLT or VOLTage, and combine upper and lower case letters at will. Therefore, VolTaGe, volt, and Volt are all acceptable. Other formats (such as VOL and VOLTAG) will produce errors.
> - Braces ({ }) enclose the parameter selection. The braces are not sent with the command string.
> - The vertical line (|) divides the parameter selection.
> - Angle brackets (< >) indicate that a value must be assigned to the parameter inside the bracket. The angle brackets are not sent with the command string.
> - Optional parameters are enclosed in square brackets ([ ]). If you do not specify a value for the optional parameter, the instrument will use the default value. For example, the [:SET] in the above command can be omitted (for example: 'VOLT? CH1'), and the command will operate on the current channel. The square brackets are not sent with the command string.

Summary of rules:
- Hierarchy separator `:`; keyword/parameter separator is a space; multiple parameters separated by `,`; query = trailing `?` appended to the command (before the parameter, e.g. `VOLT? CH1`).
- Long form = full mixed-case keyword (`VOLTage`); short form = the capital letters (`VOLT`). Matching is case-insensitive. Only the exact long or exact short form is valid; partial forms (`VOL`, `VOLTAG`) are errors.
- `{a | b}` choice; `<x>` required value; `[x]` optional (not sent). Leading `[:SOURce]` and `[:SET]`/`[:STATe]` style nodes are optional in the syntax.
- Channel notation: `(CHn)` in syntax lines, and in all examples written as `CH1`...`CH4` (e.g. `CH1,3`). The channel is the first parameter, followed by a comma and then the value (e.g. `:SOURce:VOLTage:SET CH1,3`).
- Value parameters generally accept `{<value> | MINimum | MAXimum | DEFault}` where printed.
- Boolean parameters are printed as `{OFF | ON | 0 | 1}` (ordering varies per command, see each).
- Responses in the manual are terminated with `\n` (shown in the response column), numbers are printed in the response examples with 6 decimals (voltage/current/power) or 3 decimals (list data).

⚠ manual note: The grammar section never explains the parentheses in `(CHn)`; they are not sent (all examples are `CH1`, not `(CH1)`). Whether `(CHn)` is optional is not stated explicitly; the "[:SET] ... VOLT? CH1 ... will operate on the current channel" sentence is confusing since a channel is given in that example.
⚠ manual note: Some examples omit the leading colon/`[:SOURce]` and some include it (`:SOURce:VOLTage:SET CH1,3` vs `OUTPut CH1,1`). Both are shown in the manual. Not stated whether a leading `:` is required.
⚠ manual note: The manual states `*` common commands without grammar discussion; terminator character(s) for commands sent to the instrument are not specified (see Open Questions).
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): forms, terminator and chaining (docs/hardware_findings.md Q1, Q7, Q8). Commands end in LF (CRLF also accepted); every reply ends in a single LF. The leading `:`, `SOURce:`/`SOUR:`, `:SET`, `:STATe` and `[:RUN]` are optional, long and short keywords in any case work (`ch1` too), and the channel argument is honoured in every form. A space before the comma (`CH1 ,1.9`), after it (`CH1, 1`) or no space before the channel (`VOLTage?CH1`) all work. Rejected (no reply): `VOL`, `VOLTAG`, literal brackets (`VOLTage[:SET]?`), `MEAS:POW?` (`POWER` has no short form), `OUTP:TRAC?` (`TRACK` has no short form), channels `CH0`, `CH5`, `1`, `(CH1)`. `VOLTage?` without a channel answers CH1's value; `OUTPut:TRACK? CH1` (an argument on a channel-less query) gets no reply. `;` chains work for writes and queries, but the replies of several queries are concatenated with no separator (`*IDN?;*OPC?` -> `...4.1.2.9R11`). An invalid query is never answered (the caller times out); there is no error reply.

---

## 3. Command summary (section 10.3 and the command index of 10.4)

Manual 10.3 lists only the subsystems:
1. IEEE Common Command Subsystem
2. SOURCE Command Subsystem
3. WAVE Subsystem
4. SYSTEM Subsystem
5. STORAGE Subsystem
6. CALIBRATE Subsystem
7. MEASURE Subsystem

Full command list as printed in the detail sections (10.4), in manual order. (There is no separate full command table in 10.3; this index is compiled from 10.4 and every item listed is also documented in detail below.)

| # | Subsystem | Command (as printed) | Forms |
|---|-----------|----------------------|-------|
| 1 | IEEE | `*IDN?` | query |
| 2 | IEEE | `*RST` | set |
| 3 | IEEE | `*CLS` | set |
| 4 | IEEE | `*ESE <number>` / `*ESE?` | set, query |
| 5 | IEEE | `*ESR?` | query |
| 6 | IEEE | `*OPC` / `*OPC?` | set, query |
| 7 | IEEE | `*SRE <number>` / `*SRE?` | set, query |
| 8 | IEEE | `*STB?` | query |
| 9 | IEEE | `*TST?` | query |
| 10 | IEEE | `*WAI` | set |
| 11 | SOURCE | `[:SOURce]:VOLTage[:SET]` | set, query |
| 12 | SOURCE | `[:SOURce]:OVP` | set, query |
| 13 | SOURCE | `[:SOURce]:OVP:PROTect:STATe?` | query |
| 14 | SOURCE | `[:SOURce]:CURRent[:SET]` | set, query |
| 15 | SOURCE | `[:SOURce]:OCP` | set, query |
| 16 | SOURCE | `[:SOURce]:OCP:PROTect:STATe?` | query |
| 17 | SOURCE | `[:SOURce]:OCP:DELay` | set, query |
| 18 | SOURCE | `[:SOURce]:OCP:STATe` | set, query |
| 19 | SOURCE | `[:SOURce]:OUTPut[:STATe]` | set, query |
| 20 | SOURCE | `[:SOURce]:OUTPut:ALL[:STATe]` | set, query |
| 21 | SOURCE | `[:SOURce]:OUTPut:ON:DELay` | set, query |
| 22 | SOURCE | `[:SOURce]:OUTPut:OFF:DELay` | set, query |
| 23 | SOURCE | `[:SOURce]:OUTPut:TRACK` | set, query |
| 24 | SOURCE | `[:SOURce]:MODE` | set, query |
| 25 | SOURCE | `[:SOURce]:LIST:VOLTage` | set, query |
| 26 | SOURCE | `[:SOURce]:LIST:CURRent` | set, query |
| 27 | SOURCE | `[:SOURce]:LIST:TIME` | set, query |
| 28 | SOURCE | `[:SOURce]:LIST:CLEar` | set |
| 29 | SOURCE | `[:SOURce]:LIST:CYCLes[:COUNt]` | set, query |
| 30 | SOURCE | `[:SOURce]:LIST:CONTinuous[:State]` | set, query |
| 31 | SOURCE | `[:SOURce]:LIST:RUN[:State]` | set, query |
| 32 | SOURCE | `[:SOURce]:LIST:RUN:ALL[:State]` | set |
| 33 | SOURCE | `[:SOURce]:LIST:WAIT[:STATe]` | set, query |
| 34 | SOURCE | `[:SOURce]:LIST:COUP[:STATe]` | set, query |
| 35 | SOURCE | `[:SOURce]:LIST:INFOrmation[:State]?` | query |
| 36 | SOURCE | `[:SOURce]:LOCK[:STATe]` | set, query |
| 37 | SOURCE | `[:SOURce]:RESET:PROTect` | set |
| 38 | WAVE | `WAVE:DRAW[:STATe]` | set, query |
| 39 | WAVE | `WAVE:DRAW:ALL[:STATe]` | set |
| 40 | WAVE | `WAVE:SAVE:TIME` | set, query |
| 41 | WAVE | `WAVE:SAMPle[:PERIod]` | set, query |
| 42 | WAVE | `WAVE:SAVE:STATe` | set, query |
| 43 | SYSTEM | `[:SYStem]:SOUNd:KEY` | set, query |
| 44 | SYSTEM | `[:SYStem]:SOUNd:ALARm` | set, query |
| 45 | SYSTEM | `[:SYStem]:LAN:LINK?` | query |
| 46 | SYSTEM | `[:SYStem]:DHCP` | set, query |
| 47 | SYSTEM | `[:SYStem]:LAN:IPADdress` | set, query |
| 48 | SYSTEM | `[:SYStem]:LAN:SMASk` | set, query |
| 49 | SYSTEM | `[:SYStem]:LAN:GATeway` | set, query |
| 50 | SYSTEM | `[:SYStem]:LAN:MAC?` | query |
| 51 | SYSTEM | `[:SYStem]:GPIB:ADDRess` | set, query |
| 52 | SYSTEM | `[:SYStem]:FACTory:RESET` | set |
| 53 | SYSTEM | `[:SYStem]:DEFAult:RESET` | set |
| 54 | STORAGE | `[:STORage]:UNIVersal:FILE:STATe?` | query |
| 55 | STORAGE | `[:STORage]:UNIVersal:FILE:RECAll` | set |
| 56 | STORAGE | `[:STORage]:UNIVersal:FILE:SAVE` | set |
| 57 | STORAGE | `[:STORage]:UNIVersal:FILE:DELEte` | set |
| 58 | STORAGE | `[:STORage]:LIST:FILE:STATe?` | query |
| 59 | STORAGE | `[:STORage]:LIST:FILE:RECAll` | set |
| 60 | STORAGE | `[:STORage]:LIST:FILE:SAVE` | set |
| 61 | STORAGE | `[:STORage]:LIST:FILE:DELEte` | set |
| 62 | CALIBRATE | `CALibrate:SOURce:SET` | set, query |
| 63 | MEASURE | `MEASure:VOLTage?` | query |
| 64 | MEASURE | `MEASure:CURRent?` | query |
| 65 | MEASURE | `MEASure:POWER?` | query |
| 66 | MEASURE | `MEASure[:RUN]:MODE?` | query |

Counts: 13 IEEE entries as numbered in the manual (the manual numbers `*ESE`/`*ESE?`, `*OPC`/`*OPC?`, `*SRE`/`*SRE?` separately; table above merges set/query pairs). Manual numbered entries: IEEE 13, SOURCE 27, WAVE 5, SYSTEM 11, STORAGE 8, CALIBRATE 2, MEASURE 4 = 70 numbered entries. Distinct command-form lines (set and query counted separately) = 102.

Not present anywhere in the manual: no `:STATus` subsystem, no `SYSTem:ERRor?`, no `SYSTem:VERSion?`, no `*SAV`/`*RCL`, no `*TRG`, no `INSTrument:SELect`, no `SYSTem:REMote/LOCal`, no commands for calibration procedure, 4W sense other than `MODE`, or screenshots.

---

## 4. Value ranges and units that are stated outside chapter 10

Chapter 10 itself gives **no** numeric ranges or units for any parameter. The following are taken from the front-panel chapters and are the only range information in the manual (treat applicability to SCPI as an inference to verify on hardware):

| Quantity | Statement (source section) |
|----------|---------------------------|
| Voltage, current resolution | "minimum resolution can be set to 1mV/1mA" (4.1); "5-digit voltage and current display" (4.2) |
| OVP value | "OV Protection: Set the OVP value, 0.1~1.1 times rated voltage can be set" (7.2) |
| OCP value | "OC Protection: Set the OCP value, 0.1~1.1 times rated current can be set" (7.2) |
| OCP delay | "OCP Delay: ... 0-3600s can be set with a resolution of 0.01s. The output will be turned off when OCP is still triggered after exceeding the OCP delay start time. If the delay start time is set to 0, the output will be turned off directly when OCP is triggered" (7.2) |
| Output ON delay / OFF delay | "0-3600s can be set with a resolution of 0.01s" (7.2) |
| List repeat count | "Repeat Court: The maximum is 9999" (7.2, 8.3) |
| Waveform duration | "The maximum value is 999h 59m 59s" (7.2, 8.4) |
| Waveform sample period | "The minimum value is 200ms, and the maximum is 6000ms" (7.2, 8.4) |
| Save/recall slots | "Eight group setups can be saved in memory" - Universal file1 ~ Universal file8, List file1 ~ List file8 (9.4, 9.4.1, 9.4.2) |
| Fast output response | "< 50us" (4.2) |
| Remote sense compensation | "maximum compensation voltage is 0.6V" (4.2) |
| Output terminal withstand to ground | "±240VDC" (8.2.2) |

Defaults after "Default Settings" (9.3.1) (what `DEFAult:RESET` presumably relates to; manual does not tie them together explicitly):
- Set CH2/CH3 as independent mode
- Turn off the 4W Sense mode of CH2/CH3
- Waveform display draws all channel voltage/current waveforms, waveform duration 0h 0min 30s, waveform sample period 200ms
- Key sound and alarm sound on
- List coupling state: all channels closed
- Voltage/current values of all channels set to 0
- OVP and OCP set to maximum values
- OCP state off and OCP delay 0
- On/off delays 0
- Calibration source: factory calibration data
- List voltage/current/time cleared to 0, repeat count 1, continuous state closed

Factory settings (9.3.2) additionally: "Set DHCP to on", "Set IP, Subnet Mask, Gateway, GBIP Address to 0".

---

## 5. Command descriptions (section 10.4)

Note on the `(CHn)` placeholder: examples use `CH1`..`CH4` (CH2/CH3 only for `MODE`). Parentheses are not sent.

### 5.1 IEEE Common Command Subsystem (10.4.1)

**1. `*IDN?`**
- Syntax: `*IDN?` (query only)
- Description: "Query the manufacturer, device model, device serial port number, software version number"
- Example: `*IDN?`
- Response: `Siglent\sTechnologies,SPD4306X,0123456789,4.1.2.4\n`
- ⚠ manual note: `\s` is the manual's notation, presumably a space ("Siglent Technologies"). "serial port number" is the manual's wording for serial number. The response example is for an SPD4306X; model strings for others not shown.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): `Siglent Technologies,SPD4323X,<serial>,4.1.2.9R1`: the `\s` is a plain space, 4 comma-separated fields, and the firmware field is not purely numeric (`R1` suffix) (Q4).

**2. `*RST`**
- Syntax: `*RST`
- Description: "Restore the state of the device to the initial state"
- Example: `*RST`
- ⚠ manual note: Does not define what "initial state" is (compare 9.3.1 Default Settings).
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): not sent by any tool or the plug (Q18).

**3. `*CLS`**
- Syntax: `*CLS`
- Description: "Clear the values of all event registers and clear the error list at the same time"
- Example: `*CLS`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): clears the event status register (`*ESR?` reads 0 afterwards) (Q6).

**4. `*ESE`**
- Syntax: `*ESE <number>`
- Description: "Set the enable value of the standard event status register"
- Example: `*ESE 16`

**5. `*ESE?`**
- Syntax: `*ESE?`
- Description: "Query the enable value of the standard event status register"
- Example: `*ESE?`
- Response: `64`
- ⚠ manual note: Response example (64) is not consistent with the preceding example (`*ESE 16`) - they are independent examples. No terminator printed on this response (others show `\n`).
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): answers `0`, LF-terminated (Q4).

**6. `*ESR?`**
- Syntax: `*ESR?`
- Description: "Query and clear the event value of the standard event status register"
- Example: `*ESR?`
- Response: `0`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): answers `0` normally; `32` (bit 5, command error) after unknown headers or unanswered queries, but not reliably (the same unknown query set it after `*CLS` and not after a plain `*ESR?`); clears on read; stays `0` after an invalid channel in a write, a non-numeric value or a clamped out-of-range value. Not a dependable error channel (Q6).

**7. `*OPC`**
- Syntax: `*OPC`
- Description: "Operation complete"
- Example: `*OPC`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): sets bit 0 of `*ESR?` (`*ESR?` -> `1` right after) (Q6, Q11).

**8. `*OPC?`**
- Syntax: `*OPC?`
- Description: "Query whether the current operation is complete"
- Example: `*OPC?`
- Response: `1`
- (So `*OPC?` IS documented.)
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): answers `1`; right after a write it is held for the same ~220 ms as any other query, so it adds nothing over a read-back (Q11).

**9. `*SRE`**
- Syntax: `*SRE <number>`
- Description: "Set the enable value of the status byte register"
- Example: `*SRE 24`

**10. `*SRE?`**
- Syntax: `*SRE?`
- Description: "Query the enable value of the status byte register"
- Example: `*SRE?`
- Response: `24`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): answers `0` (Q4).

**11. `*STB?`**
- Syntax: `*STB?`
- Description: "Query the event value of the status byte register"
- Example: `*STB?`
- Response: `72`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): answered `0` throughout, also when `*ESR?` showed 32 (Q6).

**12. `*TST?`**
- Syntax: `*TST?`
- Description: "Query the result of instrument self-test"
- Example: `*TST?`
- Response: `0`
- ⚠ manual note: Meaning of 0 (pass?) not stated.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): not sent (Q6).

**13. `*WAI`**
- Syntax: `*WAI`
- Description: "Wait for all outstanding operations to complete before executing any other commands"
- Example: `*WAI`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): accepted, no visible effect (Q11).

---

### 5.2 SOURCE Command Subsystem (10.4.2)

**1. Set voltage value**
- Set: `[:SOURce]:VOLTage[:SET] (CHn),{<value> | MINimum | MAXimum |DEFault}`
- Description: "Set the voltage value of the selected channel"
- Example: `:SOURce:VOLTage:SET CH1,3` - "Set the voltage value of CH1 to 3V"
- Query: `[:SOURce]:VOLTage[:SET]? (CHn)` - "Get the voltage value of the selected channel"
- Query example: `:SOURce:VOLTage:SET? CH1`
- Response: `3.000000\n`
- Units: volts (from example text "3V"). Range/default: not stated in chapter 10.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): `VOLTage CH1,1.2345` reads back `1.234500` (stored with 4 decimals, no rounding to 1 mV); values are 32-bit floats. Out-of-range values are clamped silently and never reported: `7.5` -> `6.060000` (1.01 x the 6 V rating), `-1` -> `0.000000`. `MINimum`/`MAXimum`/`DEFault` set `0.000000` / `6.060000` / `0.000000`. As query arguments `VOLTage? CH1,MAX` -> `6.060000`, also `MAXimum`, `MIN`, `DEF`, `DEFault`, with or without a space after the comma; `MAX` is per channel and ignores the track mode (32.320000 for CH2/CH3). The plug sends `:SOURce:VOLTage:SET? CHn,MAXimum` (`max_voltage()`). In SERIES `VOLTage? CH2` answers the combined voltage (`28.000000` with 14 V per half). What a write to CH2/CH3 means in a coupled mode is untested (Q9, Q14, Q21).

**2. Set OVP value**
- Set: `[:SOURce]:OVP (CHn),{<value> | MINimum | MAXimum |DEFault}`
- Description: "Set the OVP value of the selected channel"
- Example: `:SOURce:OVP CH1,8` - "Set the OVP value of CH1 to 8V"
- Query: `[:SOURce]:OVP? (CHn)` - "Get the OVP value of the selected channel"
- Query example: `:SOURce:OVP? CH1`
- Response: `15.000000\n`
- Units: volts. (Response 15 V is the CH1 rated voltage of SPD4306X/SPD4121X.)
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): default and `MAXimum` are 1.1 x the rating (`OVP? CH1` -> `6.600000`, `OVP? CH2` -> `35.200001` because values are float32); the range is 0.1 x .. 1.1 x the rating and out-of-range values are clamped silently (`OVP CH1,7.2` -> `6.600000`, `0.3` -> `0.600000`); `MINimum` -> `0.600000`. No mutual limiting with the voltage setpoint while the output is off. Not rescaled by SERIES/PARALLEL. Keywords as query arguments (`OVP? CH1,MAX`) get no reply (Q9, Q10, Q14).

**3. Get whether the channel triggers overvoltage protection**
- Query: `[:SOURce]:OVP:PROTect:STATe? (CHn)`
- Description: "Get whether the channel triggers overvoltage protection"
- Example: `:SOURce:OVP:PROTect:STATe? CH1`
- Response: `0\n`
- ⚠ manual note: Meaning of 0/1 not explicitly stated (0 presumably = not tripped). Query only; no OVP enable/disable command exists in the manual (OVP has no switch, unlike OCP).
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): answers `0` with nothing tripped; `1` = tripped has never been observed (Q10, still open).

**4. Set current value**
- Set: `[:SOURce]:CURRent[:SET] (CHn),{<value> | MINimum | MAXimum |DEFault}`
- Description: "Set the current value of the selected channel"
- Example: `:SOURce:CURRent:SET CH1,2` - "Set the current value of CH1 to 2A"
- Query: `[:SOURce]:CURRent[:SET]? (CHn)` - "Get the set current value of the selected channel"
- Query example: `:SOURce:CURRent:SET? CH1`
- Response: `2.000000\n`
- Units: amperes.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): `CURRent CH1,0.1234` reads back `0.123400`; clamped silently to 1.01 x the rating (`4` -> `3.232000`) and to 0 (`-0.1` -> `0.000000`); `MINimum`/`MAXimum`/`DEFault` -> `0.000000` / `3.232000` / `0.000000`; `CURRent? CH1,MAX` -> `3.232000`. The plug sends `:SOURce:CURRent:SET? CHn,MAXimum` (`max_current()`). In PARALLEL `CURRent? CH2` answers the combined current (`6.000000` with 3 A per half) (Q9, Q14, Q21).

**5. Set OCP value**
- Set: `[:SOURce]:OCP (CHn),{<value> | MINimum | MAXimum |DEFault}`
- Description: "Set the OCP value of the selected channel"
- Example: `:SOURce:OCP CH1,8` - "Set the OCP value of CH1 to 8A"
- Query: `[:SOURce]:OCP? (CHn)` - "Get the OCP value of the selected channel"
- Query example: `:SOURce:OCP? CH1`
- Response: (none printed in the manual)
- ⚠ manual note: No response example is given for this query. Example `OCP CH1,8` (8 A) exceeds the 1.5 A CH1 rating of SPD4306X/4121X (and 3.2 A of SPD4323X); the panel text says OCP can be set 0.1~1.1 times rated current - the example value is illustrative only / would be out of range.
- ⚠ manual note: Likewise the OVP example (`CH1,8`, 8 V) on a 6 V CH1 (SPD4323X) would exceed 1.1 x 6 V.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): `OCP? CHn` answers a plain number like `OVP?` (`3.520000` = 1.1 x 3.2 A, also the default and `MAXimum`); range 0.1 x .. 1.1 x the rating, clamped silently (`3.84` -> `3.520000`, `0.16` -> `0.320000`); `MINimum` -> `0.320000`; keywords as query arguments get no reply (Q5, Q9, Q14).

**6. Get whether the channel triggers overcurrent protection**
- Query: `[:SOURce]:OCP:PROTect:STATe? (CHn)`
- Description: "Get whether the channel triggers overcurrent protection"
- Example: `:SOURce:OCP:PROTect:STATe? CH1`
- Response: `0\n`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): answers `0` with nothing tripped; `1` = tripped has never been observed (Q10, still open).

**7. Set OCP delay value**
- Set: `[:SOURce]:OCP:DELay (CHn),{<value> | MINimum | MAXimum |DEFault}`
- Description: "Set the delay value for OCP triggering of the selected channel"
- Example: `OCP:DELay CH1,1` - "Set the delay value for OCP triggering of the CH1 to 1s"
- Query: `[:SOURce]:OCP:DELay? (CHn)` - "Get the delay value for OCP triggering of the selected channel"
- Query example: `OCP:DELay? CH1`
- Response: `0.000000\n`
- Units: seconds.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): range 0..3600 s, out-of-range values clamped silently (`3601` -> `3600.000000`, `-1` -> `0.000000`), no rounding to 0.01 s (`1.2345` reads back `1.234500`); `MAXimum`/`MINimum`/`DEFault` -> `3600.000000` / `0.000000` / `0.000000`; keywords as query arguments get no reply (Q9).

**8. Set OCP switch state**
- Set: `[:SOURce]:OCP:STATe (CHn),{ON | OFF | 0 | 1}`
- Description: "Set the OCP switch state of the selected channel"
- Example: `:SOURce:OCP:STATe CH1, 1` - "Set the OCP switch state of CH1 to ON"
- Query: `[:SOURce]:OCP:STATe? (CHn)` - "Get the OCP switch state of the selected channel"
- Query example: `:SOURce:OCP:STATe? CH1`
- Response: `1\n`
- Panel (8.1.2): "The instrument will not trigger the overcurrent protection when the OCP is in OFF state."
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): the manual example with a space after the comma (`OCP:STATe CH1, 1`) is accepted, and so is the form without the space (Q7).

**9. Set output state of the channel**
- Set: `[:SOURce]:OUTPut[:STATe] (CHn),{OFF | ON | 0 | 1}`
- Description: "Set output state of the selected channel (OFF | ON | 0 | 1 )"
- Example: `OUTPut CH1,1` - "Turn on the output of CH 1"
- Query: `[:SOURce]:OUTPut[:STATe]? (CHn)` - "Get the output state of the selected channel"
- Query example: `OUTPut? CH1`
- Response: `0\n`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): `OUTPut? CHn` answers `0` with the output off. No `OUTPut CHn,<x>` write was sent in run 1 (Q4, experiment 30 pending).

**10. Set output state of all channels**
- Set: `[:SOURce]:OUTPut:ALL[:STATe] {OFF | ON | 0 | 1}`
- Description: "Set output state of all channels (OFF | ON | 0 | 1 )"
- Example: `OUTPut:ALL 1` - "Turn on the output of all channels"
- Query: `[:SOURce]:OUTPut:ALL[:STATe]?`
- Description: "Get the output state of all channels"
- Query example: `OUTPut:ALL?`
- Response: `0\n`
- ⚠ manual note: Format of the all-channel query response (single 0/1 vs per-channel) when channels differ is not documented.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): `OUTPut:ALL?` answers `0` with all outputs off; the format with mixed channel states is still unknown. No `OUTPut:ALL <x>` write was sent in run 1.

**11. Set output ON delay value of the channel**
- Set: `[:SOURce]: OUTPut:ON:DELay (CHn) ,{<value> | MINimum | MAXimum |DEFault}` (printed with a space after `[:SOURce]:` and before the comma)
- Description: "Set output ON delay value of the selected channel"
- Example: `OUTPut:ON:DELay CH1,3` - "Set output ON delay value of CH 1 to 3s"
- Query: `[:SOURce]:OUTPut:ON:DELay? (CHn)` - "Get output ON delay value of the selected channel"
- Query example: `OUTPut:ON:DELay? CH1`
- Response: `0.000000\n`
- Units: seconds.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): only the query was exercised: `OUTPut:ON:DELay? CHn` answers a 6-decimal number; keywords as query arguments get no reply. The write was not exercised (Q9).

**12. Set output OFF delay value of the channel**
- Set: `[:SOURce]:OUTPut:OFF:DELay (CHn),{<value> | MINimum | MAXimum |DEFault}`
- Description: "Set output OFF delay value of the selected channel"
- Example: `OUTPut:OFF:DELay CH1,1` - "Set output OFF delay value of CH 1 to 1s"
- Query: `[:SOURce]:OUTPut:OFF:DELay? (CHn)` - "Get output OFF delay value of the selected channel"
- Query example: `OUTPut:OFF:DELay? CH1`
- Response: `3.000000\n`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): only the query was exercised, as for the ON delay. The write and the semantics during a pending delay (Q22) were not exercised.

**13. Set series/parallel mode**
- Set: `[:SOURce]:OUTPut:TRACK <value>` with `<value>：= {0|1|2| INDEPENDENT| SERIES| PARALLEL}`
- Description: "Set the output mode of CH2/3"
- Example: `OUTPut:TRACK 0` - "Set the output mode of CH2/3 to independent mode"
- Query: `[:SOURce]:OUTPut:TRACK?` - "Query the selected output mode of CH2/3"
- Query example: `OUTPut:TRACK?`
- Response: `0\n`
- ⚠ manual note: The only explicit mapping is 0 = independent (from the example). That 1 = series and 2 = parallel is inferred only from list order `{0|1|2| INDEPENDENT| SERIES| PARALLEL}` and is NOT stated. Whether the query returns a number or word is only shown as `0\n`. Takes no channel argument.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): the query always answers the number: `0` independent, `1` series, `2` parallel; the words and the numbers are accepted in the set command. `OUTPut:TRACK? CH1` gets no reply, and `OUTP:TRAC?` is not accepted (`TRACK` has no short form). Entering SERIES or PARALLEL copies CH2's voltage and current setpoints into CH3, and CH3 keeps them after returning to INDEPENDENT (CH3 12 V / 2 A became 14 V / 3 A). OVP/OCP are unchanged. Rejection while an output is on was not tested (Q13).

**14. Set working mode**
- Set: `[:SOURce]:MODE {CH2|CH3},{0 | 1| 2W| 4W}`
- Description: "Set the working mode of the selected channel"
- Example: `MODE CH2,2W` - "Set the working mode of the CH 2 to 2W"
- Query: `[:SOURce]:MODE? {CH2|CH3}` - "Query the working mode of the selected channel"
- Query example: `MODE? CH2`
- Response: `0\n`
- ⚠ manual note: Mapping of 0/1 to 2W/4W is not stated (do not assume). Only CH2 and CH3 are valid. Panel chapter 8.5: 4W sense only for CH2/CH3 and "not supported in series or parallel mode". Query returns a number even after setting via word, per the one printed example.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): `MODE CH2,<x>` accepts `2W`/`4W` and `0`/`1`; the query answers the number, `0` = 2W, `1` = 4W. `MODE? CH3` answers `0` (not written). `MODE? CH1` also answers `0`, although the manual lists CH2/CH3 only; CH4 was not tried (Q8, Q13).

**15. Set list voltage**
- Set: `[:SOURce]:LIST:VOLTage (CHn),<value1>,<value2>,…,<valuen>`
- Description: "Set the voltage value of the first n steps of the selected channel"
- Example: `LIST:VOLT CH1,1,2,3,4,5` - "Set the voltage value for the first 5 steps of CH 1 to 1V, 2V, 3V, 4V, 5V"
- Query: `[:SOURce]:LIST:VOLTage? (CHn)` - "Query the voltage value of effective steps"
- Query example: `LIST:VOLT? CH1`
- Response: `LIST:VOLT\s1.000,2.000,3.000,4.000,5.000\n`
- ⚠ manual note: Query response is prefixed with the literal text `LIST:VOLT` followed by `\s` (space) and uses 3 decimals, unlike scalar queries (6 decimals). Maximum number of steps is not stated in chapter 10.

**16. Set list current**
- Set: `[:SOURce]:LIST:CURRent (CHn),<value1>,<value2>,…,<valuen>`
- Description: "Set the current value of the first n steps of the selected channel"
- Example: `LIST:CURR CH1,0.1,0.2,0.3,0.4,0.5` - "Set the current value for the first 5 steps of CH 1 to 0.1A, 0.2A, 0.3A, 0.4A, 0.5A"
- Query: `[:SOURce]:LIST:CURRent? (CHn)` - "Query the current value of effective steps"
- Query example: `LIST:CURR? CH1`
- Response: `LIST:CURR\s0.100,0.200,0.300,0.400,0.500\n`

**17. Set list running time**
- Set: `[:SOURce]:LIST:TIME (CHn),<value1>,<value2>,…,<valuen>`
- Description: "Set the running time of the first n steps of the selected channel"
- Example: `LIST: TIME CH1,1,2,3,4,5` - "Set the running time of the first 5 steps of the CH 1 to 1S, 2S, 3S, 4S, 5S"
- Query: `[:SOURce]:LIST:TIME? (CHn)` - "Query the running time of effective steps"
- Query example: `LIST:TIME? CH1`
- Response: `LIST:TIME\s1.000,2.000,3.000,4.000,5.000\n`
- ⚠ manual note: The set example is printed `LIST: TIME` with a space after the colon - evident typo (the query example is `LIST:TIME?`).

**18. Clear all step data**
- Set: `[:SOURce]:LIST:CLEar (CHn)`
- Description: "Clear all step data of the list for the channel"
- Example: `LIST:CLEar CH1` - "Clear all step data of the CH 1"
- No query form.

**19. Set the number of cycles**
- Set: `[:SOURce]:LIST:CYCLes [:COUNt] (CHn),{<value> | MINimum | MAXimum |DEFault}` (printed with a space before `[:COUNt]`)
- Description: "Set the number of cycles"
- Example: `LIST:CYCLes CH1,1` - "Set the number of cycles of the list for CH 1 to 1"
- Query: `[:SOURce]:LIST:CYCLes[:COUNt]? (CHn)` - "Get the numeber of the list for the channel" (sic)
- Query example: `LIST:CYCLes? CH1`
- Response: `1\n`
- Range: panel says max repeat count 9999.

**20. Set the continuous state of list**
- Set: `[:SOURce]:LIST:CONTinuous[:State] (CHn),{OFF | ON | 0 | 1}`
- Description: "Set the continuous state of the list for the channel"
- Example: `LIST:CONTinuous CH1,1` - "Set the continuous state of the list for CH 1 to ON"
- Query: `[:SOURce]:LIST:CONTinuous[:State]? (CHn)` - "Get the continuous state of the list for the channel"
- Query example: `LIST:CONTinuous? CH1`
- Response: `0\n`

**21. Set the running state of the list for a channel**
- Set: `[:SOURce]:LIST:RUN[:State] (CHn),{OFF | ON | 0 | 1}`
- Description: "Set the running state of the list for the channel"
- Example: `LIST:RUN CH1,1` - "Set the running state of the list for CH 1 to ON"
- Query: `[:SOURce]:LIST:RUN[:State]? (CHn)` - "Get the running state of the list for the channel"
- Query example: `LIST:RUN? CH1`
- Response: `0\n`

**22. Set the running state of the list for all channels**
- Set: `[:SOURce]:LIST:RUN:ALL[:State] {OFF | ON | 0 | 1}`
- Description: "Set the running state of the list for all channels"
- Example: `LIST:RUN:ALL 1` - "Set the running state of the list for all channels to ON"
- No query form.

**23. Set the wait state of the list for a channel**
- Set: `[:SOURce]:LIST:WAIT[:STATe] (CHn),{OFF | ON | 0 | 1}`
- Description: "Set the wait state of the list for the channel"
- Example: `:SOURce:LIST:WAIT:STATe CH1,1` - "Set the wait state of the list for CH 1 to OFF"
- Query: `[:SOURce]:LIST:WAIT[:STATe]? (CHn)` - "Get the wait state of the list for the channel"
- Query example: `:SOURce:LIST:WAIT:STATe? CH1`
- Response: `0\n`
- ⚠ manual note: The example sets `1` but the description says "to OFF" - contradictory (1 normally = ON). "Wait state" is not otherwise defined (panel has a "Pause" function, 8.3, but the mapping is not stated).

**24. Set coupling state of the list for a channel**
- Set: `[:SOURce]:LIST:COUP[:STATe] (CHn),{OFF | ON | 0 | 1}`
- Description: "Set the coupling state of the list for the channel"
- Example: `:SOURce:LIST:COUP:STATe CH1,1` - "Set the coupling state of the list for CH 1 to ON"
- Query: `[:SOURce]:LIST:COUP[:STATe]? (CHn)` - "Get the coupling state of the list for the channel"
- Query example: `:SOURce:LIST:COUP:STATe? CH1`
- Response: `0\n`
- Panel (7.2, Configure "Coupling"): "In the coupling mode, the ON button of the channels and Run/Stopped in the list interface are in synchronous mode. The channels that finish running first in list are set to zero, and the other coupling channels are in the Stopped state after the list is finished running".
- ⚠ manual note: `COUP` is printed all upper-case, so the short form and long form are indistinguishable from the print (`COUPling` is not shown).

**25. Query the running state information of the list for a channel**
- Query: `[:SOURce]:LIST:INFOrmation[:State]? (CHn)`
- Description: "Get the running state information of the list for a channel, include the number of steps currently running, the running state, the wait state, the time that the current step has run, the remaining time of the current step, the number of cycles completed, and whether all cycles have been completed"
- Example: `LIST:INFO? CH1`
- Response: `step:1,run_state:0,wait_state:0,run_time:0.000,remain_time:0.000,completed_cycles:0,completed_state:0\n` (printed across two lines in the manual: `step:1,run_state:0,wait_state:0,run_time:0.000,remain_time:0.000,` / `completed_cycles:0,completed_state:0\n`)
- ⚠ manual note: Value meanings (run_state, wait_state, completed_state) not defined. The line break in the printed response is a layout break, not a separator.

**26. Set lock state of the device**
- Set: `[:SOURce]:LOCK[:STATe] { OFF | ON | 0 | 1}`
- Description: "Set the lock state of the device"
- Example: `:SOURce:LOCK:STATe ON` - "Set the lock state of the device to ON"
- Query: `[:SOURce]:LOCK[:STATe]?` - "Get the lock state of the device"
- Query example: `:SOURce:LOCK:STATe?`
- Response: `0\n`
- Note: panel chapter says the device is automatically locked when remotely controlled.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): any remote write sets `LOCK` to 1 (queries never do); `LOCK 0` unlocks and the `LOCK` write itself does not re-lock; `LOCK ON|OFF|1|0` and `:SOURce:LOCK:STATe 1` all work; remote writes still work while locked. `LOCK?` is the slowest query (up to 369 ms). Whether the panel is visibly unlocked was not reported (Q12).

**27. Clear the circuit protection status of the channel (overvoltage /overcurrent status)**
- Set: `[:SOURce]:RESET:PROTect (CHn)`
- Description: "Clear the circuit protection status of the channel(overvoltage /overcurrent status)"
- Example: `:SOURce:RESET:PROTect CH1` - "Clear the circuit protection status of CH1(overvoltage /overcurrent status)"
- No query form (use the `OVP:PROTect:STATe?` / `OCP:PROTect:STATe?` queries to read status).
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): not exercised in run 1 (no trip was provoked) (Q10).

---

### 5.3 WAVE Subsystem (10.4.3)

**1. Set waveform drawing state for a channel**
- Set: `WAVE:DRAW[:STATe] (CHn),{VOLT | CURR },{ OFF | ON | 0 | 1}`
- Description: "Set the channel waveform drawing state"
- Example: `WAVE:DRAW[:STATe] CH1,VOLT,1` - "Set the CH 1 voltage waveform drawing state to ON"
- Query: `WAVE:DRAW[:STATe]? (CHn),{VOLT | CURR }` - "Get the channel waveform drawing state"
- Query example: `WAVE:DRAW? CH1,VOLT`
- Response: `1\n`
- ⚠ manual note: The set example literally contains the optional-node brackets `[:STATe]`; these are not sent (per 10.2), so the valid form would be `WAVE:DRAW CH1,VOLT,1` or `WAVE:DRAW:STATe CH1,VOLT,1`. The query example `WAVE:DRAW? CH1,VOLT` omits `:STATe`.

**2. Set waveform drawing state for all channels**
- Set: `WAVE:DRAW:ALL[:STATe] {ON | OFF | 0 | 1}`
- Description: "Set the waveform drawing state for all channels"
- Example: `WAVE:DRAW:ALL[:STATe]` - "Set the voltage waveform drawing state for all channels to ON"
- No query form.
- ⚠ manual note: The example has no parameter and contains literal brackets; description says "voltage waveform" although the syntax has no VOLT/CURR selector, and says ON although no value is given. Behavior (voltage only? both?) unverified.

**3. Set waveform saving time**
- Set: `WAVE:SAVE:TIME <value>,<value>,<value>`
- Description: "Set waveform saving time"
- Example: `WAVE:SAVE:TIME 1,30,30` - "Set waveform saving time to 1 hour, 30 minutes and 30 seconds"
- Query: `WAVE:SAVE:TIME?` - "Query waveform saving time"
- Query example: `WAVE:SAVE:TIME?`
- Response: `0hours,0minutes,30seconds\n`
- ⚠ manual note: Parameter order inferred from the example as hours, minutes, seconds. Response format is textual (`0hours,0minutes,30seconds`), not the same as the set format. Panel maximum 999h 59m 59s.

**4. Set waveform sampling period**
- Set: `WAVE:SAMPle[:PERIod] <value>`
- Description: "Set waveform sampling period"
- Example: `WAVE:SAMPle 200` - "Set waveform sampling period to 200ms"
- Query: `WAVE:SAMPle[:PERIod]?` - "Query waveform sampling period"
- Query example: `WAVE:SAMPle[:PERIod]?` (literal brackets in the printed example)
- Response: `200\n`
- Units: milliseconds (from description). Panel range 200 ms - 6000 ms.

**5. Set waveform saving switch state**
- Set: `WAVE:SAVE:STATe {OFF | ON | 0 | 1}`
- Description: "Set the waveform saving switch state"
- Example: `WAVE:SAVE:STATe 1` - "Set to enable waveform saving"
- Query: `WAVE:SAVE:STATe?` - "Get e waveform saving switch state" (sic)
- Query example: `WAVE:SAVE:STATe?`
- Response: `1\n`
- Panel (7.2): "Run Stopped: Save the data to the U disk. The pop-up window prompts when data is successfully saved or no U disk insertion information is recognized."

---

### 5.4 SYSTEM Subsystem (10.4.4)

**1. Set key sound**
- Set: `[:SYStem]:SOUNd:KEY {OFF | ON | 0 | 1}`
- Description: "Set the key sound switch state"
- Example: `SOUNd:KEY 1` - "Set the key sound switch state to ON"
- Query: `[:SYStem]:SOUNd:KEY?` - "Get the key sound switch state"
- Query example: `SOUNd:KEY?`
- Response: `1\n`

**2. Set alarm sound**
- Set: `[:SYStem]:SOUNd:ALARm {OFF | ON | 0 | 1}`
- Description: "Set the alarm sound switch state"
- Example: `SOUNd:ALARm 1` - "Set the alarm sound switch state to ON"
- Query: `[:SYStem]:SOUNd:ALARm?` - "Get the alarm sound switch state"
- Query example: `SOUNd:ALARm?`
- Response: `1\n`

**3. Get link state of LAN**
- Query: `[:SYStem]:LAN:LINK?`
- Description: "Get link state of LAN"
- Example: `LAN:LINK?`
- Response: `1\n`

**4. Set DHCP**
- Set: `[:SYStem]:DHCP {OFF | ON | 0 | 1}`
- Description: "Set to obtain IP address dynamically or manually"
- Example: `DHCP 1` - "Set to obtain IP address dynamically"
- Query: `[:SYStem]:DHCP?` - "Get the switch state of DHCP"
- Query example: `DHCP?`
- Response: `1\n`

**5. Set IP address**
- Set: `[:SYStem]:LAN:IPADdress <value>`
- Description: "Set IP address"
- Example: `LAN:IPADdress 10.11.13.213`
- Query: `[:SYStem]:LAN:IPADdress?` - "Get IP address"
- Query example: `LAN:IPADdress?`
- Response: (none printed)
- ⚠ manual note: Quoting of the address argument not shown (example is unquoted).

**6. Set subnet mask**
- Set: `[:SYStem]:LAN:SMASk <value>`
- Description: "Set subnet mask"
- Example: `LAN:SMASk 255.255.255.0`
- Query: `[:SYStem]:LAN:SMASk?` - "Get subnet mask"
- Query example: `LAN:SMASk?`
- Response: (none printed)

**7. Set gateway**
- Set: `[:SYStem]:LAN:GATeway <value>`
- Description: "Set the gateway"
- Example: `LAN:GATeway 10.11.13.1`
- Query: `[:SYStem]:LAN:GATeway?` - "Get the gateway"
- Query example: `LAN:GATeway?`
- Response: (none printed)

**8. Get MAC address**
- Query: `[:SYStem]:LAN:MAC?`
- Description: "Get MAC address"
- Example: `LAN:MAC?`
- Response: (none printed)

**9. Set GPIB address**
- Set: `[:SYStem]:GPIB:ADDRess <value>`
- Description: "Set GPIB address"
- Example: `GPIB:ADDRess 3`
- Query: `[:SYStem]:GPIB:ADDRess?` - "Get GPIB address"
- Query example: `GPIB:ADDRess?`
- Response: (none printed)

**10. Restore factory settings**
- Set: `[:SYStem]:FACTory:RESET`
- Description: "Restore factory settings"
- Example: `FACTory:RESET`
- ⚠ manual note: Per 9.3.2 this also resets DHCP/IP/subnet/gateway/GPIB address (IP to 0, DHCP on) - would likely drop the LAN connection. Destructive; do not use in a test flow.

**11. Restore default data**
- Set: `[:SYStem]:DEFAult:RESET`
- Description: "Restore default data (Excluding LAN and GPIB settings)"
- Example: `DEFAult:RESET`
- See "Default Settings" list in section 4.

---

### 5.5 STORAGE Subsystem (10.4.5)

All eight commands are printed in the syntax line **without** a parameter, but every example passes a file serial number (`1`). The panel has 8 slots each (Universal file1~8, List file1~8).

**1. Get whether the specified universal data file is valid**
- Query: `[:STORage]:UNIVersal:FILE:STATe?`
- Description: "Get whether the specified universal data file is valid"
- Example: `:STORage:UNIVersal:FILE:STATe? 1`
- Response: `Exist\n`
- ⚠ manual note: Only the value `Exist` is shown; the response for a non-existent file is not documented.

**2. Recall the specified universal data file**
- Set: `[:STORage]:UNIVersal:FILE:RECAll`
- Description: "Recall the specified universal data file"
- Example: `:STORage:UNIVersal:FILE:RECAll 1` - "Recall the universal data file with serial number 1"

**3. Save the current universal data to the specified universal data file**
- Set: `[:STORage]:UNIVersal:FILE:SAVE`
- Description: "Save the current universal data to the specified universal data file"
- Example: `:STORage:UNIVersal:FILE:SAVE 1` - "Save the current universal data to the specified universal data file with serial number 1"

**4. Delete the specified universal data file**
- Set: `[:STORage]:UNIVersal:FILE:DELEte`
- Description: "Delete the specified universal data file"
- Example: `:STORage:UNIVersal:FILE:DELEte 1` - "Delete the specified universal data file with serial number 1"

**5. Get whether the specified list data file is valid**
- Query: `[:STORage]:LIST:FILE:STATe?`
- Description: "Get whether the specified list data file is valid"
- Example: `:STORage:LIST:FILE:STATe? 1`
- Response: `Exist\n`

**6. Recall the specified list data file**
- Set: `[:STORage]:LIST:FILE:RECAll`
- Description: "Recall the specified LIST data file"
- Example: `:STORage:LIST:FILE:RECAll 1` - "Recall the specified LIST data file with serial number 1"

**7. Save the current list data to the specified list data file**
- Set: `[:STORage]:LIST:FILE:SAVE`
- Description: "Save the current list data to the specified list data file"
- Example: `:STORage:LIST:FILE:SAVE 1` - "Save the current list data to the specified list data file with serial number 1"

**8. Delete the specified list data file**
- Set: `[:STORage]:LIST:FILE:DELEte`
- Description: "Delete the specified list data file"
- Example: `:STORage:LIST:FILE:DELEte 1` - "Delete the specified list data file with serial number 1"

Panel facts: universal setups contain "Independent/series/parallel mode" and "Output voltage/current value" (9.4). Internal vs external (U-disk) storage exist on the panel; the SCPI commands do not say which they use.

---

### 5.6 CALIBRATE Subsystem (10.4.6)

**1. Set calibration source**
- Set: `CALibrate:SOURce:SET {FACTORY | USER | 0 | 1}`
- Description: "Set calibration source"
- Example: `CALibrate:SOURce:SET FACTORY` - "Set the calibration source to the factory calibration source"

**2. Get calibration source**
- Query: `CALibrate:SOURce:SET?`
- Description: "Get calibration source"
- Example: `:SOURce:VOLTage:SET? CH1`
- Response: `0\n`
- ⚠ manual note: The query example is a copy-paste error (it is the voltage query, not a calibration query); the real query is the syntax line `CALibrate:SOURce:SET?`. Numeric mapping (0 = FACTORY? 1 = USER?) is not stated (set parameter order suggests it, but it is not explicit).
- No remote command exists for the calibration procedure (voltage/current calibration, save/clear calibration data are panel-only per 9.5).

---

### 5.7 MEASURE Subsystem (10.4.7)

**1. Get the measured voltage value**
- Query: `MEASure:VOLTage? (CHn)`
- Description: "Get the voltage measurement value of the selected channel"
- Example: `MEASure:VOLTage? CH1`
- Response: `2.991442\n`
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): with the output off the reading is a small offset, not zero (`MEASure:VOLTage? CH1` -> `0.000557`); the same value repeats within ~10 ms, so the refresh is slower than the query rate (Q4, Q11).

**2. Get the measured current value**
- Query: `MEASure:CURRent? (CHn)`
- Description: "Get the current measurement value of the selected channel"
- Example: `MEASure:CURRent? CH1`
- Response: `1.999407\n`

**3. Get the measured power value**
- Query: `MEASure:POWER? (CHn)`
- Description: "Get the measured power value of the selected channel"
- Example: `MEASure:POWER? CH1`
- Response: `19.959515\n`
- ⚠ manual note: `POWER` is printed fully upper-case (no short/long distinction visible; the short form is not given).
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): `MEASure:POWer? CH1` works, `MEAS:POW? CH1` gets no reply (Q7).

**4. Get the running state of the channel**
- Query: `MEASure[:RUN]:MODE? (CHn)`
- Description: "Get the running status of the selected channel"
- Example: `MEASure:RUN:MODE? CH1`
- Response: `CV\n`
- ⚠ manual note: Only `CV` is shown. Panel (8.2.2) describes CV and CC modes; other possible return values (e.g. `CC`, off/idle state) are not documented. `MODE` here is under `MEASure[:RUN]`, unrelated to `[:SOURce]:MODE`.

(The returned voltage/current examples 2.991442 V / 1.999407 A / 19.959515 W are consistent with the 3 V / 2 A setting examples; values are plain numbers with no unit suffix.)
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): answers `CV` with the output off; `MEASure:MODE? CH1` (optional `[:RUN]` omitted) works too. `CC` has not been observed (Q4, Q7).

---

## 6. Channel / model table (manual 4.1)

Table copied from the manual (columns in manual order; the PDF image was checked against the text dump):

| Item | SPD4323X | SPD4121X | SPD4306X | Unit |
|------|----------|----------|----------|------|
| Output channel number | 4 | 4 | 4 | CH |
| CH1 rated voltage/current | 6/3.2 | 15/1.5 | 15/1.5 | V/A |
| CH2 rated voltage/current | 32/3.2 | 12/10 | 30/6 | V/A |
| CH3 rated voltage/current | 32/3.2 | 12/10 | 30/6 | V/A |
| CH4 rated voltage/current | 6/3.2 | 15/1.5 | 15/1 | V/A |
| CH2, CH3 series voltage/current | 60/3.2 | 24/10 | 60/6 | V/A |
| CH2, CH3 parallel voltage/current | 32/6.4 | 12/20 | 30/12 | V/A |
| Rated total output power | 240 | 285 | 400 | W |
| Maximum input power | 470 | 620 | 720 | W |

⚠ manual note: SPD4306X CH4 is printed `15/1` while CH1 of the same model is `15/1.5` (and CH4 of SPD4121X is 15/1.5). Possibly a typo; verify on hardware (`CURRent:SET? CH4` with `MAXimum`, or panel).
⚠ manual note: The intro text says rated output voltages "32V, 12V, or 30V" and powers "240W, 285W or 400W". CH1/CH4 of the models (6 V, 15 V) are not covered by that sentence.
⚠ manual note: Model/channel pairing of the 240/285/400 W figures follows the table column order.
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): on the SPD4323X `VOLTage? CHn,MAX` answers `6.060000` (CH1, CH4) and `32.320000` (CH2, CH3), `CURRent? CHn,MAX` answers `3.232000` on all four channels: 1.01 x the rated values above. SPD4306X CH4 was not testable (docs/hardware_findings.md Q14).

Series/parallel (8.2.2):
- Only CH2 and CH3 have three output modes: independent, parallel, series. CH1/CH4 only have independent mode.
- "In the parallel mode, the current value is twice that of the single channel. In the series mode, the voltage value is twice that of the single channel."
- Parallel: "CH2/3 are linked internally into one channel which is controlled by CH2, and CH2 reads the parallel voltage and current values." Load connected to CH2 +/- only.
- Series: "controlled by CH2"; load connected "CH2+ & CH3-" (the manual's series text also says "CH2 reads the parallel voltage and current values" - copy-paste wording).
- SCPI: `OUTPut:TRACK` (section 5.2 item 13) selects independent/series/parallel.
- 4W sense (8.5): "Only CH2 and CH3 can activate 4W sense mode, and 4W sense mode is not supported in series or parallel mode." Max sense compensation 0.6 V (4.2). SCPI: `MODE CH2|CH3,...` (item 14).
- Default settings set CH2/CH3 independent.

---

## 7. Protection and limits

Commands (all in SOURCE subsystem, section 5.2):
- OVP: `[:SOURce]:OVP (CHn),{<value>|MINimum|MAXimum|DEFault}` / `OVP? (CHn)`. Trip status: `OVP:PROTect:STATe? (CHn)`. There is **no** OVP enable/disable command in the manual.
- OCP: `[:SOURce]:OCP (CHn),{...}` / `OCP?`; enable: `OCP:STATe (CHn),{ON|OFF|0|1}` / `OCP:STATe?`; delay: `OCP:DELay (CHn),{...}` / `OCP:DELay?`; trip status: `OCP:PROTect:STATe? (CHn)`.
- Clear trip state: `RESET:PROTect (CHn)` ("Clear the circuit protection status of the channel(overvoltage /overcurrent status)").
- Panel semantics: OVP range 0.1~1.1 x rated voltage; OCP range 0.1~1.1 x rated current; OCP delay 0-3600 s, 0.01 s resolution, output turns off if OCP still triggered after the delay, delay 0 = output off directly when triggered; "The instrument will not trigger the overcurrent protection when the OCP is in OFF state." After the default-settings operation: OVP and OCP at maximum values, OCP state off, OCP delay 0.
- Other stated limits: "Do not load the voltage at the output terminals more than 10% of the rated voltage, otherwise the internal components of the instrument will be damaged." (8.1.2); output terminal to ground withstand "± 240VDC" (8.2.2); in 4W sense mode, an unreliable output wire connection leads to an "internal short-circuit current limiting protection state. At this time, it is necessary to manually turn off the output and check the wiring"; if sense wires are not reliably connected "the actual output voltage will be higher" (8.5).
- Output ON/OFF delay: 0-3600 s (7.2).
- Verified on hardware (SPD4323X, fw 4.1.2.9R1, 2026-10-05): OVP/OCP defaults and maxima are 1.1 x the rating, the minimum 0.1 x (clamped silently); the OCP delay clamps to 0..3600 s with no 0.01 s rounding (docs/hardware_findings.md Q9, Q14). Protection trips, `RESET:PROTect` and what `OUTPut?` reads while tripped were not tested (no output was switched on).
- List: repeat count max 9999; wave duration max 999h 59m 59s; sample period 200-6000 ms.
- Constant-voltage / constant-current behavior: if the load impedance is greater than set V / set I the unit runs CV, otherwise CC (8.2.2). `MEASure:RUN:MODE?` returns `CV` in the example.

---

## 8. Open questions for hardware verification

Status after the first hardware acceptance run (2026-10-05, SPD4323X, firmware 4.1.2.9R1, raw socket, outputs off). The questions are kept as asked; each carries its status and a link to the analysis in `docs/hardware_findings.md`.

1. **Termination**: Which terminator must commands carry on the raw socket (port 5025) and on USB (`\n`? `\r\n`?). The manual shows only `\n` in responses. Does the instrument accept multiple commands per line (`;`)? Not described. **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): answered for the raw socket (LF and CRLF accepted, replies end in LF, `;` chains with concatenated replies); USB not tested.** See [hardware_findings.md Q1](hardware_findings.md#q1-termination-several-commands-per-line).
2. **USB identity**: Is the USB Device port USBTMC? What are VID/PID and the VISA resource string? Manual does not say. Is a driver required beyond NI-VISA? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): not tested (needs a USB connection).** See [hardware_findings.md Q2](hardware_findings.md#q2-usb-identity-vidpid-resource-string-usbtmc).
3. **LAN**: Does the instrument also expose VXI-11 / VISA `TCPIP::<ip>::INSTR`? Is port 5025 TCP only, single or multiple simultaneous connections? Is the web server on port 80? Telnet? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): partially answered: one socket client at a time; VXI-11, web and telnet not probed.** See [hardware_findings.md Q3](hardware_findings.md#q3-lan-vxi-11-simultaneous-connections-web-telnet).
4. **Responses**: Do queries ever return units? (Manual examples show plain numbers.) Number formatting: 6 decimals for scalar V/A/s, 3 decimals for list data, integer `1`/`0` for booleans, word `CV`/`Exist`, `0hours,0minutes,30seconds`, `step:1,run_state:0,...`. Do `*ESE?`, `*ESR?`, `*OPC?`, `*SRE?`, `*STB?`, `*TST?` end with `\n` (manual prints none for them)? What does the literal `\s` in `*IDN?` and `LIST:VOLT\s...` look like on the wire (a plain space?). What is the actual `*IDN?` string for each model? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): answered for every query the plug uses (no units, 6 decimals, float32 values, plain-space `*IDN?`).** See [hardware_findings.md Q4](hardware_findings.md#q4-response-formats-units-decimals-s-terminators-idn).
5. **Missing responses**: Responses not documented for `OCP?`, `LAN:IPADdress?`, `LAN:SMASk?`, `LAN:GATeway?`, `LAN:MAC?`, `GPIB:ADDRess?`, and for `STORage ... FILE:STATe?` when the file does not exist. **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): answered for `OCP?` (a plain number); the rest not tested.** See [hardware_findings.md Q5](hardware_findings.md#q5-missing-responses-ocp-lan-gpib-storage).
6. **Errors**: There is no error-query command (`SYST:ERR?`) in the manual, though `*CLS` "clear the error list". How are errors reported (e.g. ESR bits, status byte, silent ignore)? What bits of `*ESR?` and `*STB?` are used? What does `*TST?` = 0 mean? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): partially answered: no error reply, invalid queries are never answered, `*ESR?` bit 5 is not dependable; `*TST?` not sent.** See [hardware_findings.md Q6](hardware_findings.md#q6-error-reporting-esrstb-tst).
7. **Case/forms**: Are leading `:`/`[:SOURce]` really optional (examples vary)? Do `OUTP`, `VOLT`, `CURR` short forms work (`OUTP CH1,1`)? Do literal bracketed examples (`WAVE:DRAW[:STATe]`) fail? Is `COUP`/`POWER` accepted in any other form? Is the space between channel and value optional (`CH1, 1` shown with a space in `OCP:STATe`)? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): answered: every optional node and form works; wrong abbreviations and literal brackets get no reply.** See [hardware_findings.md Q7](hardware_findings.md#q7-case-and-forms).
8. **Channel argument**: Is `CHn` optional (apply to "current channel", per 10.2)? What happens with an invalid channel (e.g. `CH5`)? Is `CH` argument required for `OUTPut:TRACK`/`LOCK`? (They have none.) **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): mostly answered: invalid channel in a query gets no reply, `OUTPut:TRACK? CH1` gets no reply, `VOLTage?` answers CH1, `MODE? CH1` answers `0`; effect of an invalid channel in a write on CH4 unknown.** See [hardware_findings.md Q8](hardware_findings.md#q8-channel-argument-optional-invalid-on-outputtracklock).
9. **Parameter keywords**: Do `MINimum`/`MAXimum`/`DEFault` work for every command listing them, and what values do they return/set? Rounding/clamping vs error when a value is out of range (e.g. voltage above rating, OVP below set voltage, OCP outside 0.1-1.1 x rated). **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): answered for CH1: values are clamped silently, never rejected; keywords work in set commands and, as query arguments, only for `VOLTage?`/`CURRent?`.** See [hardware_findings.md Q9](hardware_findings.md#q9-minmaxdef-rounding-vs-clamping-vs-error).
10. **Interaction of OVP/OCP with settings**: Is voltage setting limited by OVP? Is OVP/OCP re-initialized when switching series/parallel? What happens to output state after a trip and after `RESET:PROTect`? Does `OUTPut` return `1` while tripped? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): partially answered (outputs off only): no mutual limiting, OVP/OCP not rescaled by the track mode; trips untested.** See [hardware_findings.md Q10](hardware_findings.md#q10-interaction-of-ovpocp-with-other-settings).
11. **Timing / settling**: How long after `OUTPut CHn,1` (and with ON-delay) until output is at voltage; is `*OPC?` meaningful for output-on, list run, or delays? Does `*WAI`/`*OPC` actually block? Response time of `MEASure` immediately after output on? Does measurement refresh rate limit polling? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): partially answered: a query after a write waits ~250 ms, `*OPC?` adds nothing, `*WAI` accepted; settling after output on untested.** See [hardware_findings.md Q11](hardware_findings.md#q11-timing-settling-opc-wai).
12. **Remote lock**: Manual says the device auto-locks when remotely controlled: does the panel stay locked after the session ends? Does `LOCK:STATe 0` need to be sent? Does it interfere with `OUTPut`? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): answered at the SCPI level: every remote write locks, `LOCK 0` unlocks; the front panel view was not reported.** See [hardware_findings.md Q12](hardware_findings.md#q12-remote-lock).
13. **`OUTPut:TRACK` / `MODE` mappings**: numeric values for series (1?) / parallel (2?); `MODE` 0/1 vs 2W/4W; what do the queries return (number vs word) after setting with words. Is `OUTPut:TRACK` rejected while outputs are on? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): answered: queries return numbers (track 0/1/2, sense 0/1); rejection of `OUTPut:TRACK` while an output is on untested; a track change copies CH2 setpoints into CH3.** See [hardware_findings.md Q13](hardware_findings.md#q13-outputtrack-and-mode-mappings).
14. **Rated table**: SPD4306X CH4 `15/1` (typo for 15/1.5?). Real limits returned by `VOLT? CHn,MAX` / `CURR? CHn,MAX`. **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): answered for the SPD4323X (`MAX` = 1.01 x rating, OVP/OCP 0.1 x .. 1.1 x); SPD4306X CH4 untested.** See [hardware_findings.md Q14](hardware_findings.md#q14-rated-table-real-limits-via--chnmax).
15. **LIST**: Maximum steps; meaning of list `WAIT` state and `run_state`/`wait_state`/`completed_state` values in `LIST:INFO?`; whether `LIST:RUN` requires output on; meaning of `LIST:CYCLes` = 0 with `CONTinuous`; what unit/valid range for `LIST:TIME` values (seconds assumed from examples). **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): not tested (out of scope).** See [hardware_findings.md Q15](hardware_findings.md#q15-list-q16-wave-q17-storage).
16. **WAVE**: Behavior of `WAVE:DRAW:ALL` (voltage only per description?), parameter order of `WAVE:SAVE:TIME`, relation of `WAVE:SAVE:STATe` to the U-disk. **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): not tested (out of scope).** See [hardware_findings.md Q15](hardware_findings.md#q15-list-q16-wave-q17-storage).
17. **STORAGE**: Does the file number accept 1-8? Does SCPI storage use the internal or the U-disk storage? Query values other than `Exist`. **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): not tested (out of scope).** See [hardware_findings.md Q15](hardware_findings.md#q15-list-q16-wave-q17-storage).
18. **`*RST`**: What state does it leave (outputs off? values 0?) - not defined in the manual. **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): not tested; `*RST` is never sent.** See [hardware_findings.md Q18](hardware_findings.md#q18-rst).
19. **Programming examples** referenced by the manual (10.1) are not included; any VISA/Socket sample code must be validated on hardware. **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): not applicable: the manual contains no programming examples.** See [hardware_findings.md Q19](hardware_findings.md#q19-programming-examples).
20. **Channel addressing with optional nodes** (added after code review): section 10.2 says a command without `[:SET]` "will operate on the current channel". Does `VOLTage CH2,5` (no `:SET`) address CH2 or the panel-selected channel? Does `:SOURce:VOLTage:SET CH2,5` always address CH2? Verify by writing a different value to each channel and reading all four back with the full printed form. **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): answered: the channel argument is honoured with and without the optional nodes.** See [hardware_findings.md Q20](hardware_findings.md#q20-channel-addressing-with-optional-nodes).
21. **Series/parallel setpoint meaning** (added after code review): in SERIES mode, is `VOLTage CH2,<v>` the combined voltage (up to 60 V on SPD4323X) or the per-half value? In PARALLEL, is `CURRent CH2,<a>` the combined current? What do `VOLTage? CH2,MAX` / `CURRent? CH2,MAX` return in each mode, and what do CH3 queries return? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): partially answered, read side only: in SERIES `VOLTage? CH2` is the combined voltage, in PARALLEL `CURRent? CH2` the combined current; the write side is untested and the plug refuses CH2/CH3 setpoints in coupled modes.** See [hardware_findings.md Q21](hardware_findings.md#q21-seriesparallel-setpoint-meaning).
22. **Output OFF delay semantics** (added after code review): after `OUTPut:OFF:DELay CHn,<s>` with s > 0, what does `OUTPut? CHn` return between the `OUTPut CHn,0` command and the actual switch-off? Does `OUTPut:ALL 0` honour per-channel delays? Does setting the delay to 0 while a delayed switch-off is pending switch off immediately? **Status (hardware run 2026-10-05, SPD4323X fw 4.1.2.9R1): not tested (needs an output on).** See [hardware_findings.md Q22](hardware_findings.md#q22-output-off-delay-semantics).
