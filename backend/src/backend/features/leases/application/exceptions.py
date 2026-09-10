from backend.features.sessions.application.exceptions import SessionNotFoundException


class LeaseNotFoundException(SessionNotFoundException):
    message = "Lease not found"
