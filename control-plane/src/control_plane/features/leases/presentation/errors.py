from typing import Literal

from fastapi import status

from control_plane.features.leases.application.exceptions import LeaseNotFoundException
from control_plane.presentation.api_errors import ApiErrorSpec
from control_plane.presentation.errors import ApiErrorCode, ApiErrorResponse


class LeaseNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.LEASE_NOT_FOUND]


LEASE_NOT_FOUND = ApiErrorSpec(
    exceptions=(LeaseNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.LEASE_NOT_FOUND,
    response_model=LeaseNotFoundError,
    description="Lease not found",
)

API_ERRORS = (LEASE_NOT_FOUND,)
