from control_plane.shared.exceptions import ControlPlaneException


class LeaseNotFoundException(ControlPlaneException):
    message = "Lease not found"
