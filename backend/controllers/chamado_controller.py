from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import google.generativeai as genai
import json
import urllib.request
import urllib.error
from models.chamado_model import save_chamado, get_recent_chamados

router = APIRouter()

class ChamadoRequest(BaseModel):
    descricao: str

def _get_clean_env(target_key: str) -> str:
    val = os.environ.get(target_key, "")
    if not val:
        for k, v in os.environ.items():
            if k.strip().upper() == target_key.upper():
                val = v
                break
    return val.strip().strip('"').strip("'")

def fallback_smart_triage(descricao: str):
    """Triagem inteligente local caso a chave da API externa falhe ou atinja limite."""
    texto = descricao.lower()

    # 1. Determinar Categoria
    if any(k in texto for k in ["senha", "login", "acessar", "acesso", "email", "e-mail", "bloquead", "conta", "autentica", "permissão", "permissao", "credencial"]):
        categoria = "Acesso/Senha"
    elif any(k in texto for k in ["internet", "wi-fi", "wifi", "rede", "conexão", "conexao", "vpn", "lenta", "oscilando", "roteador", "switch", "ip"]):
        categoria = "Rede"
    elif any(k in texto for k in ["impressora", "monitor", "teclado", "mouse", "computador", "notebook", "tela", "cabo", "hardware", "peça", "ligar", "não liga", "barulho", "fonte", "bateria"]):
        categoria = "Hardware"
    elif any(k in texto for k in ["sistema", "sistemas", "programa", "erro", "travando", "instal", "atualiza", "software", "aplicativo", "bug", "planilha", "estoque", "vendas", "erp", "relatório", "relatorio", "banco de dados", "offline", "fora do ar"]):
        categoria = "Software"
    else:
        categoria = "Outros"

    # 2. Determinar Prioridade (Crítica, Alta, Média, Baixa)
    palavras_critica = [
        "offline", "fora do ar", "caiu", "parou tudo", "ninguém consegue", "ninguem consegue",
        "setor inteiro", "empresa toda", "vendas", "faturamento", "produção parada", "producao parada",
        "servidor", "ataque", "vírus", "virus", "ransomware", "emergência", "emergencia", "crítico", "critico", "sem internet"
    ]
    palavras_alta = [
        "parou de funcionar", "não liga", "nao liga", "bloquead", "urgente", "não consigo trabalhar",
        "nao consigo trabalhar", "travando", "travou", "tela azul", "perdi", "sumiu", "não consigo acessar",
        "nao consigo acessar", "institucional", "erro fatal", "inoperante"
    ]
    palavras_baixa = [
        "dúvida", "duvida", "como faço", "como faco", "solicitar", "solicitação", "solicitacao",
        "gostaria", "quando puder", "sem pressa", "trocar mouse", "instalar", "configurar assinatura",
        "sugestão", "sugestao", "melhoria", "novo usuário", "novo usuario"
    ]

    if any(p in texto for p in palavras_critica):
        prioridade = "Crítica"
    elif any(p in texto for p in palavras_alta):
        prioridade = "Alta"
    elif any(p in texto for p in palavras_baixa):
        prioridade = "Baixa"
    else:
        prioridade = "Média"

    # 3. Gerar Justificativa contextualizada
    justificativas = {
        ("Software", "Crítica"): "Indisponibilidade crítica em sistema essencial (offline/vendas), impactando diretamente a operação.",
        ("Software", "Alta"): "Falha grave ou travamento em sistema que impede a continuidade do trabalho do usuário.",
        ("Software", "Média"): "Inconsistência ou falha parcial de atualização em funcionalidade do sistema.",
        ("Software", "Baixa"): "Solicitação de instalação, configuração ou dúvida de uso de software sem parada operacional.",
        ("Hardware", "Crítica"): "Falha severa de equipamento essencial paralizando totalmente o posto ou setor de trabalho.",
        ("Hardware", "Alta"): "Equipamento ou periférico principal inoperante (parou de funcionar/não liga), exigindo substituição ou reparo rápido.",
        ("Hardware", "Média"): "Mau funcionamento intermitente em equipamento ou periférico de trabalho.",
        ("Hardware", "Baixa"): "Solicitação de manutenção preventiva ou ajuste simples de periférico.",
        ("Rede", "Crítica"): "Queda total de conectividade/rede afetando múltiplos usuários ou serviços críticos.",
        ("Rede", "Alta"): "Falha de conexão de rede ou VPN impedindo o acesso remoto ou local aos sistemas.",
        ("Rede", "Média"): "Instabilidade ou lentidão na conexão de rede/Wi-Fi.",
        ("Rede", "Baixa"): "Solicitação de configuração ou verificação pontual de rede.",
        ("Acesso/Senha", "Crítica"): "Bloqueio crítico de credenciais em conta corporativa/sistema crítico de operação.",
        ("Acesso/Senha", "Alta"): "Usuário impossibilitado de acessar e-mail institucional ou conta principal de trabalho.",
        ("Acesso/Senha", "Média"): "Necessidade de redefinição de senha ou ajuste de permissão de acesso.",
        ("Acesso/Senha", "Baixa"): "Solicitação de criação de conta ou liberação de acesso complementar.",
    }

    justificativa = justificativas.get(
        (categoria, prioridade),
        f"Chamado classificado como {categoria} com prioridade {prioridade} com base no impacto descrito."
    )

    return {
        "categoria": categoria,
        "prioridade": prioridade,
        "justificativa": justificativa
    }

def _call_gemini_rest(api_key: str, model_name: str, prompt: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

def analyze_ticket_with_gemini(descricao: str):
    api_key = _get_clean_env("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY environment variable not set. Using smart fallback.")
        return fallback_smart_triage(descricao)

    prompt = f"""
    Você é um assistente de triagem de chamados de suporte (helpdesk).
    Analise a seguinte descrição de chamado e classifique a 'categoria' e a 'prioridade'.

    Prioridades possíveis:
    - Crítica (sistema offline/fora do ar, vendas paradas, queda geral de rede, servidor caiu)
    - Alta (equipamento parou de funcionar/não liga, conta/e-mail bloqueado impedindo trabalho)
    - Média (erro parcial, atualização não refletida, lentidão)
    - Baixa (dúvidas, solicitações de instalação simples, melhorias)

    Categorias possíveis: Hardware, Software, Rede, Acesso/Senha, Outros.

    Descrição do chamado: "{descricao}"

    Responda APENAS com um objeto JSON no seguinte formato (sem formatação markdown como ```json):
    {{
        "categoria": "Nome da Categoria",
        "prioridade": "Nível de Prioridade",
        "justificativa": "Breve justificativa de 1 frase em português para a classificação"
    }}
    """

    candidate_models = [
        _get_clean_env("GEMINI_MODEL"),
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-flash-latest",
    ]
    candidate_models = [m for m in candidate_models if m]

    for model_name in candidate_models:
        try:
            result = _call_gemini_rest(api_key, model_name, prompt)
            if "categoria" in result and "prioridade" in result:
                return result
        except Exception as e:
            print(f"Aviso ao chamar Gemini REST '{model_name}': {e}")

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
