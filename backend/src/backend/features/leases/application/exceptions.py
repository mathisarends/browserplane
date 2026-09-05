from backend.exceptions import BackendException


class LeaseNotFoundException(BackendException):
    message = "Lease not found"
