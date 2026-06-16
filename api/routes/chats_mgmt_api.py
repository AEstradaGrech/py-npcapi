import math
from typing import List

from bson import ObjectId
from loguru import logger

from api.infrastructure.models.db_schemas import ChatDetailsDoc, ChatDocSave, ChatPromptDoc, ChatSummaryDoc, SessionDoc
from api.infrastructure.repositories.mongo.chat_prompts import ChatDetailsRepository, ChatPromptsRepository, ChatSessionsRepository
from api.infrastructure.repositories.mongo.chat_summaries_repo import ChatSummariesRepository
from api.mappers.prompting_mappers import chatDocToDto, sessionDocToDto
from api.models.prompting_schemas import BotInfoDto, ChatDocDto, ChatMessageDto, ConversationDto, SessionHistoryUpdateRequest, SpeakerInfoDto, UnrealChatHistory

from fastapi import APIRouter, Request

from api.models.schemas import CollectionResponse, QueryCondition, QueryFilter
from api.utils.helpers import HTTPLoggedException, get_request_db_name
from api.utils.statics import default_db_name, praise_db_name
router = APIRouter(prefix="/mgmt/chats")


@router.post(
    "/update",
    summary="Appends a collection of chat history messages to the session current chat collection. Used to update a session after a streamed response",
    responses={
        200: {"description" : "Succesful response with the recent chat history"}
    }
)
async def update_session_chat(update_request: SessionHistoryUpdateRequest, request: Request):
    print(update_request)
    request_db = get_request_db_name(request)
    sessions_repo = ChatSessionsRepository(request_db)
    chats_repo = ChatPromptsRepository(request_db)
    session = SessionDoc.model_validate(await sessions_repo.get_by_id(update_request.sessionId))
    if session is None:
        raise HTTPLoggedException(status_code=404, detail="There is no active session with that GUID. Begin a new session by making a request to '/chats/session/init'")
    session_prompts = ChatPromptDoc.model_validate(await chats_repo.get_by_id(session.current_chat_id))
    if session_prompts is None:
        raise HTTPLoggedException(status_code=404, detail="There are no session chat messages for this session. Begin a new session by making a request to '/chats/session/init'")
    session_prompts.append_history_to_messages(update_request.chatHistory)
    await chats_repo.update(session_prompts.id, session_prompts)
    history = session_prompts.messages_as_recent_history(include_sys_msg=True)
    print(f"-- returning {len(history)} chat messages --") 
    return history

@router.post(
    "/save",
    summary="Saves a user chat document",
    responses={
        200: {"description": "Saves a user chat session along with it's settings"}
    }
)
async def save_chat(dto: ChatDocDto, request: Request) -> ChatDocDto:
  if dto.sessionId is not None and dto.sessionId != "":
      sessions_repo = ChatSessionsRepository(get_request_db_name(request))
      session = await sessions_repo.get_by_id(dto.sessionId)
      if session is None:
          raise HTTPLoggedException(status_code=404, detail=f"No session found with this identifier: {dto.sessionId}")
  repo = ChatPromptsRepository(get_request_db_name(request))
  insert = ChatPromptDoc()
  insert.map_from_dto(dto)
  return chatDocToDto(await repo.create(insert))


@router.get(
    "/{username}/chat-history/{tag}",
    summary="Returns a reduced ChatDoc dto with a typed collection of ChatMessages to be parsed by UE5",
    responses={
        200: {"description" : "Succesful response with the recent chat history"}
    }
)
async def get_user_session_chat_history(tag:str, username:str) -> UnrealChatHistory:
    repo = ChatPromptsRepository(db_name=praise_db_name)
    chat_records = await repo.query([QueryCondition(field="username", value=username), QueryCondition(field="tag", value=tag)])
    if len(chat_records) == 0:
        return UnrealChatHistory(sessionTag=tag)
    doc = ChatPromptDoc.model_validate(chat_records[0])
    chat_history = []
    for message in doc.messages:
        chat_history.append(ChatMessageDto(role=message.role, message=message.message))
    return UnrealChatHistory(chatId=doc.id, sessionTag=tag, history=chat_history)

@router.get(
    "/chat/history/{chat_id}/unreal",
    summary="Returns a reduced ChatDoc dto with a typed collection of ChatMessages to be parsed by UE5",
    responses={
        200: {"description" : "Succesful response with the recent chat history"}
    }
)
async def get_session_chat_history_by_id(chat_id:str) -> UnrealChatHistory:
    repo = ChatPromptsRepository(db_name=praise_db_name)
    chat_record = await repo.get_by_id(chat_id)
    if chat_record is None:
        return UnrealChatHistory()
    doc = ChatPromptDoc.model_validate(chat_record)
    chat_history = []
    for message in doc.messages:
        chat_history.append(ChatMessageDto(role=message.role, message=message.message))
    return UnrealChatHistory(chatId=doc.id, sessionTag=doc.tag, history=chat_history)



@router.post(
    "/document-save",
    summary="Saves a user simple prompting chat creating a new session document for it with the chat document tag name, appinding it to an existing one or as unrelated document if no tag specified",
    responses={
        200: {"description": "Saves a user chat session along with it's settings"}
    }
)
async def save_simple_prompt(dto: ChatDocSave, request: Request) -> ChatDocDto:
    sessions_repo = ChatSessionsRepository(get_request_db_name(request))
    if dto.sessionTag is None or dto.sessionTag == "":
        return await save_chat(request=dto)
    existing_session = await sessions_repo.get(varname="tag", value=dto.sessionTag)
    if dto.isAppend:
        if existing_session is None:
            raise HTTPLoggedException(status_code=404, detail=f"No session has been found with this tag: {dto.sessionTag}")
        dto.sessionId = SessionDoc.model_validate(existing_session).id
        return await save_chat(dto=dto,request=request)        
    else:   
        if existing_session is not None and dto.sessionTag == existing_session.tag:
            raise HTTPLoggedException(status_code=400, detail=f"There is already a session with this tag: {dto.sessionTag}")
        session = SessionDoc(tag=dto.tag, username=dto.username)
        session.id = ObjectId()
        session_insert = SessionDoc.model_validate(await sessions_repo.create(session))
        dto.sessionId = session_insert.id
        dto.sessionTag = session_insert.tag
        chat_insert = await save_chat(dto=dto,request=request)
        session_insert.current_chat_id = chat_insert.id
        await sessions_repo.update(session_insert.id, session_insert)
        return chat_insert

@router.get(
    "/all-chats/{id}",
    summary="Retrieves all user chat collections for the specified session id",
    responses={
        200: {"description": "Succesful query with the session chat messages and it's params"}
    }
)
async def get_all_session_chats(id:str, request: Request) -> List[ChatDocDto]:
    repo = ChatPromptsRepository(get_request_db_name(request))
    records = await repo.find_by_session_id(id)
    return [] if len(records) <= 0 else [
        ChatDocDto(id=doc.id, 
                   sessionId=doc.session_id, 
                   tag=doc.tag, 
                   username=doc.user_name, 
                   creationDate=doc.creation_date, 
                   model=doc.model, 
                   temperature=doc.temperature, 
                   maxTokens=doc.max_tokens, 
                   messages=doc.messages_to_chat_history()) for doc in records]
    
@router.get(
    "/{id}",
    summary="Retrieves a user chat collection from the database by chat collection id",
    responses={
        200: {"description": "Succesful query with the session chat messages and it's params"}
    }
)
async def get_session_chat_by_id(id:str, request: Request) -> ChatDocDto:
    repo = ChatPromptsRepository(get_request_db_name(request))
    item = await repo.get_by_id(id)
    if item is None:
        raise HTTPLoggedException(status_code=404, detail="No document has been found for this ID")
    doc = ChatPromptDoc.model_validate(item)
    print(doc)
    return ChatDocDto(id=doc.id, sessionId=doc.session_id, tag=doc.tag, username=doc.user_name, creationDate=doc.creation_date, model=doc.model, temperature=doc.temperature, maxTokens=doc.max_tokens, messages=doc.messages_to_chat_history())

@router.delete(
    "/{id}",
    summary="Deletes a user chat collection",
    responses={
        200: {"description":"Deletes a user chat session passing the session GUID"}
    }
)
async def delete_session_chat(id: str, request: Request) -> str:
  repo = ChatPromptsRepository(get_request_db_name(request))
  deleted = await repo.delete_by_id(id)
  if deleted is False:
      raise HTTPLoggedException(status_code=404, detail="No chat session found with id: " + id)
  return "OK"
 
@router.get(
    "/containing-tag/{tag}",
    summary="Retrieves a collection of session chat messages whose tag contains the specified string",
    responses={
        200: {"description" : "Succesful response with a collection of ChatPromptDoc's"}
    }
)
async def get_session_prompts_containing_tag(tag:str, request: Request) -> List[ChatPromptDoc]:
    repo = ChatPromptsRepository(get_request_db_name(request))
    docs = await repo.get_many_containing_string("tag", tag)
    return docs 

@router.post(
    "/query",
    summary="Retrieves a collection of session chat messages by dynamic filter conditions",
    responses={
        200: {"description" : "Succesful response with a collection of ChatDocDto's"}
    }
)
async def query_chats(filter: QueryFilter, request: Request)-> CollectionResponse:
    repo = ChatPromptsRepository(get_request_db_name(request))
    print(filter)
    docs = []
    if len(filter.conditions) > 0:
        docs = await repo.query(filter.conditions)
    else:    
        docs = await repo.stringy_query({})
    print(len(docs))
    #TODO: to helpers
    results = []
    if len(docs) > 0: 
        for i in range(filter.page * filter.page_size, filter.page * filter.page_size + filter.page_size if filter.page_size > 0 else len(docs)):
            if i >= len(docs):
                break
            doc = ChatPromptDoc.model_validate(docs[i])
            results.append(ChatDocDto(
                id=doc.id,
                sessionId=doc.session_id,
                username=doc.user_name,
                tag=doc.tag,
                model=doc.model,
                creationDate=doc.creation_date,
                temperature=doc.temperature,
                maxTokens=doc.max_tokens,
                messages=doc.messages_to_chat_history(),   
            ))
    pages = math.ceil(len(docs) / filter.page_size) if len(docs) > 0 and filter.page_size > 0 else 0
    return CollectionResponse(data=results, page=filter.page, total_pages=pages, total_records=len(docs))

@router.put(
    "/document/update",
    summary="Updates the chat document except for the inference params (model, temperature and max_tokens)",
    responses={
        200: {"description" : "Succesful response with the recent chat history"}
    }
)
async def update_chat_doc(dto: ChatDocDto, request): 
    repo = ChatPromptsRepository(get_request_db_name(request))
    doc = await repo.get_by_id(dto.id)
    if doc is None:
        raise HTTPLoggedException(status_code=404, detail=f"No document found with ID: {dto.id}")
    chat_doc = ChatPromptDoc.model_validate(doc)
    chat_doc.user_name = dto.username
    chat_doc.tag = dto.tag
    chat_doc.session_id = dto.sessionId
    chat_doc.messages = chat_doc.chat_history_to_messages(dto.messages)
    logger.info(f'-- updated doc --')
    print(chat_doc)
    await repo.update(chat_doc.id, chat_doc)
    if chat_doc.session_id is not None and chat_doc.session_id != '':
        sess_repo = ChatSessionsRepository(default_db_name)
        sess_record = await sess_repo.get_by_id(chat_doc.session_id)
        if sess_record is not None:
            session = SessionDoc.model_validate(sess_record)
            session.tag = chat_doc.tag
            await sess_repo.update(session.id, session)
    return dto

@router.put(
    "/{id}/reassign/{session_id}",
    summary="Assigns a chats collection to the specified session",
    responses={
        200: {"description":"Successful response with the reassigned chat document"}
    }
)
async def chat_reassing(id:str, session_id:str, request:Request) -> ChatDocDto:
    logger.info("-- chat reassign --")
    request_db = get_request_db_name(request)
    chats_repo = ChatPromptsRepository(request_db)
    sessions_repo = ChatSessionsRepository(request_db)
    summaries_repo = ChatSummariesRepository(request_db)
    chat_record = await chats_repo.get_by_id(id)
    if chat_record is None:
        raise HTTPLoggedException(status_code=404, detail=f"No chat document found with ID: {id}")
    logger.info("-- chat doc OK --")
    sess_record = await sessions_repo.get_by_id(session_id)
    if sess_record is None:
        raise HTTPLoggedException(status_code=404, detail=f"No session document found with ID: {session_id}")
    logger.info("-- new session OK --")
    chat_doc = ChatPromptDoc.model_validate(chat_record)
    sess_doc = SessionDoc.model_validate(sess_record)
    former_session:SessionDoc = None
    if chat_doc.session_id is not None and chat_doc.session_id != '':
        logger.info("-- getting former session --")
        former_session_record = await sessions_repo.get_by_id(chat_doc.session_id)
        if former_session_record is not None:
            former_session = SessionDoc.model_validate(former_session_record)
            logger.info("-- former session OK --")
    chat_doc.session_id = sess_doc.id
    logger.info("-- updating chat doc --")
    await chats_repo.update(id, chat_doc)
    logger.info("-- doc updated --")
    summary_records = await summaries_repo.query({"$and": [{"session_id": former_session.id, "chat_collection_id": id}]})
    if len(summary_records) > 0:
        logger.info(f"-- {len(summary_records)} summary docs found --")
        for record in summary_records:
            summary = ChatSummaryDoc.model_validate(record)
            summary.session_id = session_id
            logger.info("-- updating doc summary --")
            await summaries_repo.update(summary.id, summary)
    former_session_chats = await chats_repo.find_by_session_id(former_session.id)
    if len(former_session_chats) <= 0:
        await sessions_repo.delete_by_id(former_session.id)    
    return chat_doc

@router.get(
    "/chat/details/{chat_id}",
    summary="Returns a ConversationInitDto with the info about the initial chatConditions (speakers info, zone info, llm & params)",
    responses={
        200:{"description": "Successful response with the ConversationInitDto"}
    }
)
async def get_chat_details_by_chat_id(chat_id:str) -> ConversationDto:
    chats_repo = ChatPromptsRepository(praise_db_name)
    details_repo = ChatDetailsRepository(praise_db_name)
    chat = ChatPromptDoc.model_validate(await chats_repo.get_by_id(chat_id))
    details =ChatDetailsDoc.model_validate(await details_repo.get(varname="chat_doc_id", value=chat_id))
    return ConversationDto(
        zoneName=details.zoneName, 
        zoneActualContext=details.zoneContext, 
        speakerInfo=SpeakerInfoDto(
            charName=details.usercharName,
            charRole=details.usercharRole,
            factionName=details.userfaction,
            actualContext=details.usercharContext
        ),
        botInfo=BotInfoDto(
            charName=details.botcharName,
            charRole=details.botcharRole,
            factionName=details.botfaction,
            actualContext=details.botcharContext,
            personalities=details.botPersonalities,
            traits=details.botTraits,
            mood=details.botMood
        ),
        userMessage="",
        model=chat.model,
        maxTokens=chat.max_tokens,
        temperature=chat.temperature
    )