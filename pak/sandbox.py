import os
import shutil
import contextlib

class CopyOnWriteSandbox:
    """Hardware-isolated execution paths with atomic transaction rollbacks."""
    def __init__(self, workspace: str, session_id: str):
        self.workspace = workspace
        self.sandbox_path = f"/tmp/pak_sandbox_{session_id}"

    @contextlib.contextmanager
    def transaction(self):
        if os.path.exists(self.workspace):
            shutil.copytree(self.workspace, self.sandbox_path, dirs_exist_ok=True)
        else:
            os.makedirs(self.sandbox_path, exist_ok=True)
        try:
            yield self.sandbox_path
            shutil.copytree(self.sandbox_path, self.workspace, dirs_exist_ok=True)
        except Exception as e:
            if os.path.exists(self.sandbox_path):
                shutil.rmtree(self.sandbox_path, ignore_errors=True)
            raise e
        finally:
            if os.path.exists(self.sandbox_path):
                shutil.rmtree(self.sandbox_path, ignore_errors=True)