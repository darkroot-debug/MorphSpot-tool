"""
Image Forensics and Tampering Detection Package.
"""
from app.config import ForensicConfig, DEFAULT_CONFIG
from app.engine import ForensicEngine

__version__ = "1.0.0"
__all__ = ["ForensicEngine", "ForensicConfig", "DEFAULT_CONFIG"]
