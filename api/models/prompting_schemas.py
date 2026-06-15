

from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel, Field

from api.models.character_schemas import PraiseCharacterDto


class ChatDocDto(BaseModel):
    id:Optional[str] = Field(description="Db identifier document collection", default_factory=lambda: str(ObjectId()))
    sessionId:Optional[str] = Field(None, description="Db identifier for the user session this collection belongs to (if any)")
    model: str = Field(description="The infered LLM name", default="")
    tag: str = Field(description="A field to tag the record with meaningful info, usually the bot name and user name to identify the chats by actors", default="")
    maxTokens: int = Field(description="The max tokens setting passed to the LLM",  default=0)
    temperature: float = Field(description="The temperature setting passed to the LLM", default=0.0)
    username: str = Field(description="The player character / user name who queried the model",  default="")
    creationDate: datetime = Field(description="self-explanatory", alias="creationDate", default=datetime.now())
    messages: List[dict[str, str]] = Field(description="A dictionary with the complete chat history for this session",default=[])



class SpeakerInfoDto(BaseModel):
    charName:str = Field(description="Self-explanatory")
    charRole:str = Field(description="Role of the character inside the game. Influences on the character behavior and available OutputActions")
    factionName:str = Field(description="Self-explanatory")
    actualContext:Optional[str] = Field(description="Details about the character that might be relevant for the conversation (in the style of 'Injured', 'Drunk', 'Char gets angry / contextual info')")
    
class BotInfoDto(SpeakerInfoDto):
    personalities: List[str] = Field(description="Psychological traits about the character that will model the character response")
    traits: List[str] = Field(description="Character traits that might have an impact on the character behaviour during the conversation. Considered as PERKS. Linked to the gameplay behaviour of the character")
    charAge: Optional[str] = Field(description="apparent age or numerical age", default = "")
    mood: Optional[str] = Field(description="Current mood of the character. Depends on its personality and the outcomes of the conversation (getting angry) or the character actions (being drunk). Dynamic; may change every new prompt")
    characterId: Optional[str] = Field(description="DB Id of the bot character. Null if it is the first conversation with the character", default=None)

class ConversationDto(BaseModel):
    zoneName: str = Field(description="Name of the Game Zone in which the character is in")
    zoneActualContext: Optional[str] = Field(description="Context info about the current zone (if any)")
    speakerInfo: SpeakerInfoDto = Field(description="Context info about the character who is starting the conversation")
    botInfo: BotInfoDto = Field(description="Context info about the bot character being talked")
    userMessage: str = Field(description="Current user prompt")
    model:Optional[str] = Field(description="Desired LLM model for the current user prompt. Leave empty to use the default setted up model")
    maxTokens:int = Field(description="Max tokens for the llm response")
    temperature: float = Field(description="LLM parameter. No explanation needed")

class ConversationPromptDto(BaseModel):
    speakerPrompt: str = Field(description="New user prompt"),
    zoneContextUpdate: List[str] = Field(description="Zone contextual information changes", default=[])
    speakerContextUpdate: List[str] = Field(description="User contextual information change", default=[])
    botContextUpdate: List[str] = Field(description="Bot contextual information change", default=[])
    model:Optional[str] = Field(description="Desired LLM model for the current user prompt. Leave empty to use the default setted up model", default=None)
    maxTokens:Optional[int] = Field(description="Max tokens for the llm response. Leave empty to use the ChatPromptDoc settings", default=None)
    temperature: Optional[float] = Field(description="LLM parameter. No explanation needed.Leave empty to use the ChatPromptDoc settings", default=None)

class GenerateCharacterRequest(SpeakerInfoDto):
    personalities: List[str] = Field(description="Psychological traits about the character that will model the character response")
    traits: List[str] = Field(description="Character traits that might have an impact on the character behaviour during the conversation. Considered as PERKS. Linked to the gameplay behaviour of the character")
    charAge: Optional[str] = Field(description="apparent age or numerical age", default = "")

class ChatMessageDto(BaseModel):
    role:str = Field(description="chat actor tag. system | context| user | assistant")
    message:str = Field(description="Message content")

class PromptRequest(BaseModel):
    # provider: str = Field(description="The LLM provider. It might be gpt4all | ollama | huggingface")
    model_name: Optional[str] = Field(description="The LLM model to query. It has no use when using the cached gpt4all model", default=None)
    temperature: Optional[float] = Field(2.0, description="LLM parameter to regulate the llm improvisation capabilites.")
    max_tokens: Optional[int] = Field(600, description="LLM to configure the length of the response")
    #should_use_local_server: Optional[bool] = Field(False, description="Sends the prompt to the LLM provider via http api request. Available for ollama | gpt4all providers")
    system_message: Optional[str] = Field(None, description="An instruction for the llm on how to answer the request")
    message: str = Field(description="A test message")

class ChatPromptRequest(PromptRequest):
    chat_history: List[dict[str, str]] = Field(description="A dictionary with the complete chat history for this session")


class ChatReplicaRequest(PromptRequest):
    action: str = Field(description="The chat action to replicate")
    replicas: int = Field(description="Number of replicas to generate")
    reuse_template: bool = Field(description="jFlag to indicate whether the process should generate a new character for each replica or reuse the first and variate the examples")
    few_show_examples:int = Field(description="Number of EXTRA chat examples to include in the system message", default=0)
    
class InitSessionRequest(ChatPromptRequest):
    username: str = Field(description="self explanatory")
    tag: Optional[str] = Field("Tags a chat session with something meaningful for the user. Ususally the name of the chat participants (<botname-username>)")

class ChatReplicaDto(BaseModel):
    id:str
    creation_date:datetime
    action:str
    conversation_text:str
    reason:str

class ChatResultDto(BaseModel):
    action:str = Field(description="Action Tag")
    sysmsgType:int = Field(description="System messages type for templating in client apps")
    reason:str = Field(description="Brief description of the action, if any")
    isChatEnding: bool = Field(description="A Flag indicating whether the chat has come to and end or triggers a user interaction, depending on the result")
    defaultAckMessage:str = Field(description="Default user acknowledge message (if any) for this action", default="")
    defaultRejMessage:str = Field(description="Default user rejection message (for non chat-ending results)", default="")
    chatEndingEvent:str = Field(description="User acknowledge | rejection actions that will trigger the CHAT_END process. Assumed chat streaming if empty, 'any' for all")

class ChatPromptResponse(BaseModel):
    session_id:Optional[str] = Field(None, description="Db identifier for the user session this collection belongs to (if any)")
    #page_size: int = Field(description="The number of chat prompt to send to the LLM along with the new user prompt. Set the response chat_history size")
    #total_pages: int = Field(description="Total chat pages so far")
    model_name: str = Field(description="Name of the LLM the user is chatting with") 
    chat_history: List[dict[str,str]] = Field(description="Returns a list of dictionaries with the whole conversation (for now. TODO: limit messages)")

class CharacterProfileDto(BaseModel):
    id:Optional[str] = Field(None,description="Db identifier document collection")
    char_name:str = Field("Tag of the system message document containing the description of the character to pass as system instruction to the LLM. This should be UNIQUE")
    description: str = Field("Description of the character to be stored as system message document and retrieved to generate user prompts")

class InitSessionRequest(ChatPromptRequest):
    username: str = Field(description="self explanatory")
    tag: Optional[str] = Field("Tags a chat session with something meaningful for the user. Ususally the name of the chat participants (<botname-username>)")

class InitCharSessionRequest(PromptRequest):
    username: str = Field(description="self explanatory")
    char_profile_tag: Optional[str] = Field("Identifier with the tag of the system message containing the character description to use during the conversation")

class SessionDto(BaseModel):
    id: str = Field(description="DB Id of the session document")
    username: str = Field(description="self explanatory")
    tag: Optional[str] = Field(description="Tags a chat session with something meaningful for the user. Ususally the name of the chat participants (<botname-username>)",default="")
    summary: Optional[str] = Field(description="A summary of whole chat",default=""),
    characterId: str = Field(description="DB character ID for the session doc")
    currentChatId:Optional[str] = Field("Db identifier for the current chat document")
    currentChatOngoing: bool = Field("Flag indicating whether the current chat is ongoing or it has been already ended and summarized")

class ChatInitDto(SessionDto):
    conversation: ConversationDto = Field(description="Summary of the conversation actors and zone data filled with the generated bot data")
    npc: PraiseCharacterDto = Field(description="The generated NPC character")
    sysmsg: str = Field(description="The original system instruction for the character")
    
class SessionRetagRequest(BaseModel):
    session_id: str = Field("session database identifier for the session to retag")
    tag: str = Field("New tag for the session and its associated chats (optionally)"),
    retag_chats: bool=Field(description="Flag to indicate whether to retag all the associated chats or not", default=False)

class SessionHistoryUpdateRequest(BaseModel):
    sessionId: str = Field("session database identifier for the session the current chat belongs to")
    chatHistory: List[dict[str,str]] = Field("A List containing the messages to append to the current session chat collection")

class UnrealChatUpdateRequest(BaseModel):
    sessionId: str = Field("session database identifier for the session the current chat belongs to")
    chatHistory: List[ChatMessageDto] = Field("A List containing the messages to append to the current session chat collection as type messages")

class EndSessionRequest(BaseModel):
    session_id: str = Field(description="Db identifier for the session to end")
    should_trigger_on_background: bool = Field(description="Flag to indicate if the summarization must run on the background or wait for it to generate",default=False)
    should_trigger_full_summary: bool = Field(description="A flag to indicate if the process should trigger a summary of all the chat collections for this session", default=False)
    should_update_session:bool = Field(description="Flag to mark whether the generated summary is meant to be set as the SessionDoc current_summart", default=False)
    max_tokens:int = Field(description="LLM param to limit the size of the generated summary", default=600)
    temperature:float = Field(description="LLM param to set the amount of randomness added to the response", default=0.5)
    exclude_chat_sys_msg:bool = Field(description="Flag to indicate wether to include or not the system instruction passed along with the chat history to the llm", default=True)

class SessionPromptRequest(BaseModel):
    session_id: str = Field("session database identifier for the session the current chat belongs to")
    user_message: str = Field("current user prompt")
    system_message: Optional[str] = Field(None, description="System message. This is setted up when initializing the session, but this can be used to update it")

class StreamEndResponse(BaseModel):
    history: List[dict[str,str]] = Field(description="A list containing the chat history as recent messages")
    chatResult: ChatResultDto = Field(description="An Object containing the result of the OutputActions parsing analysis", default=None)
    
class UnrealChatHistory(BaseModel):
    chatId: str = Field(description="DB id of the chat document")
    sessionTag:str = Field(description="String field containing the names of the bot and the player characters")
    history: List[ChatMessageDto] = Field(description="A list containing the chat history as typed messages to be easly parsed by the game engine")

class UnrealStreamEnd(BaseModel):
    history: List[ChatMessageDto] = Field(description="A list containing the chat history as typed messages to be easly parsed by the game engine")
    chatResult: ChatResultDto = Field(description="An Object containing the result of the OutputActions parsing analysis", default=None)
    
class ActionAcknowledgeDto(BaseModel):
    userMessage: Optional[str] = Field(description="An optional user acknowledge message to feed the LLM with", default=None)
    action:str = Field(description="Acknowledged Action name")
    isUserRejection:bool

class ActionOutcomeDto(BaseModel):
    action:str = Field(description="OutputAction tag to identify the triggered Action flow")
    isUserRejection: bool = Field(description="A flag to indicate the selected user response type to mantain data cohesion")
    userMessage: str = Field(description="User OutputAction acknowledge / reject message")
    instructionUpdate:Optional[str] = Field(description="a [assistant-context-update] instruction to force a specific response / attitude / behaviour in the LLM", default=None)
    endChat: bool = Field(description="A flag to indicate whether the conversation should end after the LLM response or continue with the chat loop")

class UpdateModelSettingsRequest(BaseModel):
    model_name: Optional[str] = Field(description="name of the new model to use during inference", default=None)
    max_tokens: Optional[int] = Field(description="Max allowed tokens for the llm",default=None)
    temperature: Optional[float] = Field(description="Allows for a certain amount of creativity on the LLM response. The lower the value, more accurate will be the answer regarding the sys prompt", default=None)

class ChatEventDto(BaseModel):
    tag_id:int = Field(description="Event tag id to be converted to string inside the API")
    message:str = Field(description="Event message")
    category:str = Field(description="Chat Event Category ('assistant' | 'user' | 'remmarkable-event' | 'action-tag')")