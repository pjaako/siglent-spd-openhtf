"""OpenHTF plug for Siglent SPD4000X programmable DC power supplies."""

from .fake_resource import FakeSpdResource
from .models import MODELS
from .plug import (
    Channel,
    Identity,
    ProtectionStatus,
    Reading,
    SenseMode,
    SiglentSpdPlug,
    TrackMode,
)

__all__ = [
    'MODELS',
    'Channel',
    'FakeSpdResource',
    'Identity',
    'ProtectionStatus',
    'Reading',
    'SenseMode',
    'SiglentSpdPlug',
    'TrackMode',
]
