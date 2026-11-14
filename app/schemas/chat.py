from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class CreateGroupChatRequest(BaseModel):

    title: str = Field(min_length=2, max_length=150)

    participant_ids: List[int] = Field(
        min_length=1,
        max_length=100
    )


class ChatMessageResponse(BaseModel):

    id: int
    conversation_id: int
    sender_id: int
    content: str
    created_at: datetime

    edited_at: datetime | None = None
    is_deleted: bool = False


class ChatReadRequest(BaseModel):

    message_id: int