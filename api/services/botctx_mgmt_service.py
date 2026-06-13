from random import random
from typing import List

from loguru import logger

from api.infrastructure.models.char_db_schemas import CharacterMoodDoc, CharacterPersonalityDoc, CharacterRoleDoc, CharacterTraitDoc
from api.infrastructure.models.db_schemas import SystemMessageDoc
from api.infrastructure.repositories.mongo.mongo_repos import CharacterMoodsRepository, CharacterPersonalitiesRepository, CharacterRolesRepository, CharacterTraitsRepository, GameCharsRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.models.prompting_schemas import BotInfoDto, ConversationDto
from api.models.schemas import QueryCondition
from api.utils.helpers import HTTPLoggedException
from api.utils.statics import sys_message_types, default_praisebot_actions, praise_db_name, default_db_name

class BotContextMgmtService:

    _charsRepo: GameCharsRepository = None
    _sysRepo: SysMessagesRepository = None
    _rolesRepo: CharacterRolesRepository = None
    _traitsRepo: CharacterTraitsRepository = None
    _personsRepo: CharacterPersonalitiesRepository = None
    _moodsRepo: CharacterMoodsRepository = None
    _currentDB:str = None

    def __init__(self, repos_db: str):
        self._currentDB = repos_db if repos_db is not None and repos_db != "" else default_db_name
        self._charsRepo = GameCharsRepository(self._currentDB)
        self._sysRepo = SysMessagesRepository(self._currentDB)
        self._rolesRepo = CharacterRolesRepository(self._currentDB)
        self._traitsRepo = CharacterTraitsRepository(self._currentDB)
        self._personsRepo = CharacterPersonalitiesRepository(self._currentDB)
        self._moodsRepo = CharacterMoodsRepository(self._currentDB)

    async def get_default_bot_actions(self, char_role:str) -> List[str]:
        role = CharacterRoleDoc.model_validate(await self._rolesRepo.get(varname="name", value=char_role))
        output_actions = role.output_actions
        for action in default_praisebot_actions:
            if action not in output_actions:
                output_actions.append(action)
        return output_actions
    
    async def get_output_actions_text(self, botInfo: BotInfoDto) -> str:
        result = ""
        output_actions = await self.get_default_bot_actions(char_role=botInfo.charRole)
        for action in output_actions:
            print("-- GETTING ACTION --", action)
            doc = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(type=sys_message_types.output_action, tag=action))
            result += f"> {doc.tag}: {doc.message}\n"
        return result
    
    def join_sys_msgs(self, msgs: List[SystemMessageDoc], separator:str=",", substring:int=-1) -> str:
        result = ""
        for msg in msgs:
            result += f"- {SystemMessageDoc.model_validate(msg).message}{separator}"
        return result[:substring]
    
    async def get_formatted_sysmsg_CoTv1(self, dto:ConversationDto, with_char_desc:bool = True) -> str:
    # get base ctx msg
        template_msg = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.base_template, "CoT-v1"))
        chat_constraints = await self._sysRepo.get_many("type", sys_message_types.chat_constraints)
        chat_rules = await self._sysRepo.get_many("type", sys_message_types.chat_rules)
        world_context = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.world_context, "v1"))
        bot_faction = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.faction_context, dto.botInfo.factionName))
        speaker_faction = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.faction_context, dto.speakerInfo.factionName))
        zone_context = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.zone_context, dto.zoneName))
        char_output_actions = await self.get_output_actions_text(dto.botInfo)
        sys_msg = template_msg.message.replace("[[ChatConstraints]]", self.join_sys_msgs(chat_constraints, "\n"))
        sys_msg = sys_msg.replace("[[WorldContext]]", world_context.message)
        sys_msg = sys_msg.replace("[[ChatRules]]", self.join_sys_msgs(chat_rules, "\n"))
        sys_msg = sys_msg.replace("[[OutputActions]]", char_output_actions)
        if with_char_desc:
            sys_msg = sys_msg.replace("[[CharacterDescription]]", await self.get_formatted_character_desc(dto.botInfo))
        sys_msg = sys_msg.replace("[[BotFaction]]", f"{bot_faction.tag}. {bot_faction.message}")
        sys_msg = sys_msg.replace("[[SpeakerFaction]]", f"{speaker_faction.tag}. {speaker_faction.message}")
        #WG: controlar bien los cambios de zona en UE. if empty zoneName = CommonPath
        sys_msg = sys_msg.replace("[[ZoneContext]]", f"{zone_context.tag}. {zone_context.message}")
        return sys_msg
    
    #devuelve el texto base con todas las secciones menos las que se cachean en Details.Memo
    
    async def get_base_instruction_CoTv2(self, dto:ConversationDto, with_char_desc:bool = True) -> dict[str,str]:
        template_msg = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.base_template, "CoT-v2.3"))
        # chat_constraints = await repo.get_many("type", sys_message_types.chat_constraints)
        # chat_rules = await repo.get_many("type", sys_message_types.chat_rules)
        world_context = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.world_context, "v1"))
        bot_faction = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.faction_context, dto.botInfo.factionName))
        speaker_faction = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.faction_context, dto.speakerInfo.factionName))
        if len(dto.zoneName) == 0:
            logger.warning("-- getting zone --")
            zones=await self._sysRepo.get_many(varname="type", value=sys_message_types.zone_context)
            if len(zones) > 0:
                logger.warning("-- getting zone 2--")
                zone = zones[random.randint(0, len(zones)-1)]
                if zone is not None:
                    print(zone)
                    logger.warning("-- getting zone --3")
                    dto.zoneName = SystemMessageDoc.model_validate(zone).tag

        print(dto)
        zone_context = SystemMessageDoc.model_validate(await self._sysRepo.get_by_type_and_tag(sys_message_types.zone_context, dto.zoneName))
        output_actions_text = await self.get_output_actions_text(dto.botInfo)
        profile = await self.get_formatted_character_desc(dto.botInfo) #V2 -> esto es CharacterTemplateDto formateado
        #sys_msg = sys_msg.replace("[[ChatRules]]", self.join_sys_msgs(chat_rules, "\n"))
        sys_msg = template_msg.message.replace("[[CharacterProfile]]", profile)
        sys_msg = sys_msg.replace("[[WorldContext]]", world_context.message)
        sys_msg = sys_msg.replace("[[ZoneContext]]", f"The conversation is taking place in: {zone_context.tag}. {zone_context.message}")
        sys_msg = sys_msg.replace("[[FactionsContext]]", f"Your character belongs to the faction: {bot_faction.tag}. {bot_faction.message.strip()}\n\nThe player's character belongs to the faction: {speaker_faction.tag}. {speaker_faction.message.strip()}")
        print("-- RETURNING SYS MESSAGE COT-V2 --\n", sys_msg)
        return {"BASE": sys_msg, "PROFILE":profile ,"ACTIONS": output_actions_text}
    
    async def get_formatted_character_desc(self, botInfo: BotInfoDto) -> str:
        # v2 --> character = chars_repo.botInfo.character_id
        result = ""
        if botInfo.charName != "":
            result += f"- Character Name: {botInfo.charName}\n"
        #TODO: result += "- Character Description:\n <-- Name y Profile (tipo RandomWorlds)"
        #get role
        if botInfo.charRole == "":
            raise HTTPLoggedException(status_code=400, detail="Character role is needed to begin the conversation")
        role = CharacterRoleDoc.model_validate(await self._rolesRepo.get("name", botInfo.charRole))
        result += f"- Character Role:\n"
        result += f"> {role.name}: {role.sys_msg_text}\n"
        # get personalities
        conditions = []
        if len(botInfo.personalities) > 0 or len(botInfo.traits) > 0:
            result += "- Character Psychology:\n"
        if len(botInfo.personalities) > 0:
            for item in botInfo.personalities:
                conditions=[QueryCondition(field="name", value=item)]
                personalities = await self._personsRepo.query(conditions)
                for record in personalities:
                    doc = CharacterPersonalityDoc.model_validate(record)
                    result += f"> {doc.name}: {doc.sys_msg_text}\n"    
        # get traits
        if len(botInfo.traits) > 0:
            conditions = []
            for trait in botInfo.traits:
                conditions=[QueryCondition(field="name", value=trait)]
            traits = await self._traitsRepo.query(conditions)
            for record in traits:
                doc = CharacterTraitDoc.model_validate(record)
                result += f"> {doc.name}: {doc.sys_msg_text}\n"
        # get mood
        if botInfo.mood != "":
            mood:CharacterMoodDoc = await self.get_mood_doc(mood=botInfo.mood)
            if mood is not None:
                result += f"- Current Mood:\n> {mood.name}: {mood.sys_msg_text}" #Esto se supone que puede cambiar en el transcurso de la conversacion CHECK  / WG
        return result

    async def get_mood_doc(self, mood:str) -> CharacterMoodDoc | None:
        record = await self._moodsRepo.get("name", mood)
        return None if record is None else CharacterMoodDoc.model_validate(record)
    