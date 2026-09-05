from pydantic import BaseModel


class DownloadResponse(BaseModel):
    id: str
    filename: str
    url: str
    size: int
