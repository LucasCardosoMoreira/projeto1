from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import google.generativeai as genai
import json
from models.chamado_model import save_chamado, get_recent_chamados

router = APIRouter()

# Configure Google Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not set.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

class ChamadoRequest(BaseModel):
    descricao: str

def analyze_ticket_with_gemini(descricao: str):
    if not GEMINI_API_KEY:
        # Fallback if no API key is provided
        return {
            "categoria": "Não Categorizado",
            "prioridade": "Baixa",
            "justificativa": "Chave de API do Gemini não configurada."
        }

    try:
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        model = genai.GenerativeModel(model_name)
        prompt = f"""
        Você é um assistente de triagem de chamados de suporte (helpdesk).
        Analise a seguinte descrição de chamado e classifique a 'categoria' e a 'prioridade'.

        Prioridades possíveis: Baixa, Média, Alta, Crítica.
        Categorias possíveis: Hardware, Software, Rede, Acesso/Senha, Outros.

        Descrição do chamado: "{descricao}"

        Responda APENAS com um objeto JSON no seguinte formato (sem formatação markdown como ```json):
        {{
            "categoria": "Nome da Categoria",
            "prioridade": "Nível de Prioridade",
            "justificativa": "Breve justificativa de 1 frase para a classificação"
        }}
        """
        response = model.generate_content(prompt)
        # Parse JSON from response
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        result = json.loads(text.strip())
        return result
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return {
            "categoria": "Erro de IA",
            "prioridade": "Média",
            "justificativa": "Não foi possível analisar o chamado usando a IA."
        }

@router.post("/chamados")
def create_chamado(chamado: ChamadoRequest):
    # 1. Analyze with Gemini
    analysis_result = analyze_ticket_with_gemini(chamado.descricao)

    # 2. Save to database
    try:
        saved_ticket = save_chamado(
            descricao=chamado.descricao,
            categoria=analysis_result.get("categoria", "Desconhecido"),
            prioridade=analysis_result.get("prioridade", "Baixa"),
            justificativa=analysis_result.get("justificativa", "Sem justificativa")
        )
        return {"status": "success", "data": saved_ticket}
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Error saving to database")

@router.get("/chamados")
def read_chamados():
    try:
        chamados = get_recent_chamados()
        return {"status": "success", "data": chamados}
    except Exception as e:
         print(f"Database error: {e}")
         raise HTTPException(status_code=500, detail="Error fetching from database")
