"use client";
import { useState, useEffect, useCallback, useRef } from "react";

export interface NetworkEntry {
  id: string;
  timestamp: string;
  method: string;
  path: string;
  requestId?: string;
  status: number;
  duration_ms: number;
  requestBody?: unknown;
  responseBody?: unknown;
  error?: string;
}

export interface StateSnapshot {
  id: string;
  timestamp: string;
  label: string;
  key: string;
  preview: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: "info" | "warn" | "error" | "debug";
  event: string;
  data: Record<string, unknown>;
}

const MAX_ENTRIES = 100;
const MAX_LOGS = 200;

function useDebugCollector() {
  const [network, setNetwork] = useState<NetworkEntry[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [states, setStates] = useState<StateSnapshot[]>([]);
  const isRecording = useRef(true);

  const addNetwork = useCallback((entry: NetworkEntry) => {
    if (!isRecording.current) return;
    setNetwork((prev) => [entry, ...prev].slice(0, MAX_ENTRIES));
  }, []);

  const addLog = useCallback((entry: LogEntry) => {
    if (!isRecording.current) return;
    setLogs((prev) => [entry, ...prev].slice(0, MAX_LOGS));
  }, []);

  const trackState = useCallback((label: string, key: string, value: unknown) => {
    if (!isRecording.current) return;
    const preview = typeof value === "string"
      ? value.slice(0, 120)
      : JSON.stringify(value).slice(0, 120);
    const snap: StateSnapshot = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp: new Date().toISOString(),
      label,
      key,
      preview,
    };
    setStates((prev) => [snap, ...prev].slice(0, 50));
  }, []);

  const clear = useCallback(() => {
    setNetwork([]);
    setLogs([]);
    setStates([]);
  }, []);

  // Intercept fetch to auto-capture all API calls
  useEffect(() => {
    const orig = window.fetch;
    window.fetch = async function (...args) {
      const start = performance.now();
      const [url, init] = args;
      const urlStr = typeof url === "string" ? url : url.toString();
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const method = (init?.method ?? "GET").toUpperCase();
      const timestamp = new Date().toISOString();

      let requestBody: unknown;
      try {
        requestBody = init?.body ? JSON.parse(init.body as string) : undefined;
      } catch {
        requestBody = undefined;
      }

      let result: Response | undefined;
      let responseBody: unknown;
      let error: string | undefined;
      let status = 0;

      try {
        result = await orig(...args);
        status = result.status;
        const text = await result.clone().text();
        try { responseBody = JSON.parse(text); } catch { responseBody = text; }
        const headers: Record<string, string> = {};
        result.headers.forEach((v, k) => { headers[k] = v; });
        addNetwork({
          id,
          timestamp,
          method,
          path: urlStr,
          requestId: headers["x-request-id"],
          status,
          duration_ms: Math.round(performance.now() - start),
          requestBody,
          responseBody,
        });
      } catch (err) {
        error = err instanceof Error ? err.message : String(err);
        status = 0;
        addNetwork({
          id,
          timestamp,
          method,
          path: urlStr,
          status,
          duration_ms: Math.round(performance.now() - start),
          requestBody,
          error,
        });
      }
      return result;
    };
    return () => { window.fetch = orig; };
  }, [addNetwork]);

  return { network, logs, states, addNetwork, addLog, trackState, clear };
}

// ─────────────────────────────────────────────────────────────────────────────
// Debug Panel UI
// ─────────────────────────────────────────────────────────────────────────────

interface Props {
  onTrackState?: (label: string, key: string, value: unknown) => void;
  onAddLog?: (entry: LogEntry) => void;
}

export function DebugPanel({ onTrackState, onAddLog }: Props) {
  const { network, logs, states, addNetwork, addLog, trackState, clear } = useDebugCollector();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"network" | "logs" | "states" | "config">("network");

  // Wire external hooks
  useEffect(() => { if (onTrackState) onTrackState("init", "debug", "panel_mounted"); }, []);

  const statusColor = (s: number) =>
    s === 0 ? "#f87171" : s < 300 ? "#4ade80" : s < 500 ? "#fbbf24" : "#f87171";

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setOpen((o) => !o)}
        title="Debug Panel"
        style={{
          position: "fixed",
          bottom: 16,
          right: 16,
          zIndex: 9999,
          width: 44,
          height: 44,
          borderRadius: "50%",
          background: open ? "#3b82f6" : "#1e1e2e",
          border: "2px solid #3b82f6",
          color: "#fff",
          fontSize: "1.1rem",
          cursor: "pointer",
          boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
          transition: "all 0.2s",
        }}
      >
        🐛
      </button>

      {/* Panel */}
      {open && (
        <div style={{
          position: "fixed",
          bottom: 70,
          right: 16,
          zIndex: 9998,
          width: 680,
          height: 500,
          background: "#0d0d14",
          border: "1px solid #2a2a3a",
          borderRadius: 12,
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 8px 40px rgba(0,0,0,0.6)",
          overflow: "hidden",
          fontFamily: "'SF Mono', 'Fira Code', monospace",
          fontSize: "0.75rem",
        }}>
          {/* Header */}
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "8px 12px",
            background: "#13131f",
            borderBottom: "1px solid #2a2a3a",
          }}>
            <span style={{ color: "#a78bfa", fontWeight: 700, fontSize: "0.8rem" }}>
              BuyerOS Debug Panel
            </span>
            <div style={{ display: "flex", gap: 6 }}>
              {(["network", "logs", "states", "config"] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)} style={{
                  padding: "2px 8px",
                  borderRadius: 4,
                  border: "none",
                  background: tab === t ? "#3b82f6" : "transparent",
                  color: tab === t ? "#fff" : "#666",
                  cursor: "pointer",
                  fontSize: "0.7rem",
                  fontFamily: "inherit",
                }}>{t}</button>
              ))}
              <button onClick={clear} style={{
                padding: "2px 8px", borderRadius: 4, border: "none",
                background: "#991b1b", color: "#fff", cursor: "pointer", fontSize: "0.7rem",
                fontFamily: "inherit",
              }}>Clear</button>
              <button onClick={() => setOpen(false)} style={{
                padding: "2px 8px", borderRadius: 4, border: "none",
                background: "transparent", color: "#555", cursor: "pointer", fontSize: "0.8rem",
                fontFamily: "inherit",
              }}>✕</button>
            </div>
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflowY: "auto", padding: 8 }}>
            {tab === "network" && (
              <NetworkTab entries={network} statusColor={statusColor} />
            )}
            {tab === "logs" && (
              <LogsTab entries={logs} />
            )}
            {tab === "states" && (
              <StatesTab entries={states} />
            )}
            {tab === "config" && (
              <ConfigTab
                networkCount={network.length}
                logsCount={logs.length}
                statesCount={states.length}
              />
            )}
          </div>
        </div>
      )}
    </>
  );
}

function NetworkTab({ entries, statusColor }: { entries: NetworkEntry[]; statusColor: (s: number) => string }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", color: "#ccc" }}>
      <thead>
        <tr style={{ borderBottom: "1px solid #2a2a3a", color: "#555", textAlign: "left" }}>
          {["Status", "Method", "Path", "Duration", "Request ID"].map((h) => (
            <th key={h} style={{ padding: "3px 6px", fontSize: "0.65rem" }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {entries.length === 0 && (
          <tr><td colSpan={5} style={{ padding: 12, color: "#444", textAlign: "center" }}>
            No requests yet — try an API call
          </td></tr>
        )}
        {entries.map((e) => (
          <tr key={e.id} style={{ borderBottom: "1px solid #1a1a26" }}>
            <td style={{ padding: "3px 6px", color: statusColor(e.status) }}>{e.status || "ERR"}</td>
            <td style={{ padding: "3px 6px", color: e.method === "POST" ? "#60a5fa" : "#a78bfa" }}>{e.method}</td>
            <td style={{ padding: "3px 6px", color: "#86efac", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
              title={e.path}>{e.path}</td>
            <td style={{ padding: "3px 6px", color: e.duration_ms > 1000 ? "#fbbf24" : "#6b7280" }}>
              {e.duration_ms}ms</td>
            <td style={{ padding: "3px 6px", color: "#555", fontSize: "0.65rem" }}>{e.requestId || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function LogsTab({ entries }: { entries: LogEntry[] }) {
  const levelColor = { info: "#60a5fa", warn: "#fbbf24", error: "#f87171", debug: "#86efac" };
  return (
    <div>
      {entries.length === 0 && <p style={{ color: "#444", padding: 12 }}>No logs captured</p>}
      {entries.map((e) => (
        <div key={e.id} style={{ padding: "2px 0", borderBottom: "1px solid #1a1a26" }}>
          <span style={{ color: "#555", marginRight: 6 }}>{e.timestamp.split("T")[1]?.slice(0, 8)}</span>
          <span style={{ color: levelColor[e.level], marginRight: 6 }}>[{e.level}]</span>
          <span style={{ color: "#ccc" }}>{e.event}</span>
          {Object.keys(e.data).length > 0 && (
            <pre style={{ color: "#555", fontSize: "0.65rem", margin: "2px 0 0 16px", overflow: "hidden" }}>
              {JSON.stringify(e.data).slice(0, 200)}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}

function StatesTab({ entries }: { entries: StateSnapshot[] }) {
  return (
    <div>
      {entries.length === 0 && <p style={{ color: "#444", padding: 12 }}>No state snapshots</p>}
      {entries.map((e) => (
        <div key={e.id} style={{ padding: "3px 0", borderBottom: "1px solid #1a1a26" }}>
          <span style={{ color: "#a78bfa", marginRight: 6 }}>{e.label}</span>
          <span style={{ color: "#555", marginRight: 6 }}>{e.key}</span>
          <span style={{ color: "#ccc" }}>{e.preview}</span>
        </div>
      ))}
    </div>
  );
}

function ConfigTab({ networkCount, logsCount, statesCount }: {
  networkCount: number; logsCount: number; statesCount: number;
}) {
  const envs = [
    ["NEXT_PUBLIC_VERSION", "NEXT_PUBLIC_VERSION"],
    ["NODE_ENV", "production"],
    ["API_URL", "/api/buyeros"],
  ];
  return (
    <div style={{ color: "#aaa" }}>
      <p style={{ marginBottom: 8, color: "#666" }}>BUYEROS DEBUG CONFIG</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
        {envs.map(([k, v]) => (
          <div key={k} style={{ background: "#13131f", borderRadius: 4, padding: "4px 8px" }}>
            <span style={{ color: "#60a5fa" }}>{k}</span>
            <span style={{ color: "#555", margin: "0 6px" }}>=</span>
            <span style={{ color: "#4ade80" }}>{process.env[k] || v}</span>
          </div>
        ))}
      </div>
      <p style={{ margin: "12px 0 4px", color: "#666" }}>STATS</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 4 }}>
        {[["Network Entries", networkCount], ["Logs", logsCount], ["State Snapshots", statesCount]].map(([label, count]) => (
          <div key={label as string} style={{ background: "#13131f", borderRadius: 4, padding: "4px 8px" }}>
            <span style={{ color: "#555" }}>{label as string}: </span>
            <span style={{ color: "#fbbf24" }}>{count}</span>
          </div>
        ))}
      </div>
      <p style={{ margin: "12px 0 4px", color: "#666" }}>HOW TO USE</p>
      <pre style={{ color: "#555", fontSize: "0.65rem", lineHeight: 1.6 }}>
{`1. All fetch() calls are auto-captured in the Network tab.
2. Use window.__buyerosDebug.addLog() in console to add custom logs.
3. Use window.__buyerosDebug.trackState(key, value) to snapshot state.
4. Request IDs are auto-assigned and shown in response headers.
5. Set BUYEROS_DEBUG=1 on the backend for verbose logging.`}
      </pre>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Expose to window for console debugging
// ─────────────────────────────────────────────────────────────────────────────

if (typeof window !== "undefined") {
  (window as unknown as { __buyerosDebug?: ReturnType<typeof useDebugCollector> }).__buyerosDebug = undefined;
}
