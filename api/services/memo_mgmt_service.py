
from datetime import datetime
from typing import List

from bson import ObjectId
from loguru import logger

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.infrastructure.models.char_db_schemas import CharacterMoodDoc
from api.infrastructure.models.db_schemas import ChatDetailsDoc, ChatPromptDoc, ChatSummaryDoc, SessionDoc, SystemMessageDoc
from api.infrastructure.repositories.mongo.chat_prompts import ChatDetailsRepository, ChatPromptsRepository, ChatSessionsRepository
from api.infrastructure.repositories.mongo.chat_summaries_repo import ChatSummariesRepository
from api.infrastructure.repositories.mongo.mongo_repos import GameCharsRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.models.schemas import QueryCondition
from api.services.chats_mgmt_service import ChatsMgmtService
from api.services.mood_analysis_service import MoodAnalysisService
from api.utils.helpers import HTTPLoggedException, update_memo_cache_value
from api.utils.statics import event_tags, chat_turns_to_generate_memory, sys_message_types, praise_db_name, default_db_name, min_chat_turns_for_longterm_summary

class MemoMgmtService():

    _chats_svc: ChatsMgmtService = None
    _chatsRepo: ChatPromptsRepository = None
    _sysRepo: SysMessagesRepository = None
    _sessionsRepo: ChatSessionsRepository = None
    _summariesRepo: ChatSummariesRepository = None
    _currentDB:str = None

    def __init__(self, repos_db: str):
        self._currentDB = repos_db if repos_db is not None and repos_db != "" else default_db_name
        self._chats_svc = ChatsMgmtService(self._currentDB)
        self._chatsRepo = ChatPromptsRepository(self._currentDB)
        self._sysRepo = SysMessagesRepository(self._currentDB)
        self._sessionsRepo = ChatSessionsRepository(self._currentDB)
        self._summariesRepo = ChatSummariesRepository(self._currentDB)

    async def update_shortmemo(self, chat: ChatPromptDoc, model_provider: LLM_Provider) -> ChatSummaryDoc | None:
        sysmsgs_repo = SysMessagesRepository(praise_db_name)
        memos = await self._summariesRepo.query(conditions=[QueryCondition(field="chat_collection_id", value=chat.id)])
        chat_turns = chat.messages_to_chat_history() if len(memos) == 0 else chat.messages_to_chat_history()[(len(memos)*chat_turns_to_generate_memory):len(chat.messages)]
        print("MEMO TURNS", chat_turns)
        if len(chat_turns) < chat_turns_to_generate_memory:
            logger.info(f"-- CHAT MEMORY HANDLING >> Not enough turns to generate a Memory >> n_turns: {len(chat_turns)} --")
            return None
        summarization_doc = SystemMessageDoc.model_validate(await sysmsgs_repo.get_by_type_and_tag(type=sys_message_types.summary_template, tag="ch-of-th-v3.1.4"))
        final_history = chat_turns
        #Si es el primer MEMO, se elimina SYS_MSG con todas las reglas etc y se pasa solo info de contexto sobre chars y zona
        final_history = [{"system":await self.get_memo_contextualization_text(chat.id)}]
        for turn in chat_turns[1 if len(chat_turns) == 0 else 0:len(chat_turns)]:
            final_history.append(turn)
        print("-- ON GENERATE MEMORY - FINAL HISTORY --", final_history)
        memory = model_provider.chat_summary(sys_msg=summarization_doc.message, chat_history=final_history, exclude_sys_updates=False)
        # TODO: SentenceTransformers -> Generate Embedding w/final_history -> add ChatSummaryDoc field
        # usar SpaCy para detectar Personas Lugares etc <- si encuentran en user prompt -> se usa RAG w/memo embeddings [similarity_threshold!!!]
        summary_id = ObjectId()
        print("-- summary ID --", summary_id)
        if memory:
            memo = ChatSummaryDoc(
                sys_prompt_tag=summarization_doc.tag,
                session_id=chat.session_id,
                chat_collection_id=chat.id,
                prompt=memory[0].strip(),
                summary=memory[1].strip(),
                observations=[f"chat-chunk-{len(memos) +1}", f"{event_tags.assistant_memo}:SHORT_MEMO"]
            )
            memory_insert = await self.create_summary(memo)
            #20/05/25 --> MOOD_TRANSITIONS
            mood_analysis_split = memory[1].split("**Mood**") 
            mood_eval = mood_analysis_split[1].strip() if len(mood_analysis_split) > 0 else mood_analysis_split[0]
            label = "NEUTRAL"
            if "HOSTILE" in mood_eval:
              label = "HOSTILE"
            if "FRIENDLY" in mood_eval:
              label = "FRIENDLY"
            new_mood = await self.process_chat_mood_analysis(chat_id= chat.id, attitude_label=label)
            if new_mood != "None":
                logger.info(f"-- CHAT MOOD UPDATE >> NEW MOOD: {new_mood}")
                await self._chats_svc.insert_chat_event(chat_id=chat.id, category="assistant", event_tag=event_tags.assistant_memo, message=f"CHAT MOOD TRANSITION >> NEW MOOD: {new_mood} >> doc_id: {memory_insert.id}", turn_id=len(chat.messages))
                
            await self._chats_svc.insert_chat_event(chat_id=chat.id, category="assistant", event_tag=event_tags.assistant_memo, message=f"MEMORY_GENERATION >> {memo.observations[0]} >> doc_id: {memory_insert.id}", turn_id=len(chat.messages))
            details = await self.get_chat_details(chat_id=chat.id)
            if details is not None:
                update_memo_cache_value(details=details, key="chat-memo", value=f"\n\nSHORT TERM MEMORY {len(memos) +1}:\n{memo.summary.strip()}")
                if await self.update_details(details=details) is False:
                    raise HTTPLoggedException(status_code=500, detail="-- BOT MEMO CHACHE UPDATE FAIL >> APPEND SHORT MEMO FAIL --")    
            return memory_insert
        return None    
    
    async def update_longmemo(self, chat_id:str, model_provider: LLM_Provider) -> ChatPromptDoc:
    
        chat = ChatPromptDoc.model_validate(await self._chatsRepo.get_by_id(chat_id))
        
        memos = await self.query_summaries(conditions=[QueryCondition(field="chat_collection_id", value=chat_id)])
        chat_turns = chat.messages_to_chat_history() if len(memos) == 0 else chat.messages_to_chat_history()[(len(memos)*chat_turns_to_generate_memory):len(chat.messages)]
        print("MEMO TURNS", chat_turns)
        summarization_doc = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(type=sys_message_types.summary_template, tag="ch-of-th-v3.1.3-longterm"))
        final_history = chat_turns
        if len(memos) == 0:
            final_history = [{"system":await self.get_memo_contextualization_text(chat.id)}]
            for turn in chat_turns[1:len(chat_turns)]:
                final_history.append(turn)
        else:
            min_memos = len(memos) -1 if len(chat_turns) < min_chat_turns_for_longterm_summary else len(memos)
            short_term_memos = [memo for memo in memos[0:min_memos]] if len(memos) > 1 else memos
            short_term_memos_text = ""
            for memo in short_term_memos:
                short_term_memos_text += f"\n\n>> CONVERSATION SUMMARIZATION {memo.observations[0].split("-")[-1]}\n{memo.summary}"
            final_history = [{"context": f"{short_term_memos_text}"}]
            turns = chat.messages_to_chat_history()[(min_memos*chat_turns_to_generate_memory):len(chat.messages)] if min_memos > 0 else chat.messages_to_chat_history()
            for turn in turns:
                final_history.append(turn)
        print("-- ON GENERATE LONG MEMORY - FINAL HISTORY --", final_history)
        memory = model_provider.chat_summary(sys_msg=summarization_doc.message, chat_history=final_history, temperature=0.5, max_tokens=600, ctx_len=4096, exclude_sys_updates=False)
        summary_id = ObjectId()
        print("-- summary ID --", summary_id)
        if memory:
            memo = ChatSummaryDoc(
                sys_prompt_tag=summarization_doc.tag,
                session_id=chat.session_id,
                chat_collection_id=chat.id,
                prompt=memory[0].strip(),
                summary=memory[1].strip(),
                observations=["full-chat", f"{event_tags.assistant_memo}:LONG_MEMO"]
            )
            memory_insert = await self.create_summary(memo)
            #TODO: Session.Summary generation = Analisis de relacion con char y clasificacion FoEoN
            sessions_repo = ChatSessionsRepository(praise_db_name)
            session_doc = SessionDoc.model_validate(await sessions_repo.get_by_id(chat.session_id))
            session_doc.current_chat_summary = memory_insert.summary
            session_doc.current_chat_ongoing = False
            session_doc.current_summary_update_date = datetime.now()
            #session_doc.summary = relationship_summarization[1]
            await sessions_repo.update(session_doc.id, session_doc)
            await self._chats_svc.insert_chat_event(chat_id=chat.id, category="assistant", event_tag=event_tags.assistant_memo, message=f"LONGTERM-MEMORY_GENERATION >> {memo.observations[0]} >> doc_id: {memory_insert.id}", turn_id=len(chat.messages))
            return memory_insert
        return None  

    async def get_session_longterm_memo_text(self,session_id:str, exclude_current_chat:bool = False) -> str:

        session_doc = SessionDoc.model_validate(await self._sessionsRepo.get_by_id(session_id))
        
        conditions=[QueryCondition(field="session_id", value=session_id), QueryCondition(field="observations", value="full-chat")]    
        longterm_memos = await self._summariesRepo.query(conditions=conditions)
        print("-- LEN LONG TERM MEMOS --", len(longterm_memos))
        if exclude_current_chat is True:
            longterm_memos = [ChatSummaryDoc.model_validate(memo) for memo in longterm_memos if ChatSummaryDoc.model_validate(memo).chat_collection_id != session_doc.current_chat_id]
        section_text = ""
        if len(longterm_memos) > 0:
            section_text = "You have met this character previously. This is what you recall from the previous conversations in the order they occured:"
            for i in range(0, len(longterm_memos) -1):
                section_text += f"\n\n>> LONG TERM MEMORY {i+1}:\n{longterm_memos[i].summary}"
        return section_text  
    
    def append_longterm_memories_to_sysmsg(self,history:dict[str, str], longmemos_text):
        if len(longmemos_text) == 0:
            return history
        sysmsg = history[0]["system"]
        if sysmsg != "":
            sysmsg += longmemos_text
            history[0]["system"] = sysmsg
        return history
    
    async def process_chat_mood_analysis(self, chat_id: str, attitude_label:str) -> str:
        analysis_service = MoodAnalysisService()
        details:ChatDetailsDoc = await self._chats_svc.get_chat_details(chat_id=chat_id)
        if details is None:
            logger.warning(f"-- No chat details found for chat_id: {chat_id} - skipping chat mood transition")
            return "None"
        new_mood = analysis_service.handle_chat_mood_transition(current_bot_mood=details.botMood, bot_personalities=details.botPersonalities, chat_sentiment=attitude_label)
        if new_mood == details.botMood:
            logger.info(f"-- Chat Mood Transition result: remain in current mood --")
            return "None" 
        logger.info(f"-- NEW CHAT MOOD TRANSITION >> NEW MOOD: {new_mood}")
        details.botMood = new_mood
        mood_doc:CharacterMoodDoc = await self.get_mood_doc(mood=new_mood)
        if mood_doc is None:
            logger.warning(f"-- No MOOD DOC has been found for mood: {new_mood} >> Skipping Chat Mood Transition process")
            return "None"
        # if mood is not None:
        #     result += f"- Current Mood:\n> {mood.name}: {mood.sys_msg_text}"
        
        details.botMemory["current-mood"] = f"- Current Mood:\n> {mood_doc.name}: {mood_doc.sys_msg_text}"
        logger.info(f"-- CHAT MOOD TRANSITION >> PROFILE UPDATE:\n {details.botMemory.get("current-mood")}")
        await self.update_details(details=details)
        return details.botMood #mantiene el mood en el que está

    async def handle_chat_assistant_memo(self, chat_id:str, recent_history:dict[str,str], with_short_memos:bool = True) -> dict[str,str]:
        details = await self._chats_svc.get_chat_details(chat_id=chat_id)
        if details is None:
            raise HTTPLoggedException(status_code=500, detail=f"CHAT MEMORY SETUP ERROR >> No ChatDetailsDoc found for chat: {chat_id}. Ongoing chats MUST have an associated Details doc")
        if details.botMemory.get("chat-memo") is not None: # Añade RECEN & LONG (if any) formados OnInit (chats previos)
            recent_history[0]["system"] += f"\n\n{details.botMemory["chat-memo"]}"
        #Añade REMARKABLES ocurridos en current_session (como JOIN)
        #print("-- DETAILS EVENTS --", details.chat_events)
        # chat_remarkable_events = filter_objects_by_kvp(key="category", value=chat_event_cats.to_string(chat_event_cats.remarkable_event), objects=details.chat_events)
        # print("-- CHAT REMARKABLE EVENTS --", chat_remarkable_events)
        events_text = None
        # for rem_event in chat_remarkable_events:
        #     if events_text is None:
        #         events_text = f"\n\n>> REMARKABLE CHAT EVENTS: This are the most relevant facts that have occured during the conversation and other information that might be relevant in order to generate your answer:"
        #     events_text += f"{rem_event.category}: {rem_event.message}"
        # if events_text is not None:
        #     recent_history[0]["system"] += events_text
        # REMARKABLES v2 --> OnGenerate -> Update Cache (igual que DynActions v2)
        if details.botMemory.get("chat-remarkable-events") is not None:    
            events_text = f"\n\n>> REMARKABLE CHAT EVENTS: This are the most relevant facts that have occured during the conversation that might be relevant in order to generate your answer:\n\n{details.botMemory["chat-remarkable-events"]}"
        if events_text is not None:
            recent_history[0]["system"] += events_text
        if with_short_memos:
            recent_history = await self.append_shortmemos_to_recent_history(chat_id=chat_id, history=recent_history, from_bot_memo=True)
        return recent_history
    
    async def append_shortmemos_to_recent_history(self,chat_id:str, history:dict[str, str], from_bot_memo: bool = False, update_cache:bool = False):
        memo_msg = ""
        final_history = [history[0]]
        if from_bot_memo:
            print("-- CHECKING BOT MEMORY CACHE SHORT MEMOS --")
            details = await self._chats_svc.get_chat_details(chat_id=chat_id)
            if details is not None and details.botMemory.get("chat-memo") is not None:
                memo_cache = details.botMemory["chat-memo"]
                if memo_cache != "":
                    memo_msg = f"{event_tags.assistant_memo}: Here is some context information about your previous interactions with the Player Character and the resulting mood of it. Use this memories to provide a more accurate and rich response to the user:\n\n{memo_cache}"
        else:
            print("-- RETRIEVING SHORT MEMOS FROM DATABASE --")
            
            records = await self._summariesRepo.query(conditions=[
                QueryCondition(field="chat_collection_id", value=chat_id), 
                QueryCondition(field="observations",value=f"{event_tags.assistant_memo}:SHORT_MEMO")])
            if len(records) == 0:
                return history
            memos = [ChatSummaryDoc.model_validate(doc) for doc in records]
            memo_msg = f"{event_tags.assistant_memo}: Here is some context information about your previous interactions with the Player Character and the resulting mood of it. Use this memories to provide a more accurate and rich response to the user:"
            for memo in memos:
                id = memo.observations[0].split("-")[-1]
                memo_msg += f"\n\nSHORT TERM MEMORY {id}:\n{memo.summary}"
        if memo_msg != "":
            final_history.append({"context": f"{memo_msg}\n"}) #se intercala el mensaje con las MEMORIES entre el SysMsg original (con las reglas y LONGMEMORIES) y la conversacion reciente (con [ctx-updates])
        for i in range(1, len(history)):
            final_history.append(history[i])
        return final_history

    async def get_memo_contextualization_text(self, chat_id:str)->str:
        details_repo = ChatDetailsRepository(praise_db_name)
        details = ChatDetailsDoc.model_validate(await details_repo.get(varname="chat_doc_id", value=chat_id))
        sysmsgs_repo = SysMessagesRepository(praise_db_name)
        zone_doc = SystemMessageDoc.model_validate(await sysmsgs_repo.get_by_type_and_tag(type=sys_message_types.zone_context, tag=details.zoneName))
        text = f"{event_tags.zone_ctx}: The conversation takes place in {details.zoneName}\n- Zone Description:\n{zone_doc.message}"
        botchar_text = f"\n\n{event_tags.assistant_ctx}: Speaker type = NON-PLAYER\n{details.botMemory["profile"]}"
        text += botchar_text
        userchar_text = f"\n\n{event_tags.user_ctx}: Speaker type = PLAYER\n- Player-Character Name: {details.usercharName}\n- Player-Character Role:{details.usercharRole}\n- Player-Character Faction:{details.userfaction}"
        text += userchar_text
        return text
    
    async def create_summary(self, doc:ChatSummaryDoc) -> ChatSummaryDoc:
        repo = ChatSummariesRepository(self._currentDB)
        return ChatSummaryDoc.model_validate(await repo.create(doc))
    
    async def update_summary(self, doc:ChatSummaryDoc) -> ChatSummaryDoc:
        repo = ChatSummariesRepository(self._currentDB)
        await repo.update(doc.id, doc)
        return ChatSummaryDoc.model_validate(doc)
    
    async def query_summaries(self, conditions: List[QueryCondition]) -> List[ChatSummaryDoc]:
        repo = ChatSummariesRepository(self._currentDB)
        docs = await repo.query(conditions=conditions)
        return [ChatSummaryDoc.model_validate(doc) for doc in docs] if len(docs) > 0 else []
    