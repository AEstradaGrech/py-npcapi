from bson import ObjectId
from fastapi import APIRouter, HTTPException
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
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
    memoria_persistente = MemorySaver()
    agent = create_agent(
        model=model,
        tools=[], # Aquí añadirás tus Pydantic Tools para Unreal Engine
        checkpointer=memoria_persistente,
        system_prompt=request.system_message
    )

    try:
        # Configuramos el hilo de memoria usando el ID único del NPC
        config = {"configurable": {"thread_id": ObjectId()}}
        
        # LLAMADA ASÍNCRONA (.ainvoke con await)
        # Esto evita que Ollama bloquee las peticiones de otros NPCs
        resultado = await agent.ainvoke(
            {"messages": [("user", request.message)]}, 
            config=config
        )
        
        # Extraemos el último mensaje generado por el agente
        respuesta_final = resultado["messages"][-1].content
        
        return {
            "status": "success",
            "npc_response": respuesta_final
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class OutputAction:
    action:str = Field(description="")    
    user_input: str = Field(description="")

# @tool(tool_args=OutputAction)
# def select_output_action(user_input:str, action:str) -> str:
#     """
    
#     """
#     return "WIP"
    ##return llm.ainvoke("select action from list for input {user_input}")