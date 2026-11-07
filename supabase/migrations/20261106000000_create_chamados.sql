-- Migração inicial: Criação da tabela de chamados no Supabase (PostgreSQL)
CREATE TABLE IF NOT EXISTS public.chamados (
    id SERIAL PRIMARY KEY,
    descricao TEXT NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    prioridade VARCHAR(50) NOT NULL,
    justificativa TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice para busca rápida dos chamados mais recentes
CREATE INDEX IF NOT EXISTS idx_chamados_created_at ON public.chamados (created_at DESC);
