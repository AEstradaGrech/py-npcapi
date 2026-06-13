from typing import List, override

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.infrastructure.models.reasoning_schemas import QuestEventAnalysis
from api.services.chat_actions.action_result import ActionResultOutcome, ChatInteractionResult
from api.utils.helpers import HTTPLoggedException, replace_values
from api.utils.statics import sys_message_types

class QuestActionResult(ChatInteractionResult):
    def __init__(self, reason:str):
        super().__init__(action="QUEST", reason=reason)
        self.action_sysmsg_id = sys_message_types.quest_gen_template
        self.default_acknowledge_msg = "Count me in, I'll do my best."
        self.default_rejection_msg = "Sorry, I have no time for that right now."

    @override
    async def on_acknowledge(self, chat_id:str, llm_provider: LLM_Provider, user_ack_message:str = None, generate_memo:bool = True) -> ActionResultOutcome:
        outcome:ActionResultOutcome = await super().on_acknowledge(chat_id=chat_id, llm_provider=llm_provider, user_ack_message=user_ack_message, generate_memo=generate_memo)
        outcome.is_ending_response = True
        outcome.instruction_update = f"The player has accepted the job. Your next response must be a farewell and end the conversation. ENSURE your next response is conclussive (DO NOT ENCOURAGE THE USER TO ANSWER YOU, END THE CONVERSATION)"
        return outcome
    
    @override
    async def on_reject(self, chat_id:str, llm_provider: LLM_Provider, user_reject_message:str = None,) -> ActionResultOutcome:
        print("TODO: buscar ")
        chat = await self._chats_svc.get_chat_doc(chat_id)
        details = await self._chats_svc.get_chat_details(chat_id)
        if user_reject_message is None:
          user_reject_message = self.default_rejection_msg
        summarization_msgs = await self.action_summarization_msgs(
            recent_history=chat.messages_as_recent_history(include_sys_msg=False),
            template_tag="ONACK-ANALYSIS",
            username=details.usercharName,
            botname=details.botcharName)
        summarization_msgs.append({"user": user_reject_message})
        analysis_result:dict[str,str] = await self.analyze_and_format(summarization_msgs=summarization_msgs, llm_provider=llm_provider, is_reject=True, memo_template_tag="MEMOREJ", username=details.usercharName, botname=details.botcharName)
        #save memo
        memo = await self.add_analysis_memo(action="QUEST",
            summarizer_tag=f"{sys_message_types.to_string(self.action_sysmsg_id)}-ONACK-ANALYSIS",
            session_id=chat.session_id,
            chat_id=chat.id,
            prompt=analysis_result["PROMPT"],
            memo_text=analysis_result["MEMORY"],
            context=analysis_result["CONTEXT"],
            reason=analysis_result["REASON"],
            chat_turn=len(chat.messages),
            status="AVAILABLE")
        if await self.update_chat_details(chat.id, memory=memo.summary, chat_turn_id=len(chat.messages)) is False:
            raise HTTPLoggedException(status_code=500, detail="An error has occured while storing the generated QUEST details")
        #update_bot_cache
        instruction_update = "The player has not accepted the job, but he might come back later and accept it. Your next response should communicate to the player that this 'door' is 'still open' in case he changes his mind, and end the conversation. ENSURE your next response does terminate the conversation."
        return ActionResultOutcome(user_msg=user_reject_message, is_ending_response=True, ctx_upd=instruction_update)

    def on_generated_quest(self, is_reject:bool, summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]: 
        llm = llm_provider.current_integration().fresh_model_instance(model="llama3.1", temperature=0.1, max_tokens=600, ctx_len=4096)
        analysis_llm = llm.with_structured_output(schema=QuestEventAnalysis)     
        analysis_text = llm_provider.chat_history_to_template(chat_history=summarization_msgs, exclude_sys_message=False, exclude_sys_updates=False, template_key="praise")
        analysis_text = analysis_text.replace("<<USERNAME>>", username).replace("<<BOTNAME>>", botname)       
        analysis_result:QuestEventAnalysis = analysis_llm.invoke(analysis_text)
        print("############ QUEST ANAL RESULT ################", analysis_result)
        stringy_plan = ""
        for point in analysis_result.action_plan:
            stringy_plan += f"- {point}\n"
        quest_items = ""
        for item in analysis_result.items:
            quest_items += f"- {item}\n"
        return {
            "TITLE": analysis_result.title,
            "STATUS": "AVAILABLE" if is_reject else "ONGOING", #on_reject_analysis --> AVAILABLE y se guarda para aceptarla mas tarde si player quiere 
            "CONTEXT":analysis_result.context, 
            "GOAL": analysis_result.goal, 
            "CATEGORY": analysis_result.category,
            "TARGET": analysis_result.target, 
            "ITEMS": quest_items, 
            "PLAN": stringy_plan.strip(),
            "PROMPT": analysis_text
        }
    
    @override
    async def on_acknowledge_analysis(self, summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        return self.on_generated_quest(is_reject=False, summarization_msgs=summarization_msgs, llm_provider=llm_provider, username=username, botname=botname)
    
    @override
    async def on_reject_analysis(self,summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        return self.on_generated_quest(is_reject=True, summarization_msgs=summarization_msgs, llm_provider=llm_provider, username=username, botname=botname)
    
    @override
    async def get_templated_memo(self, analysis_result: dict[str,str], sys_msg_type:int, memo_template_tag="MEMOTEMP", username:str="Player Character", botname:str="Non-Player Character") -> str:
        memo_text = await super().get_templated_memo(analysis_result=analysis_result, sys_msg_type=sys_msg_type, memo_template_tag=memo_template_tag, username=username, botname=botname)
        memo_text = replace_values(text=memo_text, kvp=analysis_result, tag_separators=["<<",">>"])
        if analysis_result["ITEMS"] != "" and "NONE MENTIONED" not in analysis_result["ITEMS"].upper(): #por alguna razon esto va devolviendo lo que le sale de los huevos SIEMPRE en funcion de lo que yo quiero que haga (hace SIEMPRE lo contrario)
            memo_text += f"\n\nYou have also provided {username} with this item(s) to help him accomplishing the task:\n\n{analysis_result["ITEMS"]}"
        print("QUEST_GEN >> FINAL MEMO\n", memo_text)
        return memo_text
    
    @override
    async def analyze_and_format(self, summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, is_reject:bool, memo_template_tag:str = "MEMOTEMP", username:str = "Player Character", botname:str = "Non-Player Character") -> dict[str,str]:
        analysis_result = await super().analyze_and_format(summarization_msgs=summarization_msgs, llm_provider=llm_provider, is_reject=is_reject, memo_template_tag=memo_template_tag, username=username, botname=botname)
        #generate_memo.add_analysis_memo guarda CONTEXT y REASON para todas las acciones. Apañar REASON con info relevante propia de cada accion (CONTEXT es la unica SIEMPRE comun)
        analysis_result["REASON"] = analysis_result["GOAL"]
        return analysis_result
    #on_ack: Analyze -> extract Quest Info & Goal (structure quest & bridge it to UE functionality)
    #on_rej: Extract & etc + update_bot_memo -> CACHE QUEST = "If you change your mind about it let me know, my offer will still be on the table"
