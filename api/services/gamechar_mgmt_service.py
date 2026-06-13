
from random import random
from typing import List

from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger

from api.infrastructure.llm.llm_provider import LLM_Provider
from api.infrastructure.models.char_db_schemas import CharacterPersonalityDoc, CharacterRoleDoc, CharacterTraitDoc
from api.infrastructure.models.db_schemas import SystemMessageDoc
from api.infrastructure.repositories.mongo.chat_prompts import GameCharDoc
from api.infrastructure.repositories.mongo.mongo_repos import CharacterPersonalitiesRepository, CharacterRolesRepository, CharacterTraitsRepository, GameCharsRepository
from api.infrastructure.repositories.mongo.sysmsgs_repo import SysMessagesRepository
from api.models.character_schemas import CharProfileElementDto, CharacterTemplateDto, FullPraiseCharDto
from api.models.prompting_schemas import GenerateCharacterRequest
from api.utils.helpers import HTTPLoggedException
from api.utils.statics import default_db_name, praise_db_name, sys_message_types, char_profile_elem_types

class CharactersMgmtService:
    _charsRepo: GameCharsRepository = None
    _sysRepo: SysMessagesRepository = None
    _rolesRepo: CharacterRolesRepository = None
    _traitsRepo: CharacterTraitsRepository = None
    _personsRepo: CharacterPersonalitiesRepository = None
    _currentDB:str = None

    def __init__(self, repos_db: str):
        self._currentDB = repos_db if repos_db is not None and repos_db != "" else default_db_name
        self._charsRepo = GameCharsRepository(self._currentDB)
        self._sysRepo = SysMessagesRepository(self._currentDB)
        self._rolesRepo = CharacterRolesRepository(self._currentDB)
        self._traitsRepo = CharacterTraitsRepository(self._currentDB)
        self._personsRepo = CharacterPersonalitiesRepository(self._currentDB)

    async def get_random_game_faction(self) -> SystemMessageDoc:
        logger.warning("-- GETTING ALL FACTIONS TO SELECT --")
        factions = await self._sysRepo.get_many(varname="type", value=sys_message_types.faction_context)
        factions =  [faction for faction in factions if SystemMessageDoc.model_validate(faction).tag != "FactionRelationships" and SystemMessageDoc.model_validate(faction).tag != "Creatures"]
        rnd_idx: int = random.randint(0, len(factions) - 1)
        return SystemMessageDoc.model_validate(factions[rnd_idx]) if len(factions) > 0 else None
    
    async def get_random_game_role(self) -> CharacterRoleDoc:
        
        roles = await self._rolesRepo.stringy_query({})
        logger.warning("-- ON ROLES QUERY --")
        return CharacterRoleDoc.model_validate(roles[random.randint(0, len(roles) -1)]) if len(roles) > 0 else None

    async def get_random_traits(self, results: int = 1) -> List[CharacterTraitDoc]:
        
        traits = await self._traitsRepo.stringy_query({})
        if len(traits) == 0:
            return []
        rnd_trait = CharacterTraitDoc.model_validate(traits[random.randint(0, len(traits) - 1)])
        traits = [trait for trait in traits if CharacterTraitDoc.model_validate(trait).name != rnd_trait.name]
        selected_traits = [CharacterTraitDoc.model_validate(rnd_trait)]
        if results > 1:
            compatible_traits = self.select_random_compatible_trait(rnd_trait, traits, [], results= results -1)
            if len(compatible_traits) > 0:
                for comp_trait in compatible_traits:
                    selected_traits.append(comp_trait)
                return selected_traits
        else:
            return selected_traits

    def select_random_compatible_trait(self, trait: CharacterTraitDoc, available: List[CharacterTraitDoc], selected: List[CharacterTraitDoc], results: int) -> List[CharacterTraitDoc]:
        trait_doc = CharacterTraitDoc.model_validate(trait)
        if len(available) == 0:
            return selected
        rnd = CharacterTraitDoc.model_validate(available[random.randint(0, len(available) -1)])
        available = [item for item in available if item != rnd]
        if rnd.name not in trait_doc.exclusions and rnd.name not in selected:
            selected.append(rnd)
        if len(selected) == results:
            return selected
        return self.select_random_compatible_trait(trait, available, selected, results)
    
    async def get_random_personalities(self, results: int = 1) -> List[CharacterPersonalityDoc]:
        
        persons = await self._personsRepo.stringy_query({})
        if len(persons) == 0:
            return []
        logger.warning(">> selecting random personalities --")
        rnd_person = CharacterPersonalityDoc.model_validate(persons[random.randint(0, len(persons) - 1)])
        persons = [person for person in persons if CharacterPersonalityDoc.model_validate(person).name != rnd_person.name]
        selected_persons = [CharacterPersonalityDoc.model_validate(rnd_person)]
        if results > 1:
            logger.warning(f">> selecting extra persons >> total: {results}")
            compatible_persons = self.select_random_compatible_person(rnd_person, persons, [], results= results -1)
            if len(compatible_persons) > 0:
                for comp_person in compatible_persons:
                    selected_persons.append(comp_person)
                return selected_persons
        else:
            return selected_persons
        
    def select_random_compatible_person(self, trait: CharacterPersonalityDoc, available: List[CharacterPersonalityDoc], selected: List[CharacterPersonalityDoc], results: int) -> List[CharacterPersonalityDoc]:
        print(type(trait))
        trait_doc = CharacterPersonalityDoc.model_validate(trait)
        if len(available) == 0:
            return selected
        rnd = CharacterPersonalityDoc.model_validate(available[random.randint(0, len(available) -1)])
        available = [item for item in available if item != rnd]
        if rnd.name not in trait_doc.exclusions and rnd.name not in selected:
            selected.append(rnd)
        if len(selected) == results:
            return selected
        return self.select_random_compatible_person(trait, available, selected, results)
    
    async def generate_character(self, base_params: GenerateCharacterRequest, llm_provider: LLM_Provider) -> GameCharDoc:
        if base_params.charName is not None and base_params.charName == "Unknown":
            base_params.charName = None
        if base_params.charName is not None and len(base_params.charName) == 0:
            base_params.charName = None
        if base_params.charAge is not None and len(base_params.charAge) == 0:
            base_params.charAge = None
        if base_params.charRole is not None and len(base_params.charRole) == 0:
            base_params.charRole = None # svc.GetRandomGameRole
        if base_params.factionName is not None and len(base_params.factionName) == 0:
            base_params.factionName = None # svt GetRandomFaction
        repo = SysMessagesRepository(praise_db_name)
        record = await repo.get_by_type_and_tag(type=0, tag="profile-creator-v1.1")
        if record is None:
            raise HTTPLoggedException(status_code=500, detail="-- No SYSTEM MESSAGE template has been found for Praise Character Creator --")
        char_sysmsg = SystemMessageDoc.model_validate(record)
        instruction = char_sysmsg.message
        logger.warning("-- BASE CHAR CREATOR MESSAGE OK --")
        print(base_params)
        # get sysMsg CHAR_CREATOR
        
        praise_character: GameCharDoc = GameCharDoc(
            name="", 
            age="", 
            faction="", 
            role="", 
            traits=[],
            personalities=[], 
            goal = "",
            background_story="", 
            typical_routines="", 
            motivations="")
        
        template_constraints = ""
        
        # 29/05/26 --> esto lo paso como orden si no esta vacio y si no que lo añada LLM
        user_prefs:str = None
        if base_params.actualContext is not None and base_params.actualContext.strip()  != "": 
            template_constraints = f"### USER_PREFERENCES:\n{base_params.actualContext}"

        template_constraints = template_constraints + f"\n- NAME: {base_params.charName if base_params.charName is not None else ""}"
        template_constraints = template_constraints + f"\n- AGE: {base_params.charAge if base_params.charAge is not None else ""}"


        if base_params.factionName is not None:
            logger.warning(f"-- getting user selected faction: {base_params.factionName} --")
            faction_msg = await repo.get_by_type_and_tag(sys_message_types.faction_context, tag=base_params.factionName)
            if faction_msg is not None:
                faction_doc = SystemMessageDoc.model_validate(faction_msg)
                praise_character.faction = faction_doc.tag
                template_constraints = template_constraints + f"\n- FACTION: {faction_doc.tag}\n\n{faction_doc.message}"
        else:
            logger.warning(">> GETTING RANDOM FACTION")
            faction_doc = await self.get_random_game_faction()
            if faction_doc is not None:
                logger.warning(">> ON RANDOM FACTION")
                print(faction_doc)
                praise_character.faction = faction_doc.tag
                template_constraints = template_constraints + f"\n- FACTION: {faction_doc.tag}\n\n{faction_doc.message}"
            
        if base_params.charRole is not None:
            logger.warning(f"-- GETTING USER SELECTED ROLE: {base_params.charRole} --")
            roles_repo = CharacterRolesRepository(praise_db_name)
            role_msg = await roles_repo.get(varname="name", value=base_params.charRole)
            if role_msg is not None:
                role_doc = CharacterRoleDoc.model_validate(role_msg)
                praise_character.role = role_doc.name
                template_constraints = template_constraints + f"\n\n- ROLE: {role_doc.name} >> {role_doc.description}"
        else:
            logger.warning(">> GETTING RANDOM ROLE")
            role_doc = await self.get_random_game_role()
            if role_doc is not None:
                logger.warning(">> ON RANDOM ROLE")
                print(role_doc)
                praise_character.role = role_doc.name
                template_constraints = template_constraints + f"\n\n- ROLE: {role_doc.name} >> {role_doc.description}"
        
        if len(base_params.traits) > 0:
            logger.warning("-- GETTING USER SELECTED TRAITS --")
            traits_repo = CharacterTraitsRepository(praise_db_name)
            template_constraints = template_constraints + "\n\n- TRAITS:"
            for trait_tag in base_params.traits:
                trait_msg = await traits_repo.get(varname="name", value=trait_tag)
                if trait_msg is not None:
                    trait_doc = CharacterTraitDoc.model_validate(trait_msg)
                    praise_character.traits.append(trait_doc.name)
                    template_constraints += f"\n\n> {trait_doc.name}\n\n{trait_doc.description}"
        else:
            logger.warning(">> GETTING RANDOM TRAITS")
            traits = await self.get_random_traits(random.randint(0, 3))
            if len(traits) > 0:
                logger.warning(">> ON RANDOM TRAITS")
                print(traits)
                template_constraints = template_constraints + "\n\n- TRAITS:"
                for trait in traits:
                    praise_character.traits.append(trait.name)
                    template_constraints += f"\n\n> {trait.name}\n\n{trait.description}"

        if len(base_params.personalities) > 0:
            logger.warning("-- GETTING USER SELECTED PERSONALITIES --")
            persons_repo = CharacterPersonalitiesRepository(praise_db_name)
            template_constraints = template_constraints + "\n\n- PERSONALITY:"
            for pers_tag in base_params.personalities:
                pers_msg = await persons_repo.get(varname="name", value=pers_tag)
                if pers_msg is not None:
                    pers_doc = CharacterPersonalityDoc.model_validate(pers_msg)
                    praise_character.personalities.append(pers_doc.name)
                    template_constraints += f"\n\n> {pers_doc.name}\n\n{pers_doc.sys_msg_text}"
        else:
            logger.warning(">> GETTING RANDOM PERSONALITIES")
            persons = await self.get_random_personalities(random.randint(1, 2))
            if len(persons) > 0:
                logger.warning(">> RANDOM PERSONS")
                print(persons)
                template_constraints = template_constraints + "\n\n- PERSONALITY:"
                for person in persons:
                    praise_character.personalities.append(person.name)
                    template_constraints += f"\n\n> {person.name}\n\n{person.sys_msg_text}"

        logger.warning("-- ON TEMPLATE CONSTRAINTS FORMATTED --")
        print(template_constraints)
        instruction = instruction.replace("<<CHARACTER_TEMPLATE>>", template_constraints).replace("<<GAME_CONTEXT>>", "")
        logger.warning(f">> LEN OF TEMPLATE --> {len(instruction)}")
        parser = PydanticOutputParser(pydantic_object=CharacterTemplateDto)
        parser_instruction = parser.get_format_instructions()
        logger.warning("-- ON PARSER INSTRUCTION --")
        print(parser_instruction)
        logger.warning(f">> LEN OF PARSER INSTRUCTION --> {len(parser_instruction)}")
        logger.warning(f">> TOTAL LEN OF MESSAGE --> {len(instruction) + len(parser_instruction)}")
        logger.warning(">> FINAL LLM INSTRUCTION")
        print(f"{instruction}\n\n{parser_instruction}")
        for i in range(0,3):
            try:
                llm = llm_provider.current_integration().fresh_model_instance(model="hermes3", temperature=1.0, max_tokens=600, ctx_len=len(instruction) + len(parser_instruction) + 200)
                llm_response = llm.invoke(f"{instruction}\n\n{parser_instruction}")
                char_profile = parser.invoke(llm_response)
                logger.warning(">> ON LLM RESPONSE PARSED")
                print(char_profile)
                break
            except Exception as e:
                logger.warning(f" ERROR WHILE GENERATING CHAR >> e: {e}")

        praise_character.name = char_profile.name
        praise_character.age = char_profile.age
        praise_character.background_story = char_profile.background_story
        praise_character.typical_routines = char_profile.typical_routines
        praise_character.motivations = char_profile.motivations
        praise_character.goal = char_profile.goal
        return praise_character
    
    async def get_world_context(self) -> str:
        from langchain_core.output_parsers import PydanticOutputParser
        
        result:str = ""
        world_ctx = await self._sysRepo.get(varname="type", value=sys_message_types.world_context)
        if world_ctx is None:
            raise HTTPLoggedException(status_code=500, detail="No WORLD CONTEXT system message found")
        world_doc = SystemMessageDoc.model_validate(world_ctx)
        result = result + f">> WORLD CONTEXT: {world_doc.message.strip()}"
        #factions = await repo.get_many(varname="type", value=sys_message_types.faction_context)
        # if len(factions) > 0:
        #     result = result + "\n\n>> FACTIONS:\n"
        #     for faction in factions:
        #         faction_doc = SystemMessageDoc.model_validate(faction)
        #         if faction != "FactionRelationships":
        #             result = result + f"\n- {faction_doc.tag}: {faction_doc.message.strip()}"
        zones = await self._sysRepo.get_many(varname="type", value=sys_message_types.zone_context)
        if len(zones) > 0:
            result += f"\n\n>> GAME WORLD LOCATIONS:\n"
            for zone in zones:
                zone_doc = SystemMessageDoc.model_validate(zone)
                result += f"\n- {zone_doc.tag}: {zone_doc.message.strip()}"
        #roles_repo = CharacterRolesRepository(praise_db_name)
        #roles = await roles_repo.stringy_query({})
        # if len(roles) > 0:
        #     result = result + f"\n\n>> GAME ROLES:\n"
        #     for role in roles:
        #         role_doc = CharacterRoleDoc.model_validate(role)
        #         result = result + f"\n- {role_doc.name}: {role_doc.description.strip()}"
        return result
    async def save_game_character(self, character: GameCharDoc) -> GameCharDoc:
        
        # 12/04/26 --> de momento no puede haber dos notas con el mismo nombre en ningun sitio (y menos con el mismo nickname)
        # 31/05/26 --> de momento si (TODO: char_creator.is_named_character y/n TODO: onInit->impersonal->then_introduce_char = named character))
        # if len(await repo.get(varname="name", value=character.name)) > 0:
        #     raise HTTPLoggedException(status_code=400, detail="-- A Character with the same NAME already exists in the game --")
        try:
            return await self._charsRepo.create(character)
        except Exception as e:
            raise HTTPLoggedException(status_code=500, detail=f"-- An error has occured while saving the character: {character.name} --")

    async def get_full_profile(self, name:str) -> FullPraiseCharDto:
        profile: GameCharDoc = GameCharDoc.model_validate(await self._charsRepo.get(varname="name", value=name))
        if profile is None:
            raise HTTPLoggedException(status_code=400, detail=f"-- No character has been found with name: {name} --")
        role_desc: CharProfileElementDto = self.get_profile_element(type=char_profile_elem_types.role, name=profile.role)
        if role_desc is None:
            raise HTTPLoggedException(status_code=500, detail=f"-- No ROLE: {profile.role} has been found for character: {profile.name} --")
        faction_desc: CharProfileElementDto = self.get_profile_element(type=char_profile_elem_types.faction, name=profile.faction)
        if faction_desc is None:
            raise HTTPLoggedException(status_code=500, detail=f"-- No FACTION: {profile.faction} has been found for character: {profile.name} --")
        traits = List[CharProfileElementDto] = []
        for trait in profile.traits:
            trait_desc: CharProfileElementDto = self.get_profile_element(type=char_profile_elem_types.trait, name=trait)
            if trait_desc is None:
                raise HTTPLoggedException(status_code=500, detail=f"-- No TRAIT: {trait} has been found for character: {profile.name} --")
            traits.append(trait_desc)
        personalities: List[CharProfileElementDto] = []
        for personality in profile.personalities:
            pers_desc: CharProfileElementDto = self.get_profile_element(type=char_profile_elem_types.personality, name=personality)
            if trait_desc is None:
                raise HTTPLoggedException(status_code=500, detail=f"-- No PERSONALITY: {personality} has been found for character: {profile.name} --")
            personalities.append(pers_desc)
        return FullPraiseCharDto(
            id=profile.id,
            name=profile.name,
            age=profile.age,
            role=role_desc,
            faction=faction_desc,
            traits=traits,
            personalities=personalities,
            profile=profile.personal_profile,
            goal=profile.goal
        )
    
    async def get_profile_element(self, type:int, name:str) -> CharProfileElementDto:
        match type:
            case char_profile_elem_types.role:
                pass
            case char_profile_elem_types.faction:
                pass
            case char_profile_elem_types.trait:
                pass
            case char_profile_elem_types.personality:
                pass
            case char_profile_elem_types.mood:
                pass
            
        return None
    
    async def get_character(self, id:str) -> GameCharDoc:
        repo = GameCharsRepository(praise_db_name)
        record = await repo.get_by_id(id)
        if record is None:
            raise HTTPLoggedException(status_code=404, detail=f"No CHARACTER has been found with id: {id}")
        return GameCharDoc.model_validate(record)