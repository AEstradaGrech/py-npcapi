from typing import List, override

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.infrastructure.models.reasoning_schemas import FightEventAnalysis
from api.services.chat_actions.action_result import ActionResultOutcome
from api.services.chat_actions.chat_ends import EndChatResult
from api.utils.helpers import get_ctx_num_for_text
from api.utils.statics import sys_message_types

class FightActionResult(EndChatResult):
    def __init__(self, reason:str):
        super().__init__(action="FIGHT", reason=reason)
        self.action_sysmsg_id = sys_message_types.fight_template
        self.default_acknowledge_msg = "Shut up and prepare to fight!"

    @override
    async def on_acknowledge(self, chat_id:str, llm_provider: LLM_Provider, user_ack_message:str = None, generate_memo:bool = True) -> ActionResultOutcome:
        return await super().on_acknowledge(chat_id=chat_id, llm_provider=llm_provider, user_ack_message=user_ack_message, generate_memo=True)
    # @override
    # async def on_acknowledge(self, chat_id:str, llm_provider: LLM_Provider, user_ack_message:str = None) -> str:
    #     # generate_memo <- generate REMARKABLE_EVENT <- sirve para regular actitud del personaje en próximas conversaciones
    #     #   CONTEXT REASON <-- y EVALUAR ACTITUD GLOBAL? --> Paso de Friend a Foe (gameplay effect: o bien te ataca directamente (PersonalEnemies list)  
    #     #                                                                                           o STOP_TALKING si esta en zona segura o es NPC importante)
    #     #   FightAnalysis = [CONTEX - REASON] --> analisis global es otro doc (InnerThoughs.Evaluation and/or Decision) 
    #     #   >> HACE FALTA? En que casos de juego se deja a un bot con vida si {{FIGHT}} ?
    #     #   NPC's se pueden rendir. RPG feature: matar un PJ aumenta base conocimiento Lore juego. Afecta a cualquier quest o relacion dentro del juego
    #     #                                        no matarlo puede generar quest o influir en el juego ya que el tio te conoce (puede ser bueno (JOIN?), puede ser malo(FACTIONS?))
    #     #                                        (esto seria otra output action / como gestiono que el bot sepa si ha el jugador le perdona la vida [chat | timer])
    #     #                                        UE5 --> OnOutputAction("FIGHT") --> A: OnClearKnownEnemies --> Generate Memo "El desenlace de la pelea ha sido X"
    #     #                                            --> PELEA -> B: if BotHealh < X:
    #     #                                                              -> Trigger 'Scared' anim 
    #     #                                                              -> Si player habla: {{SURRENDER}} -> ACK & REJ <- DynActions
    #     #                                                                                   REJ -> Kill = if Char = Famous -> KnowledgeBase++
    #     #                                                                                   ACK -> Keep Talking = SURRENDER inicia nuevo chat con long memo
    #     #                                                                                                          if MEMOS.FIGHT:CURRENT -> add sys instruction (forzar texto SURRENDER)
    #     # trigger_end_chat_process? <- generate LONG-MEMOf
    #     dep_memo = await self.deprecate_memo(action_tag=self.complementary_action)
    #     memo = await self.generate_memo(chat_id=chat_id, llm_provider=llm_provider, deprecated_memo=dep_memo) 
        
    #     return "END_CHAT RESULTS NO TIENEN ON_REJECT"
    @override
    async def on_acknowledge_analysis(self, summarization_msgs:List[dict[str,str]], llm_provider: LLM_Provider, username:str = "Player Character", botname:str="Non-Player Character") -> dict[str,str]:
        analysis_text = llm_provider.chat_history_to_template(chat_history=summarization_msgs, exclude_sys_message=False, exclude_sys_updates=False, template_key="praise")
        analysis_text = analysis_text.replace("<<USERNAME>>", username)
        analysis_text = analysis_text.replace("<<BOTNAME>>", botname)
        print("-- FIGHT >> ANALYSIS TEMPLATED TEXT --", analysis_text)
        llm = llm_provider.current_integration().fresh_model_instance(model=llm_provider.current_model(), config=llm_provider.config().get_settings_preset("analyis"), ctx_len=get_ctx_num_for_text(analysis_text))
        analysis_llm = llm.with_structured_output(schema=FightEventAnalysis)
        analysis_result:FightEventAnalysis = analysis_llm.invoke(analysis_text)
        print("-- FIGHT >> ANALYSIS RESULT --", analysis_result)
        return { "CONTEXT":analysis_result.context, "REASON": analysis_result.reason, "INSTIGATOR": analysis_result.instigator, "PROMPT": analysis_text}
    
    @override
    async def get_templated_memo(self, analysis_result: dict[str,str], sys_msg_type:int, memo_template_tag="MEMOTEMP", username:str="Player Character", botname:str="Non-Player Character") -> str:
        memo_text = await super().get_templated_memo(analysis_result=analysis_result, sys_msg_type=sys_msg_type, memo_template_tag=memo_template_tag, username=username, botname=botname)
        return memo_text.replace("<<INSTIGATOR>>", analysis_result["INSTIGATOR"].strip())
    