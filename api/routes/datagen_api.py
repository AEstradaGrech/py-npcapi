from fastapi import APIRouter
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from api.models.schemas import ChatReplicaRequest
from loguru import logger

router = APIRouter(prefix="/data-generator")

@router.post(
    "/generate-chat",
    summary="Generates a chat replica for a given action tag",
    responses={
        200: {"description" : "The structured output model for the chat generator"}
    }
)
async def generate_chat(request: ChatReplicaRequest):
    sysmsg = f"""
    You are an auto-chatbot agent. Your task is to simulate conversations between a game NPC and a player according to your provided instructions.
    To do that you MUST follow this rules:
        - Use the 'generate_character' tool to generate a NPC character with a personality.
        - Use the 'chat_prompt' tool to passing the actor role to generate the next chat turn for the NPC or for the player.
        - Generate the specified number of TOTAL_CHAT_TURNS. 

    ### INSTRUCTIONS:
    
    {request.system_message}
    """
    model = ChatOllama(model=request.model_name, temperature=request.temperature)
    memoria_persistente = MemorySaver()
    agent = create_agent(
        model=model,
        tools=[generate_character, chat_prompt], 
        checkpointer=memoria_persistente,
        system_prompt=sysmsg
    )
    result = await agent.ainvoke(request.message)
    logger.warning("-- ON GENERATED CHAT --")
    print(result)
    return result

@tool()
async def generate_character() -> str:
    #svc.generate_character()
    # save_character
    # return f"{char_id} -ROLE: NPC {char_name}"
    return "WIP"

@tool()
async def chat_prompt(role:str, id:str) -> str:
    return "WIP"