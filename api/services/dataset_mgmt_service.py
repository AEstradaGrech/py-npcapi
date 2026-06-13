
from typing import List

from api.infrastructure.repositories.mongo.dataset_chats import DatasetChatsRepository
from loguru import logger

from api.models.schemas import ChatReplicaDto, ChatReplicaRequest

class DatasetMgmtService:
    _chatReplicasRepo: DatasetChatsRepository

    def __init__(self, repos_db_name:str = "PraiseDB"):
        self._chatReplicasRepo = DatasetChatsRepository(db_name=repos_db_name)


    async def replicate_chat(self, req: ChatReplicaRequest) -> List[ChatReplicaDto]:
        # get example
        # get traits & stuff
        # change name

        ###.---------------
        # genero para cada accion con ejemplos DataseChat 
        #   conversacion por caso de uso x Profiles
        
        pass