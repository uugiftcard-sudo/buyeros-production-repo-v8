"use client";

type MemoryEntry<T> = {
  memory_key?: string;
  content?: T;
};

interface MemoryTimelineProps {
  memories: MemoryEntry<unknown>[];
  onMemoryClick: (key: string) => void;
}

export function MemoryTimeline({ memories, onMemoryClick }: MemoryTimelineProps) {
  return (
    <div className="memory-timeline">
      <h2>Memory Timeline</h2>
      <div className="memory-list">
        {memories.map((memory, index) => (
          <button
            key={memory.memory_key || index}
            onClick={() => memory.memory_key && onMemoryClick(memory.memory_key)}
            className="memory-item"
          >
            <span className="memory-key">{memory.memory_key}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
