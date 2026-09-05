from data_plane.exceptions import DataPlaneException


class DownloadNotFoundException(DataPlaneException):
    message = "Download not found"
