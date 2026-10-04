# Hardware acceptance protocol (SPD4323X)

Purpose: answer the open questions of `docs/scpi_reference.md` section 8 in one careful,
logged session, then fold the answers back into the code, the fake and the README.

Two tools do the work. Both live in `tools/`, both support `--help` and `--dry-run`
(prints the plan, connects to nothing).

| tool | needs | what it does |
|---|---|---|
| `tools/bare_socket_check.py` | Python standard library only | Raw TCP socket on port 5025. Sends **only queries** (it refuses any string whose header has no `?`). Prints the exact bytes received (`repr`) with timing, probes terminators, syntax forms and a second concurrent connection, and ends with a summary table. |
| `tools/hw_acceptance.py` | `pyvisa` + `pyvisa-py` (`uv pip install -e .[dev]`) | Numbered experiments over PyVISA (`@py`), each answering named open questions. Writes a Markdown report. Snapshots and restores instrument state. |

## 1. Prerequisites

1. The project owner has forwarded TCP port 5025 of the supply to the machine that runs the
   tools, and `PSU_HOST` points at it. In documentation the address is `192.0.2.10`:

   ```bash
   export PSU_HOST=192.0.2.10
   ```

   Real addresses and serial numbers never go into git.
2. **Nothing is connected to any output terminal** of the supply (no DUT, no load, no
   cables, no meter leads). This is mandatory for the optional output-on experiment and
   good practice for the rest.
3. All four outputs are **off** at the start. The tool checks this itself and refuses to
   continue otherwise (`--i-know-outputs-are-on` overrides it; do not use it for acceptance).
4. Preferably someone can see the front panel. It is needed for open question 12 (is the
   panel locked after the session?) and to notice beeps or error indications. Without a
   visible panel, question 12 stays open and the panel may stay locked: a long press on the
   Lock key releases it (manual, chapter 5).
5. Model: SPD4323X (CH1 and CH4 6 V / 3.2 A, CH2 and CH3 32 V / 3.2 A). The tools refuse
   anything whose `*IDN?` does not name an `SPD4` model. The other two models have a rating table
   in the tool, but only the SPD4323X is a target of this protocol.
6. Work from a scratch directory or the repository root. These files are written to the
   current directory; the repository ignores `*.local.*`, so they are never committed:
   `bare_socket_check.local.log`, `hw_acceptance.local.log` (every command and raw reply,
   flushed per command, unredacted) and `acceptance_snapshot.local.json`.
   Name reports `*.local.md` as well (`--report acceptance_report.local.md`). The report
   replaces host and serial number with `<redacted>`, but read it before it goes anywhere near git.

## 2. Order of the session

Each step is safe to stop after. Steps 0 to 4 never switch an output on.

```bash
# 0. Plan only, no connection (anywhere, also without pyvisa)
python3 tools/bare_socket_check.py --dry-run
python3 tools/hw_acceptance.py --dry-run

# 1. Raw socket, read-only: terminator, formats, forms, second connection (about 1-3 min)
python3 tools/bare_socket_check.py --sweep-terms
#    add --probe-ports only if the supply is reachable directly (web, telnet, VXI-11 portmapper)

# 2. Decide the terminator from the summary of step 1 (Q1).
#    LF works     -> use the defaults below.
#    only CRLF    -> add  --term '\r\n'  to every hw_acceptance command  (and fix the plug, section 4).

# 3. PyVISA, still read-only: every query, forms, MIN/MAX, timing, status registers,
#    and the plug's own getters if the package is installed
python3 tools/hw_acceptance.py --read-only --report acceptance_report_readonly.local.md

# 4. Writes with all outputs staying OFF (CH1 setpoints/protection, CH2/CH3 coupling and sense, lock)
python3 tools/hw_acceptance.py --report acceptance_report.local.md

# 5. Optional, only with nothing connected: output on at 1.0 V / 0.1 A, CH1, settling curve
python3 tools/hw_acceptance.py --only 30 --allow-output --confirm-no-load \
    --report acceptance_report_output.local.md

# 6. Optional extras
python3 tools/hw_acceptance.py --read-only --only 6 --allow-selftest   # also send *TST?
python3 tools/hw_acceptance.py --read-only --only 7 --try-vxi11        # needs a direct LAN path
```

After step 4 look at the front panel and note whether it is locked (question 12).

### Exit codes of `hw_acceptance.py`

| code | meaning | what to do |
|---|---|---|
| 0 | finished | read the report |
| 1 | finished, at least one experiment raised an error | read the experiment details; the run is still valid |
| 2 | cannot connect, or `*IDN?` unanswered | check the forward, try `--term '\r\n'` |
| 3 | refused before writing: an output is on or unreadable, not an SPD4, or an unfinished snapshot exists | fix the cause; for a stale snapshot see below |
| 4 | **restore or output-off could not be confirmed** | the report names the values; fix them at the front panel, then continue |

If a run is killed or crashes after writing, `acceptance_snapshot.local.json` still has
status `taken` and the next run refuses to start. Restore the original values with:

```bash
python3 tools/hw_acceptance.py --restore-snapshot
```

## 3. Safety rules the code enforces

These are checks on every string before it reaches the socket, not just documentation.

- No output is ever switched on unless `--allow-output --confirm-no-load` is given, and then
  only `OUTPut CH1,1` (the `--channel`) inside experiment 30. `OUTPut:ALL 1` is never sent.
- Never sent, in any mode: `*RST`, `DEFault:RESET`, `FACTory:RESET`, anything under LAN, DHCP,
  GPIB, STORage, CALibrate, WAVE or LIST (queries included). `*TST?` only with
  `--allow-selftest`. Any write whose header is not on a short allow list is refused.
- Before the first write the tool reads setpoint, current, OVP, OCP, OCP state, OCP delay,
  output on/off delays, output state, track mode, CH2/CH3 sense mode and lock for all four
  channels, prints them, and saves them to `acceptance_snapshot.local.json`. If any core value cannot be
  read the tool refuses to write. If `OCP? CHn` gets no answer (the manual prints none),
  OCP can neither be read back nor restored, so OCP is never written and experiment 13 is skipped.
- Every write experiment re-checks that the outputs are off, and puts the channel state back
  (with read-back) afterwards. A final restore in a `finally:` block does it again, switches
  off anything this run switched on, reports every value it could not restore, and queries the
  outputs one last time.
- Write experiments touch CH1 only (`--channel` to change). The coupling and sense
  experiments (15, 16) necessarily use CH2/CH3, only while their outputs are off.

## 4. After the run

1. **Read the report** (`Findings by open question`, then the raw transcripts). Check the
   Safety log first: restore status and the output states at the end.
2. **Fill README "Things the manual does not tell you"**: one entry per answered question, in
   the form *what the manual leaves open, what the SPD4323X does, evidence (raw reply)*, dated, firmware
   version from `*IDN?`. Do not paste the real address or serial number.
3. **Resolve every `# ASSUMPTION(hw)`**:

   ```bash
   grep -rn "ASSUMPTION(hw)" src
   ```

   | marker (src) | answered by |
   |---|---|
   | terminator (plug `__init__`, fake) | bare_socket_check Q1 table; E1, E3, E18 |
   | track numbering, `set_track` / `track` | E15 |
   | sense numbering, `set_sense` / `sense` | E16 |
   | `OCP?` answers a plain number | bare_socket_check Q5 line; E2, E13 |
   | clamping (fake) | E10, E11, E12, E13, E14 |
   | protection state `1` = tripped | **not answerable here**: it needs a real trip with a load (out of scope); the queries only show `0` |
   | `tearDown` unlock needed (`set_lock(False)`) | E17 plus the front panel after the run |

   For each: if the hardware agrees, replace the marker by a plain comment naming the date
   (`verified on SPD4323X, firmware ...`); if not, change the plug, change the fake to behave
   like the instrument (including the exact reply strings and decimals), and add or adjust a
   test. The fake only knows what we told it; every finding goes back into it.
4. **Re-run** `pytest -q`, `python example_test.py --fake`, `ruff check .`,
   `ruff format --check .`, `mypy src`. Then `python3 tools/hw_acceptance.py --read-only` again
   (experiment 8, `plug_smoke`, calls the plug's getters against the instrument) and confirm it reports no failures.
5. Tick the answered items in `docs/scpi_reference.md` section 8 (or annotate them), update
   `HANDOFF.md`, commit. Never commit `*.local.*` files or an unreviewed report.

If the timing numbers (experiment 5, 18, 30) show replies slower than the plug's 5 s timeout
or settling slower than `wait_for_voltage`'s defaults, change those defaults too.

## 5. Checklist: open question to tool

"bare" = `tools/bare_socket_check.py`; "E<n>" = experiment number in `tools/hw_acceptance.py`
(`--dry-run` lists them).

| # | Open question (section 8) | Answered by | Remaining gap |
|---|---|---|---|
| 1 | Termination; several commands per line | bare `--sweep-terms` Q1 table and the `;` probe; E1, E3, E18 | USB terminator: needs USB |
| 2 | USB identity (VID/PID, resource string) | none | **needs USB** |
| 3 | LAN: VXI-11, simultaneous connections, web, telnet | bare second-connection test (Q3 verdict); bare `--probe-ports` (web 80, telnet 23, portmapper 111); E7 `--try-vxi11` | web/telnet/VXI-11 need a direct LAN path, not a single forwarded port |
| 4 | Response formats, units, decimals, `\s`, terminators, actual `*IDN?` | bare Q4 table; E1, E2, E10, E11, E14 | `*IDN?` of the other two models: out of scope; LIST/WAVE/STORAGE formats: out of scope |
| 5 | Missing responses (`OCP?`, LAN, GPIB, STORage) | bare Q5 line; E2, E13 | LAN/GPIB/STORage: out of scope (blocked by the safety policy) |
| 6 | Error reporting; `*ESR?`/`*STB?`; `*TST?` | bare before/after status registers; E6, E19; `*TST?` value with E6 `--allow-selftest` | what `*TST?` = 0 means: the value is recorded, its meaning needs the manufacturer |
| 7 | Case/forms: colon, `[:SOURce]`, short forms, brackets, spacing | bare forms table; E3 (queries); E14, E20 (writes) | none |
| 8 | Channel argument optional? invalid channel? | bare forms (no channel, CH0, CH5, `1`, `MODE? CH1`, `OUTPut:TRACK? CH1`); E2, E3, E19 | a write without channel is deliberately not tried (it could hit another channel) |
| 9 | MIN/MAX/DEF; rounding vs clamping vs error out of range | bare parameter-keyword table; E4 (queries); E10, E11, E12, E13, E14 (sets and read-back) | none |
| 10 | OVP/OCP interaction with other settings | E12 (OVP vs setpoint), E13 (OCP vs current), E15 (series/parallel re-initialisation) | state after a trip and after `RESET:PROTect`, `OUTPut?` while tripped: needs a load that trips protection, out of scope |
| 11 | Timing, settling, `*OPC?`, `*WAI` | E5 (median of 5), E18; E30 (output on, settling curve, `--allow-output`) | none |
| 12 | Remote lock | E17 (`LOCK`, remote writes while locked) | **needs front panel**: is it locked after the session? |
| 13 | `OUTPut:TRACK` and `MODE` mappings; query number vs word | E15, E16 | rejection of `OUTPut:TRACK` while an output is on: not tested (would need an output on), out of scope |
| 14 | Rated table; real limits via `...? CHn,MAX` | bare parameter-keyword table; E4; E15 (series/parallel limits) | SPD4306X CH4 `15/1`: needs that model, out of scope |
| 15 | LIST | none | out of scope (blocked by the safety policy) |
| 16 | WAVE | none | out of scope (blocked) |
| 17 | STORAGE | none | out of scope (blocked) |
| 18 | `*RST` state | none | out of scope: `*RST` is never sent by these tools |
| 19 | Programming examples validated | none | out of scope |

## 6. Experiment index (`hw_acceptance.py`)

| # | key | tier | questions |
|---|---|---|---|
| 1 | identity | read | 1, 4 |
| 2 | formats | read | 4, 5, 8 |
| 3 | forms | read | 1, 7, 8 |
| 4 | min_max | read | 9, 14 |
| 5 | timing | read | 11 |
| 6 | status_registers | read | 6 |
| 7 | vxi11 (`--try-vxi11`) | read | 3 |
| 8 | plug_smoke | read | plug check against the instrument |
| 10 | voltage_set | write | 4, 9 |
| 11 | current_set | write | 4, 9 |
| 12 | ovp | write | 9, 10 |
| 13 | ocp | write | 5, 9, 10 |
| 14 | ocp_state_delay | write | 4, 7, 9 |
| 15 | track | write | 10, 13, 14 |
| 16 | sense | write | 13 |
| 17 | lock | write | 12 |
| 18 | opc_wai | write | 1, 11 |
| 19 | error_reporting | write | 6, 8 |
| 20 | set_forms | write | 7 |
| 30 | output_settling (`--allow-output --confirm-no-load`) | output | 11 |

`--only 1,2,5` and `--skip 3` select experiments; `--read-only` drops the write tier.
