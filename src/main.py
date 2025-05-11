# src/main.py
import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
import logging

# Importar los procesadores y reconocedores específicos usando IMPORTACIONES RELATIVAS
# Ya que main.py está dentro del paquete src, usamos '.' para referenciar subpaquetes dentro de src
from .utils.gemini_processor import GeminiProcessor  # <-- Importación relativa
from .utils.text_processor import TextProcessor  # <-- Importación relativa
from .transcriber.google_recognizer import GoogleRecognizer  # <-- Importación relativa
# <-- Importación relativa
from .transcriber.whisper_recognizer import WhisperRecognizer
# <-- Importación relativa (para la interfaz base)
from .transcriber.speech_recognition_factory import SpeechRecognizer

from .ui.main_window import MainWindow  # <-- Importación relativa

# Importación relativa para Config
# Asumiendo que config.py está en src/config/config.py
from .config import Config  # <-- Importación relativa corregida

# Importación relativa para audio_extractor
# audio_extractor.py está en src/transcriber, main.py está en src
# <-- Importación relativa corregida
from .transcriber.audio_extractor import extract_and_transcribe

from typing import Dict, Any, Union

# Configurar el nivel de logging
logging.basicConfig(level=logging.INFO,  # <-- Nivel de logging INFO por defecto
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instancia global de Config
config = Config()


# --- Función principal que contendrá la mayor parte de la lógica de la aplicación ---
# Definir esta función ayuda a crear un scope de función necesario para 'nonlocal'
def main_app_flow():
    logger.info("Iniciando flujo principal de la aplicación...")

    # --- Inicialización de variables que serán usadas en este scope y en funciones anidadas (nonlocal) ---
    # Deben ser definidas aquí antes de ser referenciadas por 'nonlocal'
    # <-- Instancia de GeminiProcessor
    gemini_processor_instance: GeminiProcessor | None = None
    formatter_instance: TextProcessor | None = None  # El formateador
    recognizer_instance: SpeechRecognizer | None = None  # Instancia del reconocedor
    current_recognizer_type: str | None = None  # Tipo de reconocedor actual
    current_language: str | None = None  # Idioma actual
    main_window: MainWindow | None = None  # La ventana principal

    # --- Función para manejar cambios en la configuración desde la UI (definida DENTRO de main_app_flow) ---
    # En la versión anterior, esta función probablemente solo manejaba el tipo de reconocedor y el idioma.

    def handle_config_change(new_config_values: Dict[str, Any]):
        """
        Maneja los cambios en la configuración reportados por la UI.
        Actualiza la instancia global de Config, guarda, y re-inicializa componentes si es necesario.
        """
        logger.info(
            f"Cambio de configuración detectado desde UI: {new_config_values}")

        # Acceder a las variables del scope exterior que necesitamos modificar o usar
        # gemini_processor_instance y formatter_instance no cambian aquí
        nonlocal recognizer_instance, current_language, main_window

        config_updated = False  # Flag para saber si algo relevante cambió
        # Flag para saber si necesitamos re-inicializar el reconocedor
        reinitialize_recognizer = False

        # --- Manejar cambios en el tipo de reconocedor y idioma ---
        if "recognizer_type" in new_config_values and new_config_values["recognizer_type"] != config.get_recognizer_type():
            config.set_recognizer_type(new_config_values["recognizer_type"])
            config_updated = True
            reinitialize_recognizer = True
            logger.info(
                f"Tipo de reconocedor cambiado a: {config.get_recognizer_type()}")

        if "recognizer_language" in new_config_values and new_config_values["recognizer_language"] != config.get_recognizer_language():
            config.set_recognizer_language(
                new_config_values["recognizer_language"])
            config_updated = True
            # El idioma también puede requerir re-inicializar (algunos reconocedores)
            reinitialize_recognizer = True
            logger.info(
                f"Idioma del reconocedor cambiado a: {config.get_recognizer_language()}")

        # NOTA: En la versión anterior, no se manejaba el cambio de text_processor_type aquí.

        # Guardar la configuración actualizada en el archivo si algo cambió relevantemente
        if config_updated:
            config.save_config()
            logger.info("Configuración actualizada y guardada.")

        # --- Re-inicializar reconocedor si es necesario ---
        if reinitialize_recognizer:
            logger.info(
                "Re-inicializando reconocedor con nueva configuración...")
            try:
                new_recognizer_type = config.get_recognizer_type()
                new_language = config.get_recognizer_language()

                # Versión anterior: Inicializa reconocedores directamente (sin fábrica)
                if new_recognizer_type.lower() == "google":
                    recognizer_instance = GoogleRecognizer()
                elif new_recognizer_type.lower() == "whisper":
                    recognizer_instance = WhisperRecognizer()
                else:
                    # Fallback a Google si el tipo es desconocido
                    logger.warning(
                        f"Tipo de reconocedor desconocido: '{new_recognizer_type}'. Usando 'google' como fallback.")
                    recognizer_instance = GoogleRecognizer()
                    # Actualizar config si se usa fallback
                    config.set_recognizer_type("google")

                current_language = new_language  # Actualizar la variable local

                logger.info(
                    f"Nuevo reconocedor '{config.get_recognizer_type()}' inicializado correctamente con idioma '{current_language}'.")

                # Pasar la nueva instancia y idioma al área de arrastre
                if main_window:
                    # CORREGIDO: Pasar la instancia de Gemini como el argumento ai_text_processor
                    main_window.drag_drop_area.set_processors(
                        ai_text_processor=gemini_processor_instance,  # <-- Pasar como ai_text_processor
                        # Pasar la instancia del formateador (no cambia)
                        formatter=formatter_instance,
                        recognizer=recognizer_instance,  # <-- Pasar la nueva instancia del reconocedor
                        language=current_language  # <-- Pasar el idioma actualizado
                    )
                    logger.info(
                        "Área de arrastre actualizada con el nuevo reconocedor y idioma.")

            except Exception as e_reinit_rec:
                logger.error(
                    f"Error al re-inicializar reconocedor: {e_reinit_rec}")
                if main_window:
                    QMessageBox.critical(main_window, "Error al actualizar reconocedor",
                                         f"No se pudo actualizar el reconocedor:\n{e_reinit_rec}")
                # Considerar revertir la UI

    # --- Código que estaba directamente en if __name__ y ahora va DENTRO de main_app_flow ---

    # Verificar la API Key (esto puede estar aquí o movido completamente al if __name__)
    # Si está aquí, se verifica cada vez que se llama a main_app_flow.
    # Si solo se llama una vez desde if __name__, puede estar fuera.
    # Manteniéndolo aquí permite llamar main_app_flow en otros contextos si fuera necesario.
    # Sin embargo, el QMessageBox requiere un QApplication, así que la verificación inicial en if __name__ es mejor.
    # Asegúrate de que la API Key se obtiene ANTES de intentar inicializar procesadores que la requieran.

    # La verificación inicial de la API Key se hace en el bloque if __name__

    api_key = config.get_google_api_key()

    # Inicializar las instancias de los procesadores y obtener config inicial (DENTRO de main_app_flow)
    try:
        # Inicializa GeminiProcessor y TextProcessor
        gemini_processor_instance = GeminiProcessor(api_key=api_key)
        logger.info("GeminiProcessor inicializado correctamente.")

        text_processing_config = config.get_text_processing_config()
        formatter_instance = TextProcessor(
            text_processing_config=text_processing_config)
        logger.info("TextProcessor (Formateador) inicializado correctamente")

        # Obtener el idioma y el tipo de reconocedor de la configuración inicial
        current_language = config.get_recognizer_language()
        logger.info(
            f"Idioma del reconocedor configurado: '{current_language}'")

        current_recognizer_type = config.get_recognizer_type()
        logger.info(
            f"Tipo de reconocedor configurado: '{current_recognizer_type}'")

        # Inicializa el Reconocedor
        try:
            if current_recognizer_type.lower() == "google":
                recognizer_instance = GoogleRecognizer()
            elif current_recognizer_type.lower() == "whisper":
                recognizer_instance = WhisperRecognizer()
            else:
                # Fallback a Google si el tipo es desconocido
                logger.warning(
                    f"Tipo de reconocedor desconocido en config: '{current_recognizer_type}'. Usando 'google' como fallback.")
                recognizer_instance = GoogleRecognizer()
                # Actualizar config si se usa fallback
                config.set_recognizer_type("google")

            logger.info(
                f"Reconocedor '{config.get_recognizer_type()}' inicializado correctamente.")

        # --- CORRECCIÓN DEL ÁMBITO DE e_rec ---
        # Si ocurre un error al inicializar el reconocedor...
        except Exception as e_rec_initial:  # Capturamos el error inicial como e_rec_initial
            logger.error(
                f"Error al inicializar el reconocedor '{current_recognizer_type}': {e_rec_initial}")
            # Intentar fallback a google si no era google y falló
            if current_recognizer_type.lower() != "google":
                logger.warning(
                    "Intentando inicializar 'google' como alternativa...")
                current_recognizer_type = "google"  # Actualizar la variable y la config
                try:
                    recognizer_instance = GoogleRecognizer()  # Intentar Google directamente
                    config.set_recognizer_type(current_recognizer_type)
                    logger.info(
                        "Reconocedor 'google' inicializado como alternativa.")
                except Exception as e_rec_fallback:  # Capturamos el error del fallback como e_rec_fallback
                    # Si google fallback falla, es un error fatal para el reconocedor
                    # El mensaje de error ahora usa la excepción del fallback (e_rec_fallback)
                    raise Exception(
                        f"Error fatal al inicializar el reconocedor y fallback: {e_rec_fallback}") from e_rec_fallback
            else:
                # Si el reconocedor configurado era google y falló, es un error fatal
                # El mensaje de error ahora usa la excepción inicial (e_rec_initial)
                raise Exception(
                    f"Error fatal al inicializar el reconocedor '{current_recognizer_type}': {e_rec_initial}") from e_rec_initial

    except Exception as e_fatal_init:  # Capturar errores durante la inicialización de componentes principales DENTRO de main_app_flow
        logger.error(
            f"Error fatal al inicializar componentes: {str(e_fatal_init)}")
        # Mostrar un mensaje de error usando QMessageBox
        # La app QApplication ya está corriendo, así que podemos mostrar mensajes aquí
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error de Inicialización")
        # El mensaje de error ahora usa la excepción fatal capturada (e_fatal_init)
        msg_box.setText(
            f"Error al inicializar los componentes necesarios:\n{str(e_fatal_init)}")
        msg_box.exec_()  # Mostrar el mensaje y esperar que el usuario lo cierre
        # Salir si falla la inicialización
        sys.exit(f"Error al inicializar componentes: {str(e_fatal_init)}")

    # --- Verificaciones después de la inicialización (DENTRO de main_app_flow) ---
    # Asegurarse de que todas las instancias necesarias se crearon
    if gemini_processor_instance is None or formatter_instance is None:
        logger.fatal(
            "Los procesadores de texto no se inicializaron correctamente.")
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error Interno")
        msg_box.setText(
            "Algunos procesadores de texto no pudieron ser inicializados.")
        msg_box.exec_()
        sys.exit("Error interno: Procesadores de texto no inicializados.")

    if recognizer_instance is None:
        logger.fatal("El reconocedor de voz no se inicializó.")
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error Interno")
        msg_box.setText("El reconocedor de voz no pudo ser inicializado.")
        msg_box.exec_()
        sys.exit("Error interno: Reconocedor no inicializado.")

    if current_language is None:
        # Esto no debería pasar si la configuración se carga, pero es una seguridad
        logger.fatal(
            "El código de idioma del reconocedor no se obtuvo de la configuración.")
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error Interno")
        msg_box.setText(
            "El código de idioma del reconocedor no pudo ser obtenido.")
        msg_box.exec_()
        sys.exit("Error interno: Idioma no obtenido.")

    logger.info("Creando ventana principal...")
    # Crear la ventana principal.
    # Pasar la configuración a la UI
    main_window = MainWindow(config_settings=config.settings)

    # --- Conectar la señal config_changed de MainWindow al manejador handle_config_change (DENTRO de main_app_flow) ---
    # La función handle_config_change está definida justo encima en este mismo scope (main_app_flow)
    main_window.config_changed.connect(handle_config_change)

    # --- Pasar las instancias iniciales al área de arrastre al inicio (DENTRO de main_app_flow) ---
    # Esto configura el área de arrastre con los procesadores y reconocedor iniciales
    # CORREGIDO: Pasar la instancia de Gemini como el argumento ai_text_processor
    main_window.drag_drop_area.set_processors(
        ai_text_processor=gemini_processor_instance,  # <-- Pasar como ai_text_processor
        formatter=formatter_instance,  # <-- Pasar Formatter
        recognizer=recognizer_instance,
        language=current_language
    )

    # --- Mostrar ventana y entrar al bucle de eventos de Qt (DENTRO de main_app_flow) ---
    main_window.show()
    logger.info("Aplicación iniciada correctamente")
    # Iniciar el bucle de eventos de la aplicación Qt.
    # Esto bloquea la ejecución hasta que la aplicación se cierra.
    # DEBE HABER SOLO UN app.exec_()
    sys.exit(app.exec_())


# --- Punto de entrada real del script (bloque if __name__ == "__main__") ---
# Este bloque se ejecuta cuando el script es el programa principal.
if __name__ == "__main__":
    # Mensaje de debug actualizado
    print("--- DEBUG: Ejecutando version anterior ---")

    # Inicializar la aplicación Qt UNA VEZ al principio
    app = QApplication(sys.argv)
    logger.info("Iniciando aplicación Qt...")

    # Verificar la API Key aquí también, para mostrar el QMessageBox ANTES de inicializar
    # cualquier cosa que dependa de ella (procesadores).
    # Usamos la instancia global config
    GEMINI_API_KEY_INITIAL = config.get_google_api_key()

    if not GEMINI_API_KEY_INITIAL:
        GEMINI_API_KEY_ENV = os.environ.get("GOOGLE_API_KEY")
        logger.info(
            "API Key no encontrada en config. Intentando leer de variable de entorno GOOGLE_API_KEY.")

        if GEMINI_API_KEY_ENV:
            logger.info(
                "API Key encontrada en GOOGLE_API_KEY. Guardando en archivo de configuración.")
            # Guardar en config para futuras ejecuciones
            config.set_google_api_key(GEMINI_API_KEY_ENV)
            # Usar la clave del entorno para esta ejecución
            GEMINI_API_KEY_INITIAL = GEMINI_API_KEY_ENV

    if not GEMINI_API_KEY_INITIAL:
        logger.error(
            "La API Key de Google Gemini no está configurada en el archivo de configuración ni como variable de entorno GOOGLE_API_KEY.")
        # Mostrar un mensaje de error al usuario y salir
        # Se puede mostrar QMessageBox porque QApplication ya está corriendo
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Error de Configuración")
        msg_box.setText(
            f"La API Key de Google Gemini no está configurada.\nPor favor, añade tu clave al archivo:\n{config.config_path}\n\nO establece la variable de entorno GOOGLE_API_KEY.")
        msg_box.exec_()  # Mostrar el mensaje y esperar que el usuario lo cierre
        # Salir del script
        sys.exit("Error de configuración: API Key no configurada.")

    # Si la API Key está bien, llamamos a la función principal que inicia la UI y la lógica.
    # Esta función contiene el bucle principal de la aplicación Qt (app.exec_()).
    main_app_flow()

    # El código después de main_app_flow() solo se ejecutará después de que la aplicación Qt se cierre.
    logger.info("Aplicación finalizada.")
