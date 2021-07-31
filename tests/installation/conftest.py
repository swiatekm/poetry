import pytest

from cleo.io.null_io import NullIO

from poetry.core.packages.project_package import ProjectPackage
from poetry.repositories import Pool
from poetry.repositories import Repository
from poetry.utils.env import NullEnv

from .helpers import CustomInstalledRepository
from .helpers import Executor
from .helpers import Installer
from .helpers import Locker


@pytest.fixture
def cwd(fixture_base):
    return fixture_base


@pytest.fixture()
def package(cwd):
    p = ProjectPackage("root", "1.0")
    p.root_dir = cwd

    return p


@pytest.fixture()
def repo():
    return Repository()


@pytest.fixture()
def pool(repo):
    pool = Pool()
    pool.add_repository(repo)

    return pool


@pytest.fixture()
def installed():
    return CustomInstalledRepository()


@pytest.fixture()
def locker(cwd):
    # the lockfile only matters insofar as the paths of file dependencies are stored
    # relative to its path
    lockfile = cwd / "poetry.lock"
    return Locker(lock=lockfile)


@pytest.fixture()
def env():
    return NullEnv()


@pytest.fixture()
def installer(package, pool, locker, env, installed, config):
    installer = Installer(
        NullIO(),
        env,
        package,
        locker,
        pool,
        config,
        installed=installed,
        executor=Executor(env, pool, config, NullIO()),
    )
    installer.use_executor(True)

    return installer
