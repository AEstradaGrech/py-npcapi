from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SystemMessageDto(BaseModel):
    id:str = Field(description="Db identifier for the system message document")
    type: int = Field(description="Type of message enum id")
    description: str = Field(description="Brief description of the system message content or purpose, usually the type of message description (BaseTemplate, OutputAction, ChatContraints...)")
    message:str = Field(description="Actual content of the system instruction to pass to the LLM")
    tag: Optional[str] = Field(None, description="Tags a chat session with something meaningful for the user. Usually the name of the chat participants (<botname-username>)")

class CollectionResponse(BaseModel):
    data: List[Any] = Field(description="An array with the requested data", default=[])
    total_records: int = Field(description="Total documents matching the current query", default=None)
    page:int = Field(description="The current page. Index begins in 0 (the last page will be always 'total_pages -1')", default=None)
    total_pages:int = Field(description="Number of pages available for the current query", default=None)

class SysMessageTypeDto(BaseModel):
    type: int = Field(description="Numeric identifier")
    description: str = Field(description="Message type label")

class ChatSummaryDto(BaseModel):
    id:str = Field(description="Db identifier for a user chat session")
    sysMessageTag: str = Field("system template tag used to generate the final LLM prompt")
    summary: str = Field(description="Generated summary of the current chat for the specified session")

class SummaryDto(BaseModel):
    id:Optional[str] = Field(description="Db identifier for a user chat session")
    sysMessageTag: str = Field("system template tag used to generate the final LLM prompt")
    sysMessage: Optional[str] = Field("syste message used to generate the final LLM prompt")
    sessionId: str = Field("session database identifier for the session the current chat belongs to")
    chatId: str = Field(description="database identifier for the chat collection from which the summary was made")
    creationDate: Optional[str] = Field(description="self-explanatory")
    prompt:str = Field("Final prompt passed to the llm")
    summary: str = Field(description="Generated summary of the current chat for the specified session")
    observations: List[str] = Field(description="An array with a collection of observations (if any) for the generated summary", default=[])

class QueryCondition(BaseModel):
    field: str = Field(description="Name of the desired document field to use for filtering")
    value: Any = Field(description="The value for this condition")
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
class QueryFilter(BaseModel):
    conditions: List[QueryCondition] = Field(description="Array of conditions to build the query", default=[])
    page_size: Optional[int] = Field(description="Number of elements to return for the query. All of them if empty", default=None)
    page:Optional[int] = Field(description="Requested page", default=None)
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

class ModelIntegrationSettingsDto(BaseModel):
    provider:str = Field(description="The current LLM provider running in the API. Available providers: gpt4all | ollama [todo: hug-tf, hug-api, llamacpp]")
    model:str = Field(description="Name of the model to load. Depends on the available for the requested provider (check /available-models endpoint)")
    temp:Optional[int] = Field(None, description="parameter in your LLMConfig object to control the randomness of the sampling process used by the LLM to generate responses. ")   
    top_p:Optional[float] = Field(None, description="parameter in your LLMConfig object to control the cumulative probability of token selections up to that point")
    top_k:Optional[int] = Field(None,description="parameter in your LLMConfig object to control the number of highest-scoring tokens that are considered when generating responses.")
    max_tokens:Optional[int] = Field(None,description="param in your LLM to control the size of the output response")  
    repeat_last_n:Optional[int] = Field(None,description="parameter in your LLMConfig object to control how many times previous tokens are repeated during generation. ")
    repeat_penalty:Optional[float] = Field(None,description="Penalize the model for repetition. Higher values result in less repetition.")
    n_threads:Optional[int] = Field(None,description="number of CPU processor threads to use in parallel computations")
    ngl:Optional[int] = Field(None,description="number of NN Layers to load in the GPU")
    ctx_len:Optional[int] = Field(None,description="Lenght of the LLM context window")

class SpacyNER(BaseModel):
    text:str = Field(description="Analyzed token")
    label:str = Field(description="Token classification label")
    start:int = Field(description="Token starting character position")
    end:int = Field(description="Token ending position")