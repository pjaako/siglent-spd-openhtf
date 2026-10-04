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
    tested: bool  # True only for the SPD4323X


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
