import os
import shutil
import tempfile
import pytest

import recon.storage.store as store_mod


@pytest.fixture(autouse=True, scope="session")
def isolate_test_recon_home():
    """Isolates all test runs to a temporary RECON_HOME so the real .recon database is untouched."""
    temp_dir = tempfile.mkdtemp(prefix="recon_test_home_")
    old_home = os.environ.get("RECON_HOME")
    os.environ["RECON_HOME"] = temp_dir

    # Reset singleton store so routes and tests bind to the isolated test DB
    store_mod._DEFAULT_STORE = None

    yield temp_dir

    if old_home is not None:
        os.environ["RECON_HOME"] = old_home
    else:
        os.environ.pop("RECON_HOME", None)

    store_mod._DEFAULT_STORE = None
    shutil.rmtree(temp_dir, ignore_errors=True)
