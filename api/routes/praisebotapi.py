from typing import Any, List
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger
from api.infrastructure.llm.llm_provider import LLM_Provider
from api.infrastructure.llm.ollama_provider import Ollama_Provider
from api.infrastructure.llm.settings.ollama_config import Ollama_Config
from api.infrastructure.models.db_schemas import ChatDetailsDoc, ChatPromptDoc, ChatSummaryDoc, SessionDoc, SystemMessageDoc
from api.infrastructure.models.primitives import ChatEvent, ChatMessage
from api.infrastructure.models.reasoning_schemas import ActionDecision
from api.infrastructure.repositories.mongo.chat_prompts import ChatDetailsRepository, ChatPromptsRepository, ChatSessionsRepository, GameCharDoc
from api.infrastructure.repositories.mongo.chat_summaries_repo import ChatSummariesRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.mappers.prompting_mappers import botInfoToGenRequest, sessionDocToChatInitDto
from api.models.prompting_schemas import ActionAcknowledgeDto, ActionOutcomeDto, ChatPromptRequest, ChatResultDto, ConversationDto, ConversationPromptDto, SessionHistoryUpdateRequest, StreamEndResponse, UnrealChatUpdateRequest, UnrealStreamEnd, UpdateModelSettingsRequest
from api.models.schemas import QueryCondition
from api.services.botctx_mgmt_service import BotContextMgmtService
from api.services.chat_actions.action_result import ActionResultOutcome
from api.services.chat_actions.output_actions_handler import OutputActionsHandler
from api.services.gamechar_mgmt_service import CharactersMgmtService
from api.services.memo_mgmt_service import MemoMgmtService
from api.services.mood_analysis_service import MoodAnalysisService
from api.utils.helpers import HTTPLoggedException, get_ctx_num_for_text, get_llm_provider, get_request_db_name, unreal_messages_to_history, chat_history_to_unreal
from api.utils.statics import praise_db_name, event_tags, chat_event_cats, chat_turns_to_generate_memory, sys_message_types, max_ctx_len, max_ctx_len, ctx_len_offset

router = APIRouter(prefix="/praise-bot/chat")

@router.post(
    "/init-conversation",
    summary="begins or continues a conversation with a game character. Creates or updates the session, chat and chat details for a given character (if exists) , otherwise creates the character first",
    responses={
        200 : {"description": "Succesful response returning the session"}
    }
)
async def init_conversation(dto: ConversationDto, request: Request):
    print("-- ON INIT CONVERSATION REQ DTO:", dto)
    user_header = request.headers.get('app-username')
    chars_svc = CharactersMgmtService(get_request_db_name(request))
    chats_svc = CharactersMgmtService(get_request_db_name(request))
    memo_svc = MemoMgmtService(get_request_db_name(request))
    ctx_svc = BotContextMgmtService(get_request_db_name(request))
    db_character: GameCharDoc = None
    llm_provider: LLM_Provider = get_llm_provider()
    if dto.botInfo.characterId is None:
        logger.warning("-- GENERATING CHARACTER FOR BOTINFO --")
        print(dto.botInfo)
        new_character = await chars_svc.generate_character(botInfoToGenRequest(dto.botInfo), llm_provider=llm_provider)
        if new_character is None:
            raise HTTPLoggedException(status_code=500, detail= f"An error has occured while creating the new character")
        db_character = GameCharDoc.model_validate(await chars_svc.save_game_character(new_character))
        if db_character is None:
            raise HTTPLoggedException(status_code=500, detail="An error has occured while saving the created character in db")
        logger.warning("-- ON CHARACTER CREATED --")
        print(db_character)
        dto.botInfo.characterId = str(db_character.id)
        dto.botInfo.traits = db_character.traits
        dto.botInfo.personalities = db_character.personalities
        dto.botInfo.charRole = db_character.role
        dto.botInfo.charName = db_character.name
        dto.botInfo.charAge = db_character.age
        dto.botInfo.factionName = db_character.faction
        logger.warning(f"ON CHARACTER CREATED >> {dto.botInfo.charName}")
        print(db_character)
    else: 
        db_character = GameCharDoc.model_validate(await chars_svc.get_character(dto.botInfo.characterId))
    sessions_repo = ChatSessionsRepository(get_request_db_name(request))
    chats_repo = ChatPromptsRepository(get_request_db_name(request))
    chat_details_repo = ChatDetailsRepository(get_request_db_name(request))
    #SET INITIAL BOT MOOD
    mood_analysis_service = MoodAnalysisService()
    dto.botInfo.mood = mood_analysis_service.handle_personality_mood_transition("Relaxed", dto.botInfo.personalities)
    logger.info(f"-- Initial bot character MOOD: {dto.botInfo.mood} --")
    sys_msgs = await ctx_svc.get_base_instruction_CoTv2(dto)
    conversation_tag = f"{dto.botInfo.charName}-{dto.speakerInfo.charName}"
    existing_session = await sessions_repo.get(varname="character_id", value=db_character.id)
    logger.info(f"--EXISTING SESSION--")
    session_doc = SessionDoc.model_validate(existing_session) if existing_session is not None else SessionDoc.model_validate(await sessions_repo.create(SessionDoc(character_id=db_character.id,username=user_header,tag=conversation_tag, current_chat_summary="")))
    is_new_session = False if session_doc.current_chat_id is not None and session_doc.current_chat_id != "" else True
    if dto.model is not None and dto.model.strip() == "":
        dto.model = None
    chat_doc = ChatPromptDoc(
        sessionId=session_doc.id,
        username=user_header,
        tag=f"{dto.botInfo.charName}-{dto.speakerInfo.charName}",
        model=llm_provider.current_model() if dto.model is None else dto.model,
        maxTokens=dto.maxTokens,
        temperature=dto.temperature,
        messages=[ChatMessage(Role="system", Message=sys_msgs["BASE"])] #sys_msgs["BASE"]
    )
    chat_doc.id = ObjectId()
    chat_insert = ChatPromptDoc.model_validate(await chats_repo.create(chat_doc))
    # Add previous cached available actions or default ones if is new Session (first chat with this character)
    if is_new_session is False:
        #13/05/25 --> se añade esto por integracion en UE5.STOP_TALKING.SKIP_CHAT_END (todas las OUTPUT_ACTIONS generan memo excepto ese caso)
        current_chat_longmemo = await memo_svc.query_summaries([QueryCondition(field="observations", value="full-chat")])
       
       
        isNewChat = len(current_chat_longmemo) == 0
       
       
        ##if isNewChat: # return puta session con char y los details creados, idiota
         #   return await handle_conversation(chat_id=session_doc.current_chat_id, dto=dto, request=request) 
       
        if isNewChat == False:       
            logger.info(f"-- RECOVERING ACTIONS FROM PREVIOUS CHAT. SESSION.CHAT_ID: {session_doc.current_chat_id} --")
            prev_details = await chats_svc.get_chat_details(session_doc.current_chat_id)
            if prev_details is None:
                raise HTTPLoggedException(status_code=500, detail="No chat details have been found for previous session chat, unable to recover current bot actions...")
            logger.info(f"-- ADDING ACTIONS FROM PREV CHAT DETAILS. DETAILS DOC ID: {prev_details.id} --")
            print("PREV ACTIONS:\n", prev_details.botMemory['actions'])    
            sys_msgs["ACTIONS"] = prev_details.botMemory['actions'] #mantiene status OutputActions
    chat_details = ChatDetailsDoc(
        chat_doc_id=chat_insert.id,
        zoneName=dto.zoneName,
        usercharName=dto.speakerInfo.charName,
        usercharRole=dto.speakerInfo.charRole,
        userfaction=dto.speakerInfo.factionName,
        botcharName=dto.botInfo.charName,
        botcharRole=dto.botInfo.charRole,
        botfaction=dto.botInfo.factionName,
        botPersonalities=dto.botInfo.personalities,
        botTraits=dto.botInfo.traits,
        botMood=dto.botInfo.mood,
        botActions=await ctx_svc.get_default_bot_actions(dto.botInfo.charRole) if is_new_session else prev_details.botActions,
        botMemory={"profile": sys_msgs["PROFILE"], "actions": sys_msgs["ACTIONS"]}, #sys_msgs["PROFILE"], sys_msgs["ACTIONS"]
        zoneContext=dto.zoneActualContext,
        usercharContext=dto.speakerInfo.actualContext,
        botcharContext=dto.botInfo.actualContext,
    )
    chat_details.id = ObjectId()
    formatted_sys_msg = sys_msgs["BASE"].replace("[[OutputActions]]", chat_details.botMemory['actions'])
    #TODO v2 -> if session.summary --> "Your OVERALL OPINION about the other character based on your previous experiences is: session.summary"
    if is_new_session is False:
        initial_memo_text = ""
        if session_doc.current_chat_summary is not None and session_doc.current_chat_summary != "":
            logger.warning("APPENDING RECENT MEMO")
            print(session_doc)
            initial_memo_text = f"You remember this character from a recent conversation. This is what you recall from it:\n\n>> RECENT CONVERSATION MEMORY: {session_doc.current_chat_summary}"
            chat_details.chat_events.append(ChatEvent(category=chat_event_cats.to_string(chat_event_cats.assistant), 
                                                    chat_turn_id=len(chat_doc.messages), 
                                                    tag="event_tags", 
                                                    message=f">> RECENT CONVERSATION RECALL >> chat_id: {session_doc.current_chat_id}"))
        remarkable_events_text = ""
        memos_repo  = ChatSummariesRepository(get_request_db_name(request)) 
        #           18/03/25 --> se cargan todos para incluir FACTS y/o CONTRACTS | CAMBIOS_FACTION ({{ENROLL}}) - {{DISCHARGE}}
        #                    --> se añade sistema de tags para memos
        #                           - Summary.observations[0] = chat-remarkable-event (ChatEvent category)
        #                           - Summary.observations[1] = MEMO_TAG (OUTPUT_ACTION | CHARACTER_MET | LOCATION_VISITED | QUEST_GEN) <- sys_message_types.to_string():{{ACTION_TAG}}
        #                           - Summary.observations[2] = MEMO_STATUS (CURRENT | DEPRECATED) --> procesa currents (upd_sys_msg) y añade DEPS a memory (v2: RAG)

        all_event_memos = await memos_repo.query(conditions=[
            QueryCondition(field="session_id", value=session_doc.id), 
            QueryCondition(field="observations", value=chat_event_cats.to_string(chat_event_cats.remarkable_event))
        ])
        if len(all_event_memos) > 0:
            for event in all_event_memos:
                remarkable_event = ChatSummaryDoc.model_validate(event)
                print("MEMO RECALL", remarkable_event)
                if sys_message_types.to_string(sys_message_types.output_action) in remarkable_event.observations[1]:
                    action = remarkable_event.observations[1].split(":")[1]
                    status = remarkable_event.observations[2].split(":")[1]
                    logger.info(f"-- EVENT RECALL FROM OUTPUT ACTION FOUND. MEMORY_OBS[1]_SPLIT_ACTION: {action} - MEMORY_OBS[2]_SPLIT_STATUS = {status}")
                    if status == "CURRENT": #esto no sirve --> if JOIN:CURRENT -> actions += LEAVE
                        logger.info(f"-- OUTPUT_ACTION RESULT MEMORY FOUND >> {action} >> STATUS: {status}")
                        remarkable_events_text += f"\n\n- ACTION MEMORY >> {action}:\n{remarkable_event.summary.strip()}"
                #Memos generados DESPUES de OutputAction:QUEST. No tienen por qué pertenecer a una OUTPUT_ACTION de char (ej: Kill Bishop -> player Party AND JOIN.GOAL)
                elif sys_message_types.to_string(sys_message_types.quest_gen_template) in remarkable_event.observations[1]: 
                    logger.info("-- QUEST GENERATION MEMO FOUND --")
                    tag_split = remarkable_event.observations[1].split(":")
                    remarkable_events_text += f"\n\n- QUEST MEMORY >> Quest Title: {tag_split[1]} >> Status: {tag_split[2]}:\n{remarkable_event.summary.strip()}"
                else:
                    logger.info("-- ADDING NON ACTION MEMO --")
                    print(remarkable_event.summary)
                    remarkable_events_text += f"\n\n- EVENT MEMORY:\n{remarkable_event.summary.strip()}"
                chat_details.chat_events.append(ChatEvent(
                    category=chat_event_cats.to_string(chat_event_cats.assistant), 
                    chat_turn_id=len(chat_doc.messages), 
                    tag=event_tags.assistant_memo, 
                    message=f">> REMARKABLE EVENT RECALL >> Memory TAG: {remarkable_event.observations[1]} >> summary_id: {remarkable_event.id}"))
        if remarkable_events_text != "" and remarkable_events_text is not None:
            initial_memo_text += f"\n\n>> REMARKABLE MEMORIES: This are memories from important events, facts and other important information from past interactions:\n\n{remarkable_events_text.strip()}"   
        #RECUPERAR LONG MEMORIES DE CONVERSACIONES ANTERIORES A PREVIA (PREVIA SE SACA DE SESSION SUMMARY)
        longterm_memory_text = await memo_svc.get_session_longterm_memo_text(session_doc.id, exclude_current_chat=True if session_doc.current_chat_summary != "" else False)
        if longterm_memory_text != "" and longterm_memory_text is not None:
            initial_memo_text += f"\n{longterm_memory_text}"
            chat_details.chat_events.append(ChatEvent(category=chat_event_cats.to_string(chat_event_cats.assistant), 
                                                    chat_turn_id=len(chat_doc.messages), 
                                                    tag=event_tags.assistant_memo, 
                                                    message=f">> LONG TERM MEMO RECALL >> session_id: {session_doc.id}"))
    # Memory System v1: RECENT & LONGTERM MEMO se añade a sys msg y se pasa juto con reglas y desc.se guarda onInit en Details como botMemory y se añade a sysmsg en cada prompt onHandle. onHandle tambien añade CURRENT_CHAT SUMMARY (si hay) 
    #                   #WG: CTX_LEN !!! (Limitar LONGS v2:RAG)
    else:
        initial_memo_text = f"INITIALIZED. It is the first time that you meet the user's character. You don't know the user name yet, the character has not been introduced. DO NOT call the user character by it's name UNTIL intruduced in the conversation."
    if initial_memo_text != "" and initial_memo_text is not None:
        chat_details.botMemory["initial-memo"] = f"Your character has also 'memory' (e.g. summarizations of previous interactions with the Player Character),\nuse them as a 'knowledge base' to have a better understanding when the Player references past conversations, characters, locations or situations, hence providing a more contextualized and precise response. This is your 'Memory' or knowledge-base:\n{initial_memo_text}"
    # se recuperan los longterm memos de la session.current_chat_id antes de actualizar la session con la el nuevo id
    session_doc.current_chat_id = chat_insert.id
    session_doc.current_chat_summary = ""
    await sessions_repo.update(session_doc.id, session_doc)
    chat_details_insert = ChatDetailsDoc.model_validate(await chat_details_repo.create(chat_details))
    logger.info(f"--DETAILS--")
    return sessionDocToChatInitDto(doc=session_doc, npc=db_character, conversation=dto, sysmsg=formatted_sys_msg) 

@router.post(
    "/test/init-conversation",
    summary="begins or continues a conversation with a game character",
    responses={
        200 : {"description": "Succesful response streaming back the llm response (valga la redundancia)"}
    }
)
async def test_init_conversation(dto: ConversationDto) -> Any:
    botctx_svc = BotContextMgmtService()
    return await botctx_svc.get_base_instruction_CoTv2(dto)

@router.post(
    "/{chat_id}/handle-conversation/v1",
    summary="continues a conversation with a game character",
    responses={
        200 : {"description": "Succesful response streaming back the llm response (valga la redundancia)"}
    }
)
async def handle_conversation(chat_id:str, dto:ConversationPromptDto, request:Request) -> Any:
    """
    Output Actions
    """
    logger.info(f"-- ON HANDLE CONVERSATION :: CHAT ID {chat_id} --")
    print(dto)
    #TODO a service (Query + Update ChatStatsDoc)
    #sentiment_analysis = vader_analyze_current_prompt_sentiment(user_prompt=dto.speakerPrompt)
    #if (len(recentHistory) >= default_history_chats_return) -> trigger_chat_chunk_analysis |  media suma prompts -> lo guardo como event? | Tabla BotSentimentAnalysis w BotThresholds + stats | X y ademas guardo ChatEvent cada X turns
    #logger.info(f"-- SENTIMENT ANALYISIS RESULTS --\n", sentiment_analysis)
    ############## TODO: quitar (devonly) ################
    #await on_llm_settings_update(chat_id=chat_id, dto=UpdateModelSettingsRequest(model_name=dto.model, max_tokens=dto.maxTokens, temperature=dto.temperature), request=request)
    ######################################################
    memo_service = MemoMgmtService(get_request_db_name(request))
    repo = ChatPromptsRepository(get_request_db_name(request))
    doc = ChatPromptDoc.model_validate(await repo.get_by_id(chat_id))
    details_repo = ChatDetailsRepository(get_request_db_name(request))
    details = ChatDetailsDoc.model_validate(await details_repo.get(varname="chat_doc_id", value=chat_id))
    #TODO: a PraiseMgmtService
    context_update = ""
    if len(dto.zoneContextUpdate) > 0:
        for message in dto.zoneContextUpdate:
            event = ChatEvent(category=chat_event_cats.to_string(chat_event_cats.context), 
                              chat_turn_id=len(doc.messages), 
                              tag=event_tags.zone_ctx, 
                              message=message)
            if "[observation]" in message:
                event.category = chat_event_cats.to_string(chat_event_cats.observation)
                event.tag = "[observation]"
                event.message = event.message.replace("[observation]:", "")
            details.chat_events.append(event)
            zone_ctx_upd = f"{event.tag}: {event.message.strip()}\n"
            context_update += zone_ctx_upd
            details.zoneContext += zone_ctx_upd
    if len(dto.speakerContextUpdate) > 0:
        for message in dto.speakerContextUpdate:
            event = ChatEvent(category=chat_event_cats.to_string(chat_event_cats.user), 
                              chat_turn_id=len(doc.messages), 
                              tag=event_tags.user_ctx, 
                              message=message)
            details.chat_events.append(event)
            speaker_ctx_upd = f"{event.tag}: {event.message.strip()}\n" 
            context_update += speaker_ctx_upd
            details.usercharContext += speaker_ctx_upd
            #TODO: UPDATE DETAILS SPEAKER_CTX
    if len(dto.botContextUpdate) > 0:
        for message in dto.botContextUpdate:
            event = ChatEvent(category=chat_event_cats.to_string(chat_event_cats.assistant), 
                              chat_turn_id=len(doc.messages), 
                              tag=event_tags.assistant_ctx, 
                              message=message)
            details.chat_events.append(event)
            bot_ctx_upd = f"{event.tag}: {event.message.strip()}\n"
            context_update += bot_ctx_upd
            details.botcharContext += bot_ctx_upd
    await details_repo.update(details.id, details)
    #TODO: add to ChatDetails.chat-events?
    prompt_request = ChatPromptRequest(
        max_tokens=doc.max_tokens,
        temperature=doc.temperature,
        chat_history=doc.messages_as_recent_history(include_sys_msg=True),
        message=dto.speakerPrompt,
        system_message=context_update,
        model_name=doc.model
    )
    if context_update != "":
        doc.messages.append(ChatMessage(Role="context", Message=context_update))
        await repo.update(doc.id, doc)
    prompt_request.chat_history = await memo_service.handle_chat_assistant_memo(chat_id=chat_id, recent_history=prompt_request.chat_history)
    prompt_request.chat_history[0]["system"] = prompt_request.chat_history[0]["system"].replace("[[OutputActions]]", details.botMemory["actions"]).replace("[[ReasonedAction]]", "### REASONED ACTION: FIGHT. You MUST add a {{FIGHT}} tag to your response. Reason: the other character has been provoking you for too many turns and he belongs to an enemy faction")
    #TODO: Analisis sentimiento user_prompt --> OutputAction (NLP | LLM) v2: Agentic Tool
    # 2: Preparar RAG(s) <- Se añade a sys_msg initial_graph_query con info speaker y zona (info fija durante conversacion). ChatsRAG para prompt + history | augmented query (v2)
    return StreamingResponse(llm_stream(prompt_request=prompt_request, username=details.usercharName, botname=details.botcharName), media_type="text/event-stream")


@router.post(
    "/{chat_id}/handle-conversation/v2",
    summary="continues a conversation with a game character",
    responses={
        200 : {"description": "Succesful response streaming back the llm response (valga la redundancia)"}
    }
)
async def handle_conversation(chat_id:str, dto:ConversationPromptDto, request:Request) -> Any:
    """
    Output Actions
    """
    logger.info(f"-- ON HANDLE CONVERSATION :: CHAT ID {chat_id} --")
    print(dto)
    #TODO a service (Query + Update ChatStatsDoc)
    #sentiment_analysis = vader_analyze_current_prompt_sentiment(user_prompt=dto.speakerPrompt)
    #if (len(recentHistory) >= default_history_chats_return) -> trigger_chat_chunk_analysis |  media suma prompts -> lo guardo como event? | Tabla BotSentimentAnalysis w BotThresholds + stats | X y ademas guardo ChatEvent cada X turns
    #logger.info(f"-- SENTIMENT ANALYISIS RESULTS --\n", sentiment_analysis)
    ############## TODO: quitar (devonly) ################
    #await on_llm_settings_update(chat_id=chat_id, dto=UpdateModelSettingsRequest(model_name=dto.model, max_tokens=dto.maxTokens, temperature=dto.temperature), request=request)
    ######################################################
    
    ############# v2 09/06/2026 ##############
    # chat history + memos + char_Actions + profile <- SELECT ACTION
    # chat_sysms = lo mismo pero le quito las actions disponibles -> añado un #IMPORTANT : action + reason

    #########################################

    repo = ChatPromptsRepository(get_request_db_name(request))
    doc = ChatPromptDoc.model_validate(await repo.get_by_id(chat_id))
    details_repo = ChatDetailsRepository(get_request_db_name(request))
    details = ChatDetailsDoc.model_validate(await details_repo.get(varname="chat_doc_id", value=chat_id))
    #TODO: a PraiseMgmtService
    context_update = ""
    if len(dto.zoneContextUpdate) > 0:
        for message in dto.zoneContextUpdate:
            event = ChatEvent(category=chat_event_cats.to_string(chat_event_cats.context), 
                              chat_turn_id=len(doc.messages), 
                              tag=event_tags.zone_ctx, 
                              message=message)
            if "[observation]" in message:
                event.category = chat_event_cats.to_string(chat_event_cats.observation)
                event.tag = "[observation]"
                event.message = event.message.replace("[observation]:", "")
            details.chat_events.append(event)
            zone_ctx_upd = f"{event.tag}: {event.message.strip()}\n"
            context_update += zone_ctx_upd
            details.zoneContext += zone_ctx_upd
    if len(dto.speakerContextUpdate) > 0:
        for message in dto.speakerContextUpdate:
            event = ChatEvent(category=chat_event_cats.to_string(chat_event_cats.user), 
                              chat_turn_id=len(doc.messages), 
                              tag=event_tags.user_ctx, 
                              message=message)
            details.chat_events.append(event)
            speaker_ctx_upd = f"{event.tag}: {event.message.strip()}\n" 
            context_update += speaker_ctx_upd
            details.usercharContext += speaker_ctx_upd
            #TODO: UPDATE DETAILS SPEAKER_CTX
    if len(dto.botContextUpdate) > 0:
        for message in dto.botContextUpdate:
            event = ChatEvent(category=chat_event_cats.to_string(chat_event_cats.assistant), 
                              chat_turn_id=len(doc.messages), 
                              tag=event_tags.assistant_ctx, 
                              message=message)
            details.chat_events.append(event)
            bot_ctx_upd = f"{event.tag}: {event.message.strip()}\n"
            context_update += bot_ctx_upd
            details.botcharContext += bot_ctx_upd
    await details_repo.update(details.id, details)
    #TODO: add to ChatDetails.chat-events?
    prompt_request = ChatPromptRequest(
        max_tokens=doc.max_tokens,
        temperature=doc.temperature,
        chat_history=doc.messages_as_recent_history(include_sys_msg=True),
        message=dto.speakerPrompt,
        system_message=context_update,
        model_name=doc.model
    )
    if context_update != "":
        doc.messages.append(ChatMessage(Role="context", Message=context_update))
        await repo.update(doc.id, doc)
    ###############################################################
    sys_repo = SysMessagesRepository(get_request_db_name(request))
    selector_msg = await sys_repo.get_by_type_and_tag(type=sys_message_types.base_template, tag="action-selector-v0.0.1")
    logger.warning("-- on action selector sys msg query --")
    print(selector_msg)
    if selector_msg is None:
        raise HTTPLoggedException(status_code=500, detail="No sys message found with tag: action-selector-v0.0.2")
    selector_doc =SystemMessageDoc.model_validate(selector_msg);
    chat_context = "" #formatted chat history + memos & events
    selector_chats = prompt_request.chat_history[1:]
    logger.warning("-- selector chats --")
    print(selector_chats)
    llm_provider: Ollama_Provider = get_llm_provider()
    #############################################################
    formatted_chat = llm_provider.chat_history_to_template(chat_history=selector_chats, assistant_guidance_token="", template_key="praise")
    formatted_chat = formatted_chat.replace("<<USERNAME>>", details.usercharName)
    formatted_chat = formatted_chat.replace("<<BOTNAME>>", details.botcharName)
    if formatted_chat == None:
        formatted_chat = ""
    
    if details.botMemory.get("chat-memo") is not None:
        formatted_chat += f"\n\n{details.botMemory["chat-memo"]}"
    if details.botMemory.get("chat-remmarkable-events") is not None:
        formatted_chat += f"\n\n{details.botMemory["chat-remmarkable-events"]}"
    if formatted_chat is not None and formatted_chat != "":
        chat_context = f"# RECENT CHAT HISTORY:\n\n{formatted_chat.strip()}"
    logger.warning("ON FUCKING DETAILS")
    print(details.botMemory.get("profile"))
    logger.warning("ON FUCKING ACTIONS")
    print(details.botMemory.get("actions"))
    logger.warning("ON VALIDATE")
    
    selector_msg = selector_doc.message.replace("[[OutputActions]]", details.botMemory.get("actions")).replace("[[CharacterProfile]]", details.botMemory.get("profile")).replace("[[CHAT_CONTEXT]]", chat_context)
    logger.warning("ON SELECTOR MESSAGE FORMATTED")
    print(selector_msg)
    parser =PydanticOutputParser(pydantic_object=ActionDecision)
    parser_instruction = parser.get_format_instructions()
    selector_msg = f"{selector_msg}\n\n{parser_instruction}"
    logger.warning("FINAL SELECTOR MESSAGE")
    print(selector_msg)
    llm = llm_provider.fresh_model_instance(model=prompt_request.model_name, config=Ollama_Config().get_settings_preset("chat"), ctx_len=len(selector_msg) + 100 if len(selector_msg) <= max_ctx_len else max_ctx_len)
    action_response = llm.invoke(selector_msg)
    decision = parser.invoke(action_response)
    logger.warning("ON ACTION DECISION RESPONSE")
    print(decision)
    memo_service = MemoMgmtService(get_request_db_name(request))
    prompt_request.chat_history = await memo_service.handle_chat_assistant_memo(chat_id=chat_id, recent_history=prompt_request.chat_history)
    #prompt_request.chat_history[0]["system"] = prompt_request.chat_history[0]["system"].replace("[[OutputActions]]", details.botMemory["actions"])
    prompt_request.chat_history[0]["system"] = prompt_request.chat_history[0]["system"].replace("[[CommandedAction]]", f"{decision.output_action} >> REASON: {decision.reason}")
    
    #TODO: Analisis sentimiento user_prompt --> OutputAction (NLP | LLM) v2: Agentic Tool
    # 2: Preparar RAG(s) <- Se añade a sys_msg initial_graph_query con info speaker y zona (info fija durante conversacion). ChatsRAG para prompt + history | augmented query (v2)
    return StreamingResponse(llm_stream(prompt_request=prompt_request, username=details.usercharName, botname=details.botcharName), media_type="text/event-stream")

@router.post(
    "/on-stream-finished",
    summary="Appends a collection of chat history messages to the session current chat collection. Used to update a session after a streamed response",
    responses={
        200: {"description" : "Succesful response with the recent chat history"}
    }
)
async def on_stream_finished(update_request: SessionHistoryUpdateRequest, request:Request) -> StreamEndResponse:
    print("-- UPDATE REQUEST --",update_request)
    sessions_repo = ChatSessionsRepository(get_request_db_name(request))
    chats_repo = ChatPromptsRepository(get_request_db_name(request))
    memo_service = MemoMgmtService(get_request_db_name(request))
    actions_handler = OutputActionsHandler()
    session = SessionDoc.model_validate(await sessions_repo.get_by_id(update_request.sessionId))
    if session is None:
        raise HTTPException(status_code=404, detail="There is no active session with that GUID. Begin a new session by making a request to '/chats/session/init'")
    chat_doc = ChatPromptDoc.model_validate(await chats_repo.get_by_id(session.current_chat_id))
    if chat_doc is None:
        raise HTTPLoggedException(status_code=404, detail="There are no session chat messages for this session. Begin a new session by making a request to '/chats/session/init'")                                          
    #                                                         Bot se presenta    Menciona lugar   Zone | Speakers
    ### TODO: analisis de respuesta para chat-events update ([kg-char-update] | [kg-loc-update] | [ctx-update])
    chat_doc.append_history_to_messages(update_request.chatHistory)
    await chats_repo.update(chat_doc.id, chat_doc)
    print(f"-- LEN CHAT: {len(chat_doc.messages)} - TURNS TO MEMO: {chat_turns_to_generate_memory}")
    await memo_service.update_shortmemo(chat=chat_doc, model_provider=get_llm_provider())
    logger.warning("-- ON STREAM REQUEST --")
    history = chat_doc.messages_as_recent_history(include_sys_msg=True)
    logger.warning("-- ON HISTORY MESSAGES --", history)
    output_action_result = await actions_handler.handle_output_actions(chat=chat_doc,history=history) #TODO --> a PraiseMgmtService
    if output_action_result.is_chat_ending:
        logger.info(f"-- ON OUTPUT ACTION RESULT -- END CHAT >> REASON: {output_action_result.reason}")
    else:
        logger.info(f"-- ON OUTPUT ACTION RESULT -- KEEP CHATTING >> REASON: {output_action_result.reason}")
    return StreamEndResponse(history=history, 
            chatResult=ChatResultDto(
                action=output_action_result.action_tag,
                sysmsgType=output_action_result.action_sysmsg_id, 
                reason=output_action_result.reason, 
                defaultAckMessage=output_action_result.default_acknowledge_msg,
                defaultRejMessage=output_action_result.default_rejection_msg,
                chatEndingEvent=output_action_result.end_chat_event,
                isChatEnding=output_action_result.is_chat_ending))

@router.post(
    "/{chat_id}/autochat/{action}/limit/{limit}",
    summary="Generates the next player prompt for a given conversation, biasing the prompt to achieve a specific output action. The prompt should carry the extra 'reason' instructions (like 'FIGHT because Faction missalignment | repeteadly insults NPC)",
    responses={
        200: {"description" : "Succesful response with the recent chat history"}
    }
)
async def auto_chat(chat_id:str, action:str, limit:int, dto: ChatPromptRequest, request:Request) -> Any:
    #get llm
    logger.warning(f"-- ON AUTOCHAT >> {chat_id} >> {action} >> {limit} --")
    print(dto)
    sysrepo = SysMessagesRepository(get_request_db_name(request))
    repo = ChatPromptsRepository(get_request_db_name(request))
    doc = ChatPromptDoc.model_validate(await repo.get_by_id(chat_id))
    action_doc = SystemMessageDoc.model_validate(await sysrepo.get_by_type_and_tag(type=sys_message_types.output_action, tag=action))
    names = doc.tag.split("-")
    prompt_doc = SystemMessageDoc.model_validate(await sysrepo.get_by_type_and_tag(type=sys_message_types.base_template, tag="user-autochat-v0.0.4"))
    history = get_llm_provider().chat_history_to_template(chat_history=doc.messages_as_recent_history(include_sys_msg=False), assistant_guidance_token=f"### {names[1]}:", template_key="praise")
    history = history.replace("<<USERNAME>>", names[1]).replace("<<BOTNAME>>", names[0])
    guidance_msg = dto.system_message if dto.system_message is not None and len(dto.system_message) > 0 else ""
    prompt_msg = prompt_doc.message.replace("<<ACTION>>", action).replace("<<TURNS_LIMIT>>", f"{limit}").replace("<<CHAT_HISTORY>>", history).replace("<<SYSMSG>>", guidance_msg).replace("<<ACTION_RULES>>", action_doc.message)
    llm_provider= get_llm_provider()
    llm = llm_provider.fresh_model_instance(model=dto.model_name, config=Ollama_Config().get_settings_preset("chat"), ctx_len=get_ctx_num_for_text(prompt_msg))
    logger.warning("-- ON FAKE USER PROMPT >> SYSMSG --")
    print(prompt_msg)
    user_msg = llm.invoke(prompt_msg)
    logger.warning("-- ON FAKE USER RESPONSE --")
    print(user_msg)

    return StreamingResponse(llm_prompt_stream(llm_provider=llm_provider, prompt=prompt_msg, model=doc.model, temperature=doc.temperature, max_tokens=doc.max_tokens, stopping_tokens=llm_provider.stopping_tokens()), media_type="text/event-stream")

@router.post(
    "/on-unreal-stream-finished",
    summary="Appends a collection of chat history messages to the session current chat collection. Used to update a session after a streamed response",
    responses={
        200: {"description" : "Succesful response with the recent chat history"}
    }
)
async def on_unreal_stream_finished(update_request: UnrealChatUpdateRequest, request: Request) -> UnrealStreamEnd:
    print("-- UNREAL UPDATE REQUEST --",update_request)
    stream_update: StreamEndResponse = await on_stream_finished(update_request=SessionHistoryUpdateRequest(sessionId=update_request.sessionId, chatHistory=unreal_messages_to_history(update_request.chatHistory)), request=request)
    print("-- STREAM UPDATE --", stream_update)
    return UnrealStreamEnd(chatResult=stream_update.chatResult, history=chat_history_to_unreal(stream_update.history))


@router.post(
    "/{chat_id}/on-interaction-acknowledge",
    summary="Submits the user response to a non chat-discontinuing Output Action parsed from the last LLM response. Admits a user acknowledge message as next chat turn, otherwise an informative / contextual message is added",
    responses={
        200: {"description" : "Succesful response with the outcome of the triggered OutputAction process (user_message, instruction_update and end_chat flag)"}
    }
)
async def on_output_action_acknowledge(chat_id:str, dto: ActionAcknowledgeDto, request:Request) -> ActionOutcomeDto:
    actions_handler = OutputActionsHandler(get_request_db_name(request))
    action_outcome = ActionResultOutcome(user_msg="[...]")
    if dto.isUserRejection:
        #prompt_request.system_message =f"{event_tags.user_ctx}: {chat.tag.split("-")[1]} has rejected the {dto.action} proposal."
        action_outcome = await actions_handler.handle_user_reject(action=dto.action, chat_id=chat_id, user_message=dto.userMessage, llm_provider=get_llm_provider())
    else:
        #prompt_request.system_message =f"{event_tags.user_ctx}: {chat.tag.split("-")[1]} has accepted the {dto.action} proposal."
        action_outcome = await actions_handler.handle_user_acknowledge(
            action=dto.action,
            chat_id=chat_id,
            user_message=dto.userMessage, 
            llm_provider=get_llm_provider())
    logger.info("-- ON ACTION OUTCOME --")
    print(action_outcome)
    return ActionOutcomeDto(action=dto.action, 
                            isUserRejection=dto.isUserRejection, 
                            userMessage=action_outcome.user_message,
                            instructionUpdate=action_outcome.instruction_update,    
                            endChat=action_outcome.is_ending_response) #15-04-25 --> esto al igual no hace falta (Casos: EndChat | Ack-Rej = Close | UltimaResp-SeguirHablando)

@router.post(
    "/{chat_id}/on-ending-action",
    summary="Handles the user submit for an Output Action that does not return an answer. It may end the current chat (and generate a LONG MEMO) or not (TRADE.REJ | STOP TALKING...)",
    responses={
        200: {"description" : "Succesful response that may trigger a LONGMEMO generation process on the background"}
    }
)
async def on_ending_action_submit(chat_id:str, dto: ActionAcknowledgeDto, request:Request, bgtsk: BackgroundTasks):
    print(f":: ON ENDING ACTION REQ :: ", dto)
    chats_repo = ChatPromptsRepository(get_request_db_name(request))
    chat = ChatPromptDoc.model_validate(await chats_repo.get_by_id(chat_id))
    actions_handler = OutputActionsHandler(get_request_db_name(request))
    action_outcome = ActionResultOutcome(user_msg="[...]")
    if dto.isUserRejection:
        action_outcome = await actions_handler.handle_user_reject(
            action=dto.action,
            chat_id=chat_id,
            user_message=dto.userMessage, 
            llm_provider=get_llm_provider())
    else:    
        action_outcome= await actions_handler.handle_user_acknowledge(
            action=dto.action,
            chat_id=chat_id,
            user_message=dto.userMessage, 
            llm_provider=get_llm_provider())
    skip_chat_end:bool = True if "<<SKIP_CHAT_END>>" in action_outcome.user_message else False
    if skip_chat_end:
      action_outcome.user_message = action_outcome.user_message.replace("<<SKIP_CHAT_END>>", "")
    if action_outcome.instruction_update is not None:
        chat.messages.append(ChatMessage(Role="context", Message=action_outcome.instruction_update.strip()))    
    chat.messages.append(ChatMessage(Role="user", Message=action_outcome.user_message.strip()))
    if await chats_repo.update(chat.id, chat) is True:
        if skip_chat_end is False:
            logger.info(f">> Triggering CHAT_END process for action: {dto.action}. Generating Long memory document...")
            bgtsk.add_task(end_conversation, chat_id, request)
        else:
            logger.info(f"-- Skipping CHAT_END process for action: {dto.action}. Next interaction with this bot will continue with the current conversation --")
    else:
        raise HTTPLoggedException(status_code=500, detail="An error has occured while appending the user acknowledge message to the chat document. Aborting 'end-chat' process...  ")
    
@router.get(
    "/{chat_id}/end-conversation",
    summary="Triggers the ChatEnd process, summarizing the whole conversation to use it as a LongTerm Memory",
    responses={
        200: {"description" : "Succesful response with the summarized chat history"}
    }
)
async def end_conversation(chat_id:str, request:Request):
    print("-- ENDING CONVERSATION --")
    memo_service = MemoMgmtService(get_request_db_name(request))
    memory = await memo_service.update_longmemo(chat_id=chat_id,model_provider=get_llm_provider())
    if memory is None:
        raise HTTPLoggedException(status_code=500, detail="An error has occured while summarizing the conversation")
    return memory

@router.post(
    "/on-llm-settings-update/{chat_id}",
    summary="Modifies some LLM parameters (model, max_tokens & temperature) for the specified ChatPromptDoc and registers the events in the DetailsDoc",
    responses={
        200: {"description" : "Succesful response with the recent chat history"}
    }
)
async def on_llm_settings_update(chat_id:str, dto: UpdateModelSettingsRequest, request:Request):
    print("-- ON LLM SETTINGS UPDATE --", dto)
    repo = ChatPromptsRepository(get_request_db_name(request))
    details_repo = ChatDetailsRepository(get_request_db_name(request))
    doc = ChatPromptDoc.model_validate(await repo.get_by_id(chat_id))
    details = ChatDetailsDoc.model_validate(await details_repo.get(varname="chat_doc_id", value=chat_id))
    should_update_doc: bool = False
    if dto.max_tokens is not None and dto.max_tokens != doc.max_tokens:
        doc.max_tokens = dto.max_tokens
        details.chat_events.append(ChatEvent(
            category=chat_event_cats.to_string(chat_event_cats.llm), 
            chat_turn_id=len(doc.messages), 
            tag=event_tags.llm_update, 
            message=f"MAX_TOKENS - {dto.max_tokens}"))
        should_update_doc = True
    if dto.temperature is not None and dto.temperature != doc.temperature:
        doc.temperature = dto.temperature
        details.chat_events.append(ChatEvent(
            category=chat_event_cats.to_string(chat_event_cats.llm), 
            chat_turn_id=len(doc.messages), 
            tag=event_tags.llm_update, 
            message=f"TEMP - {dto.temperature}"))
        should_update_doc = True
    llm_provider: Ollama_Provider = get_llm_provider()
    if dto.model_name is not None and dto.model_name != doc.model :
        if dto.model_name in llm_provider.available_models():
            doc.model = dto.model_name
            details.chat_events.append(ChatEvent(
                category=chat_event_cats.to_string(chat_event_cats.llm),
                chat_turn_id=len(doc.messages), 
                tag=event_tags.llm_update, 
                message=f"MODEL - {dto.model_name}"))
            should_update_doc = True
    if should_update_doc:
        logger.info("-- updating praise chat LLM settings --")
        await repo.update(doc.id, doc)
        await details_repo.update(details.id, details)

def llm_stream(prompt_request:ChatPromptRequest, username:str = "Player", botname:str = "Non-Player"):
    logger.info("-- ollama praise chat stream req --")
    if prompt_request.system_message and prompt_request.system_message != "":
        prompt_request.chat_history.append({"context": prompt_request.system_message.strip()})
    prompt_request.chat_history.append({"user": prompt_request.message})
    llm_provider: Ollama_Provider = get_llm_provider()
    prompt = llm_provider.chat_history_to_template(chat_history=prompt_request.chat_history, assistant_guidance_token=f"### {botname}:", template_key="praise")
    prompt = prompt.replace("<<USERNAME>>", username)
    prompt = prompt.replace("<<BOTNAME>>", botname)
    #TODO / CHECK: replace prompt keys w/char_names:
    # request.app.model_provider.replace_final_prompt_keys(prompt, { current_key : new_key }) <- provider.templates[template_key]
    logger.warning(f"ON STREAM >> REQ MODEL {prompt_request.model_name}")
    llm = llm_provider.fresh_model_instance(model=prompt_request.model_name, config=Ollama_Config().get_settings_preset("chat"), ctx_len=len(prompt) + ctx_len_offset if len(prompt) <= max_ctx_len else max_ctx_len)
    logger.info(f"-- FINAL PROMPT >> model: {prompt_request.model_name} --")
    print(prompt)
    response = llm.stream(prompt)
    prev_token = ""
    for chunk in response:
        print(chunk)
        pair = prev_token + chunk.content
        if pair in llm_provider.stopping_tokens():
            return
        prev_token = chunk.content
        yield str(chunk.content)

def llm_prompt_stream(llm_provider: LLM_Provider, prompt: str, model:str, temperature: float, max_tokens: int, stopping_tokens: List[str]):
    logger.info("-- ollama praise chat stream req --")
    
    llm = llm_provider.fresh_model_instance(model=model, config=Ollama_Config(temp=temperature, max_tokens=max_tokens), ctx_len=get_ctx_num_for_text(text=prompt))
    logger.info("-- FINAL PROMPT --")
    print(prompt)
    response = llm.stream(prompt)
    prev_token = ""
    for chunk in response:
        print(chunk)
        pair = prev_token + chunk.content
        if pair in stopping_tokens:
            return
        prev_token = chunk.content
        yield str(chunk.content)

"""
OTRAS MOVIDAS DE RECICLE DE DOTNET_GEPETTO


NUNCA IMPLEMETADO (en DotnetGepetto, aqui se estan guardando como SysMsg.type == 8, se puede reciclar) #TODO (para pesonajes conocidos --> v2: si el bot se presenta --> actualizar DB (OutputAction? AgentTool?))
[BsonCollectionHelper("Characters")]
public class Character : Document
{
    public string Name { get; set; }
    public string? Title { get; set; }
    public string ChatContextText { get; set; }

}
"""