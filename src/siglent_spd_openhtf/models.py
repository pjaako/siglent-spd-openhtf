"""Rating table of the SPD4000X family (values from docs/scpi_reference.md section 6)."""

from __future__ import annotations

from typing import NamedTuple


class ChannelRating(NamedTuple):
    """Rated maximum voltage (V) and current (A) of one channel."""

    voltage: float
    current: float


class Model(NamedTuple):
    """Ratings of one SPD4000X model."""

    name: str
    channels: tuple[ChannelRating, ChannelRating, ChannelRating, ChannelRating]
    series: ChannelRating  # CH2 + CH3 in series
    parallel: ChannelRating  # CH2 + CH3 in parallel
    total_power_w: float
    # True once hardware acceptance (docs/acceptance.md) has been run on that model: experiment
    # 21 (the plug's write path and tearDown()) and experiment 30 (output on) both passed on the
    # SPD4323X, firmware 4.1.2.9R1, over the LAN raw socket (docs/hardware_findings.md run 2,
    # 2026-10-04). False for the two models nobody has had access to.
    tested: bool


# Instrument behaviour observed on the SPD4323X (firmware 4.1.2.9R1, 2026-10-05, raw socket).
# The rating table below stays the reference for the plug's guard; these two constants only
# describe what the instrument itself accepts, and are used by the fake.
#
# `VOLTage? CHn,MAX` / `CURRent? CHn,MAX` answer 1.01 x the rated value on every channel
# (6.06 V, 32.32 V, 3.232 A); a larger setpoint is clamped to it silently
# (docs/hardware_findings.md Q9, Q14). The extra 1 % is headroom, not a specification.
SETPOINT_MAX_FACTOR = 1.01
# OVP and OCP accept 0.1 x .. 1.1 x the rated value (clamped silently outside); the supply
# ships with, and `DEFault` selects, the 1.1 x maximum (docs/hardware_findings.md Q9, Q14).
PROTECTION_RANGE = (0.1, 1.1)

MODELS: dict[str, Model] = {
    'SPD4323X': Model(
        name='SPD4323X',
        channels=(
            ChannelRating(6, 3.2),
            ChannelRating(32, 3.2),
            ChannelRating(32, 3.2),
            ChannelRating(6, 3.2),
        ),
        series=ChannelRating(60, 3.2),
        parallel=ChannelRating(32, 6.4),
        total_power_w=240,
        tested=True,
    ),
    'SPD4121X': Model(
        name='SPD4121X',
        channels=(
            ChannelRating(15, 1.5),
            ChannelRating(12, 10),
            ChannelRating(12, 10),
            ChannelRating(15, 1.5),
        ),
        series=ChannelRating(24, 10),
        parallel=ChannelRating(12, 20),
        total_power_w=285,
        tested=False,
    ),
    'SPD4306X': Model(
        name='SPD4306X',
        channels=(
            ChannelRating(15, 1.5),
            ChannelRating(30, 6),
            ChannelRating(30, 6),
            # CH4 is printed "15/1" in the manual (CH1 of the same model is 15/1.5). Kept as
            # printed, see the manual note under the table in docs/scpi_reference.md section 6.
            ChannelRating(15, 1),
        ),
        series=ChannelRating(60, 6),
        parallel=ChannelRating(30, 12),
        total_power_w=400,
        tested=False,
    ),
}


def model_from_idn(idn: str) -> Model | None:
    """Return the model named in an ``*IDN?`` response, or None if it is not a known model.

    The model is the second comma-separated field, compared upper-cased and exactly.
    """
    fields = idn.split(',')
    if len(fields) < 2:
        return None
    return MODELS.get(fields[1].strip().upper())
