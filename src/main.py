import sys
import os
import gc
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from utils.text_processor import TextProcessor
import logging

# Configurar logging más detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_system():
    """Inicializa los componentes del sistema"""
    try:
        logger.info("Iniciando configuración del sistema...")

        # Configuración de memoria y FFmpeg
        gc.enable()
        gc.set_threshold(100, 5, 5)
        os.environ['IMAGEIO_FFMPEG_EXE'] = 'ffmpeg'
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

        # Inicializar procesador de texto
        logger.info("Inicializando procesador de texto...")
        text_processor = TextProcessor()
        logger.info("Procesador de texto inicializado correctamente")

        return text_processor
    except Exception as e:
        logger.error(f"Error en la inicialización del sistema: {str(e)}")
        raise


def main():
    try:
        # Primero crear la aplicación QT
        logger.info("Iniciando aplicación Qt...")
        app = QApplication(sys.argv)

        # Luego inicializar el sistema
        text_processor = initialize_system()

        # Finalmente crear la ventana
        logger.info("Creando ventana principal...")
        window = MainWindow(text_processor)
        window.show()
        logger.info("Aplicación iniciada correctamente")

        # Ejecutar el bucle de eventos de Qt
        sys.exit(app.exec_())  # Añadir esta línea es crucial
    except Exception as e:
        logger.error(f"Error en la aplicación: {str(e)}")
        if 'app' in locals():
            QMessageBox.critical(
                None, "Error", f"Error en la aplicación: {str(e)}")
        return 1


if __name__ == "__main__":
    main()
