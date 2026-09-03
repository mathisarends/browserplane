from control_plane.exceptions import ControlPlaneException


class LeaseNotFoundException(ControlPlaneException):
    message = "Lease not found"
