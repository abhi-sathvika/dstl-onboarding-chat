from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)

    messages: List["Message"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: Optional[int] = Field(
        default=None, foreign_key="conversation.id"
    )
    content: str
    role: str
    created_at: datetime = Field(default_factory=datetime.now)

    conversation: Optional[Conversation] = Relationship(
        back_populates="messages"
    )


# Response models for API serialization
class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    content: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True
