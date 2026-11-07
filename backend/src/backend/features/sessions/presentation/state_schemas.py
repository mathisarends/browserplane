from pydantic import BaseModel, ConfigDict, Field


class StorageItem(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: str
    value: str


class ScrollPosition(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    x: int = 0
    y: int = 0


class BrowserTabState(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    url: str
    scroll: ScrollPosition = Field(default_factory=ScrollPosition)
    session_storage: list[StorageItem] = Field(
        default_factory=list, alias="sessionStorage"
    )


class BrowserStateSchema(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    tabs: list[BrowserTabState] = Field(default_factory=list)
    active_tab_index: int = 0


class DownloadResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    filename: str
    url: str
    size: int
