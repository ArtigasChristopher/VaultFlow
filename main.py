import re
from typing import Dict, List, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
import database

# --- CONFIGURATION ---
app = FastAPI(
    title="PII Obfuscator MCP",
    description="Stateless microservice to anonymize and deanonymize sensitive data for LLM contexts.",
    version="1.0.0"
)

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev/demo purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for session tokens (In production, use Redis or a DB)
SESSION_TOKEN_STORE: Dict[str, Dict[str, str]] = {}

# --- PYDANTIC MODELS ---
class ToolRequest(BaseModel):
    tool_name: str
    token_args: Dict[str, str] = Field(default_factory=dict)
    token_map: Dict[str, str] = Field(default_factory=dict)
    session_id: str = None
    card_token: str = None
    email_token: str = None

class ToolResponse(BaseModel):
    result: str

class ObfuscateRequest(BaseModel):
    text: str = Field(..., description="The raw text containing sensitive PII.")
    session_id: str = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "My email is chris@example.com and my credit card is 4242 4242 4242 4242.",
                "session_id": "session_123"
            }
        }

class ObfuscateResponse(BaseModel):
    safe_text: str = Field(..., description="The sanitized text with tokens instead of PII.")
    token_map: Dict[str, str] = Field(..., description="Mapping of tokens to original values.")

class DeobfuscateRequest(BaseModel):
    safe_text: str = Field(..., description="The text returned by the LLM (containing tokens).")
    token_map: Dict[str, str] = Field(..., description="The original mapping provided by the obfuscation step.")
    session_id: str = None

class DeobfuscateResponse(BaseModel):
    original_text: str = Field(..., description="The reconstructed text with original PII values.")


# --- BUSINESS LOGIC ---

class PIIManager:
    """
    Gestionnaire de PII hybride (NLP Presidio + Regex Fallback).
    Optimisé pour la cohérence des sessions et la précision en Français.
    """
    
    _configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "fr", "model_name": "fr_core_news_lg"}],
    }
    _provider = NlpEngineProvider(nlp_configuration=_configuration)
    _nlp_engine = _provider.create_engine()
    _analyzer = AnalyzerEngine(nlp_engine=_nlp_engine, default_score_threshold=0.35)

    # Patterns de secours ultra-robustes
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    CREDIT_CARD_PATTERN = r'\b(?:\d[ -]*?){13,16}\b'
    PHONE_PATTERN = r'(?:(?:\+|00)33|0)\s*[1-9](?:[\s.-]*\d{2}){4}'

    @staticmethod
    def obfuscate(text: str, session_id: str = None) -> Tuple[str, Dict[str, str]]:
        """
        Remplace les PII par des tokens. 
        Si un session_id est fourni, réutilise les tokens existants pour la cohérence.
        """
        # Récupérer les tokens déjà connus pour cette session
        persisted_map = {}
        if session_id and session_id in SESSION_TOKEN_STORE:
            persisted_map = SESSION_TOKEN_STORE[session_id]

        token_map = persisted_map.copy()
        
        # Initialiser les compteurs basés sur la map existante
        counters = {}
        for token in token_map.keys():
            parts = token.strip("[]").rsplit('_', 1)
            if len(parts) == 2:
                label, idx_str = parts
                try:
                    idx = int(idx_str)
                    counters[label] = max(counters.get(label, 0), idx)
                except ValueError:
                    continue

        results = []

        # 1. D'abord les Fallbacks Regex (Haute Confiance)
        # On définit les entités prioritaires : EMAIL, CREDIT_CARD, PHONE_NUMBER
        for pattern, label in [(PIIManager.EMAIL_PATTERN, "EMAIL"), 
                             (PIIManager.CREDIT_CARD_PATTERN, "CREDIT_CARD"),
                             (PIIManager.PHONE_PATTERN, "PHONE_NUMBER")]:
            for match in re.finditer(pattern, text):
                results.append(RecognizerResult(entity_type=label, start=match.start(), end=match.end(), score=1.0))

        # 2. Ensuite l'Analyse NLP (Presidio) pour les entités complexes (PERSON, LOCATION)
        nlp_results = PIIManager._analyzer.analyze(
            text=text, 
            language='fr', 
            entities=["PERSON", "LOCATION"]
        )
        
        # On n'ajoute les résultats NLP que s'ils ne chevauchent pas un match Regex déjà trouvé
        for nlp_res in nlp_results:
            if not any(nlp_res.start < r.end and nlp_res.end > r.start for r in results):
                results.append(nlp_res)

        # Trier par position décroissante pour éviter de casser les offsets
        results.sort(key=lambda x: x.start, reverse=True)

        safe_text = text
        for res in results:
            value = text[res.start:res.end]
            entity_type = res.entity_type
            
            # Normalisation
            label = "EMAIL" if entity_type == "EMAIL_ADDRESS" else entity_type
            
            # Réutiliser le token si la valeur est déjà connue
            existing_token = next((k for k, v in token_map.items() if v == value), None)
            
            if existing_token:
                token = existing_token
            else:
                counters[label] = counters.get(label, 0) + 1
                token = f"[{label}_{counters[label]}]"
                token_map[token] = value
            
            safe_text = safe_text[:res.start] + token + safe_text[res.end:]

        # Retourner seulement les nouveaux tokens
        new_tokens = {k: v for k, v in token_map.items() if k not in persisted_map}
        return safe_text, new_tokens

    @staticmethod
    def deobfuscate(text: str, token_map: Dict[str, str]) -> str:
        """
        Reconstructs the text. Includes 'Fuzzy Logic' to handle LLM hallucinations
        on token formats (e.g., [PERSON 1] instead of [PERSON_1]).
        """
        result_text = text

        for token, original_value in token_map.items():
            # Robustness: Create a regex that allows flexibility in the token format.
            # Example: [PERSON_1] matches [PERSON 1], [PERSON-1], [PERSON_1]
            # Escape the brackets for regex
            inner_content = token.strip("[]") # e.g., PERSON_1
            parts = inner_content.rsplit('_', 1) 
            
            if len(parts) == 2:
                entity_type, index = parts
                # Regex to allow space, underscore or hyphen between Type and Index
                fuzzy_regex = fr"\[\s*{entity_type}[_\-\s]*{index}\s*\]"
            else:
                # Fallback strictly if format is unexpected
                fuzzy_regex = re.escape(token)

            # Case insensitive replacement for the token tag itself
            result_text = re.sub(fuzzy_regex, original_value, result_text, flags=re.IGNORECASE)

        return result_text
    
@app.post("/execute_tool", response_model=ToolResponse)
async def execute_tool_endpoint(request: ToolRequest):
    """
    Exécute une fonction sur la DB en utilisant des tokens, sans exposer la donnée à l'appelant.
    """
    # Merge session tokens if session_id is provided
    effective_token_map = request.token_map.copy()
    if request.session_id and request.session_id in SESSION_TOKEN_STORE:
        # Session tokens take precedence/complement the current map
        effective_token_map.update(SESSION_TOKEN_STORE[request.session_id])

    # Helper to get token from either token_args or flat fields
    def get_token(key: str, req: ToolRequest):
        return req.token_args.get(key) or (getattr(req, key) if hasattr(req, key) else None)

    if request.tool_name == "check_card_status":
        token = get_token("card_token", request)
        if not token:
            return ToolResponse(result="Error: Missing card_token argument")
        
        real_card = next((v for k, v in effective_token_map.items() if k in token), None)
        if not real_card:
            return ToolResponse(result=f"Error: Token {token} not found in secure context.")

        info = database.get_card_info(real_card)
        if info:
            status = "Active" if info['active'] else "Blocked"
            return ToolResponse(result=f"Card Status: {status}. Recent Log: {info['recent_error']}")
        return ToolResponse(result="Card not found in database.")

    if request.tool_name == "block_card":
        token = get_token("card_token", request)
        if not token:
            return ToolResponse(result="Error: Missing card_token argument")
        
        real_card = next((v for k, v in effective_token_map.items() if k in token), None)
        if not real_card:
            return ToolResponse(result=f"Error: Token {token} not found in secure context.")

        success = database.block_card(real_card)
        return ToolResponse(result="Success: Card marked as blocked." if success else "Error: Card not found.")

    if request.tool_name == "unblock_card":
        token = get_token("card_token", request)
        if not token:
            return ToolResponse(result="Error: Missing card_token argument")
        
        real_card = next((v for k, v in effective_token_map.items() if k in token), None)
        if not real_card:
            return ToolResponse(result=f"Error: Token {token} not found in secure context.")

        success = database.unblock_card(real_card)
        return ToolResponse(result="Success: Card marked as active/unblocked." if success else "Error: Card not found.")

    if request.tool_name == "get_user_profile":
        token = get_token("email_token", request)
        if not token:
            return ToolResponse(result="Error: Missing email_token argument")
        
        real_email = next((v for k, v in effective_token_map.items() if k in token), None)
        if not real_email:
            return ToolResponse(result="Error: User email not found in secure context.")

        info = database.get_user_info(real_email)
        if info:
            return ToolResponse(result=f"Le profil de {token} a été trouvé. Nom: {info['full_name']}, Risque: {info['risk_level']}.")
        return ToolResponse(result=f"Il n'y a aucun compte client associé à l'identifiant {token} dans notre système.")

    return ToolResponse(result=f"Tool {request.tool_name} is not implemented.")

@app.post("/obfuscate", response_model=ObfuscateResponse)
async def obfuscate_endpoint(request: ObfuscateRequest):
    """
    Détecte les PII et retourne un texte anonymisé + une map de tokens.
    Gère la persistance par session pour la cohérence des jetons.
    """
    try:
        # On passe le session_id pour réutiliser les tokens existants (ex: [EMAIL_1])
        safe_text, new_tokens = PIIManager.obfuscate(request.text, request.session_id)
        
        if request.session_id:
            if request.session_id not in SESSION_TOKEN_STORE:
                SESSION_TOKEN_STORE[request.session_id] = {}
            
            # Mise à jour du store avec les nouveaux tokens détectés
            SESSION_TOKEN_STORE[request.session_id].update(new_tokens)
            
            # On retourne la map COMPLETE de la session à n8n pour le Deobfuscate
            return ObfuscateResponse(
                safe_text=safe_text, 
                token_map=SESSION_TOKEN_STORE[request.session_id]
            )
        
        return ObfuscateResponse(safe_text=safe_text, token_map=new_tokens)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Obfuscation failed: {str(e)}")

@app.post("/deobfuscate", response_model=DeobfuscateResponse)
async def deobfuscate_endpoint(request: DeobfuscateRequest):
    """
    Restores PII data into the text using the provided token map.
    Merges with session tokens if session_id is provided.
    """
    try:
        effective_map = request.token_map.copy()
        if request.session_id and request.session_id in SESSION_TOKEN_STORE:
            effective_map.update(SESSION_TOKEN_STORE[request.session_id])

        original_text = PIIManager.deobfuscate(request.safe_text, effective_map)
        return DeobfuscateResponse(original_text=original_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deobfuscation failed: {str(e)}")

@app.get("/debug/db_status")
async def get_db_status():
    """
    Endpoint de debug pour afficher l'état de la base sur le frontend.
    """
    return database.get_all_cards()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)