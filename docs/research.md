# Prior-art research (2026-10-04)

Question: does an OpenHTF plug or a Python driver for the Siglent SPD4000X
(SPD4121X / SPD4306X / SPD4323X) already exist, and what can be borrowed?

## Verdict

- No OpenHTF plug for the SPD4000X exists.
- No Python driver for the SPD4000X exists. The only public SPD4323X code is a
  one-line `*IDN?` smoke test over VISA LAN (`TCPIP0::<ip>::INSTR`), which at
  least confirms the instrument answers over VXI-11 style VISA resources.
- The SCPI command set must therefore come from the manual in this folder
  (`SPD4000X_UserManual_E01C.pdf`, chapter 10), transcribed in
  `scpi_reference.md`. Commands from SPD3303X / SPD1000X projects are NOT
  valid here; the channel count (4), the channel argument syntax
  (`OUTPut CH1,1`) and the subsystems differ.

## Reference concept

- https://github.com/pjaako/rigol-dho-openhtf (the owner's own scope plug,
  MIT). The new plug follows its concept: one thin plug module over PyVISA
  (`@py` backend), a `resource=` injection seam, a hardware-free fake resource
  that logs commands and models instrument state, pytest against the fake,
  `--fake` flags on every runnable script, and SPEC.md / AGENTS.md / README.md
  as the hand-off contract with a "Done means" checklist and a hardware
  acceptance gate.

## Projects worth borrowing structure from (MIT, structure only, no commands)

| Project | What to borrow |
|---|---|
| https://github.com/umi-eng/openhtf-instruments (`packages/siglent-spd3303x`) | BasePlug with injectable VISA resource/manager, `tearDown()` that turns all outputs off, `Channel` enum, frozen measurement dataclass, GitHub Actions CI |
| https://github.com/geissdoerfer/python-spd3303x (PyPI `spd3303x`) | pytest layout with mocked transport, CLI shape |
| https://github.com/pymeasure/pymeasure (`siglent_spdbase.py`) | base-class-plus-model pattern, `shutdown()` safe state |

Not to be copied: https://github.com/Kurokesu/siglent_psu_api (GPL-3.0).

## Transports per manual

- Raw TCP socket, port 5025 (only port named in the manual).
- NI-VISA over USB device port or LAN. USBTMC VID/PID, VXI-11 and
  terminators are not specified; see "Open questions" in `scpi_reference.md`.
