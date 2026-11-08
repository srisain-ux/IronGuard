"""Request envelopes not originally covered by the shared contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SafetyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: dict
    entities: dict
    source: Literal["web", "photon"] = "web"
    text: str | None = Field(default=None, max_length=20000)

    @model_validator(mode="after")
    def protect_web_text(self):
        if self.source == "web" and self.text is not None:
            raise ValueError("Message text is accepted only in opt-in Photon mode")
        return self


class ZeroDayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alert: str = Field(min_length=1, max_length=400, pattern=r"\S")
