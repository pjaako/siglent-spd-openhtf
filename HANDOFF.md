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

## In flight
- Tool fixes from the findings (`tools/hw_acceptance.py` `Link.query` one line per command line, extended experiment 15 for the series/parallel write side, experiment 19 reading CH4, the Q6 error-list sequence, an outputs-off plug write smoke, CH4 in the restore/final check) are being made by a parallel agent; this code change does not touch `tools/` or `docs/acceptance.md`.
- Next: second hardware run (below), then phase 2 candidates.

## Blocked on hardware
- 2026-10-04 Cloud session network check: a direct TCP connection from the cloud container to a non-HTTP port (5025) times out; only proxied HTTP(S) leaves the container. Hardware acceptance therefore runs on a machine on the supply's LAN (or one that can reach the forwarded port) following `docs/acceptance.md`, not from the cloud session.
- The remaining `# ASSUMPTION(hw)` items (`grep -rn "ASSUMPTION(hw)" src`) and the still-open questions of `docs/scpi_reference.md` section 8. Run 1 closed questions 4, 5, 7, 9 (CH1), 13, 14, 20 and most of 1, 8, 12; the full table is in `docs/hardware_findings.md` "Still open". Summary:

| open item | needs | marker / question |
|---|---|---|
| output on: settling, measurement refresh, `*OPC?`, `OUTPut:ALL?` with mixed states | output on, nothing connected | experiment 30, Q11 |
| plug `tearDown()` path (`OUTPut CHn,0`, `OUTPut:ALL 0`, ON/OFF delay writes, `:SOURce:LOCK:STATe OFF`) | outputs off | plug write smoke (tool item 9.4) |
| setpoint written to CH2/CH3 in SERIES/PARALLEL: combined or per half | outputs off | Q21, `# ASSUMPTION(hw): write side of question 21` (plug and fake); the plug refuses meanwhile |
| OFF-delay semantics (`OUTPut?` while pending, `OUTPut:ALL 0` with delays) | output on | Q22, `# ASSUMPTION(hw): OUTPut? during OFF delay` (fake) |
| `OUTPut:TRACK` rejected while an output is on | output on, owner decides | Q13 |
| protection state `1` = tripped; state after a trip and `RESET:PROTect` | a deliberate trip | Q10, `# ASSUMPTION(hw): 1 means tripped` |
| panel visibly unlocked after `tearDown()` | someone at the panel | Q12, `# ASSUMPTION(hw)` in `tearDown()` |
| ON/OFF delay writes clamp like `OCP:DELay`; `MODE` on CH1/CH4 | outputs off | fake markers `same as OCP:DELay`, `not tried` |
| `VOLTage?` without a channel: CH1 or panel-selected channel | panel state | Q8, fake marker |
| effect of `VOLTage CH5,1` on CH4 (CH4 was not read back) | outputs off | Q8; ask the user to check CH4's setpoint |
| USB identity and terminator, VXI-11, web, telnet | USB cable / direct LAN | Q2, Q3 |
| SPD4121X, SPD4306X (CH4 `15/1`) | other models | Q14 |

## Out of scope for now
- LIST, WAVE, STORAGE, CALIBRATE subsystems (phase 2 candidates: LIST).

