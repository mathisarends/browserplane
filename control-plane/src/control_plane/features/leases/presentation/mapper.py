from control_plane.features.leases.application.models import Lease
from control_plane.features.leases.presentation.schemas import LeaseResponse


def to_lease_response(lease: Lease) -> LeaseResponse:
    return LeaseResponse(
        id=lease.id,
        browser_id=lease.browser_id,
        owner_id=lease.owner_id,
        expires_at=lease.expires_at,
        created_at=lease.created_at,
    )
