from datetime import datetime
from typing import Any, List, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

from api.infrastructure.models.primitives import ChatEvent, ChatMessage
from api.infrastructure.repositories.mongo.base_repo import PyObjectId
from api.models.prompting_schemas import ChatDocDto
from api.models.schemas import InitSessionRequest
from api.utils.statics import default_chat_history_length


class ChatPromptDoc(BaseModel):
    id:Optional[PyObjectId] = Field(description="Db identifier for a collection of prompts from a chat session", alias="_id", default_factory=ObjectId)
    session_id: Optional[str] = Field(description="Db identifier for the user session", alias="sessionId", default=None)
    model: str = Field(description="The infered LLM name", default="")
    tag: str = Field(description="A field to tag the record with meaningful info, usually the bot name and user name to identify the chats by actors",default="")
    max_tokens: int = Field(description="The max tokens setting passed to the LLM", alias="maxTokens", default=0)
    temperature: float = Field(description="The temperature setting passed to the LLM", default=0.0)
    user_name: str = Field(description="The player character / user name who queried the model", alias="username", default="")
    creation_date: datetime = Field(description="self-explanatory", alias="creationDate", default=datetime.now())
    messages: List[ChatMessage] = Field(description="The whole chat generated for this chat session", default=[])
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        protected_namespaces = ()
    )

    def map_from_dto(self, dto: ChatDocDto):
        self.id = ObjectId()
        self.session_id = dto.sessionId
        self.model = dto.model
        self.tag = dto.tag
        self.max_tokens = dto.maxTokens
        self.temperature = dto.temperature
        self.user_name = dto.username
        self.creation_date = datetime.now()
        self.messages=[]
        
        for kvp in dto.messages:
            key = list(kvp.keys())[0]
            self.messages.append(ChatMessage(Role=key, Message=kvp.get(key)))

    def messages_to_chat_history(self) -> List[dict[str,str]]:
        chat_history: List[dict[str,str]] = []
        for message in self.messages:
            chat_history.append({message.role: message.message})
        return chat_history
    
    def messages_as_recent_history(self, include_sys_msg:bool = True) -> List[dict[str,str]]:
        if len(self.messages) > default_chat_history_length:
            history = self.messages_to_chat_history()
            recent_msgs = history[len(history)-(default_chat_history_length):len(history)]
            remaining_msgs = history[:-default_chat_history_length]
            if include_sys_msg:
                final = [remaining_msgs.tolist()[0]]
                final.extend(recent_msgs)
            else:
                final = recent_msgs
            return final
        else:
            if include_sys_msg:
                return self.messages_to_chat_history()
            else: 
                return self.messages_to_chat_history()[1:]
            
    #OVERRIDES the whole array with the new chat_history
    def chat_history_to_messages(self, chat_history) -> List[ChatMessage]:
        self.messages:List[ChatMessage] = []
        for kvp in chat_history:
            key = list(kvp.keys())[0]
            message = ChatMessage(Role=key, Message=kvp.get(key))
            self.messages.append(message)
        return self.messages    
    
    #APPENDS the new chat history to the messages list
    def append_history_to_messages(self, chat_history):
        for kvp in chat_history:
            key = list(kvp.keys())[0]
            self.messages.append(ChatMessage(Role=key,Message=kvp[key].strip()))

class SessionDoc(BaseModel):
    id:Optional[PyObjectId] = Field(description="Db identifier for a user chat session", alias="_id", default_factory=ObjectId)
    character_id: Optional[PyObjectId] = Field(description="Db id of the character", default=None)
    username: str = Field(description="self explanatory")
    tag: Optional[str] = Field(None, description="Tags a chat session with something meaningful for the user. Ususally the name of the chat participants (<botname-username>)")
    creation_date: datetime = Field(description="self explanatory",default=datetime.now())
    current_chat_id: Optional[PyObjectId] = Field(None,description="Id of the current ChatPromptsDoc, since a session is compose of at least 1 chat collection")
    current_chat_summary: Optional[str] = Field(None, description="Summary of the current chat collection summary. None if the chat is not long enough")
    summary: Optional[str] = Field(None, description="A summary of whole chat (includes all chat collections from the 'Chat Prompts' table)")
    summary_update_date: Optional[datetime] = Field(None,description="timestamp of the last chat summary update")
    current_summary_update_date: Optional[datetime] = Field(None,description="timestamp of the last CURRENT chat summary update")
    current_chat_ongoing:bool = Field(True, description="Flag indicating whether the current chat is ongoing or it has been already finished and summarized")
    #TODO: on_max_chat_tokens_update_summary: bool & max_chat_tokens: int <-- crean resumen automatico del chat actual cuando input llega a X tokens 
    def map_from_init_request(self, req: InitSessionRequest):
        self.id = ObjectId()
        self.username = req.username
        self.tag = req.tag
        self.creation_date = datetime.now()
        self.summary_update_date = None
        self.summary = None
        self.current_chat_ongoing = True 

class SystemMessageDoc(BaseModel):
    id:Optional[PyObjectId] = Field(description="Db identifier for a user chat session", alias="_id", default_factory=ObjectId)
    type: int = Field(description="Type of message enum id")
    description: str = Field(description="Brief description of the system message content or purpose, usually the type of message description (BaseTemplate, OutputAction, ChatContraints...)")
    message:str = Field(description="Actual content of the system instruction to pass to the LLM")
    tag: Optional[str] = Field(None, description="Tags a chat session with something meaningful for the user. Usually the name of the chat participants (<botname-username>)")

class ChatSummaryDoc(BaseModel):
    id:Optional[PyObjectId] = Field(description="Db identifier for a user chat session", alias="_id", default_factory=ObjectId)
    sys_prompt_tag: str = Field("system template tag used to generate the final LLM prompt")
    session_id: str = Field("session database identifier for the session the current chat belongs to")
    chat_collection_id: str = Field(description="database identifier for the chat collection from which the summary was made")
    creation_date: datetime = Field(description="self-explanatory", default=datetime.now())
    prompt:str = Field("Final prompt passed to the llm")
    summary: str = Field(description="Generated summary of the current chat for the specified session")
    observations: List[str] = Field(description="An array with a collection of observations (if any) for the generated summary", default=[])
    embedding: Optional[List[float]] = Field(description="Related embedding (usually the summary of the document) to be used in RAG / Vector Search applications", default=None)
    def __post__init(self):
        self.id = ObjectId()
 
class ChatDetailsDoc(BaseModel):
    id:Optional[PyObjectId] = Field(description="Db identifier for a user chat session", alias="_id", default_factory=ObjectId)
    chat_doc_id:Optional[PyObjectId] = Field(description="Db identifier for the ChatPromptDoc associated with this Conversation")
    zoneName: str = Field(description="Name of the Game Zone in which the character is in")
    usercharName:str = Field(description="Self-explanatory")
    usercharRole:str = Field(description="Role of the character inside the game. Influences on the character behavior and available OutputActions")
    userfaction:str = Field(description="Self-explanatory")
    botcharName:str = Field(description="Self-explanatory")
    botcharRole:str = Field(description="Role of the character inside the game. Influences on the character behavior and available OutputActions")
    botfaction:str = Field(description="Self-explanatory")
    botActions:List[str] = Field(description="Array containing the available actions. The final text is cached as botMemory['output-actions'] and updates during the chat")
    botPersonalities: List[str] = Field(description="Array of bot personality tags that define the character",default=[])
    botTraits: List[str] = Field(description="Array of bot trait tags that define the character",default=[])
    botMood: str = Field(description="Bot Mood tag defining the character's attitude at the current moment of the conversation. Mood updates stored as chat_events")
    botMemory: dict[str,str] = Field(description="Dictionary storing chat session data such as: INITAL-MEMO, CHAT-MEMO, REMARKABLE EVENTS (prev&cur), CHAR-PROFILE, ACTIONS, GOALS (v2), X", default={})
    zoneContext: Optional[str] = Field(description="Context info about the current zone (if any)")
    usercharContext:Optional[str] = Field(description="Details about the character that might be relevant for the conversation (in the style of 'Injured', 'Drunk', 'Char gets angry / contextual info')")
    botcharContext:Optional[str] = Field(description="Details about the character that might be relevant for the conversation (in the style of 'Injured', 'Drunk', 'Char gets angry / contextual info')")
    chat_events: List[ChatEvent] = Field(description="An array containing any context or settings update occured during the conversation", default=[])
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        protected_namespaces = ()
    )
    def __post_init__(self):
        self.id = ObjectId()

class DatasetChatDoc(BaseModel):
    id: Optional[PyObjectId] = Field(description="", alias="_id", default_factory=ObjectId)
    action:str = Field(description="The replicated chat action name")
    conversation: List[ChatMessage] = Field(description="Replicated chat")
    reason: str = Field(description="A reasoned explanation of how does the replicated conversation end up with the replicated action")
    creation_date: datetime = Field(description="Self-explanatory")
    model:str = Field(description="LLM model name used to generate the replica")
    generation_params: dict[str, Any] = Field(description="dictionary containing the LLM parameters used to generate the replica")


class ChatDocSave(ChatDocDto):
    sessionTag:Optional[str] = Field(description="Session tag for a new session or tag of the session to append the ChatDoc to", default=None)
    isAppend:bool = Field(description="Flag indicating whether the ChatDocument should be appended to the specified tag or create a new one if any", default=False)
