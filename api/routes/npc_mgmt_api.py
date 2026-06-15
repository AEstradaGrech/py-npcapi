import math
from typing import Any, List
from bson import ObjectId
from fastapi import APIRouter, Request
from loguru import logger

from api.infrastructure.models.db_schemas import ChatDetailsDoc, ChatPromptDoc, SessionDoc, SystemMessageDoc
from api.infrastructure.repositories.mongo.chat_prompts import ChatDetailsRepository, ChatPromptsRepository, ChatSessionsRepository
from api.infrastructure.repositories.mongo.mongo_repos import CharacterMoodsRepository, CharacterPersonalitiesRepository, CharacterRolesRepository, CharacterTraitsRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository

from api.mappers.character_mappers import gameCharToDto, toMoodDto, toPersonalityDto, toRoleDto, toTraitDto
from api.mappers.mgmt_mappers import toSystemMessageDto
from api.mappers.prompting_mappers import charDtoToDoc
from api.models.character_schemas import CharacterMoodDto, CharacterPersonalityDto, CharacterRoleDto, CharacterTraitDto, FullPraiseCharDto, PraiseCharacterDto
from api.models.prompting_schemas import BotInfoDto, ChatEventDto, ChatMessageDto, ConversationDto, GenerateCharacterRequest, SpeakerInfoDto, UnrealChatHistory
from api.models.schemas import CollectionResponse, QueryCondition, QueryFilter, SystemMessageDto
from api.services.gamechar_mgmt_service import CharactersMgmtService
from api.utils.helpers import HTTPLoggedException, get_llm_provider, get_request_db_name
from api.utils.statics import praise_db_name, sys_message_types, chat_event_cats



router = APIRouter(prefix="/mgmt/npc")

@router.post(
    "/factions/query",
    summary="Returns a collection of game factions (SystemMessageDoc) filtering by QueryConditions. Returns all factions if no QueryConditions are passed",
    responses={
        200:{"description": "Successful response will a collection of SystemMessageDto's containing the requested factions"}
    }
)
async def query_factions(filter: QueryFilter, request:Request) -> CollectionResponse:
    repo = SysMessagesRepository(get_request_db_name(request))
    docs: List[SystemMessageDto] = []
    records: List[Any] = []
    if(len(filter.conditions) > 0):
        records = await repo.query(filter.conditions)
    else:
        records = await repo.query(conditions=[QueryCondition(field="type", value=sys_message_types.faction_context)])
    docs = [toSystemMessageDto(record) for record in records if record["tag"] != "FactionRelationships"]
    if(filter.page is None and filter.page_size is None):
        return CollectionResponse(data=docs, total_records=len(docs))
    paged_results = []
    for i in range(filter.page * filter.page_size, filter.page * filter.page_size + filter.page_size):
        if(i < len(docs)):
            paged_results.append(docs[i])
    return CollectionResponse(data=paged_results, total_records=len(docs), total_pages=math.ceil(len(docs) / filter.page_size), page=filter.page)

@router.get(
    "/zones/containing/{tag}",
    summary="Returns a collection of game factions (SystemMessageDoc) filtering by QueryConditions. Returns all factions if no QueryConditions are passed",
    responses={
        200:{"description": "Successful response will a collection of SystemMessageDto's containing the requested factions"}
    }
)
async def get_zones_containing_tag(tag:str, request: Request) -> CollectionResponse:
    repo = SysMessagesRepository(get_request_db_name(request))
    docs = []
    if tag != "_":
        docs = await repo.get_many_by_type_containing_tag(type=sys_message_types.zone_context, tag=tag)
    else:
        docs = await repo.query([QueryCondition(field="type", value=sys_message_types.zone_context)])
    return CollectionResponse(data=[toSystemMessageDto(doc) for doc in docs])
@router.post(
    "/roles/query",
    summary="Returns a collection of game roles (CharacterRoleDoc) filtering by QueryConditions. Returns all factions if no QueryConditions are passed",
    responses={
        200:{"description": "Successful response will a collection of CharacterRoleDoc's containing the requested factions"}
    }
)
async def query_roles(filter: QueryFilter, request: Request) -> CollectionResponse:
    repo = CharacterRolesRepository(get_request_db_name(request))
    docs: List[CharacterRoleDto] = []
    records: List[Any] = []
    if(len(filter.conditions) > 0):
        records = await repo.query(filter.conditions)
    else:
        records = await repo.stringy_query({})
    docs = [toRoleDto(record) for record in records]
    if(filter.page is None and filter.page_size is None):
        return CollectionResponse(data=docs, total_records=len(docs))
    paged_results = []
    for i in range(filter.page * filter.page_size, filter.page * filter.page_size + filter.page_size):
        if(i < len(docs)):
            paged_results.append(docs[i])
    return CollectionResponse(data=paged_results, total_records=len(docs), total_pages=math.ceil(len(docs) / filter.page_size), page=filter.page)

@router.post(
    "/personalities/query",
    summary="Returns a collection of character personalities (CharacterPersonalityDoc) filtering by QueryConditions. Returns all factions if no QueryConditions are passed",
    responses={
        200:{"description": "Successful response will a collection of CharacterPersonalityDto's containing the requested factions"}
    }
)
async def query_personalities(filter: QueryFilter, request: Request) -> CollectionResponse:
    repo = CharacterPersonalitiesRepository(get_request_db_name(request))
    docs: List[CharacterPersonalityDto] = []
    records: List[Any] = []
    if(len(filter.conditions) > 0):
        records = await repo.query(filter.conditions)
    else:
        records = await repo.stringy_query({})
    docs = [toPersonalityDto(record) for record in records]
    if(filter.page is None and filter.page_size is None):
        return CollectionResponse(data=docs, total_records=len(docs))
    paged_results = []
    for i in range(filter.page * filter.page_size, filter.page * filter.page_size + filter.page_size):
        if(i < len(docs)):
            paged_results.append(docs[i])
    return CollectionResponse(data=paged_results, total_records=len(docs), total_pages=math.ceil(len(docs) / filter.page_size), page=filter.page)

@router.post(
    "/traits/query",
    summary="Returns a collection of character traits (CharacterTraitDoc) filtering by QueryConditions. Returns all factions if no QueryConditions are passed",
    responses={
        200:{"description": "Successful response will a collection of CharacterTraitDto's containing the requested factions"}
    }
)
async def query_traits(filter: QueryFilter, request: Request) -> CollectionResponse:
    repo = CharacterTraitsRepository(get_request_db_name(request))
    docs: List[CharacterTraitDto] = []
    records: List[Any] = []
    if(len(filter.conditions) > 0):
        records = await repo.query(filter.conditions)
    else:
        records = await repo.stringy_query({})
    docs = [toTraitDto(record) for record in records]
    if(filter.page is None and filter.page_size is None):
        return CollectionResponse(data=docs, total_records=len(docs))
    paged_results = []
    for i in range(filter.page * filter.page_size, filter.page * filter.page_size + filter.page_size):
        if(i < len(docs)):
            paged_results.append(docs[i])
    return CollectionResponse(data=paged_results, total_records=len(docs), total_pages=math.ceil(len(docs) / filter.page_size), page=filter.page)

@router.post(
    "/moods/query",
    summary="Returns a collection of game factions (CharacterMoodDoc) filtering by QueryConditions. Returns all factions if no QueryConditions are passed",
    responses={
        200:{"description": "Successful response will a collection of CharacterMoodDto's containing the requested factions"}
    }
)
async def query_moods(filter: QueryFilter, request: Request) -> CollectionResponse:
    repo = CharacterMoodsRepository(get_request_db_name(request))
    docs: List[CharacterMoodDto] = []
    records: List[Any] = []
    if(len(filter.conditions) > 0):
        records = await repo.query(filter.conditions)
    else:
        records = await repo.stringy_query({})
    docs = [toMoodDto(record) for record in records]
    if(filter.page is None and filter.page_size is None):
        return CollectionResponse(data=docs, total_records=len(docs))
    paged_results = []
    for i in range(filter.page * filter.page_size, filter.page * filter.page_size + filter.page_size):
        if(i < len(docs)):
            paged_results.append(docs[i])
    return CollectionResponse(data=paged_results, total_records=len(docs), total_pages=math.ceil(len(docs) / filter.page_size), page=filter.page)

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

@router.get(
    "/chat/llm-replicate/{chat_id}",
    summary="Generates a conversation in the style of the specified one using an LLM model",
    responses={
        200: {"description" : "Succesful response with the new conversation"}
    }
)
async def replicate_chat(chat_id:str, request:Request):
    repo = ChatPromptsRepository(get_request_db_name(request))
    sysmsg_repo = SysMessagesRepository(get_request_db_name(request))
    sessions_repo = ChatSessionsRepository(get_request_db_name(request))
    sysmsg_rec = await sysmsg_repo.get(varname="tag", value="chat-replicator")
    if sysmsg_rec is None:
        raise HTTPLoggedException(status_code=500, detail="-- No system message has been found for the chat-replication task --")
    sysmsg_doc: SystemMessageDoc = SystemMessageDoc.model_validate(sysmsg_rec)
    session_rec = await sessions_repo.get(varname="tag", value=sysmsg_doc.tag)
    session:SessionDoc = None
    if session_rec is None:
        session = SessionDoc(username="PraiseDeveloper", tag=sysmsg_doc.tag)
        session = SessionDoc.model_validate(await sessions_repo.create(session))
    else:
        session = SessionDoc.model_validate(session_rec)       
    chat_rec = await repo.get_by_id(chat_id)
    if chat_rec is None:
        raise HTTPLoggedException(status_code=400, details=f"-- No chat document has been found to replicate with ID: {chat_id}")
    chat:ChatPromptDoc = ChatPromptDoc.model_validate(chat_rec)
    chat_history = chat.messages_to_chat_history()
    history_text = request.app.model_provider.chat_history_to_template(chat_history=chat_history, exclude_sys_message=False, exclude_sys_updates=False, template_key="praise")
    names_split = chat.tag.split("-")
    formatted_history = history_text.replace("<<BOTNAME>>", names_split[0]).replace("<<USERNAME>>", names_split[1])
    print(formatted_history)
    # format_history <- chat_history_to_template(template-key='praise')
    #   chat_doc.split(tag) history = history.replace(<<BOTNAME>>, split[0]).replace("<<USERNAME>>", split[1])
    # sysmsg = sysmsg_doc.message.format("<<CHAT>>", formatted_history)
    # results = azure_prompt("GENERATE", sysmsg=sysmsg)
    # parse_result_with_template
    # return new doc_dto

@router.post(
    "/character/generate",
    summary="Returns a generated game char dto containing a minimal version of the character faction, profile, traits etc",
    responses={
        200: {"description" : "Succesful response with the full game char data model"}
    }
)
async def generate_character(req: GenerateCharacterRequest, request: Request) -> Any:
    svc = CharactersMgmtService(get_request_db_name(request))
    try:
        
        # personalities -> getall -> pick random -> if total < rnd_idx pickRandom[current.excluyent]
        # lo mismo con traits
        # con todo menos el nombre y la edad saco el lore
        # con tdo eso hago el profile aunque sea por partes
        logger.warning("### ON GENERATE CHARACTER REQUEST ##\n\n")
        print(req)
        result = await svc.generate_character(req, get_llm_provider())
        return gameCharToDto(result)
        if result is not None:
            insert = await svc.save_game_character(result)
            return gameCharToDto(insert)
        else:
            return None
    except Exception as e:
        raise HTTPLoggedException(status_code=500, detail=f"-- an error has occured while generating the character --\n{e}")

@router.post(
    "/character/save",
    summary="Saves a PraiseCharacterDto in Mongo",
    responses={
        200: {"description" : "Succesful response with the full game char data model"}
    }
)
async def save_character(req: PraiseCharacterDto, request: Request):
    svc = CharactersMgmtService(get_request_db_name(request))
    insert = await svc.save_game_character(charDtoToDoc(req))
    return gameCharToDto(insert)
@router.get(
    "/character/{name}/full-profile",
    summary="Returns a generated game char dto containing all the data to display (faction / role / trait descriptons, profile...)",
    responses={
        200: {"description" : "Succesful response with the full game char data model"}
    }
)
async def get_full_profile_by_name(name:str, request: Request) -> FullPraiseCharDto:
    svc = CharactersMgmtService(get_request_db_name(request))
    return await svc.get_full_profile(name=name)

@router.get(
    "/character/{id}/profile",
    summary="Returns a generated game char dto containing the minimal data to display (faction / role / trait descriptons, profile...)",
    responses={
        200: {"description" : "Succesful response with the reduced game char data model"}
    }
)
async def get_character_by_id(id: str, request: Request) -> PraiseCharacterDto:
    svc = CharactersMgmtService(get_request_db_name(request))
    return gameCharToDto(await svc.get_character(id))   

@router.post(
    "/chat/{chat_id}/add-event",
    summary="Generates a conversation in the style of the specified one using an LLM model",
    responses={
        200: {"description" : "Succesful response with the new conversation"}
    }
)
async def add_chat_event(chat_id:str, dto: ChatEventDto, request: Request) -> bool:
    if chat_id is None or len(chat_id) == 0:
        raise HTTPLoggedException(status_code=400, detail="NO CHAT ID PRESENT IN THE REQUEST")
    if dto is None:
        raise HTTPLoggedException(status_code=400, detail="EVENT DTO IS NULL")
    if len(dto.message) == 0:
        raise HTTPLoggedException(status_code=400, detail="NO CHAT EVENT MESSAGE PRESENT IN DTO")
    if len(dto.category) == 0:
        raise HTTPLoggedException(status_code=400, detail="NO CHAT EVENT CATEGORY PRESENT IN DTO")
    svc = CharactersMgmtService(get_request_db_name(request))
    return await svc.insert_chat_event(chat_id=chat_id, category=dto.category, event_tag=chat_event_cats.to_string(dto.tag_id), message=dto.message)
    