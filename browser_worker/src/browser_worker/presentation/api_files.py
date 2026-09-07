from collections.abc import Iterable
from typing import Any, Final

from fastapi import status

from browser_worker.presentation.api_errors import ApiErrorSpec, api_error_responses

OCTET_STREAM: Final = "application/octet-stream"

_BINARY_SCHEMA: Final = {"type": "string", "format": "binary"}


def api_file_response(
    description: str,
    *errors: ApiErrorSpec,
    media_types: Iterable[str] = (OCTET_STREAM,),
) -> dict[int | str, dict[str, Any]]:
    """Build the OpenAPI ``responses`` entry for a binary file body."""
    return {
        status.HTTP_200_OK: {
            "content": {
                media_type: {"schema": _BINARY_SCHEMA} for media_type in media_types
            },
            "description": description,
        },
        **api_error_responses(*errors),
    }
