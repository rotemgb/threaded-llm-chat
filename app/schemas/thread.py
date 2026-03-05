from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ThreadCreate(BaseModel):
    system_prompt: str
    title: Optional[str] = None
    initial_model: Optional[str] = None


class ThreadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: Optional[str]
    system_prompt: str
    current_model: Optional[str]
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str
    sender: Optional[str] = None
    model: Optional[str] = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    thread_id: int
    role: str
    sender: Optional[str]
    content: str
    model_id: Optional[str]
    created_at: datetime


class SummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    level: int
    summary_text: str
    covers_up_to_message_id: Optional[int]
    created_at: datetime

