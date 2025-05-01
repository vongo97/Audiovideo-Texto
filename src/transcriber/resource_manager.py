from contextlib import contextmanager
import os


class ResourceManager:
    @contextmanager
    def managed_audio_file(self, audio_file):
        try:
            yield audio_file
        finally:
            if hasattr(audio_file, 'close'):
                audio_file.close()

    @contextmanager
    def managed_temp_file(self, file_path):
        try:
            yield file_path
        finally:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
