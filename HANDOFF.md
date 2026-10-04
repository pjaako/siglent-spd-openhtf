# HANDOFF

Status for a cold agent. Keep this current at every commit.

## Done
- 2026-10-04 Prior-art research (`docs/research.md`): nothing to reuse; build from the manual.
- 2026-10-04 `docs/scpi_reference.md` transcribed from the manual; it is the only SCPI source.
- 2026-10-04 `SPEC.md` (phase 1: core control, protection, measurement, track/sense, safe teardown) and `AGENTS.md` written.

## In flight
- Phase 1 implementation per `SPEC.md` (delegated to a coder agent), then review.

## Blocked on hardware
- All `# ASSUMPTION(hw)` items and `docs/scpi_reference.md` section 8. The user will forward TCP port 5025 of the SPD4323X to the session on request.

## Out of scope for now
- LIST, WAVE, STORAGE, CALIBRATE subsystems (phase 2 candidates: LIST).
