# HANDOFF

Status for a cold agent. Keep this current at every commit.

## Done
- 2026-10-04 Prior-art research (`docs/research.md`): nothing to reuse; build from the manual.
- 2026-10-04 `docs/scpi_reference.md` transcribed from the manual; it is the only SCPI source.
- 2026-10-04 `SPEC.md` (phase 1: core control, protection, measurement, track/sense, safe teardown) and `AGENTS.md` written.
- 2026-10-04 Phase 1 implemented per `SPEC.md` (plug, fake, model table, tests, example, CI, README) and reviewed; the review fixes are listed below.

### Phase 1 review items fixed
- strict boolean arguments (`set_output(1, 'off')` no longer switches ON; `ValueError` before anything is sent).
- verbatim manual-example command forms built in one place (`_Scpi`; the channel-addressing assumption was confirmed on hardware 2026-10-05, both verbatim and short forms work).
- `tearDown()` zeroes a non-zero OFF delay of channels that are on before `OUTPut:ALL 0` and skips the restore after a transport error.
- `snapshot()`/`restore()` include ON/OFF delays, write the track mode first and only if it differs, skip channels whose output is on (and CH2/CH3 if the track restore failed) and name them in the error.
- fake: OFF delay observable (`advance()`), OCP trips at `I >= OCP` even for 0, OVP/OCP clamp to 0.1x..1.1x of the track-aware rating.
- tests parametrized over all three models; example `--fake` keeps the default teardown; README says hardware acceptance is pending and marks USBTMC, VXI-11 and the unlock step unverified; `models.tested` is False for every model; CI runs Python 3.11 and 3.13.

### Hardware acceptance run 1 and the code that follows from it
- 2026-10-05 Hardware acceptance run 1 on a real SPD4323X (firmware 4.1.2.9R1, LAN raw socket, all outputs off, nothing connected), analysed in `docs/hardware_findings.md`. What ran: read tier (experiments 1-6, 8) and write tier on CH1 with CH2/CH3 touched for track/sense (10-20), `tools/bare_socket_check.py --sweep-terms`. What did not run: experiment 30 (output on; no `OUTPut CHn,<x>` or `OUTPut:ALL <x>` was sent at all), 7 (VXI-11), `*TST?`, USB, web/telnet; the plug's `tearDown()` path has never run on hardware.
- 2026-10-05 Code brought in line with `SPEC.md` (commit 439ceb8) and the findings: guard at the rated value (not 1.01 x); CH2/CH3 setters, `configure_channel` and `restore()` refuse/skip setpoints while the track mode is SERIES or PARALLEL (open question 21, write side); `set_track()` warns when CH3's setpoints change; `max_voltage()`/`max_current()`; `restore()` reads first and writes only what differs; `tearDown()` documents that the unlock must be the last write. Fake: float32 replies (`35.200001`), 1.1 x OVP/OCP defaults, 1.01 x V/I clamps, delay clamps, MIN/MAX/DEF keywords, auto-lock on writes, status registers, `;` chaining, CH2 to CH3 copy on track change. `models.SETPOINT_MAX_FACTOR` and `PROTECTION_RANGE` added; `models.tested` stays `False`. README "Things the manual does not tell you" filled (15 dated items); `docs/scpi_reference.md` carries `Verified on hardware` lines and a status per open question.

### Hardware acceptance run 2 and the code that follows from it
- 2026-10-04 Hardware acceptance run 2 on the same SPD4323X (firmware 4.1.2.9R1, LAN raw socket), owner at the instrument, analysed in `docs/hardware_findings.md` ("Run 2"). (a) `tools/hw_acceptance.py` with outputs off: experiments 1-6, 8, 10-21, clean restore (0 FAILED, snapshot `restored`). (b) `--only 30,31 --allow-output --confirm-no-load`: CH1 on at 1.0 V / 0.1 A with nothing connected, off confirmed, clean restore. (c) Panel after the run: unlocked, CH4 0 V / 0 A, CH3 back at 12 V / 2 A. Not run: VXI-11, USB, `*TST?`, a protection trip, `OUTPut:TRACK` with an output on, `OUTPut:ALL?` with mixed states. One change outside the tool, at the owner's request: key sound switched off (`SOUNd:KEY 0`; persistent instrument setting; alarm sound untouched).
- What the hardware showed: (1) a setpoint written to CH2 in a coupled mode is the **combined** value, CH3 follows with half (SERIES `VOLTage CH2,20` -> CH2 20 / CH3 10; PARALLEL `CURRent CH2,5` -> 5 / 2.5, above the 3.232 A `MAX`), the `MAXimum` keyword stays per channel; (2) with an OFF delay `OUTPut CHn,0` **and** `OUTPut:ALL 0` keep the output live until the delay elapsed (`OUTPut?` -> 1), writing the delay 0 while pending switches off at once; (3) output on: the first reading is at the setpoint after ~295 ms (write latency), the open output decays below 20 mV in ~0.7 s after off; (4) the plug's write path and `tearDown()` work on hardware, panel unlocked; (5) invalid-channel writes change none of CH1-CH4; (6) the "empty error list" explanation of `*ESR?` bit 5 is refuted, `*ESR?` stays unusable.
- Code and docs changed accordingly (the coupled-mode rule below was widened again by the addendum that follows): the coupled-mode refusal is lifted for exactly the two verified writes (CH2 voltage in SERIES, CH2 current in PARALLEL; guard = model series/parallel rating) and kept for everything else (CH3, the other quantity of CH2), in `set_voltage`/`set_current`/`configure_channel`/`restore()`; the allowed writes also need a `tested` model, the track mode is queried fresh before every CH2/CH3 setter (an Opus review found the stale-cache and untested-model holes), and `restore()` leaves CH2 alone while CH3 is on; fake: combined coupled writes with CH3 following, keywords per channel, numeric limit 2 x `MAX` (`ASSUMPTION(hw)`), OFF delay 0 switches a pending output off; markers for OFF delay and unlock resolved; `models.tested` is `True` for the SPD4323X (experiments 21 and 30 passed); SPEC.md, README ("Things the manual does not tell you" items 16-20, model table "tested over LAN (raw socket), firmware 4.1.2.9R1"), `docs/scpi_reference.md` annotated. `tearDown()` needed no change (the zero-the-OFF-delay-first order is now verified as necessary).

- 2026-10-04 (later) Extra visit, outputs off, new experiment 22 `followups` (`docs/hardware_findings.md` "Run 2 addendum"): CH3 writes are ignored in SERIES/PARALLEL (CH3 follows CH2); the current of CH2 in SERIES and the voltage of CH2 in PARALLEL are per channel; the combined value is limited to 60 V (SERIES) and 6.464 A (PARALLEL) and the `MAXimum` keyword stays per channel; CH3's current in SERIES reads CH2's + 0.1 A (the old `3.1 A` oddity); ON/OFF delay writes clamp like `OCP:DELay`; `MODE? CH4` -> `0`, `MODE CH1|CH4` ignored; `VOLTage?` without channel answers CH1 even with CH2 selected on the panel. Plug: every CH2 voltage/current write is allowed in a coupled mode on a tested model, CH3 writes raise before sending, `restore()` writes CH2 and lets CH3 follow, `set_track()` ignores the +0.1 A display offset; the fake models all of it. Clean restore, panel not looked at again. Not run: the output-on items (`OUTPut:TRACK` with a live output, a protection trip, `OUTPut:ALL?` with mixed states).

- Instrument state at the end of 2026-10-04 (outside the repo's control): key sound off (`SOUNd:KEY 0`, alarm sound on); the owner switched **CH2's output on by hand** at the panel and selected CH2 (nothing connected, 14 V / 3 A setpoints) and was asked to switch it off. `tools/hw_acceptance.py` refuses to write while any output is on, so a next run needs all outputs off first (check `OUTPut? CH1..CH4`). Evidence is in the repo as redacted copies (serial and address replaced by the placeholders, line numbers unchanged): `docs/evidence/run2_hw_acceptance.log` ("acc N" of the run-2 findings), `run2_addendum_hw_acceptance.log` ("acc3 N"), and the reports `run2_report.md`, `run2_output_report.md`, `run2_addendum_report.md`. Run 1's logs were never committed (the "acc"/"bare" numbers of the run-1 section refer to files that stay on the machine that ran it). The unredacted originals are git-ignored `*.local.*` files on the machine that ran the visits. The supply's address is not in the repo (`PSU_HOST`).

## In flight
- Nothing. Next: a third, small hardware visit for the items below, then phase 2 candidates (LIST).

## Open (needs hardware or another model)
`grep -rn "ASSUMPTION(hw)" src` lists the remaining markers (protection `1` = tripped, lock effect of ignored writes, the other quantity of CH2 above `MAX`, MINimum/DEFault in a combined coupled write); the questions are in `docs/hardware_findings.md` "Still open after the addendum":

| open item | needs | marker / question |
|---|---|---|
| USB identity and terminator, VXI-11, web, telnet | USB cable / direct LAN | Q2, Q3 |
| protection state `1` = tripped; state after a trip and `RESET:PROTect` | a real trip (OCP needs a load; OVP without load is a deliberate fault) | Q10, `# ASSUMPTION(hw): 1 means tripped` |
| `OUTPut:TRACK` rejected while an output is on | output on, owner decides (live output) | Q13 |
| `OUTPut:ALL?` with mixed channel states | two outputs on, nothing connected | Q4 |
| whether an ignored write (CH3 in a coupled mode, `MODE` on CH1/CH4) locks the panel; the other quantity of CH2 above the per-channel `MAX`; MINimum/DEFault in a combined coupled write | outputs off | fake markers `ASSUMPTION(hw)` |
| SPD4121X, SPD4306X (CH4 `15/1`) | other models | Q14 |

Tool state: `tools/hw_acceptance.py` ran without defects in run 2 (the run-1 fixes held: one reply line per command line, the extended experiments 15/19/21, CH4 in snapshot and restore). The cloud session cannot reach the instrument (raw TCP is blocked); hardware runs happen on a machine on the supply's LAN following `docs/acceptance.md`. On a network share `uv pip install` can fail on AppleDouble `._*` files and the share creates `._*.py` files that `test_source_has_no_factory_reset_or_unlisted_subsystems` trips over: delete them (`find . -name '._*' -not -path './.venv/*' -delete`).

## Out of scope for now
- LIST, WAVE, STORAGE, CALIBRATE subsystems (phase 2 candidates: LIST).
