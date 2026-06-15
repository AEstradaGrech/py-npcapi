from datetime import datetime
import json
import math
from typing import Any, List
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from api.infrastructure.models.db_schemas import ChatPromptDoc, ChatSummaryDoc, SessionDoc, SystemMessageDoc
from api.infrastructure.repositories.mongo.chat_prompts import ChatPromptsRepository, ChatSessionsRepository
from api.infrastructure.repositories.mongo.chat_summaries_repo import ChatSummariesRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.mappers.mgmt_mappers import toSystemMessageDto
from api.models.schemas import ChatSummaryDto, SummaryDto, SystemMessageDto
from api.models.summary_schemas import ChatSummaryRequest, ChatSummaryResponse
from api.utils.statics import sys_message_types
from api.utils.helpers import get_llm_provider, get_request_db_name


router = APIRouter(prefix="/mgmt/summaries")

@router.get(
    "/chat/{chat_id}",
    summary="Returns a ChatSummaryDto with for the specified ChatPromptDoc",
    responses = {
        200 : {"description": "Successful response with the summary data"}
    }
)
async def get_chat_summary(chat_id:str, request: Request) -> Any:
    repo = ChatSummariesRepository(get_request_db_name(request))
    doc = await repo.get_chat_summary(chat_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"No summary found for chat doc with ID: {chat_id}")
    return ChatSummaryDto(id=doc.id, sysMessageTag=doc.sys_prompt_tag, summary=doc.summary)

@router.get(
    "/summarization-messages/containing-tag/{tag}",
    summary="Returns a collection of summarization system messages filtering by tag",
    responses = {
        200 : {"description": "Successful response with the summary data"}
    }
)
async def get_summarization_messages_containing_tag(tag:str, request: Request) -> List[SystemMessageDto]:
    repo = SysMessagesRepository(get_request_db_name(request))
    print(f"-- req tag: {tag} --")
    docs = await repo.get_many(varname="type",value=sys_message_types.summary_template) if tag == "_" else await repo.get_many_by_type_containing_tag(type=sys_message_types.summary_template, tag=tag)
    logger.info("-- docs retrieved --")
    print(docs)
    return [toSystemMessageDto(doc) for doc in docs]

@router.post(
    "/summarize/session",
    summary="Summarizes the current chat collection for a given session",
    responses={
        200: {"description" : "Succesful response with a summary of the conversation"}
    }
)
async def summarize_session_chat(req: ChatSummaryRequest, request: Request) -> ChatSummaryResponse:
    logger.info('-- on summarize session --')
    print(req)
    sessions_repo = ChatSessionsRepository(get_request_db_name(request))
    chats_repo = ChatPromptsRepository(get_request_db_name(request))
    sys_messages_repo = SysMessagesRepository(get_request_db_name(request))
    session = SessionDoc.model_validate(await sessions_repo.get_by_id(req.sessionId))
    session_chats = ChatPromptDoc.model_validate(await chats_repo.get_by_id(session.current_chat_id))
    sys_msg = SystemMessageDoc.model_validate(await sys_messages_repo.get_by_type_and_tag(sys_message_types.summary_template, req.sysMessageTag))
    chat_history = session_chats.messages_to_chat_history()
    temp = req.temperature
    max_tokens = req.maxTokens
    summary_response = get_llm_provider().chat_summary(chat_history=chat_history, sys_msg=sys_msg.message if req.sysMessage is None else req.sysMessage,temperature=temp, max_tokens=max_tokens, ctx_len=req.contextLength, exclude_sys_updates=req.excludeSystemUpdates)
    print('-- on summary completed --', summary_response[1])
    return ChatSummaryResponse(sessionId=req.sessionId, chatId=session_chats.id, prompt=summary_response[0], summary=summary_response[1])


@router.post(
    "/save",
    summary="Saves a chat collection summarization along with the parameters used to generate it, mainly for development purposes",
    responses={
        200: {"description" : "Succesful response with the created document"}
    }
)
async def save_chat_summary(req: SummaryDto, request: Request) -> SummaryDto:
    repo = ChatSummariesRepository(get_request_db_name(request))
    doc = ChatSummaryDoc(id=None, 
                         sys_prompt_tag=req.sysMessageTag, 
                         session_id=req.sessionId, 
                         chat_collection_id=req.chatId, 
                         creation_date=datetime.now(), 
                         prompt=req.prompt, 
                         summary=req.summary, 
                         observations=req.observations)
    del doc.id
    insert = ChatSummaryDoc.model_validate(await repo.create(doc))
    return SummaryDto(id=insert.id, 
                      sysMessageTag=insert.sys_prompt_tag, 
                      sessionId=insert.session_id, 
                      chatId=insert.chat_collection_id, 
                      creationDate=str(insert.creation_date), 
                      prompt=insert.prompt, 
                      summary=insert.summary, 
                      observations=insert.observations)


# @router.get(
#     "/{summary_id}/generate-embedding",
#     summary="Generates and saves an embedding made from the ChatSummaryDoc.summary field",
#     responses={
#         200: {"description" : "Succesful response with the created document"}
#     }
# )
# async def generate_embedding(summary_id:str, request: Request):
#     repo = ChatSummariesRepository(get_request_db_name(request))
#     record = await repo.get_by_id(id=summary_id)
#     if record is None:
#         raise HTTPException(status_code=400, detail=f"No summary document has been found for id: {summary_id}")
#     doc:ChatSummaryDoc = ChatSummaryDoc.model_validate(record)
#     transformer = sentence_transformer(device="gpu")
#     embedding = transformer.encode(doc.summary).tolist()
#     print(f":: NEW EMBEDDING >> type: {type(embedding) }::")
#     print(embedding)
#     doc.embedding = embedding
#     await repo.update(doc.id, doc)

# @router.get(
#     "/chat/{chat_id}/generate-memo-embeddings",
#     summary="Generates embeddings for every generated short memo embedding the chat_history chunk instead the memo summary",
#     responses={
#         200: {"description" : "Succesful response with the created document"}
#     }
# )
# async def generate_chat_embeddings(chat_id:str, request: Request):
#     repo = ChatSummariesRepository(get_request_db_name(request))
#     chats_repo = ChatPromptsRepository(get_request_db_name(request))
#     chat_record = await chats_repo.get_by_id(chat_id)
#     if chat_record is None:
#         raise HTTPException(status_code=400, detail=f"No chat doc has been found for doc id: {chat_id}")
#     chat_doc:ChatPromptDoc = ChatPromptDoc.model_validate(chat_record)
#     # proceso copia session -> get_history_chunk -> append to new chat_doc -> generate memo + embedding
#     history = chat_doc.messages_to_chat_history()[1:]
#     print(len(history))
#     transformer = sentence_transformer(model="nomic-ai/nomic-embed-text-v1", device="gpu")
#     for i in range(math.ceil(len(history) / 8)):
#         if i == 0:
#             new_doc:ChatPromptDoc = ChatPromptDoc(sessionId=chat_doc.session_id, model=chat_doc.model, max_tokens=chat_doc.max_tokens, temperature=chat_doc.temperature, tag=chat_doc.tag)
#             new_doc.messages.append(chat_doc.messages[0])
#             new_doc.id = ObjectId()
#             await chats_repo.create(new_doc)
#             #create details doc
#         if i < len(history):
#             messages = history[8 * i:8 * (i +1)]
#             print(f"memo_{i} msgs: {len(messages)}\n\n{messages}")
#             new_doc.append_history_to_messages(messages)
#             await chats_repo.update(new_doc.id, new_doc)
#             embeddings = transformer.encode(json.dumps(messages))
#             #memo = svc.update_short_memo
#             #memo.embeddings = embeddings
#             #repo.update(memo.id, memo)
#             print(f"new embeddings. length: {len(embeddings)}")

# generate_session_embeddings(session_id)
# setup mongo VectorSearchIndex 'short-memo-chats'
# añadir spaCy NER. añadir Spans (Karl Maria Willigut, BotVille)
# prueba rapida: QA 'guiado' (que puedes contarme sobre <SPAN>?) -> si detecta NER = rag, si no chat
# integracion: genera embeddings durante update_short_memo. Modelo spacy configurado con KB(Spans, Links, Matchers) o entrenado