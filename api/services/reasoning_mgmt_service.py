from langchain_core.output_parsers import PydanticOutputParser

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.infrastructure.llm.settings.ollama_config import Ollama_Config
from api.infrastructure.models.db_schemas import ChatDetailsDoc, ChatPromptDoc, SystemMessageDoc
from api.infrastructure.models.reasoning_schemas import ActionReasoning
from api.infrastructure.repositories.mongo.chat_prompts import ChatDetailsRepository, ChatPromptsRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.utils.helpers import HTTPLoggedException
from api.utils.statics import default_db_name, sys_message_types
from langgraph.graph import END, START, StateGraph
from typing import List, TypedDict
from loguru import logger
"""
# Multiple nodes can access and modify shared state
class WorkflowState(TypedDict):
    user_input: str
    search_results: list
    generated_response: str
    validation_status: str

def search_node(state):
    # Access shared state
    results = search(state["user_input"])
    return {"search_results": results}

def validation_node(state):
    # Access results from previous node
    is_valid = validate(state["generated_response"])
    return {"validation_status": "valid" if is_valid else "invalid"}

"""

class ReasoningState(TypedDict):
    chat_id:str
    current_history: List[str]
    char_profile: str
    current_mood: str
    chat_memos: str
    chat_events: str
    reasoning: ActionReasoning

class ReasoningMgmtService:
    _currentDB:str
    _sysRepo: SysMessagesRepository = None
    _chats_repo: ChatPromptsRepository = None
    _details_repo: ChatDetailsRepository = None
    _llm: LLM_Provider = None

    def __init__(self, llm: LLM_Provider, repos_db: str):
        self._currentDB = repos_db if repos_db is not None else default_db_name
        self._sysRepo = SysMessagesRepository(self._currentDB)
        self._chats_repo = ChatPromptsRepository(self._currentDB)
        self._details_repo = ChatDetailsRepository(self._currentDB)
        self._llm = llm

    async def handle_chat_reasoning(self, chat_id:str):
        logger.info("-- on background task init >> HANDLE CHAT REASONING --")
        graph_state = StateGraph(ReasoningState)
        graph_state.add_node(self.retrieve_chat_data)
        graph_state.add_node(self.action_reasoning)
        graph_state.add_node(self.update_reasoned_action)
        graph_state.add_edge(START, "retrieve_chat_data")
        graph_state.add_edge("retrieve_chat_data", "action_reasoning")
        graph_state.add_edge("action_reasoning", "update_reasoned_action")
        graph_state.add_edge("update_reasoned_action", END)
        #grap_state.add_node(retrieve_data)
        #   evaluate_action
        #   no se me ocurre nada mas 
        #graph_state.add_node(update_details_doc_with_reasoning)
        #graph_state.add_edge(START, "get_history")
        # [...] analysis nodes
        #   recuperar info de details para analysis y meterla en el state
        #   ReasoningState.char_profile
        #                 .memos
        #graph_state.add_edge("update_details", END)
        workflow = graph_state.compile()
        return await workflow.ainvoke({"chat_id" : chat_id})

    async def retrieve_chat_data(self, state: ReasoningState):
        chat_rec = await self._chats_repo.get_by_id(state.chat_id)
        if chat_rec is None:
            raise HTTPLoggedException(status_code=404, detail=f"No chat data found for id: {state.chat_id}")
        chat_doc = ChatPromptDoc.model_validate(chat_rec)
        details_rec = self._details_repo.get("chat_doc_id", state.chat_id)
        if details_rec is None:
            raise HTTPLoggedException(status_code=404, detail=f"No Chat Details Document found for chat id: {state.chat_id}")
        details_doc = ChatDetailsDoc.model_validate(details_rec)
        # details_doc.profile lleva toda la info de pyschology & full_profile
        # details_doc.chat-memo lleva short-memos & initial
        # details_doc.remmarkable_events lleva resultado de actions y en un futuro puede que mas cosas (que vengan de gameplay)
        state.current_history = chat_doc.messages_as_recent_history()
        state.profile = details_doc.botMemory.get("profile")
        state.current_mood = details_doc.botMemory.get("current-mood")
        state.chat_events = details_doc.botMemory.get("chat-remmarkable-events")
        return state

    async def action_reasoning(self, state: ReasoningState):
        record = self._sysRepo.get_by_type_and_tag(type=sys_message_types.base_template(0), tag="output-actions-reasoner-v0.0.1")
        if record is None:
            raise HTTPLoggedException(status_code=404, detail="No actions reasoner message found with tag: output-actions-reasoner-v0.0.1")
        sysmsg_doc:SystemMessageDoc = SystemMessageDoc.model_validate(record)
        sysmsg = sysmsg_doc.message

        sysmsg.replace("[[CHARACTER_PROFILE]]", state.char_profile)
        sysmsg.replace("[[CURRENT_MOOD]]", state.current_mood)
        #...
        parser = PydanticOutputParser(pydantic_object=ActionReasoning)
        parser_instruction = parser.get_format_instructions()
        final_sysmsg = f"{sysmsg}\n{parser_instruction}"
        messages = [
            {"system": final_sysmsg},
            { "user": "Analyse the conversation and it's context and reason if your character should or must add an action tag to the next response or select 'None' and keep chatting for now"}
        ]
        config: Ollama_Config = self._llm.config().get_settings_preset("action-reasoning")
        llm = self._llm.fresh_model_instance(model="", config=config).as_structured_llm()
        response = await llm.ainvoke(messages)
        parsed_response:ActionReasoning = parser.invoke(response)
        if parsed_response.output_action != "TALK":
            priority_msg = f"You MUST append the {parsed_response.output_action} tag to your response." if parsed_response.is_mandatory else f"You should consider adding the {parsed_response.output_action} tag to your response."
            state.reasoning = f"{parsed_response.output_action}.{priority_msg} Reason: {parsed_response.reason}"
        else:
            state.reasoning = ""
        return state

    async def update_reasoned_action(self, state: ReasoningState):
        # get details
        # if len(state.reasoning) > 0:
        #   details.botMemory["reasoned-action"] = state.reasoning
        #   await update_details
        return state
        

