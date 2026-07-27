from bson import ObjectId
from fastapi import APIRouter, HTTPException
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver, MemorySaver
from langchain.agents import create_agent
from pydantic import Field

from api.models.prompting_schemas import PromptRequest


router = APIRouter(prefix="/agent")

@router.post(
    "/test",
    summary="Creates a react agent with langchain",
    responses={
        200: {"description" : "Succesful response that may trigger a LONGMEMO generation process on the background"}
    }
)
async def dev_create_agent(request: PromptRequest):
    model = ChatOllama(model=request.model_name, temperature=request.temperature)
    # get_llm() w/ settings (ChatAgent o yo que se)
    agent = create_agent(
        model=model,
        system_prompt=request.system_message, # repo base template sin el tema de las actions + ### OUTPUT ACTION SUGGESTION: NONE | Analysis TAG + reason (incluye grado de prioridad SHOULD | MUST)
        tools=[], # ChatTool & OutputActionTool
        checkpointer=InMemorySaver()
    )

    try:
        # Configuramos el hilo de memoria usando el ID único del NPC
        config = {"configurable": {"thread_id": ObjectId()}}
        
        # LLAMADA ASÍNCRONA (.ainvoke con await)
        # Esto evita que Ollama bloquee las peticiones de otros NPCs
        resultado = await agent.ainvoke(
            {"messages": [("user", request.message)]}, # DB history
            config=config
        )
        #stream
        # Extraemos el último mensaje generado por el agente
        respuesta_final = resultado["messages"][-1].content
        
        return {
            "status": "success",
            "npc_response": respuesta_final
        }
        # TODO ASYNC FASTAPI STREAM
        # for chunk in await agent.astream(
        #     {"messages": [("user", request.message)]}, # DB history
        #     config=config,
        #     stream_mode="messages",
        #     version="v2"
        # ):
        #     if chunk["type"] == "messages":
        #         token, metadata = chunk["data"]
        #         print(f"node: {metadata['langgraph_node']}")
        #         print(f"content: {token.content_blocks}")
        #         print("\n") 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#init_conversation(Conversation)
#   hace lo mismo que ahora pero genera agent
#handle_conversation(ConversationDto)
#  retrieve chat history
#  
# SOLO HACE FALTA UNA TOOL QUE SE USA SI 'SUGGESTED_ACTION != NONE'
# ASI NO SE PUEDE HACER STREAM
# @tool()
# def select_output_action(chat_id: str, user_input:str, action:str) -> str:
#     """
    
#     """
#     Toda la logica de handle output action
    ##return llm.ainvoke("select action from list for input {user_input}")