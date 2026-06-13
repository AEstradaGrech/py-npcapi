
from typing import List, Optional

from bson import ObjectId
from loguru import logger

from api.infrastructure.models.db_schemas import ChatDetailsDoc, ChatPromptDoc, ChatSummaryDoc, SessionDoc, SystemMessageDoc
from api.infrastructure.models.primitives import ChatEvent
from api.infrastructure.repositories.mongo.chat_prompts import ChatDetailsRepository, ChatPromptsRepository, ChatSessionsRepository
from api.infrastructure.repositories.mongo.chat_summaries_repo import ChatSummariesRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.models.schemas import QueryCondition
from api.utils.helpers import HTTPLoggedException, filter_objects_by_kvp


class ChatsMgmtService:

    _chatsRepo: ChatPromptsRepository = None
    _sysRepo: SysMessagesRepository = None
    _sessionsRepo: ChatSessionsRepository = None
    _summariesRepo: ChatSummariesRepository = None
    _currentDB:str = None

    def __init__(self, repos_db: str):
        self._currentDB = repos_db if repos_db is not None and repos_db != "" else default_db_name
        self._chatsRepo = ChatPromptsRepository(self._currentDB)
        self._sysRepo = SysMessagesRepository(self._currentDB)
        self._sessionsRepo = ChatSessionsRepository(self._currentDB)
        self._summariesRepo = ChatSummariesRepository(self._currentDB)

    async def get_chat_details(self, chat_id:str) -> Optional[ChatDetailsDoc]:
        repo = ChatDetailsRepository(praise_db_name)
        record = await repo.get(varname="chat_doc_id", value=chat_id)
        return None if record is None else ChatDetailsDoc.model_validate(record)
    
    async def get_session_current_chat(self, session_id:str) -> Optional[ChatPromptDoc]:
        sessions_repo = ChatSessionsRepository(praise_db_name)
        session_record = await sessions_repo.get_by_id(session_id)
        if session_record is None:
            return None
        session = SessionDoc.model_validate(session_record)
        chats_repo = ChatPromptsRepository(praise_db_name)
        chat = await chats_repo.get_by_id(session.current_chat_id)
        return None if chat is None else ChatPromptDoc.model_validate(chat)
    
    async def get_chat_doc(self, id:str) -> ChatPromptDoc:
        chats_repo = ChatPromptsRepository(praise_db_name)
        return ChatPromptDoc.model_validate(await chats_repo.get_by_id(id))
    
    async def insert_chat_event(self, chat_id:str, category:str, event_tag:str, message:str, turn_id:int = None) -> bool:
        details_repo = ChatDetailsRepository(praise_db_name)
        details_record = await details_repo.get(varname="chat_doc_id", value=chat_id)
        if details_record is None:
            logger.info(f"-- NO CHAT DETAILS found for chat id: {chat_id}")
            return False
        details = ChatDetailsDoc.model_validate(details_record)
        if turn_id is None:
            chats_repo = ChatPromptsRepository(praise_db_name)
            chat = ChatPromptDoc.model_validate(await chats_repo.get_by_id(id=chat_id))
            turn_id = len(chat.messages)
        details.chat_events.append(ChatEvent(category=category, chat_turn_id=turn_id, tag=event_tag, message=message))
        return await details_repo.update(details.id, details) #TODO: check return result
        
    async def create_summary(self, doc:ChatSummaryDoc) -> ChatSummaryDoc:
        repo = ChatSummariesRepository(praise_db_name)
        doc.id = ObjectId()
        return ChatSummaryDoc.model_validate(await repo.create(doc))
    
    async def update_summary(self, doc:ChatSummaryDoc) -> ChatSummaryDoc:
        repo = ChatSummariesRepository(praise_db_name)
        await repo.update(doc.id, doc)
        return ChatSummaryDoc.model_validate(doc)
    
    async def query_summaries(self, conditions: List[QueryCondition]) -> List[ChatSummaryDoc]:
        repo = ChatSummariesRepository(praise_db_name)
        docs = await repo.query(conditions=conditions)
        return [ChatSummaryDoc.model_validate(doc) for doc in docs] if len(docs) > 0 else []
    
    async def update_details(self, details:ChatDetailsDoc) -> ChatDetailsDoc:
        repo = ChatDetailsRepository(praise_db_name)
        await repo.update(details.id, details)
        return ChatDetailsDoc.model_validate(details)
    
    async def get_output_action_docs(self, filter_tags:List[str] = []) -> List[SystemMessageDoc]:
        results = []
        repo = SysMessagesRepository(praise_db_name)
        docs = await repo.query(conditions=[QueryCondition(field="type", value=sys_message_types.output_action)])
        if len(docs) == 0:
            return []
        if len(filter_tags) > 0:
            for item in docs:
                doc = SystemMessageDoc.model_validate(item)
                if doc.tag in filter_tags:
                    results.append(doc)
        else:
            results = [SystemMessageDoc.model_validate(doc) for doc in docs]
        return results
    
    async def remove_chat_event_with_tag(self, chat_id:str, tag:str, category_filter:str = None) -> bool:
        repo = ChatDetailsRepository(praise_db_name)
        record = await repo.get(varname="chat_doc_id", value=chat_id)
        if record is None:
            logger.info(f"-- attempting to remove chat event with tag: {tag} / cat: {category_filter if category_filter is not None else "NONE"}. Chat with id: {chat_id} NOT FOUND")
            return False
        is_event_removed: bool = False
        details = ChatDetailsDoc.model_validate(record)
        chat_events = details.chat_events if category_filter is None else filter_objects_by_kvp(key="category", value=category_filter, objects=details.chat_events) 
        logger.info(f"-- total events with tag {tag} = {len(chat_events)}")
        print(chat_events)
        for event in chat_events:
            if event.tag == tag:
                details.chat_events.remove(event)
                await repo.update(details.id, details)
                is_event_removed = True
        return is_event_removed
    
    async def set_current_session_chat_status(session_id: str, status:bool):
        repo = ChatSessionsRepository(db_name=praise_db_name)
        record = await repo.get_by_id(session_id)
        if record is not None:
            doc = SessionDoc.model_validate(record)
            doc.current_chat_ongoing = status
            await repo.update(doc.id, doc)

    async def set_current_session_chat_status_by_chat_id(chat_id: str, status:bool):
        sessions_repo = ChatSessionsRepository(db_name=praise_db_name)
        chats_repo = ChatPromptsRepository(db_name=praise_db_name)
        chat_record = await chats_repo.get_by_id(chat_id)
        if chat_record is None:
            raise HTTPLoggedException(status_code=400, detail=f"-- No chat doc has been found for id {chat_id} --")
        chat_doc = ChatPromptDoc.model_validate(chat_record)
        record = await sessions_repo.get_by_id(chat_doc.session_id)
        if record is not None:
            doc = SessionDoc.model_validate(record)
            doc.current_chat_ongoing = status
            await sessions_repo.update(doc.id, doc)
    