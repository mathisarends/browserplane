class BrowserWorkerError(Exception):
    pass


class BrowserWorkerResponseError(BrowserWorkerError):
    def __init__(self, status_code: int, code: str | None) -> None:
        super().__init__(f"Browser worker returned HTTP {status_code}")
        self.status_code = status_code
        self.code = code
