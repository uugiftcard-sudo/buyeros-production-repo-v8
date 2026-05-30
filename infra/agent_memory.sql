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

CREATE INDEX IF NOT EXISTS agent_memory_content_session_id_idx
    ON agent_memory ((content->>'session_id'));

CREATE INDEX IF NOT EXISTS agent_memory_content_task_id_idx
    ON agent_memory ((content->>'task_id'));

CREATE INDEX IF NOT EXISTS agent_memory_content_source_provider_idx
    ON agent_memory ((content->>'source_provider'));
