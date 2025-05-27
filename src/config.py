# src/config/config.py
import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Config:
    # Ruta del archivo de configuración en el directorio de usuario
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".video_transcriber")
    CONFIG_FILE = "config.json"
    config_path = os.path.join(CONFIG_DIR, CONFIG_FILE)

    # Configuración por defecto (Versión Anterior)
    DEFAULT_CONFIG = {
        # Es mejor que la API Key esté en el archivo de configuración del usuario.
        "google_api_key": "",
        "recognizer_type": "google",  # Tipo de reconocedor por defecto
        "recognizer_language": "es-ES",  # Idioma por defecto para el reconocedor
        "translate_to_spanish": False,
        # "text_processor_type": "gemini", # <-- Esta opción no existía en la versión anterior
        "text_processing_config": {  # Configuración para el TextProcessor (formateador)
            "entity_patterns": [
                {"pattern": [{"LOWER": "sr"}, {
                    "IS_TITLE": True}], "label": "PER"},
                {"pattern": [{"LOWER": "sra"}, {
                    "IS_TITLE": True}], "label": "PER"},
                {"pattern": [{"LOWER": "dr"}, {
                    "IS_TITLE": True}], "label": "PER"},
                {"pattern": [
                    {"TEXT": {"REGEX": "^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+$"}}], "label": "PER"}
            ],
            "metadata_keywords": [
                "suscríbete", "dale me gusta", "atención", "video", "canal", "práctica", "ejercicio", "lección"
            ],
            "speaker_indicators": [
                "dice", "responde", "pregunta", "contesta", "explica"
            ],
            "punctuation_rules": {
                "greetings": ["hola", "buenos días", "buenas tardes", "adiós", "gracias"],
                "affirmations": ["sí", "no", "claro", "exacto", "vale"],
                "questions": ["qué", "cómo", "dónde", "cuándo", "quién", "cuál", "por qué"],
                "conjunctions": ["pero", "y", "o", "porque", "que", "sino"]
            },
            "format_config": {
                "line_spacing": 2,
                "indent_size": 4,
                "max_line_length": 80,
                "capitalize_names": True
            }
        }
    }

    def __init__(self):
        """Inicializa la configuración cargando desde archivo o usando valores por defecto."""
        self.settings: Dict[str, Any] = {}
        self.load_config()
        # Asegurarse de que todas las claves por defecto existan en la configuración cargada
        self._ensure_default_keys(self.settings, self.DEFAULT_CONFIG)
        self.save_config()  # Guardar para incluir nuevas claves si se añadieron

    def load_config(self):
        """Carga la configuración desde el archivo de usuario o usa la por defecto."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                # Fusionar configuración por defecto con la cargada (la cargada tiene prioridad)
                if isinstance(loaded_settings, dict):
                    self.settings = {**self.DEFAULT_CONFIG, **loaded_settings}
                    logger.info("Configuración cargada desde archivo.")
                else:
                    logger.warning(
                        f"Contenido del archivo de configuración {self.config_path} no es un diccionario. Usando configuración por defecto.")
                    self.settings = self.DEFAULT_CONFIG

            except json.JSONDecodeError as e:
                logger.error(
                    f"Error al parsear JSON del archivo de configuración {self.config_path}: {e}")
                logger.warning(
                    "Usando configuración por defecto debido a error de parseo JSON.")
                # Usar la configuración por defecto en caso de error de parseo
                self.settings = self.DEFAULT_CONFIG
            except Exception as e:
                logger.error(
                    f"Error general al cargar configuración del archivo {self.config_path}: {e}")
                logger.warning(
                    "Usando configuración por defecto debido a error de carga.")
                # Usar la configuración por defecto en caso de error
                self.settings = self.DEFAULT_CONFIG
        else:
            logger.info(
                f"Archivo de configuración no encontrado en {self.config_path}. Usando configuración por defecto.")
            self.settings = self.DEFAULT_CONFIG
            # El guardado inicial ocurre al final de __init__

    def save_config(self):
        """Guarda la configuración actual en el archivo de usuario."""
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                # Usar indent=4 para formato legible
                json.dump(self.settings, f, indent=4)
            logger.info(f"Configuración guardada en: {self.config_path}")
        except Exception as e:
            logger.error(
                f"Error al guardar configuración en el archivo {self.config_path}: {e}")

    # Método auxiliar para asegurar que las claves por defecto existan (Versión Anterior/Simplificada)
    # Esta versión es más simple y no tiene la lógica extra para diccionarios anidados
    # que añadimos para la integración de DeepSeek.
    def _ensure_default_keys(self, settings: Dict[str, Any], default_settings: Dict[str, Any]):
        """Asegura que todas las claves por defecto existan en el diccionario settings."""
        for key, default_value in default_settings.items():
            if key not in settings:
                settings[key] = default_value
                logger.debug(
                    f"DEBUG _ensure_default_keys: Clave '{key}' faltante, añadiendo valor por defecto.")
            # NOTA: Esta versión no maneja recursión para diccionarios anidados.
            # Si text_processing_config faltara completamente, se añadiría como dict vacío.

    # --- Métodos Getter y Setter para acceder a la configuración ---

    def get_google_api_key(self) -> str:
        # Usar .get() con valor por defecto para seguridad
        return self.settings.get("google_api_key", self.DEFAULT_CONFIG.get("google_api_key", ""))

    def set_google_api_key(self, api_key: str):
        self.settings["google_api_key"] = api_key
        self.save_config()

    def get_recognizer_type(self) -> str:
        # Usar .get() con valor por defecto para seguridad
        return self.settings.get("recognizer_type", self.DEFAULT_CONFIG.get("recognizer_type", "google"))

    def set_recognizer_type(self, recognizer_type: str):
        self.settings["recognizer_type"] = recognizer_type
        self.save_config()

    def get_recognizer_language(self) -> str:
        # Usar .get() con valor por defecto para seguridad
        return self.settings.get("recognizer_language", self.DEFAULT_CONFIG.get("recognizer_language", "es-ES"))

    def set_recognizer_language(self, language: str):
        self.settings["recognizer_language"] = language
        self.save_config()

    def get_text_processing_config(self) -> Dict[str, Any]:
        # Usar .get() con valor por defecto para seguridad
        # Devolvemos una copia defensiva si la estructura interna fuera mutable y expuesta
        # pero para dicts simples, get basta.
        return self.settings.get("text_processing_config", self.DEFAULT_CONFIG.get("text_processing_config", {}))

    def get_deepseek_api_key(self) -> str:
        return self.settings.get("deepseek_api_key", self.DEFAULT_CONFIG.get("deepseek_api_key", ""))

    def set_deepseek_api_key(self, api_key: str):
        self.settings["deepseek_api_key"] = api_key
        self.save_config()

    def get_text_processor_type(self) -> str:
        return self.settings.get("text_processor_type", self.DEFAULT_CONFIG.get("text_processor_type", "gemini"))

    def set_text_processor_type(self, processor_type: str):
        self.settings["text_processor_type"] = processor_type
        self.save_config()
    # --- Métodos Getter y Setter para text_processor_type (ELIMINADOS en esta versión) ---
    # def get_text_processor_type(self) -> str: ...
    # def set_text_processor_type(self, processor_type: str): ...

    # Puedes añadir más getters/setters si expones más opciones de configuración
