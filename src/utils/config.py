import json
from pathlib import Path


class Config:
    DEFAULT_CONFIG = {
        "language": "es-ES",
        "chunk_duration": 180,
        "recognizer": "google",
        "temp_dir": "temp",
        "output_dir": "transcripciones"
    }

    def __init__(self):
        self.config_path = Path.home() / ".video_transcriber_config.json"
        self.load_config()

    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.settings = json.load(f)
        else:
            self.settings = self.DEFAULT_CONFIG
            self.save_config()

    def save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.settings, f, indent=4)
