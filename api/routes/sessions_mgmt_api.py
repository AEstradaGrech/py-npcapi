import math
from typing import List

from bson import ObjectId
from loguru import logger

from api.infrastructure.models.db_schemas import ChatDocSave, ChatPromptDoc, ChatSummaryDoc, SessionDoc
from api.infrastructure.repositories.mongo.chat_prompts import ChatPromptsRepository, ChatSessionsRepository
from api.infrastructure.repositories.mongo.chat_summaries_repo import ChatSummariesRepository
from api.mappers.prompting_mappers import chatDocToDto, sessionDocToDto
from api.models.prompting_schemas import SessionDto, SessionHistoryUpdateRequest, SessionRetagRequest

from fastapi import APIRouter, Request

from api.models.schemas import CollectionResponse, QueryCondition, QueryFilter
from api.utils.helpers import HTTPLoggedException, get_request_db_name
from api.utils.statics import default_db_name, praise_db_name
router = APIRouter(prefix="/mgmt/sessions")

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
    repo = ChatSessionsRepository(get_request_db_name(request))
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
