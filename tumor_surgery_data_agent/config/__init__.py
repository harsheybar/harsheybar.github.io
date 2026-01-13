"""Configuration management for tumor surgery data agent."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration loader and manager."""

    def __init__(self, config_dir: str = None):
        """
        Initialize configuration loader.

        Args:
            config_dir: Path to configuration directory. Defaults to ./config
        """
        if config_dir is None:
            config_dir = Path(__file__).parent
        self.config_dir = Path(config_dir)

        self.medical_codes = self._load_yaml("medical_codes.yaml")
        self.data_sources = self._load_yaml("data_sources.yaml")

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def get_cpt_codes(self) -> list:
        """Get list of CPT codes for craniotomy tumor resections."""
        return [
            item['code']
            for item in self.medical_codes['cpt_codes']['craniotomy_tumor_resection']
        ]

    def get_drg_codes(self) -> list:
        """Get list of DRG codes for cranial surgeries."""
        return [
            item['code']
            for item in self.medical_codes['drgs']['cranial_surgery']
        ]

    def get_date_range(self) -> Dict[str, str]:
        """Get the target date range for data collection."""
        return self.medical_codes['date_range']

    def get_data_source_config(self, source_name: str) -> Dict[str, Any]:
        """Get configuration for a specific data source."""
        sources = self.data_sources['data_sources']
        if source_name not in sources:
            raise ValueError(f"Unknown data source: {source_name}")
        return sources[source_name]


# Singleton instance
_config = None


def get_config() -> Config:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
