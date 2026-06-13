from typing import List, override

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.infrastructure.models.db_schemas import ChatSummaryDoc, SystemMessageDoc
from api.infrastructure.models.reasoning_schemas import JoinEventAnalysis, JoinRejectAnalysis, LeavePartyEventAnalysis, StayInGroupEventAnalysis
from api.services.chat_actions.action_result import ActionResultOutcome
from api.services.chat_actions.output_actions_handler import ChatInteractionResult
from api.utils.helpers import HTTPLoggedException, get_ctx_num_for_text
from api.utils.statics import event_tags, sys_message_types

class JoinActionResult(ChatInteractionResult):
    def __init__(self, reason:str):
        super().__init__(action="JOIN", reason=reason)
        self.complementary_action = "LEAVE_PARTY"
        self.action_sysmsg_id = sys_message_types.join_party_template
        self.default_acknowledge_msg = f"Fine, I'm glad we are on the same team!"
        self.default_rejection_msg = f"No thanks, maybe in some other moment"

    @override
    async def on_acknowledge(self, chat_id:str, llm_provider: LLM_Provider, user_ack_message:str = None, generate_memo:bool = True) -> ActionResultOutcome:
        outcome:ActionResultOutcome = await super().on_acknowledge(chat_id=chat_id, llm_provider=llm_provider, user_ack_message=user_ack_message, generate_memo=generate_memo)
        outcome.is_ending_response = False
        outcome.instruction_update = f"{event_tags.assistant_ctx}: The player has accepted to join forces with you."
        return outcome
    
    @override
    async def on_reject(self, chat_id:str, llm_provider: LLM_Provider, user_reject_message:str = None,) -> ActionResultOutcome:
        chat = await self._chats_svc.get_chat_doc(chat_id)
        if chat is None:
            raise HTTPLoggedException(f"-- No chat has been found with ID: {chat_id} --")
        details = await self._chats_svc.get_chat_details(chat_id=chat_id)
        if details is None:
            raise HTTPLoggedException(f"-- No chat details doc has been found for chat with ID: {chat_id} --")
        user_reject_message = self.default_rejection_msg if user_reject_message is None else user_reject_message
        outcome = ActionResultOutcome(user_msg=user_reject_message)
        summarization_msgs = await self.action_summarization_msgs(
            recent_history=chat.messages_as_recent_history(include_sys_msg=False),
            template_tag="ONREJ-ANALYSIS",
            username=details.usercharName,
            botname=details.botcharName)
        summarization_msgs.append({"user": user_reject_message})
        analysis_result = await self.analyze_and_format(summarization_msgs=summarization_msgs, llm_provider=llm_provider, is_reject=True, memo_template_tag="MEMOREJ", username=details.usercharName, botname=details.botcharName)
        analysis_result["MEMORY"] = analysis_result["MEMORY"].replace("<<USERWORDS>>", user_reject_message)
        memo = await self.add_analysis_memo(action="JOIN",
            summarizer_tag=f"{sys_message_types.to_string(self.action_sysmsg_id)}-ONREJ-ANALYSIS",
            session_id=chat.session_id,
            chat_id=chat_id,
            prompt=analysis_result["PROMPT"],
            memo_text=analysis_result["MEMORY"],
            context=f"{analysis_result["CONTEXT"]} Reason to team up: {analysis_result["REASON"]}",
            reason=f"Reasons to reject: {user_reject_message}",
            chat_turn=len(chat.messages),
            status="DEPRECATED") #se guarda como DEP y se añadiria en otras sessions como equivalente a un LEAVE PARTY (sys_msgs)
        if await self.update_chat_details(chat.id, memory=memo.summary, chat_turn_id=len(chat.messages), update_actions=False) is False:
            raise HTTPLoggedException(status_code=500, detail="An error has occured while storing the generated QUEST details")
        outcome.is_ending_response = False
        outcome.instruction_update = f"{event_tags.assistant_ctx}: The player has refused to join forces with you, at least for now."
        return outcome
    
    @override
    async def on_acknowledge_analysis(self, summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        analysis_text = llm_provider.chat_history_to_template(chat_history=summarization_msgs, exclude_sys_message=False, exclude_sys_updates=False, template_key="praise")
        analysis_text = analysis_text.replace("<<USERNAME>>", username)
        analysis_text = analysis_text.replace("<<BOTNAME>>", botname)
        print("-- JOIN >> ANALYSIS TEMPLATED TEXT --", analysis_text)
        llm = llm_provider.current_integration().fresh_model_instance(model="llama3.1-lexi-v2", temperature=0.5, max_tokens=450, ctx_len=get_ctx_num_for_text(analysis_text))
        analysis_llm = llm.with_structured_output(schema=JoinEventAnalysis)
        analysis_result:JoinEventAnalysis = analysis_llm.invoke(analysis_text)
        return { "CONTEXT":analysis_result.context, "REASON": analysis_result.goal, "PROMPT": analysis_text}
        
    @override
    async def on_reject_analysis(self,summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        analysis_text = llm_provider.chat_history_to_template(chat_history=summarization_msgs, exclude_sys_message=False, exclude_sys_updates=False, template_key="praise")
        analysis_text = analysis_text.replace("<<USERNAME>>", username)
        analysis_text = analysis_text.replace("<<BOTNAME>>", botname)
        print("-- JOIN REJECT>> ANALYSIS TEMPLATED TEXT --", analysis_text)
        llm = llm_provider.current_integration().fresh_model_instance(model="llama3.1-lexi-v2", temperature=0.5, max_tokens=450, ctx_len=get_ctx_num_for_text(analysis_text))
        analysis_llm = llm.with_structured_output(schema=JoinRejectAnalysis)
        analysis_result:JoinEventAnalysis = analysis_llm.invoke(analysis_text)
        print("-- JOIN REJECT>> ANALYSIS RESULT --", analysis_result)
        return { "CONTEXT":analysis_result.context, "REASON": analysis_result.goal, "PROMPT": analysis_text}
    
    @override
    async def get_templated_memo(self, analysis_result: dict[str,str], sys_msg_type:int, memo_template_tag="MEMOTEMP", username:str="Player Character", botname:str="Non-Player Character") -> str:
        memo_text = await super().get_templated_memo(analysis_result=analysis_result, sys_msg_type=sys_msg_type, memo_template_tag=memo_template_tag, username=username, botname=botname)
        memo_text = memo_text.replace("<<GOAL>>", analysis_result["REASON"].strip() if analysis_result is not None else "")
        return memo_text
    
    @override 
    async def analyze_and_format(self, summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, is_reject:bool, memo_template_tag:str = "MEMOTEMP", username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        analysis_result:dict[str,str] = None
        if is_reject:
            analysis_result = await self.on_reject_analysis(summarization_msgs=summarization_msgs, llm_provider=llm_provider, username=username, botname=botname)
        else:
            analysis_result = await self.on_acknowledge_analysis(summarization_msgs=summarization_msgs, llm_provider=llm_provider, username=username, botname=botname)
        analysis_result["MEMORY"] = await self.get_templated_memo(
            analysis_result=analysis_result, 
            sys_msg_type=self.action_sysmsg_id, 
            memo_template_tag=memo_template_tag if is_reject or (is_reject is False and analysis_result["REASON"] is None) else "GOAL-MEMOTEMP", 
            botname=botname,
            username=username)
        return analysis_result
    

class LeavePartyActionResult(ChatInteractionResult):
    def __init__(self, reason:str):
        super().__init__(action="LEAVE_PARTY", reason=reason)
        self.complementary_action = "JOIN"
        self.action_sysmsg_id = sys_message_types.leave_party_template
        self.default_acknowledge_msg = f"Good luck."
        self.end_chat_event = "acknowledge"

    @override
    async def on_acknowledge(self, chat_id:str, llm_provider: LLM_Provider, user_ack_message:str = None, generate_memo:bool = True) -> ActionResultOutcome:
        outcome:ActionResultOutcome = await super().on_acknowledge(chat_id=chat_id, llm_provider=llm_provider, user_ack_message=user_ack_message, generate_memo=generate_memo)
        outcome.is_ending_response = True
        outcome.instruction_update = f"The group you where part of is now dissolved and you are no longer part of the player party."
        return outcome
    
    @override
    async def on_reject(self, chat_id:str, llm_provider: LLM_Provider, user_reject_message:str = None,) -> ActionResultOutcome:
        chat = await self._chats_svc.get_chat_doc(chat_id)
        details = await self._chats .get_chat_details(chat_id)
        if user_reject_message is None:
          user_reject_message = self.default_rejection_msg
        dep_memo = await self.deprecate_memo(session_id=chat.session_id, action_tag=self.complementary_action)
        if dep_memo is None:
            raise HTTPLoggedException(status_code=500, detail="-- CHAT LOOP FAIL: NO COMPLEMENTARY 'JOIN' ACTION HAS BEEN FOUND FOR THIS LEAVE_PARTY EVENT --")
        summarization_msgs = await self.action_summarization_msgs(
            recent_history=chat.messages_as_recent_history(include_sys_msg=False),
            template_tag="ONREJECT-ANALYSIS",
            username=details.usercharName,
            botname=details.botcharName)
        summarization_msgs.append({"user": user_reject_message})
        analysis_msg = summarization_msgs[0]["system"].replace("<<JOIN_MEMO>>", dep_memo.summary)
        analysis_msg = analysis_msg.replace("<<CHARACTER_PROFILE>>", details.botMemory.get("profile"))
        analysis_msg = analysis_msg.replace("<<USER_MSG>>", user_reject_message)
        summarization_msgs[0]["system"] = analysis_msg
        ######################################### ON REJECT ANALYSIS##########################################################################
        # llm = llm_provider.current_integration().fresh_model_instance(model="llama3.1", temperature=0.5, max_tokens=500, ctx_len=4096)
        # analysis_llm = llm.with_structured_output(schema=StayInGroupEventAnalysis)
        # analysis_text = llm_provider.chat_history_to_template(chat_history=summarization_msgs, exclude_sys_message=False, exclude_sys_updates=False, template_key="praise")
        # analysis_text = analysis_text.replace("<<USERNAME>>", details.usercharName).replace("<<BOTNAME>>", details.botcharName)
        # #analysis_text = analysis_text.replace("<<BOTNAME>>", details.botcharName)
        # print("-- LEAVE REJECTION ANAL PROMPT --", analysis_text)
        # analysis_result:StayInGroupEventAnalysis = analysis_llm.invoke(analysis_text)
        # print("-- ON STAY IN GROUP EVALUATION --", analysis_result)
        ######################################################################################################################################
        analysis_result: dict[str,str] = await self.on_reject_analysis(summarization_msgs=summarization_msgs, llm_provider=llm_provider, username=details.usercharName, botname=details.botcharName)
        instruction_update = None
        memo: ChatSummaryDoc = None
        match analysis_result["DECISION"]:
            case "STAY":
                join_memo_temp = await self._sysRepo.get_by_type_and_tag(sys_message_types.join_party_template, "MEMOTEMP")
                if join_memo_temp is None:
                    raise HTTPLoggedException(status_code=500, detail="-- No JOIN MEMOTEMP has been found for action LEAVE_ACTION.REJ")
                join_memo = SystemMessageDoc.model_validate(join_memo_temp).message.replace("<<CONTEXT>>", analysis_result["CONTEXT"])
                join_memo += f"\n{analysis_result["REASON"]}"
                memo = await self.add_analysis_memo(action="JOIN", 
                    summarizer_tag=f"{sys_message_types.to_string(self.action_sysmsg_id)}-ONREJECT-ANALYSIS", 
                    session_id=chat.session_id, 
                    chat_id=chat.id,
                    prompt=analysis_result["PROMPT"],
                    memo_text=join_memo.replace("<<USERNAME>>", details.usercharName).replace("<<BOTNAME>>", details.botcharName), 
                    context=analysis_result["CONTEXT"],
                    reason=analysis_result["REASON"])
                instruction_update = f"{event_tags.assistant_ctx}: You have decided to renew your current alliance with the player and keep following him in his adventures as a team."
            case "LEAVE":
                leave_memo_temp = await self._sysRepo.get_by_type_and_tag(sys_message_types.leave_party_template, "MEMOTEMP")
                if leave_memo_temp is None:
                    raise HTTPLoggedException(status_code=500, detail="-- No LEAVE_PARTY MEMOTEMP has been found for action LEAVE_ACTION.REJ")
                leave_memo = SystemMessageDoc.model_validate(leave_memo_temp).message.replace("<<CONTEXT>>", analysis_result["CONTEXT"])
                leave_memo = leave_memo.replace("<<REASON>>", analysis_result["REASON"]).replace("<<USERNAME>>", details.usercharName).replace("<<BOTNAME>>", details.botcharName)
                memo = await self.add_analysis_memo(action="LEAVE", 
                    summarizer_tag=f"{sys_message_types.to_string(self.action_sysmsg_id)}-ONREJECT-ANALYSIS", 
                    session_id=chat.session_id, 
                    chat_id=chat.id,
                    prompt=analysis_result["PROMPT"],
                    memo_text=leave_memo,  
                    context=analysis_result["CONTEXT"],
                    reason=analysis_result["REASON"])
                instruction_update = f"You have decided to leave the group and split paths with the player. You MUST express that in your next response by farewelling the user to end the conversation. ENSURE your next response is conclussive (DO NOT ENCOURAGE THE USER TO ANSWER YOU, END THE CONVERSATION)"
            case _:
                print(" -- OUTPUT LABEL FAIL - BY DEFAULT --> LEAVE")
        if memo is None:
            raise HTTPLoggedException(status_code=500, detail="-- An error has occured while generating the LEAVE PARTY REJECTION MEMORY --")
        if await self.update_chat_details(chat_id=chat_id, memory=memo.summary, chat_turn_id=len(chat.messages), update_actions=analysis_result["DECISION"] == "LEAVE") is False:
            raise HTTPLoggedException(status_code=500, detail=f"Unable to update chat status in chat details document for chat {chat_id} >> ACTION: {self.action_tag}")
        return ActionResultOutcome(user_msg=user_reject_message, ctx_upd=instruction_update, is_ending_response=analysis_result["DECISION"] == "LEAVE") #ESTO ESTA MAL -> isEndingResponse dispara proceso end chat SIN ultima respuesta LLM
     
    @override
    async def on_acknowledge_analysis(self, summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        print("-- LEAVE_PARTY >> SUMARIZATION MESSAGES --", summarization_msgs)
        analysis_text = llm_provider.chat_history_to_template(chat_history=summarization_msgs, exclude_sys_message=False, exclude_sys_updates=False, template_key="praise")
        analysis_text = analysis_text.replace("<<USERNAME>>", username).replace("<<BOTNAME>>", botname)
        print("-- LEAVE_PARTY >> ANALYSIS TEMPLATED TEXT --", analysis_text)
        llm = llm_provider.current_integration().fresh_model_instance(model="llama3.1-lexi-v2", temperature=0.5, max_tokens=450, ctx_len=get_ctx_num_for_text(analysis_text))
        analysis_llm = llm.with_structured_output(schema=LeavePartyEventAnalysis)
        analysis_result:LeavePartyEventAnalysis = analysis_llm.invoke(analysis_text)
        return { "CONTEXT":analysis_result.context, "REASON": analysis_result.reason, "PROMPT": analysis_text}
    
    @override
    async def on_reject_analysis(self,summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        analysis_text = llm_provider.chat_history_to_template(chat_history=summarization_msgs, exclude_sys_message=False, exclude_sys_updates=False, template_key="praise")
        analysis_text = analysis_text.replace("<<USERNAME>>", username).replace("<<BOTNAME>>", botname)
        print("-- LEAVE REJECTION ANAL PROMPT --", analysis_text)
        llm = llm_provider.current_integration().fresh_model_instance(model="llama3.1-lexi-v2", temperature=0.5, max_tokens=500, ctx_len=get_ctx_num_for_text(analysis_text))
        analysis_llm = llm.with_structured_output(schema=StayInGroupEventAnalysis)
        analysis_result:StayInGroupEventAnalysis = analysis_llm.invoke(analysis_text)
        print("-- ON STAY IN GROUP EVALUATION --", analysis_result)
        return {"CONTEXT": analysis_result.context, "REASON": analysis_result.reason, "DECISION": analysis_result.decision, "PROMPT": analysis_text}
    