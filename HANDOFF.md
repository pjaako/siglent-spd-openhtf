# HANDOFF

Status for a cold agent. Keep this current at every commit.

## Done
- 2026-10-04 Prior-art research (`docs/research.md`): nothing to reuse; build from the manual.
- 2026-10-04 `docs/scpi_reference.md` transcribed from the manual; it is the only SCPI source.
- 2026-10-04 `SPEC.md` (phase 1: core control, protection, measurement, track/sense, safe teardown) and `AGENTS.md` written.
- 2026-10-04 Phase 1 implemented per `SPEC.md` (plug, fake, model table, tests, example, CI, README) and reviewed; the review fixes are listed below.

### Phase 1 review items fixed
- strict boolean arguments (`set_output(1, 'off')` no longer switches ON; `ValueError` before anything is sent).
- verbatim manual-example command forms built in one place (`_Scpi`, marked `# ASSUMPTION(hw): channel addressing / optional nodes`).
- `tearDown()` zeroes a non-zero OFF delay of channels that are on before `OUTPut:ALL 0` and skips the restore after a transport error.
- `snapshot()`/`restore()` include ON/OFF delays, write the track mode first and only if it differs, skip channels whose output is on (and CH2/CH3 if the track restore failed) and name them in the error.
- fake: OFF delay observable (`advance()`), OCP trips at `I >= OCP` even for 0, OVP/OCP clamp to 0.1x..1.1x of the track-aware rating.
- tests parametrized over all three models; example `--fake` keeps the default teardown; README says hardware acceptance is pending and marks USBTMC, VXI-11 and the unlock step unverified; `models.tested` is False for every model; CI runs Python 3.11 and 3.13.

## In flight
- Nothing. Next: hardware acceptance (below), then phase 2 candidates.

## Blocked on hardware
- Hardware acceptance of phase 1 (nothing has run on a real supply yet): all `# ASSUMPTION(hw)` items (`grep -rn "ASSUMPTION(hw)" src`) and `docs/scpi_reference.md` section 8, in particular questions 20-22 (channel addressing with optional nodes, series/parallel setpoint meaning, OFF-delay semantics). The user will forward TCP port 5025 of the SPD4323X to the session on request.

## Out of scope for now
- LIST, WAVE, STORAGE, CALIBRATE subsystems (phase 2 candidates: LIST).

