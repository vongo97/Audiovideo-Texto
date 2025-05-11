import json
from pathlib import Path


class Config:

    # Configuración general para el procesamiento de texto
    TEXT_PROCESSING_CONFIG = {
        # Patrones para identificar entidades
        "entity_patterns": [
            {"pattern": [{"LOWER": "sr"}, {"IS_TITLE": True}], "label": "PER"},
            {"pattern": [{"LOWER": "sra"}, {
                "IS_TITLE": True}], "label": "PER"},
            {"pattern": [{"LOWER": "dr"}, {"IS_TITLE": True}], "label": "PER"},
            {"pattern": [
                {"TEXT": {"REGEX": "^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+$"}}], "label": "PER"}
        ],

        # Palabras para ignorar en metadata
        "metadata_keywords": [
            "suscríbete", "dale me gusta", "atención", "video", "canal",
            "práctica", "ejercicio", "lección"
        ],

        # Expresiones que indican cambio de hablante
        "speaker_indicators": [
            "dice", "responde", "pregunta", "contesta", "explica"
        ],

        # Palabras que requieren puntuación específica
        "punctuation_rules": {
            "greetings": ["hola", "buenos días", "buenas tardes", "adiós", "gracias"],
            "affirmations": ["sí", "no", "claro", "exacto", "vale"],
            "questions": ["qué", "cómo", "dónde", "cuándo", "quién", "cuál", "por qué"],
            "conjunctions": ["pero", "y", "o", "porque", "que", "sino"]
        },

        # Configuración de formato
        "format_config": {
            "line_spacing": 2,
            "indent_size": 4,
            "max_line_length": 80,
            "capitalize_names": True
        }
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
