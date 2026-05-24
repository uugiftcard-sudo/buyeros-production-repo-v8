"use client";
import { useState, useEffect, useCallback, useRef } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface NetworkEntry {
  id: string;
  timestamp: string;
  method: string;
  path: string;
  requestId?: string;
  traceId?: string;
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
  value: unknown;
  preview: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: "info" | "warn" | "error" | "debug";
  event: string;
  data: Record<string, unknown>;
}

export interface SystemHealth {
  ok: boolean;
  memory?: { ok: boolean };
  redis?: { ok: boolean };
  providers?: Array<{ name: string; status: string; enabled: boolean }>;
  ai_router?: { circuit_state: string; api_key_configured: boolean };
  telegram_configured?: boolean;
  api_key_required?: boolean;
  features?: Record<string, boolean>;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MAX_ENTRIES = 100;
const MAX_LOGS = 200;

// Module-level collector ref so window.__buyerosDebug can access state from outside
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _collectorRef: any = null;

// ─── Collector Hook ───────────────────────────────────────────────────────────

function useDebugCollector() {
  const [network, setNetwork] = useState<NetworkEntry[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [states, setStates] = useState<StateSnapshot[]>([]);
  const [currentRequestId, setCurrentRequestId] = useState<string>("—");
  const isRecording = useRef(true);

  const addNetwork = useCallback((entry: NetworkEntry) => {
    if (!isRecording.current) return;
    setNetwork((prev) => [entry, ...prev].slice(0, MAX_ENTRIES));
    if (entry.requestId) setCurrentRequestId(entry.requestId);
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
      value,
      preview,
    };
    setStates((prev) => [snap, ...prev].slice(0, 50));
  }, []);

  const clear = useCallback(() => {
    setNetwork([]);
    setLogs([]);
    setStates([]);
    setCurrentRequestId("—");
  }, []);

  // Intercept fetch to auto-capture all API calls + capture request IDs
  useEffect(() => {
    const orig = window.fetch;
    window.fetch = (async (...args: Parameters<typeof window.fetch>): Promise<Response> => {
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
      let requestId: string | undefined;
      let traceId: string | undefined;

      try {
        result = await orig(...args);
        status = result.status;
        const text = await result.clone().text();
        try { responseBody = JSON.parse(text); } catch { responseBody = text; }
        const headers: Record<string, string> = {};
        result.headers.forEach((v, k) => { headers[k] = v; });
        requestId = headers["x-request-id"];
        traceId = headers["x-trace-id"];
        addNetwork({
          id, timestamp, method, path: urlStr,
          requestId, traceId, status,
          duration_ms: Math.round(performance.now() - start),
          requestBody, responseBody,
        });
        if (requestId) setCurrentRequestId(requestId);
        return result;
      } catch (err) {
        error = err instanceof Error ? err.message : String(err);
        addNetwork({
          id, timestamp, method, path: urlStr,
          status: 0,
          duration_ms: Math.round(performance.now() - start),
          requestBody, error,
        });
        throw err;
      }
    }) as typeof window.fetch;

    return () => { window.fetch = orig; };
  }, [addNetwork]);

  // Register ref globally so window.__buyerosDebug works
  useEffect(() => {
    if (typeof window !== "undefined") {
      _collectorRef = { network, logs, states, addNetwork, addLog, trackState, clear };
    }
  }, [network, logs, states, addNetwork, addLog, trackState, clear]);

  return { network, logs, states, currentRequestId, addNetwork, addLog, trackState, clear };
}

// ─── Debug Panel UI ───────────────────────────────────────────────────────────

interface Props {
  onTrackState?: (label: string, key: string, value: unknown) => void;
  onAddLog?: (entry: LogEntry) => void;
}

export function DebugPanel({ onTrackState, onAddLog }: Props) {
  const { network, logs, states, currentRequestId, addLog, trackState, clear } = useDebugCollector();
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"network" | "logs" | "states" | "health" | "config">("network");
  const [selectedEntry, setSelectedEntry] = useState<NetworkEntry | null>(null);

  useEffect(() => { if (onTrackState) onTrackState("init", "debug", "panel_mounted"); }, []);

  const statusColor = (s: number) =>
    s === 0 ? "#f87171" : s < 300 ? "#4ade80" : s < 500 ? "#fbbf24" : "#f87171";

  const tabList = ["network", "logs", "states", "health", "config"] as const;

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setOpen((o) => !o)}
        title={`Debug Panel — ReqID: ${currentRequestId}`}
        style={{
          position: "fixed", bottom: 16, right: 16, zIndex: 9999,
          width: 44, height: 44, borderRadius: "50%",
          background: open ? "#3b82f6" : "#1e1e2e",
          border: "2px solid #3b82f6", color: "#fff",
          fontSize: "1.1rem", cursor: "pointer",
          boxShadow: "0 4px 16px rgba(0,0,0,0.4)", transition: "all 0.2s",
        }}
      >
        🐛
      </button>

      {/* Panel */}
      {open && (
        <div style={{
          position: "fixed", bottom: 70, right: 16, zIndex: 9998,
          width: 720, height: 520,
          background: "#0d0d14", border: "1px solid #2a2a3a",
          borderRadius: 12, display: "flex", flexDirection: "column",
          boxShadow: "0 8px 40px rgba(0,0,0,0.6)", overflow: "hidden",
          fontFamily: "'SF Mono', 'Fira Code', monospace", fontSize: "0.75rem",
        }}>
          {/* Header */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "8px 12px", background: "#13131f", borderBottom: "1px solid #2a2a3a",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ color: "#a78bfa", fontWeight: 700, fontSize: "0.8rem" }}>
                BuyerOS Debug
              </span>
              {currentRequestId !== "—" && (
                <span style={{
                  background: "#1e1e2e", border: "1px solid #3a3a4a",
                  borderRadius: 4, padding: "1px 6px",
                  color: "#60a5fa", fontSize: "0.65rem",
                }}>
                  req:{currentRequestId.slice(0, 12)}
                </span>
              )}
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              {tabList.map((t) => (
                <button key={t} onClick={() => setTab(t)} style={{
                  padding: "2px 7px", borderRadius: 4, border: "none",
                  background: tab === t ? "#3b82f6" : "transparent",
                  color: tab === t ? "#fff" : "#555",
                  cursor: "pointer", fontSize: "0.65rem", fontFamily: "inherit",
                  textTransform: "capitalize",
                }}>{t}</button>
              ))}
              <button onClick={clear} style={{
                padding: "2px 7px", borderRadius: 4, border: "none",
                background: "#7f1d1d", color: "#fca5a5", cursor: "pointer",
                fontSize: "0.65rem", fontFamily: "inherit",
              }}>Clear</button>
              <button onClick={() => setOpen(false)} style={{
                padding: "2px 7px", borderRadius: 4, border: "none",
                background: "transparent", color: "#444", cursor: "pointer",
                fontSize: "0.8rem", fontFamily: "inherit",
              }}>✕</button>
            </div>
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflowY: "auto", padding: 8 }}>
            {tab === "network" && (
              <NetworkTab entries={network} statusColor={statusColor} onSelect={setSelectedEntry} />
            )}
            {tab === "logs" && <LogsTab entries={logs} />}
            {tab === "states" && <StatesTab entries={states} onInspect={(s) => setSelectedEntry(s as unknown as NetworkEntry)} />}
            {tab === "health" && <HealthTab />}
            {tab === "config" && (
              <ConfigTab networkCount={network.length} logsCount={logs.length} statesCount={states.length} />
            )}
          </div>

          {/* Detail drawer */}
          {selectedEntry && (
            <DetailDrawer entry={selectedEntry} onClose={() => setSelectedEntry(null)} statusColor={statusColor} />
          )}
        </div>
      )}
    </>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function NetworkTab({
  entries, statusColor, onSelect,
}: {
  entries: NetworkEntry[]; statusColor: (s: number) => string;
  onSelect: (e: NetworkEntry) => void;
}) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", color: "#ccc" }}>
      <thead>
        <tr style={{ borderBottom: "1px solid #2a2a3a", color: "#555", textAlign: "left" }}>
          {["#", "Status", "Method", "Path", "Duration", "Request ID"].map((h, i) => (
            <th key={h} style={{ padding: "3px 6px", fontSize: "0.65rem" }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {entries.length === 0 && (
          <tr><td colSpan={6} style={{ padding: 12, color: "#444", textAlign: "center" }}>
            No requests yet — trigger an API call
          </td></tr>
        )}
        {entries.map((e, i) => (
          <tr
            key={e.id}
            onClick={() => onSelect(e)}
            style={{ borderBottom: "1px solid #1a1a26", cursor: "pointer" }}
            onMouseEnter={(ev) => ((ev.currentTarget as HTMLElement).style.background = "#13131f")}
            onMouseLeave={(ev) => ((ev.currentTarget as HTMLElement).style.background = "transparent")}
          >
            <td style={{ padding: "3px 6px", color: "#333", fontSize: "0.6rem" }}>{entries.length - i}</td>
            <td style={{ padding: "3px 6px", color: statusColor(e.status), fontWeight: 600 }}>{e.status || "ERR"}</td>
            <td style={{ padding: "3px 6px", color: e.method === "POST" ? "#60a5fa" : "#a78bfa" }}>{e.method}</td>
            <td style={{ padding: "3px 6px", color: "#86efac", maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={e.path}>{e.path}</td>
            <td style={{ padding: "3px 6px", color: e.duration_ms > 1000 ? "#fbbf24" : "#6b7280" }}>{e.duration_ms}ms</td>
            <td style={{ padding: "3px 6px", color: "#555", fontSize: "0.65rem" }}>
              {e.requestId ? <span style={{ color: "#60a5fa" }}>{e.requestId.slice(0, 8)}…</span> : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function LogsTab({ entries }: { entries: LogEntry[] }) {
  const levelColor: Record<string, string> = { info: "#60a5fa", warn: "#fbbf24", error: "#f87171", debug: "#86efac" };
  return (
    <div>
      {entries.length === 0 && <p style={{ color: "#444", padding: 12 }}>No logs captured — use window.__buyerosDebug.addLog() in console</p>}
      {entries.map((e) => (
        <div key={e.id} style={{ padding: "2px 0", borderBottom: "1px solid #1a1a26" }}>
          <span style={{ color: "#333", marginRight: 6 }}>{e.timestamp.split("T")[1]?.slice(0, 8)}</span>
          <span style={{ color: levelColor[e.level] ?? "#ccc", marginRight: 6, fontWeight: 700 }}>[{e.level.toUpperCase()}]</span>
          <span style={{ color: "#ccc" }}>{e.event}</span>
          {Object.keys(e.data).length > 0 && (
            <pre style={{ color: "#444", fontSize: "0.65rem", margin: "2px 0 0 16px", overflow: "hidden" }}>
              {JSON.stringify(e.data).slice(0, 300)}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}

function StatesTab({ entries, onInspect }: { entries: StateSnapshot[]; onInspect: (e: StateSnapshot) => void }) {
  return (
    <div>
      {entries.length === 0 && <p style={{ color: "#444", padding: 12 }}>No state snapshots — call trackState() to capture</p>}
      {entries.map((e) => (
        <div
          key={e.id}
          onClick={() => onInspect(e)}
          style={{ padding: "4px 0", borderBottom: "1px solid #1a1a26", cursor: "pointer" }}
          onMouseEnter={(ev) => ((ev.currentTarget as HTMLElement).style.background = "#13131f")}
          onMouseLeave={(ev) => ((ev.currentTarget as HTMLElement).style.background = "transparent")}
        >
          <span style={{ color: "#a78bfa", marginRight: 6 }}>{e.label}</span>
          <span style={{ color: "#555", marginRight: 6 }}>{e.key}</span>
          <span style={{ color: "#ccc" }}>{e.preview}</span>
        </div>
      ))}
    </div>
  );
}

function HealthTab() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = () => {
    setLoading(true);
    setError(null);
    fetch("/api/buyeros/health/ready")
      .then((r) => r.json())
      .then(setHealth)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch_(); }, []);
  const elapsed = Date.now();

  if (loading) return <p style={{ color: "#555", padding: 12 }}>Loading system health…</p>;
  if (error) return (
    <div>
      <p style={{ color: "#f87171", padding: 8 }}>Failed to load: {error}</p>
      <button onClick={fetch_} style={{ padding: "4px 12px", background: "#1e1e2e", color: "#60a5fa", border: "1px solid #3b82f6", borderRadius: 4, cursor: "pointer", fontFamily: "inherit" }}>Retry</button>
    </div>
  );

  const providerStatusColor = (s: string) =>
    s === "ready" ? "#4ade80" : s === "degraded" ? "#fbbf24" : "#f87171";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <p style={{ color: "#666", margin: 0 }}>SYSTEM HEALTH</p>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ color: health?.ok ? "#4ade80" : "#f87171", fontWeight: 700 }}>
            {health?.ok ? "✓ HEALTHY" : "✕ DEGRADED"}
          </span>
          <button onClick={fetch_} style={{ padding: "2px 8px", background: "#1e1e2e", color: "#60a5fa", border: "1px solid #3b82f6", borderRadius: 4, cursor: "pointer", fontFamily: "inherit", fontSize: "0.65rem" }}>Refresh</button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
        {/* Core services */}
        <div style={{ background: "#13131f", borderRadius: 6, padding: 8 }}>
          <p style={{ color: "#555", margin: "0 0 6px", fontSize: "0.65rem" }}>SERVICES</p>
          {[["Memory", health?.memory?.ok], ["Redis", health?.redis?.ok]].map(([label, ok]) => (
            <div key={label as string} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
              <span style={{ color: "#aaa" }}>{label}</span>
              <span style={{ color: ok ? "#4ade80" : "#f87171" }}>{ok ? "✓" : "✕"}</span>
            </div>
          ))}
          <div style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
            <span style={{ color: "#aaa" }}>Telegram</span>
            <span style={{ color: health?.telegram_configured ? "#4ade80" : "#555" }}>{health?.telegram_configured ? "✓ configured" : "✕ not set"}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
            <span style={{ color: "#aaa" }}>API Key</span>
            <span style={{ color: health?.api_key_required ? "#4ade80" : "#555" }}>{health?.api_key_required ? "✓ required" : "✕ optional"}</span>
          </div>
        </div>

        {/* AI Router */}
        <div style={{ background: "#13131f", borderRadius: 6, padding: 8 }}>
          <p style={{ color: "#555", margin: "0 0 6px", fontSize: "0.65rem" }}>AI ROUTER</p>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
            <span style={{ color: "#aaa" }}>Circuit</span>
            <span style={{
              color: health?.ai_router?.circuit_state === "closed" ? "#4ade80"
                : health?.ai_router?.circuit_state === "open" ? "#f87171" : "#fbbf24"
            }}>{health?.ai_router?.circuit_state ?? "N/A"}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
            <span style={{ color: "#aaa" }}>API Key</span>
            <span style={{ color: health?.ai_router?.api_key_configured ? "#4ade80" : "#555" }}>
              {health?.ai_router?.api_key_configured ? "✓ set" : "✕ missing"}
            </span>
          </div>
        </div>

        {/* Features */}
        <div style={{ background: "#13131f", borderRadius: 6, padding: 8 }}>
          <p style={{ color: "#555", margin: "0 0 6px", fontSize: "0.65rem" }}>FEATURES</p>
          {health?.features && Object.entries(health.features).map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
              <span style={{ color: "#aaa" }}>{k.replace(/_/g, " ")}</span>
              <span style={{ color: v ? "#4ade80" : "#555" }}>{v ? "✓" : "✕"}</span>
            </div>
          ))}
        </div>

        {/* Providers */}
        <div style={{ background: "#13131f", borderRadius: 6, padding: 8 }}>
          <p style={{ color: "#555", margin: "0 0 6px", fontSize: "0.65rem" }}>PROVIDERS</p>
          {health?.providers?.slice(0, 6).map((p) => (
            <div key={p.name} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
              <span style={{ color: "#aaa" }}>{p.name}</span>
              <span style={{ color: providerStatusColor(p.status) }}>{p.status} {p.enabled ? "" : "(disabled)"}</span>
            </div>
          ))}
        </div>
      </div>

      <p style={{ color: "#333", marginTop: 8, fontSize: "0.6rem" }}>
        Last refreshed: {new Date().toLocaleTimeString()}
      </p>
    </div>
  );
}

function ConfigTab({ networkCount, logsCount, statesCount }: {
  networkCount: number; logsCount: number; statesCount: number;
}) {
  return (
    <div style={{ color: "#aaa" }}>
      <p style={{ marginBottom: 8, color: "#555" }}>BUYEROS DEBUG CONFIG</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4 }}>
        {[
          ["NEXT_PUBLIC_VERSION", process.env.NEXT_PUBLIC_VERSION ?? "dev"],
          ["NODE_ENV", process.env.NODE_ENV ?? "development"],
          ["API_PROXY", "/api/buyeros"],
        ].map(([k, v]) => (
          <div key={k} style={{ background: "#13131f", borderRadius: 4, padding: "4px 8px" }}>
            <span style={{ color: "#60a5fa" }}>{k}</span>
            <span style={{ color: "#444", margin: "0 6px" }}>=</span>
            <span style={{ color: "#4ade80" }}>{v}</span>
          </div>
        ))}
      </div>
      <p style={{ margin: "12px 0 4px", color: "#555" }}>STATS</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 4 }}>
        {[
          ["Network Entries", networkCount],
          ["Logs", logsCount],
          ["State Snapshots", statesCount],
        ].map(([label, count]) => (
          <div key={label as string} style={{ background: "#13131f", borderRadius: 4, padding: "4px 8px" }}>
            <span style={{ color: "#555" }}>{label as string}: </span>
            <span style={{ color: "#fbbf24" }}>{count}</span>
          </div>
        ))}
      </div>
      <p style={{ margin: "12px 0 4px", color: "#555" }}>CONSOLE HELP</p>
      <pre style={{ color: "#444", fontSize: "0.65rem", lineHeight: 1.7 }}>
{`// In browser DevTools console:
window.__buyerosDebug.addLog({
  level: 'info', event: 'my_event', data: { foo: 1 }
})
window.__buyerosDebug.trackState('component', 'counter', 42)
window.__buyerosDebug.clear()

// Backend verbose logging:
BUYEROS_DEBUG=1 uvicorn ...`}
      </pre>
    </div>
  );
}

function DetailDrawer({
  entry, onClose, statusColor,
}: {
  entry: NetworkEntry | null;
  onClose: () => void;
  statusColor: (s: number) => string;
}) {
  if (!entry) return null;
  return (
    <div style={{
      borderTop: "1px solid #2a2a3a", background: "#0a0a12",
      maxHeight: 200, overflowY: "auto", padding: 8,
      fontSize: "0.7rem",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ color: "#a78bfa" }}>
          {entry.method} {entry.path}
        </span>
        <button onClick={onClose} style={{
          background: "transparent", border: "none", color: "#555",
          cursor: "pointer", fontFamily: "inherit",
        }}>✕</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <div>
          <p style={{ color: "#555", margin: "0 0 4px" }}>STATUS: <span style={{ color: statusColor(entry.status) }}>{entry.status}</span></p>
          <p style={{ color: "#555", margin: "0 0 4px" }}>DURATION: <span style={{ color: "#6b7280" }}>{entry.duration_ms}ms</span></p>
          <p style={{ color: "#555", margin: "0 0 4px" }}>REQUEST ID: <span style={{ color: "#60a5fa" }}>{entry.requestId ?? "—"}</span></p>
          <p style={{ color: "#555", margin: "0 0 4px" }}>TRACE ID: <span style={{ color: "#60a5fa" }}>{entry.traceId ?? "—"}</span></p>
        </div>
        <div>
          {entry.requestBody != null && (
            <>
              <p style={{ color: "#555", margin: "0 0 2px" }}>REQUEST BODY:</p>
              <pre style={{ color: "#4ade80", margin: 0, fontSize: "0.65rem", maxHeight: 80, overflow: "auto" }}>
                {JSON.stringify(entry.requestBody, null, 2).slice(0, 500)}
              </pre>
            </>
          )}
          {entry.responseBody != null && (
            <>
              <p style={{ color: "#555", margin: "4px 0 2px" }}>RESPONSE BODY:</p>
              <pre style={{ color: "#fbbf24", margin: 0, fontSize: "0.65rem", maxHeight: 80, overflow: "auto" }}>
                {JSON.stringify(entry.responseBody, null, 2).slice(0, 500)}
              </pre>
            </>
          )}
          {entry.error && (
            <p style={{ color: "#f87171", margin: "4px 0 0" }}>ERROR: {entry.error}</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Window exposure ───────────────────────────────────────────────────────────




if (typeof window !== "undefined") {
  (window as unknown as {
    __buyerosDebug?: {
      addLog: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
      trackState: (label: string, key: string, value: unknown) => void;
      clear: () => void;
    };
  }).__buyerosDebug = {
    addLog: (entry) => {
      if (_collectorRef) {
        _collectorRef.addLog({
          ...entry,
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          timestamp: new Date().toISOString(),
        });
      } else {
        console.warn("[buyeros] Debug collector not yet initialized");
      }
    },
    trackState: (label, key, value) => {
      _collectorRef?.trackState(label, key, value);
    },
    clear: () => {
      _collectorRef?.clear();
    },
  };
}
