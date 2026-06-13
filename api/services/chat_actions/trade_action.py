from typing import override
from api.services.chat_actions.action_result import ActionResultOutcome, ChatInteractionResult

class TradeActionResult(ChatInteractionResult):
    def __init__(self, reason:str):
        super().__init__(action="TRADE", reason=reason)
        self.default_acknowledge_msg = "Thanks, it has been a good deal for both parts. Until the next time!"
        self.default_rejection_msg = "No thanks, maybe later."
        self.end_chat_event = ""
        self.is_chat_ending = False
    # ACK == open TRADE UI
    # @override
    # async def on_acknowledge(self, chat_id, llm_provider, user_ack_message = None, generate_memo = True):
    #     if user_ack_message is None:
    #         user_ack_message = self.default_acknowledge_msg
    #     instruction_update = ""
    #     return ActionResultOutcome(user_msg=user_ack_message, is_ending_response=self.is_chat_ending, ctx_upd=instruction_update)
    
    @override
    async def on_reject(self, chat_id, llm_provider, user_reject_message = None):
        if user_reject_message is None:
            user_reject_message = self.default_rejection_msg
        instruction_update = "The player does not want to trade right now. You must politely acknowledge that and keep talking with the player. DO NOT offer the player to trade again unless the player expresses the opposite or it is a completely new transaction"
        return ActionResultOutcome(user_msg=user_reject_message, is_ending_response=self.is_chat_ending, ctx_upd=instruction_update)
