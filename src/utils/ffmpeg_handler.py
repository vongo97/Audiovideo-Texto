import os
import subprocess
from pathlib import Path


class FFmpegHandler:
    @staticmethod
    def check_ffmpeg():
        try:
            subprocess.run(['ffmpeg', '-version'],
                           capture_output=True, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    @staticmethod
    def download_ffmpeg():
        """Descarga e instala FFmpeg"""
        if os.name == 'nt':  # Windows
            # Implementar lógica de descarga para Windows
            pass
        else:  # Linux/Mac
            try:
                if os.name == 'posix':
                    subprocess.run(
                        ['apt-get', 'install', 'ffmpeg', '-y'], check=True)
            except subprocess.SubprocessError as e:
                raise Exception(f"No se pudo instalar FFmpeg: {str(e)}")
