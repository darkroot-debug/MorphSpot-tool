"""
Configuration settings for the Image Forensics and Manipulation Detection Framework.
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ELAConfig:
    quality: int = 90
    scale_multiplier: float = 15.0
    patch_size: int = 16
    variance_threshold: float = 120.0
    disparity_weight: float = 0.6


@dataclass
class NoiseConfig:
    patch_size: int = 24
    filter_kernel_size: int = 5
    mad_threshold: float = 2.5
    min_noise_floor: float = 0.001


@dataclass
class CopyMoveConfig:
    feature_type: str = "SIFT"  # 'SIFT', 'ORB', or 'AKAZE'
    max_features: int = 2500
    ratio_threshold: float = 0.72
    min_spatial_distance: float = 35.0  # Pixel distance to avoid trivial self-matches
    eps_spatial_cluster: float = 40.0  # DBSCAN clustering radius
    min_cluster_size: int = 4  # Minimum matches in a cluster to indicate clone
    displacement_bin_size: float = 15.0


@dataclass
class EdgeConfig:
    canny_low: int = 50
    canny_high: int = 150
    blur_kernel_size: int = 7
    sobel_kernel_size: int = 3
    transition_width_threshold: float = 4.5
    sharpness_disparity_threshold: float = 2.0


@dataclass
class LuminanceConfig:
    patch_size: int = 32
    poly_degree: int = 2
    color_temp_threshold: float = 15.0


@dataclass
class MetadataConfig:
    suspicious_software: List[str] = field(default_factory=lambda: [
        "photoshop", "gimp", "canva", "picsart", "pixelmator", "snapseed",
        "lightroom", "midjourney", "stable diffusion", "dall-e", "affinity",
        "paint.net", "facetune", "retouch", "befunky", "pixlr", "fotor",
        "vsco", "afterlight", "adobe firefly", "generative fill"
    ])


@dataclass
class FusionWeights:
    # Baseline weights for forensic indicators (sum to 1.0)
    ela: float = 0.28
    noise: float = 0.24
    copy_move: float = 0.22
    edges: float = 0.16
    luminance: float = 0.10
    
    # Critical anomaly escalations (added or scaled when strong evidence is found)
    copy_move_high_confidence_boost: float = 25.0
    metadata_flag_boost: float = 15.0


@dataclass
class ForensicConfig:
    ela: ELAConfig = field(default_factory=ELAConfig)
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    copy_move: CopyMoveConfig = field(default_factory=CopyMoveConfig)
    edges: EdgeConfig = field(default_factory=EdgeConfig)
    luminance: LuminanceConfig = field(default_factory=LuminanceConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    weights: FusionWeights = field(default_factory=FusionWeights)

    # Classification Thresholds
    authentic_threshold: float = 30.0
    suspicious_threshold: float = 65.0
    
    # Maximum processing dimension (images resized proportionally for speed while maintaining aspect ratio)
    max_dimension: int = 1600


DEFAULT_CONFIG = ForensicConfig()
