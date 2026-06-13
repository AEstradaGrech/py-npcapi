from typing import override

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.services.chat_actions.action_result import ActionResult, ActionResultOutcome
from api.utils.helpers import HTTPLoggedException
from api.utils.statics import default_chat_history_length, sys_message_types

class UserEndReqResult(ActionResult):
    #event msg
    def __init__(self, action:str, reason:str):
        super().__init__(action=action, reason=reason)
        self.is_chat_ending = False
        self.default_acknowledge_msg = "I have to go now, bye."
        self.end_chat_event = "any"
        self.action_tag = "USER_END_REQ"
        self.action_sysmsg_id = sys_message_types.user_endchat_req_template

    @override
    async def on_acknowledge(self, chat_id:str, llm_provider: LLM_Provider, user_ack_message:str = None, generate_memo:bool = False) -> ActionResultOutcome:
        if user_ack_message is None:
            user_ack_message = self.default_acknowledge_msg
        instruction_update = "The player wants to end the conversation. ENSURE your next response is conclussive (DO NOT ENCOURAGE THE USER TO ANSWER YOU, END THE CONVERSATION), You MUST add the OutputAction tag {{STOP_TALKING}} at the end of your next response."
        return ActionResultOutcome(user_msg=user_ack_message, is_ending_response=self.is_chat_ending, ctx_upd=instruction_update)
    
class EndChatResult(ActionResult):
    #event msg
    def __init__(self, action:str, reason:str):
        super().__init__(action=action, reason=reason)
        self.is_chat_ending = True
        self.default_acknowledge_msg = "[...]"
        self.end_chat_event = "any"
        self.action_sysmsg_id = sys_message_types.stop_talking_template
        
    @override
    async def on_acknowledge(self, chat_id:str, llm_provider: LLM_Provider, user_ack_message:str = None, generate_memo:bool = False) -> ActionResultOutcome:
        chat = await self._chats_svc.get_chat_doc(chat_id)
        if chat is None:
            raise HTTPLoggedException(status_code=500, details=f"-- No chat document has been found with ID: {chat_id} --")
        user_ack_message = self.default_acknowledge_msg if user_ack_message is None else user_ack_message
        should_end_chat: bool = True if len(chat.messages) > 2 * default_chat_history_length else False
        await super().on_acknowledge(chat_id=chat_id, llm_provider=llm_provider, user_ack_message=user_ack_message, generate_memo=generate_memo)
        if should_end_chat is False:
            user_ack_message += " <<SKIP_CHAT_END>>"
        return ActionResultOutcome(user_msg=user_ack_message, is_ending_response=True)
    