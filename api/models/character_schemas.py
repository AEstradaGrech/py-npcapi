from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


# TODO: Generic 'CharacterDto' (sin referencias a lore especifico)
class PraiseCharacterDto(BaseModel):
    """
    Core character identity and psychological profile for NPC dialogue generation.
    
    This schema captures the essential traits, personality facets, and demographic info
    needed for LLMs to generate in-character dialogue, behavioral responses, and consistent
    interaction patterns. Used for comprehensive characterization.
    
    Output requirements:
    - All traits, personalities, and role must be consistent with each other
    - Traits (3-5) should be concrete, observable characteristics
    - Personalities (3-5) should represent emotional/psychological archetypes
    """
    id:str = Field(description="DB identifier for the character", default_factory=lambda: str(ObjectId()))
    name:str = Field(description="Character name.Optionally with nickname")
    age: str = Field(description="Age of the character in numeric format or an approximation (example: 'mid-thirties' or 'around forty years')"),
    role: str = Field(
        description="Character's primary function in game world (2-5 words, max 50 chars). "
                   "Examples: 'Town Guard Captain', 'Hedge Witch', 'Merchant Guild Master', 'Wandering Bard'. "
                   "This determines available interactions, dialogue tone, and behavioral constraints.",
        default=None
    )
    faction: str = Field(
        description="Name of the Character's game faction or guild if any (it can be 'None' for unaligned character)." 
                    "Examples: 'BotVille', 'WipTown', 'Outlaws', 'Territorial Guard' or 'None'" 
                    "Factions can be enemies, allies or indiferent. The selected faction determines the mood and attitude of character towards the other.",
        default=None)
    traits: list[str] = Field(
        description="List of 3-5 observable character traits/quirks. These are concrete, behavioral characteristics "
                   "that manifest consistently in interactions. Format: Short adjectives or brief descriptions (2-4 words each). "
                   "Examples: ['Sharp-tongued', 'Always fidgets with coin', 'Observant gaze', 'Speaks in riddles', 'Impeccably dressed']. "
                   "Traits should inform dialogue patterns and NPC reactions.",
        default=[]
    )
    personalities: list[str] = Field(
        description="List of 3-5 psychological/emotional personality archetypes or traits. These define emotional response patterns, "
                   "conflict tendencies, and motivational drivers. Format: Psychological descriptors (2-4 words each). "
                   "Examples: ['Cautiously optimistic', 'Quick to anger but remorseful', 'Protective of allies', 'Secretly insecure', "
                   "'Naturally charismatic']. These determine how the character reacts emotionally to game events and dialogue.",
        default=[]
    )
    backgroundStory: str = Field(description="Historical context and origin story (100-200 words). Include key life events that shaped the character.")
    typicalRoutines: str = Field(description="Day-to-day activities and habits  Includes professional duties, personal habits, social interactions, and pastimes.")
    motivations: str = Field(description="Core driving forces and desires. Includes ideological (beliefs), professional (career goals), personal (relationships), and psychological (internal needs) motivations.")
    goal: Optional[str] = Field(description="Current character goal in life (if any). It might generate (or help to generate) a game QUEST event depending on it's relationship with the player")

class CharProfileElementDto(BaseModel):
    name: str = Field(description="Title or name of the element (maps from sysmsg doc 'tag')")
    description: str = Field(description="Text description of the element. Maps to sysmsg doc 'message'")

# To generate characters with structured output
class CharacterTemplateDto(BaseModel):
    """
    Comprehensive character development template for RPG/game narrative generation.
    
    This schema defines the deep narrative elements of a character that establish their motivations,
    daily life, and long-term goals. Used by LLMs to generate contextual dialogue, quest hooks,
    and behavioral patterns consistent with the character's established background.
    
    Output requirements:
    - All content must be written in third person, presenting the character not role-playing it
    - In case the user specifies a name and / or an age for the character, USE them. Otherwise the character can be an individual (with First Name and Last Name) or impersonal characters.
    - All fields must be internally consistent and mutually reinforcing
    - Goals must be achievable within a game narrative context
    - Routines should reflect the character's role and personality
    - Ensure no contradictions between background_story and motivations
    """
    name: str = Field(
    description="Character display name with optional nickname in parentheses (max 50 chars). "
                   "Format: 'FirstName LastName' or 'FirstName \"Nickname\" LastName'. "
                   "Must be unique within game context. "
                   "Example: 'Elara \"The Silent\" Darkwood' or 'Brother Thomas'"
    )
    age: str = Field(
        description="Character age as numeric value or age range descriptor (max 30 chars). "
                   "Format: Specific number ('32 years old', '45'), approximate range ('mid-thirties', 'early twenties'), "
                   "or relative term ('ancient', 'youthful'). This informs voice, experience level, and worldview. "
                   "Example: '47 years old' or 'appears to be in their late forties'"
    )
    background_story: str = Field(
        description="Historical context and origin story (100-200 words). Include key life events that shaped the character. "
                   "Format: narrative prose describing formative experiences, family background, or significant past events. "
                   "Example: 'Born a merchant's daughter in a trade city, witnessed her father's business collapse due to corruption, "
                   "now seeks to expose fraudulent practices.' Avoid vague statements; be specific about places, people, and events."
    )
    typical_routines: str = Field(
        description="Day-to-day activities and habits (50-150 words). What does this character do on a typical day/week? "
                   "Include: professional duties, personal habits, social interactions, and pastimes. "
                   "Format: bullet points or narrative describing activities. "
                   "Example: 'Manages the tavern from dawn to dusk, mentors young barmaids, attends evening council meetings, "
                   "reads scholarly texts about ancient civilizations before bed.' These routines should align with character role."
    )
    motivations: str = Field(
        description="Core driving forces and desires (100-200 words). What does the character fundamentally want? "
                   "Include ideological (beliefs), professional (career goals), personal (relationships), and psychological (internal needs) motivations. "
                   "Format: Clear statement of primary and secondary motivations. "
                   "Example: 'Primarily motivated by justice and exposing corruption (ideological). "
                   "Secondarily seeks wealth to fund investigations (professional) and gain her father's posthumous vindication (personal).'"
    )
    goal: Optional[str] = Field(
        description="Lifetime or shor-term goal for the charcter that might lead to a narrative-driven game quest. It does not need to be too specific, it's purpose is to trigger a possible conversation to to give precise details about it."
                   "Should be game-compatible and achievable within reasonable game scope. "
                   "Format: Single, vague objective phrased as action-oriented goal. "
                   "Example: 'Investigate and expose the noble house that bribed her father's competitors, recovering her father's "
                   "sealed ledgers as proof.' Avoid: vague aspirations like 'become famous' or impossible goals like 'change the world.'"
    )
class CharacterMoodDto(BaseModel):
    id:str = Field(description="Db identifier for a user chat session")
    name:str = Field(description="Display name for the role / game class")
    systemMessage: str = Field(description="Text to pass to the llm as part of the sys_msg")

class CharacterPersonalityDto(CharacterMoodDto):
    exclusions: List[str] = Field(description="Array of personalities that are mutually exclusive")

class CharacterTraitDto(CharacterPersonalityDto):
    description: str = Field(description="A more descriptive definition of the Trait")

class CharacterRoleDto(BaseModel):

    id: str = Field(
        description="Database identifier for this role template (unique key). "
                   "Used to reference this role throughout game world. "
                   "Example: '507f1f77bcf86cd799439011' (MongoDB ObjectId format)"
    )
    gameClassId: int = Field(
        description="Unreal Engine game class ID representing this role numerically (typically 1-20). "
                   "Used by game client to filter NPCs by role, apply role-specific mechanics, and trigger role-based quests. "
                   "Example: 1 (Guard), 2 (Merchant), 3 (Wizard), 4 (Thief). "
                   "Must be consistent with Unreal Engine's class enumeration."
    )
    name: str = Field(
        description="Display name for this role archetype (1-3 words, max 30 chars). "
                   "Should be a recognizable game role. Examples: 'Town Guard', 'Merchant', 'Archmage', 'Tavern Owner'. "
                   "Used as fallback if charRole field is unrecognized. Players and NPCs alike have 'roles'."
    )
    description: str = Field(
        description="Detailed explanation of the role's purpose in game world (100-300 words). "
                   "Explain: What the role represents in society, where they're typically found, what they do, "
                   "social status, typical relationships with other roles. "
                   "Format: Narrative description suitable for designer documentation. "
                   "Example: 'Town Guard: Enforces law within city walls. Reports to Captain of Guard. "
                   "Typical personality: lawful, suspicious of crime, protective of citizens. Typical locations: city gate, streets, jail.'"
    )
    systemMessage: str = Field(
        description="LLM system prompt template for generating dialogue from NPCs with this role (200-600 words). "
                   "Should include: Role behavioral guidelines, speech patterns, topics of interest, conflict resolution style, "
                   "and how they interact with different player types. "
                   "Format: Prompt instruction text for LLM. "
                   "Example: 'You are a Town Guard [rest of instructions]. Speak formally. Suspects crime the moment. "
                   "You follow orders from Captain. You are cautious with strangers.' Templated to support {{variables}} if needed."
    )
    outputActions: list[str] = Field(
        description="List of 3-8 OutputActions available to NPCs with this role (e.g., quest offers, dialogue branches). "
                   "Format: Action tag names in UPPER_SNAKE_CASE. "
                   "Examples: ['OFFER_BOUNTY_QUEST', 'SHARE_RUMORS', 'DEMAND_TAXES', 'PROPOSE_ALLIANCE']. "
                   "When LLM generates dialogue, it should only suggest these valid actions. "
                   "Limits available player choices to role-consistent interactions."
    )
    
    # readonly model for UI | NFT metadata (entonces goal tiene que ser mas a largo plazo o generar quest)
class FullPraiseCharDto(BaseModel):
    id:str = Field(description="DB identifier for the character", default_factory=lambda: str(ObjectId()))
    name:str = Field(description="Character name.Optionally with nickname")
    age: str = Field(description="Age of the character in numeric format or an approximation (example: 'mid-thirties' or 'around forty years')"),
    faction: CharProfileElementDto = Field(description="object containing faction's name and display text / description")
    role: CharProfileElementDto = Field(description="object containing character's  role name and display text / description")
    personalities: List[CharProfileElementDto] = Field(description="List of elements containing personality objects with 'name' and display text / description")
    traits: List[CharProfileElementDto] = Field(description="List of elements containing game trait objects with 'name' and display text / description")
    profile: str = Field(description="Character profile containing a string version of the CharacterTemplateDto data")
    goal: Optional[str] = Field(description="Current game goal for the character", default=None)