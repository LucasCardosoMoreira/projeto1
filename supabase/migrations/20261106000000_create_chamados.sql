-- Migração e sincronização da tabela de chamados no Supabase (PostgreSQL)
CREATE TABLE IF NOT EXISTS public.chamados (
    id SERIAL PRIMARY KEY,
    setor TEXT NOT NULL DEFAULT 'Geral',
    descricao TEXT NOT NULL,
    categoria VARCHAR(100),
    prioridade VARCHAR(50) NOT NULL,
    justificativa TEXT,
    status TEXT DEFAULT 'Triado pela IA',
    data_criacao TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Caso a tabela já tenha sido criada anteriormente apenas com (id, setor, descricao, prioridade, status, data_criacao),
-- garante que as colunas usadas pela IA também existam:
ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS setor TEXT DEFAULT 'Geral';
ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS categoria VARCHAR(100);
ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS justificativa TEXT;
ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Triado pela IA';
ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS data_criacao TIMESTAMP DEFAULT NOW();
ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Índice para busca rápida dos chamados mais recentes
CREATE INDEX IF NOT EXISTS idx_chamados_created_at ON public.chamados (created_at DESC);
