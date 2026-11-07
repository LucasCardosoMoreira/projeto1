-- Migração e limpeza automática da tabela de chamados no Supabase (PostgreSQL)
CREATE TABLE IF NOT EXISTS public.chamados (
    id SERIAL PRIMARY KEY,
    descricao TEXT NOT NULL,
    categoria VARCHAR(100) NOT NULL DEFAULT 'Geral',
    prioridade VARCHAR(50) NOT NULL,
    justificativa TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Garante que as colunas essenciais existam
ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS categoria VARCHAR(100) DEFAULT 'Geral';
ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS justificativa TEXT;
ALTER TABLE public.chamados ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- Se houver registros antigos onde categoria estava em 'setor', copia antes de remover 'setor'
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'chamados' AND column_name = 'setor'
    ) THEN
        EXECUTE 'UPDATE public.chamados SET categoria = COALESCE(categoria, setor, ''Geral'') WHERE categoria IS NULL';
    END IF;
END $$;

-- Define obrigatoriedade (losango cheio no Supabase) nas colunas essenciais
UPDATE public.chamados SET categoria = 'Geral' WHERE categoria IS NULL;
UPDATE public.chamados SET created_at = NOW() WHERE created_at IS NULL;
ALTER TABLE public.chamados ALTER COLUMN categoria SET NOT NULL;
ALTER TABLE public.chamados ALTER COLUMN created_at SET NOT NULL;

-- Remove as colunas duplicadas ou sem uso no projeto
ALTER TABLE public.chamados DROP COLUMN IF EXISTS setor;
ALTER TABLE public.chamados DROP COLUMN IF EXISTS status;
ALTER TABLE public.chamados DROP COLUMN IF EXISTS data_criacao;

-- Índice para busca rápida dos chamados mais recentes
CREATE INDEX IF NOT EXISTS idx_chamados_created_at ON public.chamados (created_at DESC);
