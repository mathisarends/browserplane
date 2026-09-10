from fastapi_canon import ErrorRegistry

from browser_worker.features.browser.presentation.errors import ERRORS as BROWSER_ERRORS
from browser_worker.features.downloads.presentation.errors import (
    ERRORS as DOWNLOAD_ERRORS,
)
from browser_worker.features.recordings.presentation.errors import (
    ERRORS as RECORDING_ERRORS,
)
from browser_worker.features.release.presentation.errors import ERRORS as RELEASE_ERRORS
from browser_worker.features.state.presentation.errors import ERRORS as STATE_ERRORS

API_ERRORS = ErrorRegistry.merge(
    BROWSER_ERRORS,
    STATE_ERRORS,
    DOWNLOAD_ERRORS,
    RECORDING_ERRORS,
    RELEASE_ERRORS,
    name="browser-worker-api",
)
