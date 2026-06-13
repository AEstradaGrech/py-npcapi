

from typing import Any, List

from fastapi import APIRouter, Request
from loguru import logger

from api.infrastructure.models.db_schemas import SystemMessageDoc
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.mappers.mgmt_mappers import toSystemMessageDto
from api.models.schemas import CollectionResponse, QueryCondition, QueryFilter, SysMessageTypeDto, SystemMessageDto
from api.services.sysmsg_mgmt_service import SysmsgMgmtService
from api.utils.helpers import HTTPLoggedException, get_request_db_name
from api.utils.statics import sys_message_types

router = APIRouter(prefix="/mgmt/sys_messages")

@router.get(
    "/{id}",
    summary="Gets a SysMessageDoc by its GUID",
    responses={
        200: {"description" : "Succesful response with the system message document"}
    }
)
async def get_sys_message_by_id(id:str, request: Request) -> SystemMessageDto:
    svc = SysmsgMgmtService(repo_collection=get_request_db_name(request))
    return await svc.get_sys_message_by_id(id=id)
    
@router.post(
    "/create",
    summary="Creates a system message document",
    responses={
        200: {"description" : "Succesful response with the created document"}
    }
)
async def create_sys_message(dto: SystemMessageDto, request: Request) -> SystemMessageDto:
    repo = SysMessagesRepository(get_request_db_name(request))
    doc = SystemMessageDoc(type=dto.type, description=dto.description, message=dto.message, tag=dto.tag)
    doc.description = sys_message_types.to_string(value=doc.type)
    del doc.id
    inserted = SystemMessageDoc.model_validate(await repo.create(doc))
    return SystemMessageDto(id=inserted.id, type=inserted.type, description=inserted.description, message=inserted.message, tag=inserted.tag)

@router.put(
    "/update",
    summary="Update a system message document",
    responses={
        200: {"description" : "Succesful response with the update document"}
    }
)
async def update(dto: SystemMessageDto, request: Request) -> Any:
    print(dto)
    repo = SysMessagesRepository(get_request_db_name(request))
    doc = SystemMessageDoc.model_validate(await repo.get_by_id(dto.id))
    doc.message = dto.message
    doc.tag = dto.tag
    doc.type = dto.type
    doc.description = sys_message_types.to_string(dto.type)
    await repo.update(doc.id, doc)
    print(doc)
    return SystemMessageDto(id=doc.id, type=doc.type, description=doc.description, message=doc.message, tag=doc.tag)

@router.delete(
    "/{id}",
    summary="Deletes a system message document",
    responses={
        200: {"description" : "Succesful response with boolean"}
    }
)
async def delete_sys_message_by_id(id:str, request: Request) -> bool:
    repo = SysMessagesRepository(get_request_db_name(request))
    doc = await repo.get_by_id(id)
    if doc is None:
        raise HTTPLoggedException(status_code=404, detail="No document has been found with that GUID")
    await repo.delete_by_id(id)
    return True

@router.get(
    "/collection/by-tag/{tag}",
    summary="Gets a system message document",
    responses={
        200: {"description" : "Succesful response with a nice and simple 'OK'"}
    }
)
async def get_sys_messages_by_tag(tag:str, request: Request) -> List[SystemMessageDoc]:
    svc = SysmsgMgmtService(repo_db_name=get_request_db_name(request))
    return await svc.get_sys_messages_by_tag(tag=tag)

@router.get(
    "/collection/by-desc/{description}",
    summary="Deletes a system message document",
    responses={
        200: {"description" : "Succesful response with a nice and simple 'OK'"}
    }
)
async def get_sys_messages_by_description(description:str, request: Request) -> List[SystemMessageDoc]:
    repo = SysMessagesRepository(get_request_db_name(request))
    logger.info("-- on get many --")
    docs = await repo.get_many("description", description)
    logger.info("-- docs retrieved --")
    print(type(docs))
    print(docs)
    return docs

@router.get(
    "/collection/containing-tag/{tag}",
    summary="Retrieves a collection of system messages whose tag contains the specified string",
    responses={
        200: {"description" : "Succesful response with a collection of SystemMessageDoc's"}
    }
)
async def get_sys_messages_containing_tag(tag:str, request: Request) -> List[SystemMessageDoc]:
    repo = SysMessagesRepository(get_request_db_name(request))
    logger.info("-- on get many --")
    docs = await repo.get_many_containing_string("tag", tag)
    logger.info("-- docs retrieved --")
    print(docs)
    return docs

@router.get(
    "/collection/type/{type}/containing-tag/{tag}",
    summary="Retrieves a collection of system messages of the specified type whose tag contains the specified string",
    responses={
        200: {"description" : "Succesful response with a collection of SystemMessageDoc's"}
    }
)
async def get_sys_messages_containing_tag(tag:str, type:int, request: Request) -> List[SystemMessageDto]:
    repo = SysMessagesRepository(get_request_db_name(request))
    logger.info("-- on get many --")
    print("TAG", tag)
    if tag == "_":
        docs  = await repo.query([QueryCondition(field="type", value=type)])
    else:
        docs = await repo.get_many_by_type_containing_tag(type=type, tag=tag)
    logger.info("-- docs retrieved --")
    print(docs)
    return [toSystemMessageDto(doc) for doc in docs] if len(docs) > 0 else []


@router.post(
    "/query",
    summary="Returns a collection of SystemMessageDto's filtered by conditions (if any) with optional pagination",
    responses={
        200: {"description" : "Succesful response with the updated session data"}
    }
)
async def query(filter: QueryFilter, request: Request) -> CollectionResponse:
    print("ON SYS MSG QUERY")
    svc = SysmsgMgmtService(repo_db_name=get_request_db_name(request))
    return await svc.query(filter=filter)

@router.get(
    "/msg/types",
    summary="Returns a dictionary with al the message types and their descriptions",
    responses={
        200: {"description" : "Succesful response with the system message types"}
    }
)
async def get_message_types() -> List[SysMessageTypeDto]:
    values = sys_message_types.values
    results = []
    for value in values.keys():
        results.append(SysMessageTypeDto(type=value, description=values[value]))
    return results