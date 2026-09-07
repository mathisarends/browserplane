from browser_worker.exceptions import BrowserWorkerException


class WorkerNotSupervisedException(BrowserWorkerException):
    message = "Worker has no restart policy"
