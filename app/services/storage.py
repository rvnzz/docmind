import os
import shutil
from pathlib import Path

class LocalStorageManager:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir or os.getenv("DOCUMENTS_DIR", "./documents"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, filename, content):
        path = self.base_dir / filename
        with open(path, "wb") as f:
            f.write(content)
        return str(path)

    def delete_file(self, path):
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except:
            return False

    def file_exists(self, path):
        return os.path.exists(path)

    def get_file_path(self, filename):
        return str(self.base_dir / filename)

    def delete_directory(self):
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
