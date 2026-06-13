import math
from typing import List

from bson import ObjectId
from loguru import logger

from api.infrastructure.models.db_schemas import ChatDocSave, ChatPromptDoc, ChatSummaryDoc, SessionDoc
from api.infrastructure.repositories.mongo.chat_prompts import ChatPromptsRepository, ChatSessionsRepository
from api.infrastructure.repositories.mongo.chat_summaries_repo import ChatSummariesRepository
from api.mappers.prompting_mappers import chatDocToDto, sessionDocToDto
from api.models.prompting_schemas import ChatDocDto, SessionDto, SessionHistoryUpdateRequest, SessionRetagRequest

from fastapi import APIRouter, Request

from api.models.schemas import CollectionResponse, QueryCondition, QueryFilter
from api.utils.helpers import HTTPLoggedException, get_request_db_name
from api.utils.statics import default_db_name, praise_db_name
router = APIRouter(prefix="/mgmt/chats")

@router.get(
    "/{tag}/session",
    summary="gets the session doc data for a given character-player profile",
    responses={
        200 : {"description": "Succesful response with the Session doc for this character and player"}
    }
)
async def get_chat_session(tag:str, request: Request) -> SessionDto:
    #get session
    sessions_repo = ChatSessionsRepository(db_name=get_request_db_name(request))
    record = await sessions_repo.get(varname="tag", value=tag)
    return SessionDto(tag=tag) if record is None else sessionDocToDto(SessionDoc.model_validate(record))

@router.get(
    "/{id}",
    summary="Get a user session",
    responses={
        200: {"description":"Get the user session data passing the session GUID"}
    }
)
async def get_session_by_id(id:str, request: Request) -> SessionDto:
    repo = ChatSessionsRepository(get_request_db_name(request))
    doc = await repo.get_by_id(id)
    if doc is None:
        raise HTTPLoggedException(status_code=404, detail="No document found for this GUID")
    session = SessionDoc.model_validate(doc)
    return SessionDto(id=session.id, username=session.username, tag=session.tag, summary=session.current_chat_summary, currentChatId=session.current_chat_id)

@router.get(
    "/containing-tag/{tag}",
    summary="Retrieves session documents whose tag contains the specified string",
    responses={
        200: {"description" : "Succesful response with a collection of SessionDocs's"}
    }
)
async def get_sessions_containing_tag(tag:str, request: Request) -> List[SessionDto]:
    repo = ChatSessionsRepository(get_request_db_name(request))
    docs = await repo.get_many_containing_string("tag", tag)
    print("-- SESSION DOCS --")
    dtos = []
    for i in range(0, len(docs)):
        if i < len(docs):
            doc = SessionDoc.model_validate(docs[i])
            dtos.append(SessionDto(id=doc.id, username=doc.username, tag=doc.tag, summary=doc.current_chat_summary, currentChatId=doc.current_chat_id))
    return dtos
 
@router.get(
    "/praise-character-session/{tag}",
    summary="Retrieves session documents whose tag contains the specified string",
    responses={
        200: {"description" : "Succesful response with a collection of SessionDocs's"}
    }
)
async def get_session_with_tag(tag:str, request: Request) -> SessionDto:
    repo = ChatSessionsRepository(get_request_db_name(request))
    record = await repo.get(varname="tag", value=tag)
    print("-- SESSION DOC --")
    if record is None:
        raise HTTPLoggedException(status_code=500, detail="-- No session / character profile has been found with this 'botname-username' tag --")
    doc = SessionDoc.model_validate(record)
    return SessionDto(id=doc.id, username=doc.username, tag=doc.tag, summary=doc.current_chat_summary, currentChatId=doc.current_chat_id)
     

@router.get(
    "/user/{username}/containing-tag/{tag}",
    summary="Retrieves user session documents whose tag contains the specified string",
    responses={
        200: {"description" : "Succesful response with a collection of SessionDocs's"}
    }
)
async def get_user_sessions_containing_tag(username:str,tag:str, request: Request) -> List[SessionDto]:
    repo = ChatSessionsRepository(get_request_db_name(request))
    docs = await repo.get_user_sessions_containing_tag(username=username, tag=tag) if tag != "_"  else await repo.get_many(varname="username", value=username)
    dtos = []
    for i in range(0, len(docs)):
        doc = SessionDoc.model_validate(docs[i])
        dtos.append(SessionDto(id=doc.id, username=doc.username, tag=doc.tag, summary=doc.current_chat_summary, currentChatId=doc.current_chat_id, characterId=None if doc.character_id is None else doc.character_id))
    return dtos 

@router.get(
    "/user/{username}/matching-tag/{tag}",
    summary="Retrieves user session document whose tag matches the specified string",
    responses={
        200: {"description" : "Succesful response with a of SessionDocs"}
    }
)
async def get_user_sessions_matching_tag(username:str,tag:str, request: Request) -> SessionDto:
    repo = ChatSessionsRepository(get_request_db_name(request))
    docs = await repo.query([QueryCondition(field="username", value=username), QueryCondition(field="tag", value=tag)])
    if len(docs) == 0:
        return SessionDto(id="", username="")
    doc = SessionDoc.model_validate(docs[0])
    return SessionDto(id=doc.id, username=doc.username, tag=doc.tag, summary=doc.current_chat_summary, currentChatId=doc.current_chat_id, characterId=None if doc.character_id is None else doc.character_id)
 

@router.get(
    "/last/containing-tag/{tag}",
    summary="Retrieves session documents whose tag contains the specified string",
    responses={
        200: {"description" : "Succesful response with a collection of SessionDocs's"}
    }
)
async def get_last_session_containing_tag(tag:str, request: Request) -> SessionDto:
    repo = ChatSessionsRepository(get_request_db_name(request))
    docs = await repo.get_many_sorted_containing_string(varname="tag", match=tag, sortvar="creation_date", descending=True)
    if len(docs) <= 0:
       raise HTTPLoggedException(status_code=404, detail=f"No documents found with tag: {tag}")
    print(f"-- LAST USER SESSIONS WITH TAG: {tag} --", docs)
    last_doc = SessionDoc.model_validate(docs[0])
    dto = SessionDto(id=last_doc.id, username=last_doc.username, tag=last_doc.tag, summary=last_doc.current_chat_summary, currentChatId=last_doc.current_chat_id, characterId=None if last_doc.character_id is None else last_doc.character_id)
    return dto
@router.get(
    "/last/user-session/{username}",
    summary="Retrieves the last session document created for this user",
    responses={
        200: {"description" : "Succesful response with a SessionDto containing the data for the most recient user session"}
    }
)
async def get_last_user_session(username:str, request: Request) -> SessionDto:
    repo = ChatSessionsRepository(get_request_db_name(request))
    docs = await repo.get_many_sorted_containing_string(varname="username", match=username, sortvar="creation_date", descending=True)
    if len(docs) <= 0:
       raise HTTPLoggedException(status_code=404, detail=f"No documents found for user: {username}")
    last_doc = SessionDoc.model_validate(docs[0])
    dto = SessionDto(id=last_doc.id, username=last_doc.username, tag=last_doc.tag, summary=last_doc.current_chat_summary, currentChatId=last_doc.current_chat_id, characterId=None if last_doc.character_id is None else last_doc.character_id)
    return dto
@router.delete(
    "/{id}",
    summary="Deletes a user session",
    responses={
        200: {"description":"Deletes a user chat session passing the session GUID"}
    }
)

@router.post(
    "/retag",
    summary="Retags a session with a new string, optionally retagging its associated chat documents",
    responses={
        200: {"description" : "Succesful response with the updated session data"}
    }
)
async def retag_session(req:SessionRetagRequest, request: Request) -> SessionDto:
    logger.info("-- retag init --")
    request_db = get_request_db_name(request)
    sessions_repo = ChatSessionsRepository(request_db)
    session = SessionDoc.model_validate(await sessions_repo.get_by_id(req.session_id))
    logger.info("-- retag doc retrieved --")
    session.tag = req.tag
    print(session)
    await sessions_repo.update(session.id, session)
    logger.info("-- retagged doc updated --" + session.tag)
    if req.retag_chats:
        chats_repo = ChatPromptsRepository(request_db)
        logger.info("-- getting session chats --")
        docs = await chats_repo.get_many("SessionId", req.session_id)
        if len(docs) > 0:
            logger.info("-- retagging session chats --")
            for record in docs:
                doc = ChatPromptDoc.model_validate(record)
                doc.tag = req.tag
                logger.info("-- updating session chat --" + doc.tag)
                await chats_repo.update(doc.id, doc)
    return SessionDto(id=session.id, username=session.username, tag=session.tag, summary=session.summary, currentChatId=session.current_chat_id, characterId=None if doc.character_id is None else doc.character_id)

async def delete_session(id: str, request: Request) -> str:
  repo = ChatSessionsRepository(get_request_db_name(request))
  deleted = await repo.delete_by_id(id)
  if deleted is False:
      raise HTTPLoggedException(status_code=404, detail="No chat session found with id: " + id)
  #TODO? borrar todos los ChatPrompts de esta session
  return "OK"

@router.post(
    "/query",
    summary="Retrieves a collection of sessions by dynamic filter conditions",
    responses={
        200: {"description" : "Succesful response with a collection of SessionDto's"}
    }
)
async def query_sessions(filter: QueryFilter, request: Request)-> CollectionResponse:
    repo = ChatSessionsRepository(praise_db_name)
    print(filter)
    docs = []
    if len(filter.conditions) > 0:
        docs = await repo.query(filter.conditions)
    else:    
        docs = await repo.stringy_query({})
    results = []
    if len(docs) > 0:
        if filter.page is None and filter.page_size is None:
            return CollectionResponse(data=[sessionDocToDto(doc) for doc in docs], total_records=len(docs), page=0, total_pages=1)
        for i in range(filter.page * filter.page_size, filter.page * filter.page_size + filter.page_size if filter.page_size > 0 else len(docs)):
            if i >= len(docs):
                break
            results.append(sessionDocToDto(docs[i]))
    pages = math.ceil(len(docs) / filter.page_size) if len(docs) > 0 and filter.page_size > 0 else 1 if len(docs) > 0 else 0
    return CollectionResponse(data=results, page=filter.page, total_pages=pages if pages is not None else 0, total_records=len(docs))

@router.post(
    "/chat/update",
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
    "/chats/save",
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

@router.post(
    "/chats/document-save",
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
    "/chats/{id}",
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
    "/chats/{id}",
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
    "/chats/containing-tag/{tag}",
    summary="Retrieves a collection of session chat messages whose tag contains the specified string",
    responses={
        200: {"description" : "Succesful response with a collection of ChatPromptDoc's"}
    }
)
async def get_session_prompts_containing_tag(tag:str, request: Request) -> List[ChatPromptDoc]:
    repo = ChatPromptsRepository(get_request_db_name(request))
    docs = await repo.get_many_containing_string("Tag", tag)
    return docs 

@router.post(
    "/chats/query",
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
    "/chats/document/update",
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
    "chat/{id}/reassign/{session_id}",
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

@router.patch(
    "/{id}/set-current-chat/{chat_id}",
    summary="Sets the specified chat as the current chat for the specified session",
    responses={
        200: {"description":"Successful response with the updated SessionDto"}
    }
)
async def set_session_current_chat(id:str, chat_id:str, request: Request) -> SessionDto:
    request_db = get_request_db_name(request)
    sessions_repo = ChatSessionsRepository(request_db)
    chats_repo = ChatPromptsRepository(request_db)
    summaries_repo = ChatSummariesRepository(request_db)
    session = await sessions_repo.get_by_id(id)
    if session is None:
        raise HTTPLoggedException(status_code=404, detail=f"No session found with ID: {id}")
    chat = await chats_repo.get_by_id(chat_id)
    if chat is None:
        raise HTTPLoggedException(status_code=404, detail=f"No chat document found with ID: {chat_id}")

    session_doc = SessionDoc.model_validate(session)
    chat_doc = ChatPromptDoc.model_validate(chat)

    session_doc.current_chat_id = chat_doc.id
    chat_summary = await summaries_repo.get_chat_summary(chat_id=chat_id)
    if chat_summary is not None:
        summary_doc = ChatSummaryDoc.model_validate(chat_summary)
        session_doc.current_chat_summary = summary_doc.summary
    await sessions_repo.update(session_doc.id, session_doc)
    logger.info('-- update session --')
    print(session_doc)
    return SessionDto(id=session_doc.id, username=session_doc.username, tag=session_doc.tag, currentChatId=session_doc.current_chat_id, summary=session_doc.summary)
