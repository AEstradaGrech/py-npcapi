from typing import List

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.models.prompting_schemas import ChatPromptRequest
from api.services.chat_actions.action_result import ActionResult, ActionResultOutcome, ChatInteractionResult
from api.services.chat_actions.chat_ends import EndChatResult, UserEndReqResult
from api.services.chat_actions.fight_action import FightActionResult
from api.services.chat_actions.join_action import JoinActionResult, LeavePartyActionResult
from api.services.chat_actions.quest_action import QuestActionResult
from api.services.chat_actions.trade_action import TradeActionResult
from api.utils.statics import event_tags

class OutputActionsHandler:
    def get_chat_result(self, action:str="404") -> ActionResult:
        match action:
            case "JOIN":
                return JoinActionResult(reason="You wait for the player to accept or reject the 'join group' agreement") #REASON se añade como assistant-ctx-upd message
            case "LEAVE_PARTY":
                return LeavePartyActionResult(reason="You wait for the player to agree or refuse the 'leave party' proposal") # Deshace el grupo actual
            case "PICK_ITEM":
                return ChatInteractionResult(action=action,reason="TODO Item Picked-up ackgnowledge from NPC Output Action") #Añade Item a BotMemory
            case "GIVE_ITEM":
                return ChatInteractionResult(action=action,reason="TODO Item offering from NPC Output Action") #Elimina Itme de BotMemory
            case "HIRE":
                return ChatInteractionResult(action=action,reason="You wait for the player to accept or reject the hiring agreement") #añade StatusUpdate a BotMemory // #User: I would like to hire you + Bot: OK {{HIRE}} | Bot: I might work for you if we agree on the right price {{TRADE}}
            case "TRADE":
                return TradeActionResult(reason="You wait for the player to agree or refuse the trading proposal")
            case "FIGHT":
                return FightActionResult(reason="You start a fighting with the player")
            case "QUEST":
                return QuestActionResult(reason="You have offered a job to the player and you are waiting for him to accept or reject the offering")
            case "STOP_TALKING":
                return EndChatResult(action=action, reason="You have ended your conversation with the player")
            case "USER_END_REQ":
                return UserEndReqResult(action=action, reason="The player wants to finish your current conversation")
        return ActionResult()
    
    async def handle_output_actions(self, chat:ChatPromptRequest, history:dict[str,str]) -> ActionResult:
     
        llm_response = history[len(history)-1]["assistant"]
        action_docs = await self._ctx_svc.get_output_action_docs()
        actions = [action.tag for action in action_docs]
        output_result = self.get_chat_result()
        for action in actions:
            tag = "{"+"{"+f"{action}" + "}" + "}"
            if tag in llm_response:
                output_result = output_result = self.get_chat_result(action=action)
        if output_result.action_tag != "404":
            await self._chats_svc.insert_chat_event(chat_id=chat.id,category="assistant", event_tag=f"{event_tags.assistant_ctx}", message=f"{output_result.action_tag} >> {output_result.reason}")
        return output_result

    def on_init_handle_dynamic_actions(self, memo_actions:List[str], base_msg:str) -> str:
        dynamic_content = ""
        for action in memo_actions:
            handler = self.get_chat_result(action=action)
            dynamic_content += handler.get_dynamic_content()
        return base_msg.replace("[[DynamicActions]]", dynamic_content)
    
    async def handle_user_acknowledge(self, chat_id:str, action:str, user_message:str | None, llm_provider: LLM_Provider) -> ActionResultOutcome: 
        await self._chats_svc.insert_chat_event(chat_id=chat_id, category="user", event_tag=event_tags.user_ctx, message=f"{action} >> ACCEPTED")
        actions_handler = OutputActionsHandler()
        action:ActionResult = actions_handler.get_chat_result(action=action)
        return await action.on_acknowledge(chat_id=chat_id, user_ack_message=user_message, llm_provider=llm_provider)
        
    async def handle_user_reject(self, chat_id:str, action:str, user_message:str | None, llm_provider: LLM_Provider) -> ActionResultOutcome: 
        await self._chats_svc.insert_chat_event(chat_id=chat_id, category="user", event_tag=event_tags.user_ctx, message=f"{action} >> REJECTED")
        actions_handler = OutputActionsHandler()
        action:ActionResult = actions_handler.get_chat_result(action=action)
        return await action.on_reject(chat_id=chat_id, user_reject_message=user_message, llm_provider=llm_provider)