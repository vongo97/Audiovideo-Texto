import sys
import os
import gc
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    # Configuración de memoria y FFmpeg
    gc.enable()
    gc.set_threshold(100, 5, 5)  # Recolección de basura más agresiva

    # Configurar FFmpeg
    os.environ['IMAGEIO_FFMPEG_EXE'] = 'ffmpeg'

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
