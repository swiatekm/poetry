import json

from pathlib import Path

from poetry.core.toml.file import TOMLFile
from poetry.installation import Installer as BaseInstaller
from poetry.installation.executor import Executor as BaseExecutor
from poetry.installation.noop_installer import NoopInstaller
from poetry.packages import Locker as BaseLocker
from poetry.repositories.installed_repository import InstalledRepository


class Installer(BaseInstaller):
    def _get_installer(self):
        return NoopInstaller()


class Executor(BaseExecutor):
    def __init__(self, *args, **kwargs):
        super(Executor, self).__init__(*args, **kwargs)

        self._installs = []
        self._updates = []
        self._uninstalls = []

    @property
    def installations(self):
        return self._installs

    @property
    def updates(self):
        return self._updates

    @property
    def removals(self):
        return self._uninstalls

    def _do_execute_operation(self, operation):
        super(Executor, self)._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, "_{}s".format(operation.job_type)).append(operation.package)

    def _execute_install(self, operation):
        return 0

    def _execute_update(self, operation):
        return 0

    def _execute_uninstall(self, operation):
        return 0


class CustomInstalledRepository(InstalledRepository):
    @classmethod
    def load(cls, env):
        return cls()


class Locker(BaseLocker):
    def __init__(self, lock=None):
        lock = lock or Path.cwd().joinpath("poetry.lock")
        self._lock = TOMLFile(lock)
        self._written_data = None
        self._locked = False
        self._content_hash = self._get_content_hash()

    @property
    def written_data(self):
        return self._written_data

    def set_lock_path(self, lock):
        self._lock = TOMLFile(Path(lock).joinpath("poetry.lock"))

        return self

    def locked(self, is_locked=True):
        self._locked = is_locked

        return self

    def mock_lock_data(self, data):
        self._lock_data = data

    def is_locked(self):
        return self._locked

    def is_fresh(self):
        return True

    def _get_content_hash(self):
        return "123456789"

    def _write_lock_data(self, data):
        for package in data["package"]:
            python_versions = str(package["python-versions"])
            package["python-versions"] = python_versions

        self._written_data = json.loads(json.dumps(data))
        self._lock_data = data
