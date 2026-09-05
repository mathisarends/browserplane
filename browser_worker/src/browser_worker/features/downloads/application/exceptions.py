from browser_worker.exceptions import BrowserWorkerException


class DownloadNotFoundException(BrowserWorkerException):
    message = "Download not found"
