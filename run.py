#!/usr/bin/env python
# run.py - Script para ejecutar la aplicación Video Transcriber

import os
import sys

# Añadir el directorio src al path para poder importar los módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Importar el módulo main
from src import main

# Ejecutar la aplicación
if __name__ == "__main__":
    # El código principal ya está en el bloque if __name__ == "__main__" de main.py
    # Así que simplemente importar main es suficiente
    pass