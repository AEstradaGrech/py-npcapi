from typing import List

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.models.prompting_schemas import ChatPromptRequest
from api.services.botctx_mgmt_service import BotContextMgmtService
from api.services.chat_actions.action_result import ActionResult, ActionResultOutcome, ChatInteractionResult
from api.services.chat_actions.chat_ends import EndChatResult, UserEndReqResult
from api.services.chat_actions.fight_action import FightActionResult
from api.services.chat_actions.join_action import JoinActionResult, LeavePartyActionResult
from api.services.chat_actions.quest_action import QuestActionResult
from api.services.chat_actions.trade_action import TradeActionResult
from api.services.chats_mgmt_service import ChatsMgmtService
from api.utils.statics import event_tags, default_db_name

class OutputActionsHandler:

    _currentDB:str = None
    _chats_svc: ChatsMgmtService = None
    _ctx_svc: BotContextMgmtService = None

    def __init__(self, repos_db:str = "PyNPCsDB"):
        self._currentDB = repos_db if repos_db is not None else default_db_name
        self._chats_svc = ChatsMgmtService(self._currentDB)
        self._ctx_svc = BotContextMgmtService(self._currentDB)
        
    def get_chat_result(self, action:str="404") -> ActionResult:
        match action:
            case "JOIN":
                return JoinActionResult(reason="You wait for the player to accept or reject the 'join group' agreement", repos_db=self._currentDB) #REASON se añade como assistant-ctx-upd message
            case "LEAVE_PARTY":
                return LeavePartyActionResult(reason="You wait for the player to agree or refuse the 'leave party' proposal", repos_db=self._currentDB) # Deshace el grupo actual
            case "PICK_ITEM":
                return ChatInteractionResult(action=action,reason="TODO Item Picked-up ackgnowledge from NPC Output Action", repos_db=self._currentDB) #Añade Item a BotMemory
            case "GIVE_ITEM":
                return ChatInteractionResult(action=action,reason="TODO Item offering from NPC Output Action", repos_db=self._currentDB) #Elimina Item de BotMemory
            case "HIRE":
                return ChatInteractionResult(action=action,reason="You wait for the player to accept or reject the hiring agreement", repos_db=self._currentDB) #añade StatusUpdate a BotMemory // #User: I would like to hire you + Bot: OK {{HIRE}} | Bot: I might work for you if we agree on the right price {{TRADE}}
            case "TRADE":
                return TradeActionResult(reason="You wait for the player to agree or refuse the trading proposal", repos_db=self._currentDB)
            case "FIGHT":
                return FightActionResult(reason="You start a fighting with the player", repos_db=self._currentDB)
            case "QUEST":
                return QuestActionResult(reason="You have offered a job to the player and you are waiting for him to accept or reject the offering", repos_db=self._currentDB)
            case "STOP_TALKING":
                return EndChatResult(action=action, reason="You have ended your conversation with the player", repos_db=self._currentDB)
            case "USER_END_REQ":
                return UserEndReqResult(action=action, reason="The player wants to finish your current conversation", repos_db=self._currentDB)
        return ActionResult(repos_db=self._currentDB)
    
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

    async def handle_user_acknowledge(self, chat_id:str, action:str, user_message:str | None, llm_provider: LLM_Provider) -> ActionResultOutcome: 
        await self._chats_svc.insert_chat_event(chat_id=chat_id, category="user", event_tag=event_tags.user_ctx, message=f"{action} >> ACCEPTED")
        action:ActionResult = self.get_chat_result(action=action)
        return await action.on_acknowledge(chat_id=chat_id, user_ack_message=user_message, llm_provider=llm_provider)
        
    async def handle_user_reject(self, chat_id:str, action:str, user_message:str | None, llm_provider: LLM_Provider) -> ActionResultOutcome: 
        await self._chats_svc.insert_chat_event(chat_id=chat_id, category="user", event_tag=event_tags.user_ctx, message=f"{action} >> REJECTED")
        action:ActionResult = self.get_chat_result(action=action)
        return await action.on_reject(chat_id=chat_id, user_reject_message=user_message, llm_provider=llm_provider)