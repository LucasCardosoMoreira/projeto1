from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import google.generativeai as genai
import json
from models.chamado_model import save_chamado, get_recent_chamados

router = APIRouter()

class ChamadoRequest(BaseModel):
    descricao: str

def fallback_smart_triage(descricao: str):
    """Triagem inteligente local caso a chave da API externa falhe ou atinja limite."""
    texto = descricao.lower()

    if any(k in texto for k in ["senha", "login", "acessar", "acesso", "email", "e-mail", "bloquead", "conta", "autentica"]):
        categoria = "Acesso/Senha"
        prioridade = "Alta" if any(u in texto for u in ["urgente", "não consigo trabalhar", "bloquead", "institucional", "todos"]) else "Média"
        justificativa = "Problema relacionado a credenciais, login ou acesso a conta/e-mail."
    elif any(k in texto for k in ["internet", "wi-fi", "wifi", "rede", "conexão", "conexao", "cabo", "vpn", "lenta", "fora do ar"]):
        categoria = "Rede"
        prioridade = "Crítica" if any(u in texto for u in ["parou", "todos", "setor inteiro", "fora do ar"]) else "Alta"
        justificativa = "Indisponibilidade ou instabilidade de conectividade e rede."
    elif any(k in texto for k in ["impressora", "monitor", "teclado", "mouse", "computador não liga", "notebook", "tela", "cabo", "hardware", "peça"]):
        categoria = "Hardware"
        prioridade = "Alta" if "não liga" in texto else "Média"
        justificativa = "Falha física em equipamento ou periférico de trabalho."
    elif any(k in texto for k in ["sistema", "programa", "erro", "travando", "instal", "atualiza", "software", "aplicativo", "bug", "planilha"]):
        categoria = "Software"
        prioridade = "Alta" if any(u in texto for u in ["travando", "erro", "parou"]) else "Média"
        justificativa = "Falha de funcionamento ou necessidade de suporte em aplicativo/sistema."
    else:
        categoria = "Outros"
        prioridade = "Baixa"
        justificativa = "Solicitação geral encaminhada para análise da equipe de suporte."

    return {
        "categoria": categoria,
        "prioridade": prioridade,
        "justificativa": justificativa
    }

def analyze_ticket_with_gemini(descricao: str):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if not api_key:
        print("Warning: GEMINI_API_KEY environment variable not set. Using smart fallback.")
        return fallback_smart_triage(descricao)

    genai.configure(api_key=api_key)

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

    candidate_models = [
        os.environ.get("GEMINI_MODEL", "").strip(),
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-flash-latest",
    ]
    candidate_models = [m for m in candidate_models if m]

    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            result = json.loads(text.strip())
            if "categoria" in result and "prioridade" in result:
                return result
        except Exception as e:
            print(f"Aviso ao chamar modelo Gemini '{model_name}': {e}")

    print("Usando triagem inteligente de fallback.")
    return fallback_smart_triage(descricao)

@router.post("/chamados")
def create_chamado(chamado: ChamadoRequest):
    # 1. Analyze with Gemini (or smart fallback)
    analysis_result = analyze_ticket_with_gemini(chamado.descricao)

    # 2. Save to database
    try:
        saved_ticket = save_chamado(
            descricao=chamado.descricao,
            categoria=analysis_result.get("categoria", "Outros"),
            prioridade=analysis_result.get("prioridade", "Média"),
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
