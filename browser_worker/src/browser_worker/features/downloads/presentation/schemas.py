from pydantic import BaseModel, ConfigDict


class DownloadResponse(BaseModel):
    """A completed download as the API reports it."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    url: str
    size: int
