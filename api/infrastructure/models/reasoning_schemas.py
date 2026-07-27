from typing import List, Optional
from pydantic import BaseModel, Field

## modelo para npc bot v2
class ActionDecision(BaseModel):
    reason: str = Field(description="A brief explanation of your deliberation (15-20 words)")
    output_action: str = Field(description="Name of the selected OUTPUT ACTION")

class ActionReasoning(BaseException):
    """
    Schema representing the output of a reasoning about which is the best OUTPUT ACTION to pick for the given character profile and
    conversation context.
    """
    reason: str = Field(description="A brief explanation of your deliberation (15-20 words) justifiying why you selected the OUTPUT ACTION")
    output_action: str = Field(description="Name of the selected OUTPUT ACTION from the list of available")
    is_mandatory: bool = Field(description="A boolean value to indicate whether the action must be appended to the next NPC response or it is a consideration to bias the model a bit")
        
class JoinEventAnalysis(BaseModel):
    """
    Analysis of a conversation where two characters agree to team up.
    
    This schema captures LLM's analysis of a dialogue fragment in which characters establish a partnership,
    join forces, or form a group. Used for NPC party system, relationship tracking, and quest cohesion.
    The LLM analyzes player dialogue and NPC response to determine if partnership was proposed and accepted.
    
    Output requirements:
    - context must explain the circumstances leading to group formation
    - goal should reflect the shared objective uniting the group
    - both context and goal must be consistent with the conversation's tone and character motivations
    """
    context: str = Field(
        description="Narrative analysis of the situation in which characters teamed up (100-300 words). "
                   "Format: Prose description explaining: What events led to the partnership? What circumstances made teaming up necessary? "
                   "How did the characters approach the agreement? What was the tone (reluctant, enthusiastic, pragmatic)? "
                   "Example: 'The player revealed they both seek Bishop Willigut for different reasons. "
                   "Character was suspicious initially but agreed after player demonstrated they share the same enemy.' "
                   "Should capture emotional and logistical context of the joining."
    )
    goal: Optional[str] = Field(
        default=None,
        description="Shared objective that unites the newly formed group (50-200 words). "
                   "Format: Clear, actionable goal statement. "
                   "Examples: 'Defeat Bishop Willigut and expose his cult', 'Recover the stolen artifact before dark lord finds it', "
                   "'Protect the village from incoming bandits'. "
                   "This goal should drive party behavior and quest generation. Should be specific enough to guide gameplay, "
                   "not vague like 'have adventures'. May be set as current bot_goal in NPC memory."
    )

class JoinRejectAnalysis(BaseModel):
    """
    Analysis of a conversation where one character proposes partnership but is rejected.
    
    This schema captures LLM analysis when a teaming proposal fails. Used for tracking failed relationships,
    understanding NPC motivations for rejection, and informing future interaction possibilities.
    The LLM analyzes dialogue to understand both what partnership was proposed and why it was refused.
    
    Output requirements:
    - context must explain both the offer AND the reasoning for rejection
    - goal should describe what the rejecting character seeks instead
    - rejection reasons must seem plausible based on established character personality
    """
    context: str = Field(
        description="Narrative analysis of the partnership proposal and rejection (150-350 words). "
                   "Format: Prose description explaining: What partnership was proposed by whom? On what terms? What reasons did the rejecting party give? "
                   "Was the rejection final or negotiable? What emotional tone accompanied the refusal? "
                   "Example: 'Player proposed joining forces to investigate a haunted manor. Character refused, claiming she prefers to work alone "
                   "and doesn't trust outsiders. Rejection was polite but firm.' "
                   "Should capture both the offer and the full context of the refusal."
    )
    goal: Optional[str] = Field(
        default=None,
        description="What the rejecting character seeks to accomplish instead (50-200 words). "
                   "Format: Description of their alternative goal/motivation. "
                   "Examples: 'Prefers solitary investigation to prove herself', 'Seeks revenge alone', 'Protecting family secrets'. "
                   "Explains why partnership was incompatible with character's core drive. "
                   "This informs whether future partnership might be possible if circumstances change."
    )

class LeavePartyEventAnalysis(BaseModel):
    """ Analysis of the conversation fragment and the context in which two characters split up the group they had previously formed, 
        and output of the context in which the team split occured and the reasons that leaded to one character to leave the party.
    """
    context:str = Field(description="Result of the analysis describing the context or situation in which the group is dissembled")
    reason:Optional[str] = Field(description="A description of the reasons why the characters are dissembling the group / party", default=None)

class StayInGroupEventAnalysis(BaseModel):
    """
    Analysis of a negotiation where a party member decides whether to stay or leave the group.
    
    This schema captures a critical decision point - when an NPC character evaluates whether to remain
    with or separate from the group. Used for party stability, relationship dynamics, and driving
    high-stakes conversations. The LLM first analyzes context, then makes a definitive STAY/LEAVE decision.
    
    Output requirements:
    - context must fully describe the negotiation and all arguments made
    - reason should explain the thought process leading to the decision
    - decision must be binary (STAY or LEAVE) based on the analysis
    - decision should follow logically from context + character personality
    """
    context: str = Field(
        description="Detailed narrative of the separation negotiation (200-400 words). "
                   "Format: Prose describing: What triggered the crisis? What arguments were made for staying/leaving? "
                   "How did characters express their positions? What emotions were present (fear, anger, hope)? "
                   "Example: 'Player argued the party is stronger together. Character countered they're a liability, slowing down the group. "
                   "Player offered to change tactics. Character remained skeptical but listened.' "
                   "Should capture all major arguments and emotional undercurrents."
    )
    reason: str = Field(
        description="Analysis of why the character makes their final decision (150-300 words). "
                   "Format: Explanation of decision-making factors. "
                   "Include: How does the decision align with character personality? What arguments were most persuasive? "
                   "Are there underlying fears/hopes driving the choice? "
                   "Examples: 'Character values loyalty but fears death. The dangerous quest threatens both. "
                   "Recent near-death experience triggers survival instinct over loyalty.' Or: 'Character's primary goal (revenge) "
                   "aligns with the group's direction. Fear of abandonment overrides doubts. Chooses to STAY despite reservations.' "
                   "Explain the thought process comprehensively."
    )
    decision: str = Field(
        description="Final binary decision: 'STAY' or 'LEAVE'. "
                   "Format: Must be EXACTLY one of these two values (case-insensitive: STAY, LEAVE, Stay, Leave, stay, leave all valid). "
                   "STAY: Character commits to remaining with the group despite concerns. Implies they'll help with upcoming tasks. "
                   "LEAVE: Character separates from group. May become hostile, neutral, or simply unavailable for quests. "
                   "This decision drives NPC behavior in subsequent interactions and quest availability."
    )

class FightEventAnalysis(BaseModel):
    """
    Analysis of a conversation escalating to combat or violent conflict.
    
    This schema captures LLM's interpretation of dialogue that breaks down into conflict. Used for
    tracking NPC hostility, understanding conflict roots, and informing future interactions.
    The LLM analyzes the conversation to identify what triggered the fight and who bears responsibility.
    
    Output requirements:
    - context must detail the escalation path leading to conflict
    - reason must explain underlying causes (not surface arguments)
    - instigator should be based on character actions/responsibility, not just who threw first blow
    - All three fields should form a cohesive narrative of conflict genesis
    """
    context: str = Field(
        description="Narrative description of how the conflict escalated to combat (150-350 words). "
                   "Format: Detailed timeline of escalation. Walk through: Initial tension → provocation → counter-provocation → physical conflict. "
                   "Include: What was said? What actions triggered aggression? Was there a moment where de-escalation was possible? "
                   "What was the tone (heated argument, sudden violence, mutual combat agreement)? "
                   "Example: 'Player made insulting remark about character's family. Character took offense but remained composed. "
                   "Player escalated with physical threat. Character drew weapon, player attacked, fight began.' "
                   "Should show clear causation chain."
    )
    reason: str = Field(
        description="Root causes underlying the conflict, beyond surface arguments (100-250 words). "
                   "Format: Analysis of deeper motivations and grievances. "
                   "Examples: 'Character felt disrespected; pride demanded action despite desire to avoid conflict', "
                   "'Player wanted to intimidate NPC into compliance; miscalculated NPC's willingness to fight', "
                   "'Long-standing tension from betrayal finally reached breaking point'. "
                   "Explain the psychological/relational causes underneath the immediate trigger."
    )
    instigator: str = Field(
        description="Which character initiated/was primarily responsible for the conflict (character name, 1-3 words). "
                   "Format: Character name or brief identifier. "
                   "Examples: 'Player', 'Character Name (NPC)', 'Mutual provocation'. "
                   "Assessment should be based on who initiated aggression or created the condition making violence inevitable, "
                   "not necessarily who threw the first punch. Affects reputation consequences and NPC relations."
    ) 
    
class QuestEventAnalysis(BaseModel):
    """
    Extraction of a quest from character dialogue for game integration.
    
    This schema enables LLMs to transform NPC dialogue into structured quests. The LLM analyzes
    conversation to identify quest hooks, extract objectives, determine targets/locations, and
    build action plans. This bridges narrative dialogue and gameplay mechanics for seamless quest generation.
    
    Output requirements:
    - title must be memorable and concise (1-6 words)
    - goal and context must be mutually reinforcing
    - category must be one of the EXACT enum values provided
    - target must be specific to the category (location for investigate, character name for others)
    - action_plan should be 3-7 concrete steps leading to goal achievement
    - All fields must be logically consistent (goal + context explain why items/plan are needed)
    """
    title: str = Field(
        description="Quest name/heading (1-6 words, max 50 chars). "
                   "Should be descriptive and memorable. Format: Imperative or descriptive title. "
                   "Examples: 'Investigate the Haunted Manor', 'Eliminate the Bandit Lord', 'Recover the Lost Artifact'. "
                   "Used in quest log and UI. Should hint at quest type without being overly long."
    )
    goal: str = Field(
        description="Primary quest objective - what the player must accomplish (50-150 words). "
                   "Format: Clear, actionable goal statement. Should be singular and achievable. "
                   "Examples: 'Defeat the corrupted bishop and retrieve evidence of his cult activities', "
                   "'Locate the missing merchant and return him safely to the city'. "
                   "This is what triggers quest completion. Should be specific enough for clear success criteria."
    )
    context: str = Field(
        description="Background story and motivation for the quest (100-300 words). "
                   "Format: Narrative prose explaining: Who requested the quest and why? What events led to this point? "
                   "What's at stake? How is the game world affected? "
                   "Examples: 'The merchant's family hired you to find him after he disappeared. Rumors say the cult kidnapped him.', "
                   "'Bishop Willigut's cult has been poisoning the water supply. Investigate and stop them.' "
                   "Should provide emotional and logistical context that justifies the quest's urgency."
    )
    category: str = Field(
        description="Quest type category - must be EXACTLY one of: 'ELIMINATE TARGET' | 'PROTECT TARGET' | 'INVESTIGATE LOCATION' | 'TALK TO' "
                   "(case-insensitive). "
                   "ELIMINATE TARGET: Kill/defeat a specific enemy. Format: target = enemy name/description. "
                   "PROTECT TARGET: Guard/defend a person or location. Format: target = person/location name. "
                   "INVESTIGATE LOCATION: Explore and find evidence at a location. Format: target = location name. "
                   "TALK TO: Interview/persuade a specific NPC. Format: target = NPC name/description. "
                   "Category drives quest mechanics and available interaction types."
    )
    target: str = Field(
        description="Specific target relevant to the quest category (max 100 chars). "
                   "Format: Depends on category - character name, location, or description. "
                   "ELIMINATE TARGET examples: 'Bishop Willigut', 'The Cult Leader', 'Bandit Captain Morghul'. "
                   "PROTECT examples: 'The Village of Riverside', 'Lady Elowen', 'The Mayor'. "
                   "INVESTIGATE examples: 'The Cult's Underground Temple', 'The Merchant Caravan's Last Camp'. "
                   "TALK TO examples: 'The Town Guard Captain', 'Investigator Aldric'. "
                   "Must be specific enough that player can identify/find the target."
    )
    items: list[str] = Field(
        default=[],
        description="List of items mentioned or likely needed for quest completion (0-10 items). "
                   "Format: Item names or descriptions. "
                   "Examples: ['Bishop's ledgers proving cult activity', 'Ancient seal to unlock the vault', 'Healing potions (bring your own)', "
                   "'Map to the temple entrance']. "
                   "These populate inventory requirements and influence dialogue prompts. Can be empty if no items are needed."
    )
    action_plan: list[str] = Field(
        default=[],
        description="Ordered list of 3-7 key steps to accomplish the quest (major milestones, not every micro-action). "
                   "Format: Action descriptions in imperative or past tense, 1-2 sentences each. "
                   "Examples: ['Meet investigator at the windmill on outskirts of town at midnight', "
                   "'Discuss strategy to infiltrate the bishop's cult compound', "
                   "'Gather evidence: ledgers, witness testimonies, ritual artifacts', "
                   "'Confront bishop with evidence and trigger quest completion']. "
                   "These serve as guideposts for player progression. Should be specific enough to guide, flexible enough to allow player agency."
    )

class ChatMoodAnalysis(BaseModel):
    """
    Analysis and summarization of a conversation between a Non-Player Character and a Player of a role videogame.
    """
    context: str = Field(description="A brief explanation of the context and mood of the conversation (40-50 words).")
    summary: List[str] = Field(description="Summarization of the conversation in a concise mannera, listing the facts and key points in the order they were given in the conversation, with special attention to mentions to locations or characters."
                                           "Single string containing the result."),
    mood: str = Field(description="Label to represent the mood of the analyzed conversation."
                                  "Represents the relationship between the chat participants."
                                  "Mood Label Values: 'FRIENDLY' | 'NEUTRAL' | 'HOSTILE' ")


class ChatReplica(BaseModel):
    action: str = Field(description="")
    conversation_text: str = Field(description="A plain text representation of the replicated chat using the same tag format than in the provided example.")
    reason: str = Field(description="A brief (40-50 word) reasoned justification of your generated chat explaining the reasons why conversation ends up in the selected action.")
    
    ################## QUEST ACTION ####################
    """ Cortesia del tipico prompt random de llm

        Investigator's name: unknown
        Goal: gather evidence for Tribunal of the Creed against Bishop Willigut
        Plan:
            * Meet up with investigator tonight at windmill on outskirts of town
            * Discuss strategy to infiltrate bishop's cults and
    """

    """ OTRA IDEA DE UN PROMPT RANDOM (fuente: STAY_IN_GROUP_TESTING)

        *I look at you with a mix of surprise and curiosity* Ah, what? You're saying we should stick together after all? *I raise an eyebrow*

        You know, traveler... *my voice is still laced with skepticism but also a hint of interest* I have to admit that your sudden change of heart has piqued my attention. What's changed your mind?

        *I take a step closer, my expression more serious now*

        Tell me the truth: what really brought you here? Was it just about taking down Bishop Willigut's cults... or was there something else at play?

        *my hand rests on the hilt of my sword, ready for any situation that might arise*

        And by the way... *I glance around us cautiously before leaning in closer* If we're going to team up again and take down those cultists together... I think it's time we had a more open conversation about our goals and motivations.

        *I look at you with an intense gaze, my eyes searching for any sign of deception or hidden agendas*

        What do you say? Are you ready to put your cards on the table?

        **OUTPUT ACTION:** [[ASK_ABOUT_GOALS]] (deberia ser algo como --> [[SET_GOALS]] = Update bot_memo) 
    
    1 --> Ya es el segundo tag que saca en ese formato [[ACTION_NAME]] --> cambiar formato a ver si acierta mas / predice mejor
    2 --> ASK_ABOUT_GOALS / REQUIRE INFO / REQUIRE X --> set de acciones que gestionan BOT_REQUESTS (lo que quiere el bot, sus inquietudes --> aumentan KnowledgeBase) 
           --> FIJA los objetivos (BOT_GOALS) -> influye en lo que quiere. Por ejemplo, si GOAL = Hunt Bishop Willigut, no acepta acompañarte en otras tareas. 
               COMPORTAMIENTO AUTONOMO?! --> Si disuelves el grupo, Andrew Whyte seguirá intentando matar a Willigut (UE->BotTask+Event/Quest generator si te lo encuentras de camino)
    """
