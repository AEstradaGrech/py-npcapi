from typing import Any, List
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from api.utils.statics import personality_mood_weight, chat_sentiment_weight, current_mood_inertia, personality_moods_map, chat_mood_transitions, dominant_personality_weight
from api.models.schemas import SpacyNER
import random
import nltk

"""
What does NOT go in requirements

    - spaCy models (like en_core_web_sm) are:

You install them after your env is ready:

    - python -m spacy download en_core_web_sm

This is the correct workflow. Do not try to force models into pip-tools.
"""
import spacy
nltk.download('vader_lexicon')


class MoodAnalysisService:
    """
    https://medium.com/@rslavanyageetha/vader-a-comprehensive-guide-to-sentiment-analysis-in-python-c4f1868b0d2e#id_token=eyJhbGciOiJSUzI1NiIsImtpZCI6ImVlMTkzZDQ2NDdhYjRhMzU4NWFhOWIyYjNiNDg0YTg3YWE2OGJiNDIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIyMTYyOTYwMzU4MzQtazFrNnFlMDYwczJ0cDJhMmphbTRsamRjbXMwMHN0dGcuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiIyMTYyOTYwMzU4MzQtazFrNnFlMDYwczJ0cDJhMmphbTRsamRjbXMwMHN0dGcuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDgwNDk0NzUzOTM3NjUxMTQxNzQiLCJlbWFpbCI6ImFsdmFyby5lc3RyYWRhODlAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5iZiI6MTc0MjIzODc5MywibmFtZSI6IkFsdmFybyBFc3RyYWRhIiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0s2X2hFLVZncEhPbkVzdmxxaGMyR1B2ZTk2QzN1UW9pRFhtNkdlSEgzVzJSSUV4UT1zOTYtYyIsImdpdmVuX25hbWUiOiJBbHZhcm8iLCJmYW1pbHlfbmFtZSI6IkVzdHJhZGEiLCJpYXQiOjE3NDIyMzkwOTMsImV4cCI6MTc0MjI0MjY5MywianRpIjoiZTQ1MDYyMWIwNWZlMTk3NzBhNDU3Mjk4NzBjODUxZDQ2ODJlNmJjYyJ9.NdmJIsxa4ESifpyV5s7hDjozy4n4gffArwxqYMZ8n-43do16hpWhvgj4oX03IFUbS52bjCR3e184t_xruP4_Ik2HALIuIGrKwhfuMaTUa0nY8dDNquQk2jyOYDYBDon6ql2zkXYttJHLJJ-x29eLu4TmYWj6PrgeCH5tZTS9eceIAyPbkGSydd-KecXZfaMvjXjAyr_hzokVCMZPBLNtf_h2MkEug1YmFIn5bL5tAgLYtc_UiC-GZA_XFJZVXgYmq23aegRny1fn0IAyj_zJmmtmMOtQgrMXm4wjS_ZgEgxlBYOZuVJIlCmiZF-Mr5C45Njza-dPAiyYPHry9uHmyQ

    The SentimentIntensityAnalyzer class provides a method called polarity_scores() that takes 
    a piece of text as input and returns a dictionary containing the sentiment scores for the text. 
    The dictionary contains four keys: neg, neu, pos, and compound.

    neg: the negative sentiment score (between 0 and 1)
    neu: the neutral sentiment score (between 0 and 1)
    pos: the positive sentiment score (between 0 and 1)
    compound: the overall sentiment score (between -1 and 1)
    """
    def vader_analyze_current_prompt_sentiment(self, user_prompt:str, prev_llm_res:str = None, context_update:str = None) -> Any:
        analyzer = SentimentIntensityAnalyzer()
        text = user_prompt
        if prev_llm_res is not None:
            text = f"- {prev_llm_res}\n-{user_prompt}"
        if context_update is not None:
            text += f"\n{context_update}"
        result = analyzer.polarity_scores(text)
        if result["pos"] > 0:
            result["pos"] = 1 - result["neu"]
        result["avg"] = result["pos"] - result["neg"]
        result["neutrality"] = result["neu"] - abs(result["avg"])
        print("-- anal vader --",result)
        return result

    def spacy_ner(self, user_prompt:str) -> List[SpacyNER]:
        nlp = spacy.load("en_core_web_sm")
        config = {
            "overwrite_ents": True
        }
        praise_ruler = nlp.add_pipe(factory_name="entity_ruler", config=config)
        patterns = [{"label": "GPE", "pattern": "BotVille"}, {"label": "GPE", "pattern": "La Comarca"},{"label": "GPE", "pattern": "Hobbiton"}, {"label": "ORG", "pattern": "Notario Tech"}]
        praise_ruler.add_patterns(patterns)

        doc = nlp(user_prompt)
        results:List[SpacyNER] = []
        for ent in doc.ents:
            print(f"\nTOKEN ANALYSIS >> {ent.text}\n- label: {ent.label_}\n- start: {ent.start_char}\n- end: {ent.end_char}")
            results.append(SpacyNER(text=ent.text, label=ent.label_, start=ent.start_char, end=ent.end_char))
        return results
    """
    NLP - EXTRAER SIGNIFICADO / AÑADIR CONCEPTOS:

    SPACY: https://spacy.io/usage/linguistic-features#named-entities

        doc = nlp("fb is hiring a new vice president of global policy")
        ents = [(e.text, e.start_char, e.end_char, e.label_) for e in doc.ents]
        print('Before', ents)
        # The model didn't recognize "fb" as an entity :(

        # Create a span for the new entity
        fb_ent = Span(doc, 0, 1, label="ORG")
        orig_ents = list(doc.ents)

    DATA PREPARATION / KNOWLEDGE BASE CONSTRUCTION: se añaden SPANS con LOCS ORGS y CHARS
    """

    #hay TRES formas de cambiar humor: en funcion de SHORT_MEMO, en funcion de vader analysis (solo para comentarios negativos o positivos) y en funcion de BotPersonality
    # TODO: cada short_memo se evalua mood en funcion de chat_sentiment (chat_mood_transitions)
    #       cada turn se hace un vader_analysis --> acumulacion NEG/POS = moodTransition
    #       cada X tiempo mood transition en funcion de personalities (personality_moods_map)
    def handle_personality_mood_transition(self, current_bot_mood:str, bot_personalities:list[str]) -> str:
        mood_weights:dict[str, float] = {}
        dominant_weight_sum = dominant_personality_weight
        for i in range(0, len(bot_personalities)- 1):
                dominant_weight_sum += (1 - dominant_personality_weight)
        for i in range(0, len(bot_personalities)):
            personality = bot_personalities[i]
            personality_weights = personality_moods_map.get(personality, {})
            print(":: PERSONALITY WEIGHTS ::\n", personality_weights)
            dominant_weight = 1.0 if len(bot_personalities) == 1 else dominant_personality_weight / dominant_weight_sum
            for k,v in personality_weights.items():
                if i > 0:
                    dominant_weight = (1 - dominant_personality_weight) / dominant_weight_sum
                print(f":: NORMALIZED DOMINANT WEIGHT {dominant_weight} ::")
                mood_weights[k] = mood_weights.get(k, 0) + v * dominant_weight # v*random_deviation? personalidad_dominante = personalities[0] * 0.6 else 0.4
        print(":: MOOD WEIGHTS ::\n", mood_weights)                
        mood_weights[current_bot_mood] = mood_weights.get(current_bot_mood, 0) + current_mood_inertia
        total_weights = sum(mood_weights.values())
        normalized = { k: v / total_weights for k,v in mood_weights.items()}
        print(":: NORMALIZED Ks ::\n", list(normalized.keys()))
        print(":: NORMALIZED Vs ::\n", list(normalized.values()))
        return random.choices(list(normalized.keys()), weights=list(normalized.values()))[0]
    
    def handle_chat_mood_transition(self, current_bot_mood:str, bot_personalities:list[str], chat_sentiment:str = "NEUTRAL"):
        mood_weights:dict[str, float] = {}
        for i in range(0, len(bot_personalities)):
            personality = bot_personalities[i]
            personality_weights = personality_moods_map.get(personality, {})
            dominant_weight = 1.0 if len(bot_personalities) == 1 else dominant_personality_weight
            for k,v in personality_weights.items():
                if i > 0:
                    dominant_weight = 1 - dominant_personality_weight
                print(f":: DOMINANT WEIGHT {dominant_weight} ::")
                mood_weights[k] = mood_weights.get(k, 0) + v * personality_mood_weight * dominant_weight
            sentiments_map = chat_mood_transitions.get(chat_sentiment, {})
            sentiment_weights = sentiments_map.get(personality, {})
            for k, v in sentiment_weights.items():
                mood_weights[k] = mood_weights.get(k, 0) + v * chat_sentiment_weight
        print(":: MOOD WEIGHTS ::\n", mood_weights)
        mood_weights[current_bot_mood] = mood_weights.get(current_bot_mood, 0) + current_mood_inertia
        total_weights = sum(mood_weights.values())
        normalized = { k: v / total_weights for k,v in mood_weights.items()}
        print(":: NORMALIZED Ks ::\n", list(normalized.keys()))
        print(":: NORMALIZED Vs ::\n", list(normalized.values()))
        return random.choices(list(normalized.keys()), weights=list(normalized.values()))