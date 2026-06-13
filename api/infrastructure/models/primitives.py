
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role:str = Field(description="The role of the chat actor (system | assistant | user)", alias="Role")
    message:str = Field(description="The actor message", alias="Message")

class ChatEvent(BaseModel):
    category:str = Field(description="Name of the category the event belongs to (User | Assistant | Context | LLM)")
    chat_turn_id: int = Field(description="Id of the chat turn in which the event was added")
    tag: str = Field(description="Event tag preceding the message")
    message: str = Field(description="Event content description")
   