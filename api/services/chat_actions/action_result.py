from typing import List, Optional

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.infrastructure.models.db_schemas import ChatDetailsDoc, ChatPromptDoc, ChatSummaryDoc, SystemMessageDoc
from api.infrastructure.models.primitives import ChatEvent
from api.infrastructure.repositories.mongo.chat_prompts import ChatDetailsRepository, ChatPromptsRepository, ChatSessionsRepository
from api.infrastructure.repositories.mongo.chat_summaries_repo import ChatSummariesRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.models.schemas import QueryCondition
from api.services.botctx_mgmt_service import BotContextMgmtService
from api.services.chats_mgmt_service import ChatsMgmtService
from api.services.memo_mgmt_service import MemoMgmtService
from api.utils.helpers import HTTPLoggedException, update_memo_cache_value
from api.utils.statics import chat_event_cats, event_tags, praise_db_name, default_db_name, sys_message_types

class ActionResultOutcome:
    user_message: str
    instruction_update:Optional[str]
    is_ending_response:bool
    
    def __init__(self, user_msg:str, is_ending_response:bool = False, ctx_upd:Optional[str] = None):
        self.user_message = user_msg
        self.instruction_update = ctx_upd
        self.is_ending_response = is_ending_response

class ActionResult():
    action_tag:str
    reason:str
    is_chat_ending:bool
    complementary_action:Optional[str]
    action_sysmsg_id: int
    default_acknowledge_msg:str = "[...]"
    default_rejection_msg:str = "[...]"
    # "" = keep talking = stream = on-action-acknowledge
    # 'any' = end chat = on-ending-action
    # 'acknowledge' | 'reject' = end-chat or stream segun user selection
    end_chat_event:str = ""
    
    _chats_svc: ChatsMgmtService = None
    _ctx_svc: BotContextMgmtService = None
    _memo_svc: MemoMgmtService = None

    _sysRepo: SysMessagesRepository = None
    _detailsRepo: ChatDetailsRepository = None
    _chatsRepo: ChatPromptsRepository = None
    _currentDB:str = None

    def __init__(self, action:str = "404", reason:str = "No Output Action tag found in the LLM response", repos_db:str = None):
        self.action_tag = action
        self.reason = reason
        self.is_chat_ending = False
        self.complementary_action = None
        self.action_sysmsg_id = -1
        self._currentDB = repos_db if repos_db is not None and repos_db != "" else default_db_name
        self._chats_svc = ChatsMgmtService(self._currentDB)   
        self._ctx_svc = BotContextMgmtService(self._currentDB)
        self._memo_svc = MemoMgmtService(self._currentDB)
        self._chatsRepo = ChatPromptsRepository(self._currentDB)
        self._detailsRepo = ChatDetailsRepository(self._currentDB)
        self._sysRepo = SysMessagesRepository(self._sysRepo)

    async def notify_chat_event(self, chat_id:str, message:str, chat_turn_id:int = None) -> bool:
        return await self._chats_svc.insert_chat_event(
            chat_id=chat_id,
            category=f"{chat_event_cats.to_string(chat_event_cats.remarkable_event)}", 
            event_tag=f"{event_tags.output_action}:{self.action_tag}",
            message=message, turn_id=chat_turn_id)
    
    #AQUI SE PUEDE METER UN PROMPT ESPECIFICO PARA USER_RES
    #EJ: LEAVE_PARTY + USER_REJECT (no quiere que deje el grupo) = prompt_evaluacion_relacion | chat = OK | {{END_CHAT}}
    #  : HIRE + Negociar precio / objetivos / tareas 
    async def on_acknowledge(self, chat_id:str, llm_provider: LLM_Provider, user_ack_message:str = None, generate_memo:bool = True) -> ActionResultOutcome:
        print(f"-- ACKNOWLEDGE OF: {self.action_tag} --")
        chat = await self._chats_svc.get_chat_doc(chat_id)
        if user_ack_message is None:
          user_ack_message = self.default_acknowledge_msg
        dep_memo = None
        if self.complementary_action is not None:
            dep_memo = await self.deprecate_memo(session_id=chat.session_id, action_tag=self.complementary_action)
        if generate_memo is True:
            memo = await self.generate_memo(chat_id=chat_id, user_msg=user_ack_message, llm_provider=llm_provider, deprecated_memo=dep_memo)
            # UPDATE DETAILS.ACTIONS & OVERWRITE MEMO['actions & rem-events'] & INSERT_EVENT
            if await self.update_chat_details(chat_id=chat_id, memory=memo.summary, chat_turn_id=len(chat.messages)) is False:
                raise HTTPLoggedException(status_code=500, detail=f"Unable to update chat status. No details found for chat {chat_id} >> ACTION: {self.action_tag}")
        #Por defecto las acciones to finalizan chat ni añaden instruction_update (si hiciese falta -> override [LEAVE_PARTY.REJ])
        return ActionResultOutcome(user_msg=user_ack_message)
    
    async def on_reject(self, chat_id:str, llm_provider: LLM_Provider, user_reject_message:str = None) -> ActionResultOutcome:
        return ActionResultOutcome(user_msg="")
      
    async def update_chat_details(self, chat_id:str, memory:str, chat_turn_id:int, update_actions:bool = True) -> False:
        details = await self._chats_svc.get_chat_details(chat_id=chat_id)
        if details is None:
            return False
        if update_actions:
            updated_actions = []
            for action in details.botActions:
                if self.complementary_action is None or action != self.action_tag:
                    if action not in updated_actions:
                        updated_actions.append(action)
            if self.complementary_action is not None and self.complementary_action not in updated_actions:
                updated_actions.append(self.complementary_action)
            print("-- UPDATED OUTPUT ACTIONS --", updated_actions)
            sys_msg_section = ""
            action_docs = await self._ctx_svc.get_output_action_docs(filter_tags=updated_actions)
            for doc in action_docs:
                sys_msg_section += f"> {doc.tag}: {doc.message.strip()}\n"
            update_memo_cache_value(details=details, key='actions', value=sys_msg_section, isAppend=False)
            details.botActions = updated_actions
        update_memo_cache_value(details=details, key='chat-remarkable-events', value=f"# REMARKABLE CHAT EVENT:\n{memory.strip()}\n", isAppend=True)
        details.chat_events.append(ChatEvent(
            category=f"{chat_event_cats.to_string(chat_event_cats.remarkable_event)}", 
            tag=f"{event_tags.output_action}:{self.action_tag}",
            message="Output action memory generation", 
            chat_turn_id=chat_turn_id))
        return await self._chats_svc.update_details(details=details)

    async def action_summarization_msgs(self, recent_history:List[dict[str,str]], template_tag:str = "ONACK-ANALYSIS", username:str = "Player Character", botname:str = "Non-Player Character", context:str = ""):
        sys_repo = SysMessagesRepository(praise_db_name)
        print(f"ACTION ID {self.action_sysmsg_id} TEMP_TAG: {template_tag}")
        analysis_msg = SystemMessageDoc.model_validate(await sys_repo.get_by_type_and_tag(type=self.action_sysmsg_id, tag=template_tag))
        analysis_basemsg = analysis_msg.message.replace("<<USERNAME>>", username)
        summarization_msgs = [{"system": analysis_basemsg.replace("<<BOTNAME>>", botname) }]
        if context != "":
            summarization_msgs.append({"context": context})
        for message in recent_history:
            summarization_msgs.append(message)
        print("-- SUMMARIZATION HISTORY MESSAGES --", summarization_msgs)
        return summarization_msgs
    
    async def add_analysis_memo(self, action:str, summarizer_tag:str, session_id:str, chat_id:str, prompt:str, memo_text:str, context:str, reason:str, chat_turn:int = None, status:str = "CURRENT") -> ChatSummaryDoc:
        if chat_turn is None:
            chat = await praise_service.get_chat_doc(chat_id)
            chat_turn = len(chat.messages)
        memo = ChatSummaryDoc(
            sys_prompt_tag=summarizer_tag,
            session_id=session_id,
            chat_collection_id=chat_id,
            prompt=prompt,
            summary=memo_text,
            observations=[chat_event_cats.to_string(chat_event_cats.remarkable_event), 
                          f"{sys_message_types.to_string(sys_message_types.output_action)}:{action}", # OutputAction:X <- para queries
                          f"STATUS:{status}",
                          f"CONTEXT: {context}",
                          f"REASON: {reason}",
                          f"{event_tags.output_action}:{action} >> chat_turn: {chat_turn}"] # [output-action-result]:X <- track eventos / formato chat_events
        )
        return await self._chats_svc.create_summary(memo)

    async def deprecate_memo(self, session_id:str, action_tag:str) -> ChatSummaryDoc | None:
        docs = await self._memo_svc.query_summaries(conditions=[
            QueryCondition(field="session_id",value=session_id),
            QueryCondition(field="observations", value=chat_event_cats.to_string(chat_event_cats.remarkable_event)),
            QueryCondition(field="observations", value=f"{sys_message_types.to_string(sys_message_types.output_action)}:{action_tag}"), 
            QueryCondition(field="observations", value="STATUS:CURRENT")])
        if len(docs) > 0:      
            current_join_memo_doc = docs[0]
            current_join_memo_doc.observations[2] = "STATUS:DEPRECATED"
            return await self._memo_svc.update_summary(current_join_memo_doc)
            #return current_join_memo_doc # DEVONLY None
        else:
            return None
    
    async def action_depmemo_context(self, dep_memo:ChatSummaryDoc, botname:str = "", username:str = "") -> str:
        sys_repo = SysMessagesRepository(praise_db_name)
        sysmsg = SystemMessageDoc.model_validate(await sys_repo.get_by_type_and_tag(self.action_sysmsg_id, tag="DEP-MEMOTEMP"))
        formatted_msg = sysmsg.message.replace("<<BOTNAME>>", botname)
        formatted_msg = formatted_msg.replace("<<USERNAME>>", username)
        return formatted_msg.replace("<<MEMORY>>", dep_memo.summary)
    
    async def analyze_and_format(self, summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, is_reject:bool, memo_template_tag:str = "MEMOTEMP", username:str = "Player Character", botname:str = "Non-Player Character") -> dict[str,str]:
        analysis_result:dict[str,str] = None
        if is_reject:
            analysis_result = await self.on_reject_analysis(summarization_msgs=summarization_msgs, llm_provider=llm_provider, username=username, botname=botname)
        else:
            analysis_result = await self.on_acknowledge_analysis(summarization_msgs=summarization_msgs, llm_provider=llm_provider, username=username, botname=botname)
        print("############## ANALYSIS RESULT ################", analysis_result)
        analysis_result["MEMORY"] = await self.get_templated_memo(
            analysis_result=analysis_result, 
            sys_msg_type=self.action_sysmsg_id, 
            memo_template_tag=memo_template_tag, 
            botname=botname,
            username=username)
        return analysis_result

    async def on_acknowledge_analysis(self,summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        return {"CONTEXT":"", "REASON":"", "PROMPT": "", "MEMORY": ""}
    
    async def on_reject_analysis(self,summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        return {"CONTEXT":"", "REASON":"", "PROMPT": "", "MEMORY": ""}
    
    async def get_templated_memo(self, analysis_result: dict[str,str], sys_msg_type:int, memo_template_tag="MEMOTEMP", username:str="Player Character", botname:str="Non-Player Character") -> str:

        memo_temp = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(type=sys_msg_type, tag=memo_template_tag))
        memo_text = memo_temp.message.replace("<<USERNAME>>", username)
        memo_text = memo_text.replace("<<BOTNAME>>", botname)
        if analysis_result.get("REASON") is not None:
            memo_text = memo_text.replace("<<REASON>>", analysis_result["REASON"].strip())
        return memo_text.replace("<<CONTEXT>>", analysis_result["CONTEXT"].strip())

    async def generate_memo(self, chat_id:str, llm_provider:LLM_Provider, user_msg:str = None, memo_template_tag:str = "MEMOTEMP", deprecated_memo: ChatSummaryDoc = None) -> ChatSummaryDoc:
        
        chat = ChatPromptDoc.model_validate(await self._chatsRepo.get_by_id(chat_id))
        details = ChatDetailsDoc.model_validate(await self._detailsRepo.get(varname="chat_doc_id",value=chat.id))
        ctx_msg = ""
        if details.zoneContext != "":
            ctx_msg = f"{event_tags.zone_ctx}: {details.zoneContext}"
        if details.botcharContext != "":
            ctx_msg += f"{event_tags.assistant_ctx}: {details.botcharContext}"
        if details.usercharContext != "":
            ctx_msg += f"{event_tags.user_ctx}: {details.usercharContext}"
        summarization_msgs = await self.action_summarization_msgs(
            recent_history=chat.messages_as_recent_history(include_sys_msg=False),
            username=details.usercharName,
            botname=details.botcharName,
            context=ctx_msg)
        if user_msg is not None:
            summarization_msgs.append({"user": user_msg})
        if deprecated_memo is not None:
            summarization_msgs[0]["system"] += await self.action_depmemo_context(dep_memo=deprecated_memo, botname=details.botcharName, username=details.usercharName)
            print(f"-- APPENDING DEPRECATED MEMORY CONTEXT INFO TO {sys_message_types.to_string(self.action_sysmsg_id)}-ONACK_ANALYSIS")
            print("FINAL SUMMARIZATION MESSAGE\n\n", summarization_msgs[0]["system"])
        # if current_chat_memo is not None: NO HACE FALTA <- CURRENT CHAT GENERA SIEMPRE MEMO. SIEMPRE HAY UN DEP_MEMO PARA TODAS LAS ACTIONS
        
        #WG: 18-03-25 --> structured_output requiere model w/tools enabled. Modelos role-play no valen. 
        #                 Cambio modelo llama3.1 a ChatCurrentModel hace recachear Ollama (lento)
        #WG: AHORA MISMO SE ESTA PASANDO SOLO RECENT HISTORY. EL CONTEXTO LO COGE POR SHORT MEMOS (se añaden a chat, el chat mantiene el contexto)
        #    --> SUM_CTX_v2: TodosLosZoneContexEvents como msje de contexto + recent_history | le paso SHORTS + recent_history  
        #                   Nota: en realidad los zoneContext se pasan al chat. Quedan por RECENT | SHORTS (no deberia hacer falta pasar nada mas al analyzer)
        analysis_result = await self.analyze_and_format(
            summarization_msgs=summarization_msgs,
            is_reject=False, 
            memo_template_tag=memo_template_tag, 
            botname=details.botcharName,
            username=details.usercharName, 
            llm_provider=llm_provider)
        print("-- ON ANALYZE AND FORMAT RESULT --", analysis_result["MEMORY"])
        memo = await self.add_analysis_memo(
            action=self.action_tag,
            summarizer_tag=f"{sys_message_types.to_string(self.action_sysmsg_id)}-ONACK_ANALYSIS",
            session_id=chat.session_id,
            chat_id=chat.id,
            prompt=analysis_result["PROMPT"],
            memo_text=analysis_result["MEMORY"],
            context=analysis_result["CONTEXT"],
            reason=analysis_result["REASON"])
        return memo