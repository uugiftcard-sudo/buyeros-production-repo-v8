CREATE TABLE IF NOT EXISTS agent_memory (
    id BIGSERIAL PRIMARY KEY,
    namespace TEXT[] NOT NULL,
    memory_key TEXT NOT NULL,
    content JSONB NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS agent_memory_namespace_idx
    ON agent_memory USING GIN (namespace);

CREATE INDEX IF NOT EXISTS agent_memory_key_idx
    ON agent_memory (memory_key);

CREATE INDEX IF NOT EXISTS agent_memory_created_at_idx
    ON agent_memory (created_at DESC);
