"""
Forensic Detection Modules.
"""
from app.modules.ela import ELADetector
from app.modules.noise import NoiseDetector
from app.modules.copy_move import CopyMoveDetector
from app.modules.edges import EdgeInconsistencyDetector
from app.modules.luminance import LuminanceDetector
from app.modules.metadata import MetadataAuditor

__all__ = [
    "ELADetector",
    "NoiseDetector",
    "CopyMoveDetector",
    "EdgeInconsistencyDetector",
    "LuminanceDetector",
    "MetadataAuditor",
]
