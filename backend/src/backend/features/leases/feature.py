from fastapi_canon import Feature

from backend.features.leases.infrastructure.provider import LeaseProvider

feature = Feature(
    name="leases",
    providers=(LeaseProvider,),
)
