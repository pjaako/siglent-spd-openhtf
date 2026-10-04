import pytest

from siglent_spd_openhtf.models import MODELS, ChannelRating, model_from_idn


def test_models_are_the_three_documented_ones() -> None:
    assert set(MODELS) == {'SPD4323X', 'SPD4121X', 'SPD4306X'}
    for name, model in MODELS.items():
        assert model.name == name
        assert len(model.channels) == 4


def test_only_the_spd4323x_counts_as_tested() -> None:
    # experiments 21 and 30 passed on an SPD4323X (docs/hardware_findings.md run 2)
    assert [name for name, m in MODELS.items() if m.tested] == ['SPD4323X']


def test_spd4323x_ratings() -> None:
    m = MODELS['SPD4323X']
    assert m.channels == (
        ChannelRating(6, 3.2),
        ChannelRating(32, 3.2),
        ChannelRating(32, 3.2),
        ChannelRating(6, 3.2),
    )
    assert m.series == ChannelRating(60, 3.2)
    assert m.parallel == ChannelRating(32, 6.4)
    assert m.total_power_w == 240


def test_spd4121x_ratings() -> None:
    m = MODELS['SPD4121X']
    assert [tuple(c) for c in m.channels] == [(15, 1.5), (12, 10), (12, 10), (15, 1.5)]
    assert m.series == ChannelRating(24, 10)
    assert m.parallel == ChannelRating(12, 20)
    assert m.total_power_w == 285


def test_spd4306x_ratings_keep_ch4_as_printed() -> None:
    m = MODELS['SPD4306X']
    assert [tuple(c) for c in m.channels] == [(15, 1.5), (30, 6), (30, 6), (15, 1)]
    assert m.series == ChannelRating(60, 6)
    assert m.parallel == ChannelRating(30, 12)
    assert m.total_power_w == 400


@pytest.mark.parametrize('name', sorted(MODELS))
def test_parallel_doubles_the_current_series_keeps_it(name: str) -> None:
    m = MODELS[name]
    ch2 = m.channels[1]
    assert m.parallel.voltage == ch2.voltage
    assert m.parallel.current == 2 * ch2.current
    assert m.series.current == ch2.current


@pytest.mark.parametrize(
    ('idn', 'expected'),
    [
        ('Siglent Technologies,SPD4323X,SPD4XXXXXXXXXX,1.0.0.0', 'SPD4323X'),
        ('Siglent Technologies,spd4121x,123,1.0', 'SPD4121X'),
        ('Siglent Technologies, SPD4306X ,123,1.0', 'SPD4306X'),
        ('Siglent\\sTechnologies,SPD4306X,0123456789,4.1.2.4', 'SPD4306X'),
    ],
)
def test_model_from_idn_known(idn: str, expected: str) -> None:
    model = model_from_idn(idn)
    assert model is not None
    assert model.name == expected


@pytest.mark.parametrize(
    'idn',
    [
        'Siglent Technologies,SPD4323,1,1',
        'Siglent Technologies,SPD4323XE,1,1',
        'Siglent Technologies,SPD3303X,1,1',
        'SPD4323X',
        '',
    ],
)
def test_model_from_idn_unknown(idn: str) -> None:
    assert model_from_idn(idn) is None
