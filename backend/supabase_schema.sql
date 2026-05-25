-- ============================================================
-- AI Chatbot — Supabase Schema
-- Run this in the Supabase SQL editor (Dashboard → SQL Editor)
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- USERS (minimal profile — auth handled by Firebase/Clerk)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          text PRIMARY KEY,          -- Firebase UID or Clerk user_id
    email       text UNIQUE,
    display_name text,
    created_at  timestamptz DEFAULT now(),
    updated_at  timestamptz DEFAULT now()
);

-- ============================================================
-- CHAT SESSIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       text NOT NULL,
    title         text DEFAULT 'New Chat',
    collection    text DEFAULT 'documents',   -- ChromaDB collection
    is_active     boolean DEFAULT true,
    message_count int DEFAULT 0,
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id   ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON chat_sessions(is_active);

-- ============================================================
-- CHAT MESSAGES
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id     text NOT NULL,
    role        text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     text NOT NULL,
    metadata    jsonb DEFAULT '{}',
    tokens_used int DEFAULT 0,
    created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON chat_messages(created_at);

-- ============================================================
-- USER MEMORY (long-term persona facts)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_memory (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      text NOT NULL,
    memory_type  text NOT NULL DEFAULT 'fact'
                   CHECK (memory_type IN ('fact', 'preference', 'context')),
    content      text NOT NULL,
    importance   int DEFAULT 1 CHECK (importance BETWEEN 1 AND 5),
    source       text DEFAULT 'inferred'
                   CHECK (source IN ('user_stated', 'inferred')),
    is_active    boolean DEFAULT true,
    created_at   timestamptz DEFAULT now(),
    updated_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_user_id    ON user_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_importance ON user_memory(importance DESC);

-- ============================================================
-- CONVERSATION SUMMARIES
-- ============================================================
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    user_id       text NOT NULL,
    summary       text NOT NULL,
    message_range jsonb DEFAULT '{}',   -- {"from": 0, "to": 20}
    token_count   int DEFAULT 0,
    created_at    timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_summaries_session_id ON conversation_summaries(session_id);

-- ============================================================
-- INGESTED DOCUMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS ingested_documents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ingestion_id    text NOT NULL UNIQUE,
    filename        text NOT NULL,
    collection      text NOT NULL DEFAULT 'documents',
    status          text NOT NULL DEFAULT 'pending',
    pages_loaded    int DEFAULT 0,
    total_chunks    int DEFAULT 0,
    new_chunks      int DEFAULT 0,
    duplicate_chunks int DEFAULT 0,
    document_ids    jsonb DEFAULT '[]',
    error           text,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_docs_collection ON ingested_documents(collection);
CREATE INDEX IF NOT EXISTS idx_docs_status     ON ingested_documents(status);

-- ============================================================
-- ROW-LEVEL SECURITY (enable after testing)
-- ============================================================
-- ALTER TABLE chat_sessions      ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE chat_messages      ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_memory        ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE conversation_summaries ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (uncomment when auth is wired up):
-- CREATE POLICY "users_own_sessions"
--   ON chat_sessions FOR ALL
--   USING (user_id = auth.uid()::text);
