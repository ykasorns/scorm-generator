from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal, Dict, Any
import re

ItemType = Literal["page", "video", "quiz", "scenario"]
ScormEdition = Literal["1.2", "2004"]

ISO8601_DURATION = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")

class TimelineItem(BaseModel):
    id: str
    type: ItemType
    title: str = Field(min_length=1, max_length=160)
    content: Optional[str] = None
    asset_ref: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class Module(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=160)
    items: List[TimelineItem] = Field(default_factory=list)

    @validator("items")
    def ensure_items(cls, v):
        if not v:
            raise ValueError("Module must have at least 1 item")
        return v

class ScormSettings(BaseModel):
    edition: ScormEdition = "2004"
    schemaVersion: str = "4th"
    masteryScore: int = 80
    maxTimeAllowed: str = "PT30M"
    completionBy: str = "completed"
    successBy: str = "passed"
    launchInNewWindow: bool = True
    suspendDataLimitGuard: bool = True
    reportInteractions: bool = True

    @validator("masteryScore")
    def mastery_range(cls, v):
        if v < 0 or v > 100:
            raise ValueError("masteryScore must be between 0 and 100")
        return v

    @validator("maxTimeAllowed")
    def duration_format(cls, v):
        if not ISO8601_DURATION.match(v):
            raise ValueError("maxTimeAllowed must be ISO8601 duration like PT30M, PT1H, PT10M30S")
        return v

class Project(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    language: str = Field(default="en", max_length=12)
    version: str = Field(default="1.0.0", max_length=24)
    scorm: ScormSettings = Field(default_factory=ScormSettings)
    structure: List[Module] = Field(default_factory=list)

    # "A" => keep everything (we'll store ui_state too in persistence)
    ui_state: Dict[str, Any] = Field(default_factory=dict)

    @validator("structure")
    def ensure_structure(cls, v):
        if not v:
            raise ValueError("Project must have at least 1 module")
        return v
