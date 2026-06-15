default_chat_history_length = 10
chat_turns_to_generate_memory = 16
min_chat_turns_for_longterm_summary = 10
default_provider:str = 'ollama'
allowed_llm_providers = ['ollama']
allowed_local_server_providers = ['ollama', 'gpt4all']
chat_summary_template_tag = "<<CHAT>>"
summary_role_tags = {
    "assistant":"NPC",
    "user": "PLAYER",
    "system": "<<CONTEXTUAL>>"
}

default_db_name = "PyNPCsDB"
praise_db_name = "PraiseDB"
max_ctx_len = 10000
ctx_len_offset = 100
class SysMessageType:
    base_template:int = 0
    chat_constraints:int = 1
    world_context:int = 2
    chat_rules:int = 3
    zone_context:int = 4
    faction_context:int = 5
    output_action: int = 6
    summary_template: int = 7
    character: int = 8
    join_party_template: int = 9
    leave_party_template: int = 10
    fight_template: int = 11
    quest_gen_template: int = 12
    stop_talking_template:int = 13
    user_endchat_req_template:int = 14
    chat_replicator:int = 15

    values: dict[int,str] = {
        0 : "BaseTemplate",
        1 : "ChatConstraints",
        2 : "WorldContext",
        3 : "ChatRules",
        4 : "ZoneContext",
        5 : "FactionContext",
        6 : "OutputAction",
        7 : "Summarization",
        8 : "CharacterProfile",
        9 : "JoinGroupTemplate",
        10: "LeavePartyTemplate",
        11: "FightTemplate",
        12: "QuestGeneration",
        13: "StopTalking",
        14: "UserEndReq",
        15: "ChatReplicator"
    }

    def to_string(self, value: int) -> str:
        return self.values.get(value) or ""

sys_message_types: SysMessageType = SysMessageType()

class ChatEventCategory:
    llm:int = 0
    context:int = 1
    user:int = 2
    assistant:int = 3
    observation:int = 4
    remarkable_event: int = 5
    values:dict[int,str] ={
        0 : "llm",
        1 : "context",
        2 : "user",
        3 : "assistant",
        4 : "observation",
        5 : "chat-remarkable-event"
    }
    def to_string(self, value: int) -> str:
        return self.values.get(value) or ""
chat_event_cats: ChatEventCategory = ChatEventCategory()

class CharProfileElementType:
    role:int = 0
    faction:int = 1
    trait:int = 2
    personality:int = 3
    mood: int = 4

    values: dict[int,str] = {
        0 : "role",
        1 : "faction",
        2 : "trait",
        3 : "personality",
        4 : "mood"
    }

    def to_string(self, value: int) -> str:
        return self.values.get(value) or ""
    
char_profile_elem_types: CharProfileElementType = CharProfileElementType()

class GameClass:
    mercenary:int = 4
    merchant:int = 5
    guard:int = 6
    bandit:int = 7
    traveller:int = 8
    values: dict[int,str] = {
        4 : "Mercenary",
        5 : "Merchant",
        6 : "Guard",
        7 : "Bandit",
        8 : "Traveller"
    }

    def to_string(self, value: int) -> str:
        return self.values.get(value) or ""
    
praise_game_classes: GameClass = GameClass()

class ChatEventCategory:
    llm:int = 0
    context:int = 1
    user:int = 2
    assistant:int = 3
    observation:int = 4
    remarkable_event: int = 5
    values:dict[int,str] ={
        0 : "llm",
        1 : "context",
        2 : "user",
        3 : "assistant",
        4 : "observation",
        5 : "chat-remarkable-event"
    }
    def to_string(self, value: int) -> str:
        return self.values.get(value) or ""
chat_event_cats: ChatEventCategory = ChatEventCategory()
"""
enum class ECharClass : uint8
{
	NONE				UMETA(DisplayName = "None"),
	//Player & Bot Game Classes
	CREATURE_HUNTER		UMETA(DisplayName = "Creature Hunter"),
	ACOLYT				UMETA(DisplayName = "Acolyt"),
	COLLECTOR			UMETA(DisplayName = "Collector"),
	MERCENARY			UMETA(DisplayName = "Mercenary"),
	//Bot-Only Game Classes (CharRoles)
	MERCHANT			UMETA(DisplayName = "Merchant"),
	GUARD			    UMETA(DisplayName = "Guard"),
	BANDIT				UMETA(DisplayName = "Bandit"),
	TRAVELLER			UMETA(DisplayName = "Traveller")
};
"""
class ChatEventTags:
    zone_ctx:str = "[zone-context-update]"
    user_ctx:str = "[user_context_update]"
    assistant_ctx:str = "[assistant-context-update]"
    assistant_memo:str = "[assistant-memory-update]"
    output_action:str = "[output-action-result]"
    chat_sentiment:str = "[sentiment-analysis-update]"
    llm_update:str = "[llm-settings-update]"

event_tags:ChatEventTags = ChatEventTags()


class CharProfileElementType:
    role:int = 0
    faction:int = 1
    trait:int = 2
    personality:int = 3
    mood: int = 4

    values: dict[int,str] = {
        0 : "role",
        1 : "faction",
        2 : "trait",
        3 : "personality",
        4 : "mood"
    }

    def to_string(self, value: int) -> str:
        return self.values.get(value) or ""
    
char_profile_elem_types: CharProfileElementType = CharProfileElementType()

default_praisebot_actions = ["KEEP_TALKING","STOP_TALKING"]

chat_moods = ["HOSTILE", "UNFRIENDLY", "NEUTRAL", "FRIENDLY", "BELOVED"]

personality_mood_weight = 0.6
chat_sentiment_weight = 0.4
current_mood_inertia = 0.2
dominant_personality_weight = 0.7

personality_moods_map = {
    "Shy" : { "Relaxed": 0.5, "Bitter": 0.3, "Lively": 0.1, "Irritated": 0.2, "Melancholic": 0.4, "Cheerful": 0.0, "Tense": 0.3 },
    "Irascible" : {"Relaxed": 0.3, "Bitter": 0.2, "Lively": 0.3, "Irritated": 0.5, "Melancholic": 0, "Cheerful": 0.1, "Tense": 0.4 },
    "Sensible" : {"Relaxed": 0.5, "Bitter": 0.3, "Lively": 0.2, "Irritated": 0.3, "Melancholic": 0.3, "Cheerful": 0.3, "Tense": 0.3 },
    "Impulsive" : {"Relaxed": 0.4, "Bitter": 0.1, "Lively": 0.5, "Irritated": 0.3, "Melancholic": 0.1, "Cheerful": 0.4, "Tense": 0.4 },
    "Reckless" : {"Relaxed": 0.5, "Bitter": 0.2, "Lively": 0.5, "Irritated": 0.2, "Melancholic": 0, "Cheerful": 0.3, "Tense": 0.4 },
    "Reflective" : {"Relaxed": 0.5, "Bitter": 0.4, "Lively": 0.1, "Irritated": 0.2, "Melancholic": 0.4, "Cheerful": 0.3, "Tense": 0.3 },
    "Extroverted" : {"Relaxed": 0.5, "Bitter": 0.1, "Lively": 0.4, "Irritated": 0.1, "Melancholic": 0.2, "Cheerful": 0.5, "Tense": 0.2 }
}


chat_mood_transitions = {
    "NEUTRAL":{
        "Shy" : { "Relaxed": 0.2, "Bitter": 0.2, "Lively": 0.0, "Irritated": 0.0, "Melancholic": 0.2, "Cheerful": 0.0, "Tense": 0.1 },
        "Irascible" : {"Relaxed": 0.2, "Bitter": 0.1, "Lively": 0.1, "Irritated": 0.2, "Melancholic": 0, "Cheerful": 0.0, "Tense": 0.2 },
        "Sensible" : {"Relaxed": 0.2, "Bitter": 0.1, "Lively": 0.0, "Irritated": 0.1, "Melancholic": 0.1, "Cheerful": 0.1, "Tense": 0.2 },
        "Impulsive" : {"Relaxed": 0.2, "Bitter": 0.1, "Lively": 0.3, "Irritated": 0.1, "Melancholic": 0.1, "Cheerful": 0.2, "Tense": 0.3 },
        "Reckless" : {"Relaxed": 0.2, "Bitter": 0.1, "Lively": 0.2, "Irritated": 0.1, "Melancholic": 0.1, "Cheerful": 0.1, "Tense": 0.2 },
        "Reflective" : {"Relaxed": 0.2, "Bitter": 0.2, "Lively": 0.0, "Irritated": 0.1, "Melancholic": 0.2, "Cheerful": 0.1, "Tense": 0.2 },
        "Extroverted" : {"Relaxed": 0.3, "Bitter": 0.1, "Lively": 0.3, "Irritated": 0.1, "Melancholic": 0.2, "Cheerful": 0.3, "Tense": 0.1 }
    },
    "HOSTILE":{
        "Shy" : { "Relaxed": 0.0, "Bitter": 0.4, "Lively": 0.1, "Irritated": 0.4, "Melancholic": 0.2, "Cheerful": 0.0, "Tense": 0.4 },
        "Irascible" : {"Relaxed": 0.0, "Bitter": 0.2, "Lively": 0.4, "Irritated": 0.6, "Melancholic": 0, "Cheerful": 0.0, "Tense": 0.5 },
        "Sensible" : {"Relaxed": 0.0, "Bitter": 0.4, "Lively": 0.2, "Irritated": 0.5, "Melancholic": 0.1, "Cheerful": 0.0, "Tense": 0.4 },
        "Impulsive" : {"Relaxed": 0.0, "Bitter": 0.2, "Lively": 0.6, "Irritated": 0.6, "Melancholic": 0.0, "Cheerful": 0.0, "Tense": 0.5 },
        "Reckless" : {"Relaxed": 0.0, "Bitter": 0.2, "Lively": 0.5, "Irritated": 0.7, "Melancholic": 0, "Cheerful": 0.0, "Tense": 0.6 },
        "Reflective" : {"Relaxed": 0.0, "Bitter": 0.4, "Lively": 0.1, "Irritated": 0.2, "Melancholic": 0.4, "Cheerful": 0.3, "Tense": 0.3 },
        "Extroverted" : {"Relaxed": 0.0, "Bitter": 0.2, "Lively": 0.6, "Irritated": 0.6, "Melancholic": 0.2, "Cheerful": 0.0, "Tense": 0.4 }
    },
    "FRIENDLY":{
        "Shy" : { "Relaxed": 0.3, "Bitter": 0.0, "Lively": 0.2, "Irritated": 0.0, "Melancholic": 0.2, "Cheerful": 0.3, "Tense": 0.1 },
        "Irascible" : {"Relaxed": 0.3, "Bitter": 0.1, "Lively": 0.3, "Irritated": 0.1, "Melancholic": 0, "Cheerful": 0.2, "Tense": 0.3 },
        "Sensible" : {"Relaxed": 0.3, "Bitter": 0.0, "Lively": 0.3, "Irritated": 0.1, "Melancholic": 0.2, "Cheerful": 0.4, "Tense": 0.2 },
        "Impulsive" : {"Relaxed": 0.3, "Bitter": 0.1, "Lively": 0.6, "Irritated": 0.2, "Melancholic": 0.1, "Cheerful": 0.5, "Tense": 0.3 },
        "Reckless" : {"Relaxed": 0.5, "Bitter": 0.2, "Lively": 0.5, "Irritated": 0.2, "Melancholic": 0, "Cheerful": 0.3, "Tense": 0.4 },
        "Reflective" : {"Relaxed": 0.5, "Bitter": 0.3, "Lively": 0.0, "Irritated": 0.1, "Melancholic": 0.2, "Cheerful": 0.4, "Tense": 0.2 },
        "Extroverted" : {"Relaxed": 0.5, "Bitter": 0.1, "Lively": 0.5, "Irritated": 0.0, "Melancholic": 0.1, "Cheerful": 0.7, "Tense": 0.2 }
    }
}