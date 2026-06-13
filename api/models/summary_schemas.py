from typing import Optional
from pydantic import BaseModel, Field

class ChatSummaryRequest(BaseModel):
    sysMessageTag:str = Field(description="DB tag for the summarization template to use to generate the summary",default="default")
    sysMessage:Optional[str] = Field(description="Custom summarization message. 'None' to use the tag", default=None)
    sessionId: str = Field("session database identifier for the session the current chat belongs to")
    maxTokens:int = Field(description="LLM param to limit the size of the generated summary", default=600)
    temperature:float = Field(description="LLM param to set the amount of randomness added to the response", default=0.5)
    excludeSystemUpdates:bool = Field(description="Flag to indicate wether to include or not the system instruction passed along with the chat history to the llm", default=True)
    contextLength:Optional[int] = Field(description="LLM param to limit the size of the generated summary", default=800)

class ChatSummaryResponse(BaseModel):
    sessionId: str = Field("session database identifier for the session the current chat belongs to")
    chatId: str = Field(description="database identifier for the chat collection from which the summary was made")
    prompt:str = Field("Final prompt passed to the llm")
    summary: str = Field(description="Generated summary of the current chat for the specified session")
