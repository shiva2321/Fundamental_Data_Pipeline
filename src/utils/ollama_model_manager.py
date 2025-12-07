"""
Ollama Model Manager - Handles model availability checking, downloading, and status updates.
"""
import requests
import logging
import threading
from typing import List, Dict, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class OllamaModelManager:
    """
    Manages Ollama models: checking availability, downloading, and status updates.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.available_models = []
        self.downloading_models = set()

    def is_ollama_running(self) -> bool:
        """Check if Ollama service is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=1)  # Reduced from 2s to 1s
            return response.status_code == 200
        except:
            return False

    def get_installed_models(self) -> List[Dict[str, any]]:
        """Get list of installed models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)  # Reduced from 5s to 2s
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                self.available_models = [m.get('name', '').split(':')[0] for m in models]
                return models
            return []
        except Exception as e:
            logger.error(f"Failed to get installed models: {e}")
            return []

    def is_model_installed(self, model_name: str) -> bool:
        """Check if a specific model is installed."""
        models = self.get_installed_models()
        for model in models:
            name = model.get('name', '').split(':')[0]
            if name == model_name:
                return True
        return False

    def download_model(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        completion_callback: Optional[Callable[[bool, str], None]] = None
    ) -> threading.Thread:
        """
        Download a model from Ollama in a background thread.

        Args:
            model_name: Name of the model to download
            progress_callback: Called with (status_message, progress_percentage)
            completion_callback: Called with (success, message) when done

        Returns:
            Thread object for the download operation
        """
        def _download():
            try:
                self.downloading_models.add(model_name)

                if progress_callback:
                    progress_callback(f"Starting download of {model_name}...", 0)

                logger.info(f"Pulling Ollama model: {model_name}")

                # Make streaming request to pull API
                response = requests.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name},
                    stream=True,
                    timeout=3600  # 1 hour timeout for large models
                )

                if response.status_code != 200:
                    error_msg = f"Failed to pull model {model_name}: HTTP {response.status_code}"
                    logger.error(error_msg)
                    if completion_callback:
                        completion_callback(False, error_msg)
                    return

                # Process streaming response
                total_size = 0
                downloaded = 0
                last_progress = 0

                for line in response.iter_lines():
                    if line:
                        try:
                            import json
                            data = json.loads(line.decode('utf-8'))

                            status = data.get('status', '')

                            # Track download progress
                            if 'total' in data and 'completed' in data:
                                total_size = data['total']
                                downloaded = data['completed']

                                if total_size > 0:
                                    progress = int((downloaded / total_size) * 100)

                                    # Only update if progress changed significantly
                                    if progress != last_progress and progress % 5 == 0:
                                        if progress_callback:
                                            size_mb = downloaded / (1024 * 1024)
                                            total_mb = total_size / (1024 * 1024)
                                            progress_callback(
                                                f"Downloading {model_name}: {size_mb:.1f}MB / {total_mb:.1f}MB",
                                                progress
                                            )
                                        last_progress = progress

                            # Log status updates
                            if status:
                                logger.info(f"Model {model_name}: {status}")
                                if progress_callback and 'verifying' in status.lower():
                                    progress_callback(f"Verifying {model_name}...", 95)
                                elif progress_callback and 'success' in status.lower():
                                    progress_callback(f"{model_name} downloaded successfully!", 100)

                        except json.JSONDecodeError:
                            pass  # Ignore invalid JSON lines

                # Download completed
                logger.info(f"Successfully downloaded model: {model_name}")
                if completion_callback:
                    completion_callback(True, f"Model {model_name} is now available!")

            except requests.exceptions.Timeout:
                error_msg = f"Download timeout for {model_name}. The model is too large or connection is slow."
                logger.error(error_msg)
                if completion_callback:
                    completion_callback(False, error_msg)

            except Exception as e:
                error_msg = f"Error downloading {model_name}: {str(e)}"
                logger.exception(error_msg)
                if completion_callback:
                    completion_callback(False, error_msg)

            finally:
                self.downloading_models.discard(model_name)

        thread = threading.Thread(target=_download, daemon=True)
        thread.start()
        return thread

    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get detailed information about an installed model."""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")
            return None

    def delete_model(self, model_name: str) -> bool:
        """Delete a model from Ollama."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name},
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to delete model {model_name}: {e}")
            return False

    def get_available_models_list(self) -> List[str]:
        """Get list of popular models available for download."""
        return [
            "llama3.2",
            "llama3.2:1b",
            "llama3.1",
            "llama2",
            "mistral",
            "mixtral",
            "phi",
            "gemma",
            "codellama",
            "neural-chat",
            "starling-lm",
            "orca-mini",
            "vicuna",
            "llama2-uncensored"
        ]

    def get_model_size_estimate(self, model_name: str) -> str:
        """Get estimated size of a model."""
        # Approximate sizes - actual sizes may vary
        size_map = {
            "llama3.2": "~2GB",
            "llama3.2:1b": "~1.3GB",
            "llama3.1": "~5GB",
            "llama2": "~4GB",
            "mistral": "~4GB",
            "mixtral": "~26GB",
            "phi": "~2GB",
            "gemma": "~5GB",
            "codellama": "~4GB",
            "neural-chat": "~4GB",
            "starling-lm": "~4GB",
            "orca-mini": "~2GB",
            "vicuna": "~4GB",
            "llama2-uncensored": "~4GB"
        }
        return size_map.get(model_name, "~4GB")

