"""
Configuration management for the application.

This module provides a central Config class that loads configuration from:
1. Environment variables
2. Configuration files
3. Interactive user input (when requested)

Key features:
- Secure storage and retrieval of API keys
- Configuration persistence
- Interactive configuration mode
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List

DEFAULT_CONFIG_FILE = "config/config.yaml"


class Config:
    """
    Configuration manager for the application.

    Handles loading configuration from environment variables, files,
    and interactive user input.
    """

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or DEFAULT_CONFIG_FILE
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file if it exists."""
        config = {
            "api_keys": {
                "polygon": os.environ.get("POLYGON_API_KEY", ""),
                "reddit": os.environ.get("REDDIT_API_KEY", ""),
                "news": os.environ.get("NEWS_API_KEY", ""),
                "alpha_vantage": os.environ.get("ALPHA_VANTAGE_API_KEY", ""),
            },
            "mongodb": {
                "uri": os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
                "db_name": os.environ.get("MONGO_DB", "companies"),  # Changed default to companies
            },
            "collections": {  # Added collections section
                "minute_data": "minutebyminute",
                "profiles": "profiles",
                "daily_data": "dailydata",
                "fundamentals": "fundamentals",
                "sentiment": "sentiment"
            },
            "rate_limits": {
                "polygon": int(os.environ.get("POLYGON_RATE_LIMIT", "120")),
            },
            "update_frequency": {
                "market_data": "15_MINUTES",
                "sentiment": "HOURLY",
                "fundamentals": "DAILY",
                "institutional": "QUARTERLY",
            },
            "general": {
                "max_threads": int(os.environ.get("MAX_THREADS", "5")),
                "default_output_dir": "reports",
                "sequential_processing": True,  # Added flag for sequential vs parallel processing
            }
        }

        # Create sample config if file doesn't exist
        if not os.path.exists(self.config_file):
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
                with open(self.config_file, "w") as f:
                    if self.config_file.endswith(".yaml") or self.config_file.endswith(".yml"):
                        yaml.dump(config, f, default_flow_style=False)
                    else:
                        json.dump(config, f, indent=2)
                print(f"Created sample configuration file: {self.config_file}")
            except Exception as e:
                print(f"Error creating sample config file {self.config_file}: {e}")
                return config

        # Load from existing file
        try:
            with open(self.config_file, "r") as f:
                if self.config_file.endswith(".yaml") or self.config_file.endswith(".yml"):
                    file_config = yaml.safe_load(f)
                else:
                    file_config = json.load(f)

            # Merge configs (file overrides defaults)
            if file_config:
                self._merge_configs(config, file_config)
        except Exception as e:
            print(f"Error loading config from {self.config_file}: {e}")

        return config

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)

            with open(self.config_file, "w") as f:
                if self.config_file.endswith(".yaml") or self.config_file.endswith(".yml"):
                    yaml.dump(self.config, f, default_flow_style=False)
                else:
                    json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config to {self.config_file}: {e}")

    # API Key methods
    def get_polygon_api_key(self) -> str:
        """Get Polygon.io API key."""
        return self.config["api_keys"]["polygon"]

    def get_reddit_api_key(self) -> str:
        """Get Reddit API key."""
        return self.config["api_keys"]["reddit"]

    def get_news_api_key(self) -> str:
        """Get News API key."""
        return self.config["api_keys"]["news"]

    def get_alpha_vantage_api_key(self) -> str:
        """Get Alpha Vantage API key."""
        return self.config["api_keys"]["alpha_vantage"]

    # MongoDB methods
    def get_mongo_uri(self) -> str:
        """Get MongoDB URI."""
        return self.config["mongodb"]["uri"]

    def get_mongo_db(self) -> str:
        """Get MongoDB database name."""
        return self.config["mongodb"]["db_name"]

    # Collection methods
    def get_collection_name(self, collection_type: str) -> str:
        """Get collection name by type."""
        return self.config["collections"].get(collection_type, collection_type)

    # Rate limit methods
    def get_polygon_rate_limit(self) -> int:
        """Get Polygon.io API rate limit."""
        return self.config["rate_limits"]["polygon"]

    # General settings methods
    def get_max_threads(self) -> int:
        """Get maximum number of threads for parallel processing."""
        return self.config["general"]["max_threads"]

    def get_output_dir(self) -> str:
        """Get default output directory."""
        return self.config["general"]["default_output_dir"]

    def get_sequential_processing(self) -> bool:
        """Get whether to process sequentially or in parallel."""
        return self.config["general"].get("sequential_processing", True)

    # Update methods
    def update_api_key(self, service: str, key: str) -> None:
        """Update API key for a service."""
        self.config["api_keys"][service] = key

    def update_mongodb_config(self, uri: str, db_name: str) -> None:
        """Update MongoDB configuration."""
        self.config["mongodb"]["uri"] = uri
        self.config["mongodb"]["db_name"] = db_name

    def update_collection_name(self, collection_type: str, name: str) -> None:
        """Update collection name."""
        self.config["collections"][collection_type] = name


def load_config(config_file: Optional[str] = None) -> Config:
    """
    Load configuration from file and return Config instance.

    Args:
        config_file: Optional path to config file. Uses default if not specified.
    Returns:
        Config instance initialized with the specified or default config file
    """
    return Config(config_file)