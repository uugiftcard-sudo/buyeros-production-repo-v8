"use client";

import { AgentCard as AgentCardType } from "@/app/page";

interface AgentCardProps {
  agent: AgentCardType;
  isActive: boolean;
  onSelect: (agentId: string) => void;
}

export function AgentCard({ agent, isActive, onSelect }: AgentCardProps) {
  return (
    <button
      onClick={() => onSelect(agent.id)}
      className={`agent-card ${isActive ? "active" : ""}`}
    >
      <h3>{agent.name}</h3>
      <p className="role">{agent.role}</p>
      <p className="best-for">{agent.bestFor}</p>
      <p className="tone">{agent.tone}</p>
    </button>
  );
}

interface AgentGridProps {
  agents: AgentCardType[];
  activeAgentId: string | null;
  onSelectAgent: (agentId: string) => void;
}

export function AgentGrid({ agents, activeAgentId, onSelectAgent }: AgentGridProps) {
  return (
    <div className="agent-grid">
      {agents.map((agent) => (
        <AgentCard
          key={agent.id}
          agent={agent}
          isActive={activeAgentId === agent.id}
          onSelect={onSelectAgent}
        />
      ))}
    </div>
  );
}
