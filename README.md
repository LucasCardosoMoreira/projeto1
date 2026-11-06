# Inteligência Artificial em Helpdesk (Triagem)

Este projeto demonstra a criação de uma aplicação web simples de Helpdesk onde as descrições dos chamados de suporte são analisadas por Inteligência Artificial (Google Gemini) para determinar automaticamente a **Categoria** e a **Prioridade** do problema.

## Arquitetura MVC
O projeto segue a arquitetura Model-View-Controller:
- **Models (`backend/models/`)**: Gerencia a conexão com o banco de dados Supabase e as operações de salvar/buscar chamados.
- **Controllers (`backend/controllers/`)**: Contém a lógica de negócio, integração com a API do Gemini e rotas da API.
- **Views (`frontend/`)**: Interface do usuário construída com HTML, CSS e Vanilla JS.

## Tecnologias Utilizadas
- **Backend:** Python, FastAPI, SQLAlchemy, Uvicorn
- **IA:** Google Generative AI (Gemini Pro)
- **Banco de Dados:** Supabase (PostgreSQL)
- **Frontend:** Vanilla HTML, CSS, JavaScript

## Como rodar localmente

1. Configure as variáveis de ambiente (`GEMINI_API_KEY`, `DATABASE_URL`).
2. Navegue até a pasta `backend` e instale as dependências: `pip install -r requirements.txt`
3. Inicie o servidor FastAPI: `uvicorn main:app --reload`
4. Abra o arquivo `frontend/index.html` em um navegador (ou use o Live Server).
