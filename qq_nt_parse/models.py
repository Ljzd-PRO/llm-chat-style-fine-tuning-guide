import base64
from datetime import datetime
from functools import cached_property
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from enums import NTGroupMsgFieldEnum


class NTGroupMsgModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    group_id: Optional[int] = Field(None, alias=str(NTGroupMsgFieldEnum.GROUP_ID.value))
    time: Optional[datetime] = Field(None, alias=str(NTGroupMsgFieldEnum.TIME.value))
    name: Optional[str] = Field(None, alias=str(NTGroupMsgFieldEnum.NAME.value))
    raw_message: Optional[bytes] = Field(None, alias=str(NTGroupMsgFieldEnum.MESSAGE.value))
    user_id: Optional[int] = Field(None, alias=str(NTGroupMsgFieldEnum.USER_ID.value))

    @field_validator("time", mode="before")
    def validate_time(cls, value):
        return None if not value else value

    @cached_property
    def message_from_base64(self) -> Optional[bytes]:
        return base64.decodebytes(self.raw_message) if self.raw_message else None

    @cached_property
    def message_from_unicode(self) -> bytes:
        return self.raw_message.decode().encode()
