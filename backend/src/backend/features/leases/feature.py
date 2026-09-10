from fastapi_canon import Feature

from backend.features.leases.infrastructure import LeaseProvider

feature = Feature(
    name="leases",
    providers=(LeaseProvider,),
)
