from dataclasses import dataclass
from typing import Dict, List
from fiber.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class PlatformConfig:
    """Configuration for each supported platform."""

    name: str
    emission_weight: float
    metrics: List[str]
    error_metrics: List[str]
    success_metrics: List[str]

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not 0 <= self.emission_weight <= 1:
            raise ValueError(
                f"Emission weight must be between 0 and 1, got {self.emission_weight}"
            )
        if not self.metrics:
            raise ValueError("Metrics list cannot be empty")
        if not self.success_metrics:
            raise ValueError("Success metrics list cannot be empty")


class PlatformManager:
    """Manager for multi-platform scoring configuration."""

    def __init__(self):
        """Initialize the PlatformManager with default platform configurations."""
        self.platforms: Dict[str, PlatformConfig] = {
            "twitter": PlatformConfig(
                name="twitter",
                emission_weight=0.9,  # 90% of emissions
                metrics=[
                    "scrapes",
                    "returned_tweets",
                    "returned_profiles",
                    "auth_errors",
                    "errors",
                    "ratelimit_errors",
                ],
                error_metrics=["auth_errors", "errors", "ratelimit_errors"],
                success_metrics=["returned_tweets", "returned_profiles"],
            ),
            "tiktok": PlatformConfig(
                name="tiktok",
                emission_weight=0.1,  # 10% of emissions
                metrics=["transcription_success", "transcription_errors"],
                error_metrics=["transcription_errors"],
                success_metrics=["transcription_success"],
            ),
        }

        # Validate that emission weights sum to 1.0
        total_weight = sum(config.emission_weight for config in self.platforms.values())
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(
                f"Platform emission weights must sum to 1.0, got {total_weight}"
            )

        logger.info(f"Initialized PlatformManager with {len(self.platforms)} platforms")
        for name, config in self.platforms.items():
            logger.info(f"Platform {name}: {config.emission_weight*100:.1f}% emissions")

    def get_platform(self, name: str) -> PlatformConfig:
        """Get platform configuration by name."""
        if name not in self.platforms:
            raise ValueError(f"Unknown platform: {name}")
        return self.platforms[name]

    def get_all_platforms(self) -> Dict[str, PlatformConfig]:
        """Get all platform configurations."""
        return self.platforms.copy()

    def get_platform_names(self) -> List[str]:
        """Get list of all platform names."""
        return list(self.platforms.keys())

    def get_total_emission_weight(self) -> float:
        """Get total emission weight (should be 1.0)."""
        return sum(config.emission_weight for config in self.platforms.values())

    def add_platform(self, config: PlatformConfig) -> None:
        """Add a new platform configuration."""
        if config.name in self.platforms:
            raise ValueError(f"Platform {config.name} already exists")

        self.platforms[config.name] = config

        # Validate emission weights still sum to 1.0
        total_weight = sum(c.emission_weight for c in self.platforms.values())
        if abs(total_weight - 1.0) > 1e-6:
            logger.warning(f"Platform emission weights sum to {total_weight}, not 1.0")

        logger.info(
            f"Added platform {config.name} with {config.emission_weight*100:.1f}% emissions"
        )

    def update_platform_weights(self, weights: Dict[str, float]) -> None:
        """Update emission weights for platforms."""
        for platform_name, weight in weights.items():
            if platform_name not in self.platforms:
                raise ValueError(f"Unknown platform: {platform_name}")
            self.platforms[platform_name].emission_weight = weight

        # Validate that weights sum to 1.0
        total_weight = sum(config.emission_weight for config in self.platforms.values())
        if abs(total_weight - 1.0) > 1e-6:
            raise ValueError(
                f"Platform emission weights must sum to 1.0, got {total_weight}"
            )

        logger.info("Updated platform emission weights")
        for name, config in self.platforms.items():
            logger.info(f"Platform {name}: {config.emission_weight*100:.1f}% emissions")
