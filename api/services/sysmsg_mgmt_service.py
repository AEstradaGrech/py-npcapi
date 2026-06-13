from typing import Any, List

from api.infrastructure.models.db_schemas import SystemMessageDoc
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.mappers.mgmt_mappers import toSystemMessageDto
from api.models.schemas import CollectionResponse, SysMessageTypeDto, SystemMessageDto, QueryFilter
from api.utils.statics import sys_message_types, default_db_name
from api.utils.helpers import get_request_db_name
from loguru import logger
import math

class SysmsgMgmtService:
    _repo: SysMessagesRepository

    def __init__(self, repo_db_name:str = None, repo_collection:str = None):
        if repo_db_name is None:
            repo_db_name = default_db_name
        self._repo = SysMessagesRepository(db_name=repo_db_name) if repo_collection is None else SysMessagesRepository(db_name=repo_db_name, col_name=repo_collection)
        logger.info(f"-- Initializing System Messages Service >> db: {repo_db_name} >> collection: {repo_collection if repo_collection is not None else "SystemMessages"}")

    async def get_sys_message_by_id(self, id:str) -> SystemMessageDoc:
        return toSystemMessageDto(await self._repo.get_by_id(id))

    async def get_sys_messages_by_tag(self, tag:str) -> List[SystemMessageDto]:
        logger.info("-- on get many --")
        docs = await self._repo.get_many("tag", tag)
        logger.info("-- docs retrieved --")
        return [ toSystemMessageDto(doc) for doc in docs ]
    
    async def get_sys_messages_by_type_and_tag(self, type: int, tag:str) -> List[SystemMessageDto]:
        logger.info(f"-- on get many by type ({type}) and tag ({tag}) --")
        docs = await self._repo.get_by_type_and_tag(type=type, tag=tag)
        logger.info("-- docs retrieved --")
        return [ toSystemMessageDto(doc) for doc in docs ]
    
    async def get_sys_messages_by_type_containing_tag(self, type: int, tag:str) -> List[SystemMessageDto]:
        logger.info(f"-- on get many by type ({type}) containing tag ({tag}) --")
        docs = await self._repo.get_many_by_type_containing_tag(type=type, tag=tag)
        logger.info("-- docs retrieved --")
        return [ toSystemMessageDto(doc) for doc in docs ]
    
    async def query(self, filter: QueryFilter) -> CollectionResponse:
        logger.info("-- on sysmsg service query --")
        docs = []
        if len(filter.conditions) > 0:
            docs = await self._repo.query(filter.conditions)
        else:    
            docs = await self._repo.stringy_query({})
        results = []
        print('retrieved docs',docs)
        if len(docs) > 0:
            if filter.page is None and filter.page_size is None:
                results = [toSystemMessageDto(doc) for doc in docs]
                return CollectionResponse(data=results, page=0, total_pages=1, total_records=len(docs))
            for i in range(filter.page * filter.page_size, filter.page * filter.page_size + filter.page_size):
                if i >= len(docs):
                    break
                results.append(toSystemMessageDto(docs[i]))
            pages = math.ceil(len(docs) / filter.page_size) if len(docs) > 0 else 0
            return CollectionResponse(data=results, page=filter.page, total_pages=pages, total_records=len(docs))
        return CollectionResponse(data=results, page=0, total_pages=0, total_records=0)