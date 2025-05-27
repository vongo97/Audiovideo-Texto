#!/usr/bin/env python
# run.py - Script para ejecutar la aplicación Video Transcriber

import os
import sys

# Añadir el directorio src al path para poder importar los módulos
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'src')))

# Ejecutar la aplicación
if __name__ == "__main__":
    from src.main import main_app_flow

    # Inicializar la aplicación Qt
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)

    # Ejecutar la función principal
    main_app_flow(app)
