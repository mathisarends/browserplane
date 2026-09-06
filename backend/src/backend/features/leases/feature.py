from backend.features.leases.infrastructure import LeaseProvider
from backend.shared.feature import Feature

feature = Feature(
    name="leases",
    providers=(LeaseProvider,),
)
