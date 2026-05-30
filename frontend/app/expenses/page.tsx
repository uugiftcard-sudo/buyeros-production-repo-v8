"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ExpenseClaim = {
  id: string;
  buyer_name: string;
  amount: number;
  currency: string;
  category: string;
  description: string;
  receipt_url?: string;
  status: "pending" | "approved" | "rejected";
  submitted_at: string;
  reviewed_at?: string;
  reviewer?: string;
  reviewer_note?: string;
};

type ApiConfig = {
  proxyUrl: string;
  apiKey: string;
};

const CATEGORIES = [
  "travel",
  "accommodation",
  "meals",
  "shipping",
  "samples",
  "marketing",
  "office",
  "other",
] as const;

const CATEGORY_LABELS: Record<string, string> = {
  travel: "差旅",
  accommodation: "住宿",
  meals: "餐飲",
  shipping: "運費",
  samples: "樣品",
  marketing: "推廣",
  office: "辦公",
  other: "其他",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "待審批",
  approved: "已批准",
  rejected: "已拒絕",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "#b8860b",
  approved: "#2e7d32",
  rejected: "#c62828",
};

const defaultProxy = "/api/buyeros";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtAmount(amount: number, currency: string) {
  return `${currency} ${amount.toLocaleString("zh-HK", { minimumFractionDigits: 2 })}`;
}

function fmtDate(iso?: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("zh-HK", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ExpensesPage() {
  const [cfg, setCfg] = useState<ApiConfig>({ proxyUrl: defaultProxy, apiKey: "" });
  const [claims, setClaims] = useState<ExpenseClaim[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Filters
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterBuyer, setFilterBuyer] = useState<string>("");

  // Submit form
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    buyer_name: "",
    amount: "",
    currency: "HKD",
    category: "other",
    description: "",
    receipt_url: "",
  });

  // Approve/reject modal
  const [reviewTarget, setReviewTarget] = useState<ExpenseClaim | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewer, setReviewer] = useState("");

  // ─── API helpers ────────────────────────────────────────────────────────────

  const headers = useCallback(
    () => ({
      "Content-Type": "application/json",
      ...(cfg.apiKey ? { "x-buyeros-api-key": cfg.apiKey } : {}),
    }),
    [cfg.apiKey]
  );

  const proxyUrl = cfg.proxyUrl.replace(/\/$/, "") || defaultProxy;

  async function apiFetch(path: string, init: RequestInit = {}) {
    const res = await fetch(`${proxyUrl}${path}`, { ...init, headers: headers() });
    const text = await res.text();
    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
    if (!res.ok) {
      const msg = (data as { detail?: string })?.detail ?? res.statusText;
      throw new Error(msg);
    }
    return data;
  }

  // ─── Load claims ────────────────────────────────────────────────────────────

  const loadClaims = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      if (filterBuyer) params.set("buyer_name", filterBuyer);
      params.set("limit", "200");
      const data = (await apiFetch(`/expenses?${params}`)) as { claims: ExpenseClaim[] };
      setClaims(data.claims ?? []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cfg, filterStatus, filterBuyer]);

  useEffect(() => {
    loadClaims();
  }, [loadClaims]);

  // ─── Submit expense ─────────────────────────────────────────────────────────

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await apiFetch("/expenses", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          amount: parseFloat(form.amount),
          receipt_url: form.receipt_url || undefined,
        }),
      });
      setSuccess("報帳單已提交，待審批。");
      setShowForm(false);
      setForm({ buyer_name: "", amount: "", currency: "HKD", category: "other", description: "", receipt_url: "" });
      await loadClaims();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // ─── Approve / Reject ────────────────────────────────────────────────────────

  async function handleReview(newStatus: "approved" | "rejected") {
    if (!reviewTarget) return;
    setLoading(true);
    setError(null);
    try {
      await apiFetch(`/expenses/${reviewTarget.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus, reviewer, reviewer_note: reviewNote }),
      });
      setSuccess(`報帳單已${newStatus === "approved" ? "批准" : "拒絕"}。`);
      setReviewTarget(null);
      setReviewNote("");
      setReviewer("");
      await loadClaims();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  // ─── CSV export ──────────────────────────────────────────────────────────────

  async function handleExport() {
    const params = new URLSearchParams();
    if (filterStatus) params.set("status", filterStatus);
    if (filterBuyer) params.set("buyer_name", filterBuyer);
    const url = `${proxyUrl}/expenses/export/csv?${params}`;
    const res = await fetch(url, { headers: headers() });
    if (!res.ok) { setError("匯出失敗"); return; }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "expenses.csv";
    a.click();
  }

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 900, margin: "0 auto", padding: "24px 16px" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>買手報帳系統</h1>
      <p style={{ color: "#666", marginBottom: 20, fontSize: 14 }}>Buyer Expense Claims</p>

      {/* Config strip */}
      <details style={{ marginBottom: 16, background: "#f5f5f5", borderRadius: 6, padding: "8px 12px" }}>
        <summary style={{ cursor: "pointer", fontSize: 13, color: "#555" }}>API 設定</summary>
        <div style={{ marginTop: 8, display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input
            placeholder="Proxy URL (default: /api/buyeros)"
            value={cfg.proxyUrl}
            onChange={(e) => setCfg((c) => ({ ...c, proxyUrl: e.target.value }))}
            style={inputStyle}
          />
          <input
            type="password"
            placeholder="API Key (BUYEROS_API_KEY)"
            value={cfg.apiKey}
            onChange={(e) => setCfg((c) => ({ ...c, apiKey: e.target.value }))}
            style={inputStyle}
          />
        </div>
      </details>

      {/* Alerts */}
      {error && (
        <div style={{ background: "#ffebee", border: "1px solid #ef9a9a", borderRadius: 6, padding: "10px 14px", marginBottom: 12, color: "#b71c1c", fontSize: 14 }}>
          ❌ {error}
        </div>
      )}
      {success && (
        <div style={{ background: "#e8f5e9", border: "1px solid #a5d6a7", borderRadius: 6, padding: "10px 14px", marginBottom: 12, color: "#1b5e20", fontSize: 14 }}>
          ✅ {success}
        </div>
      )}

      {/* Actions bar */}
      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={() => { setShowForm((v) => !v); setError(null); setSuccess(null); }} style={btnPrimary}>
          {showForm ? "取消" : "+ 提交報帳"}
        </button>
        <button onClick={loadClaims} style={btnSecondary} disabled={loading}>
          {loading ? "載入中…" : "刷新"}
        </button>
        <button onClick={handleExport} style={btnSecondary}>
          ↓ 匯出 CSV
        </button>
        <span style={{ marginLeft: "auto", fontSize: 13, color: "#888" }}>
          共 {claims.length} 筆
        </span>
      </div>

      {/* Submit form */}
      {showForm && (
        <form onSubmit={handleSubmit} style={{ background: "#f9f9f9", border: "1px solid #ddd", borderRadius: 8, padding: 16, marginBottom: 20 }}>
          <h3 style={{ margin: "0 0 12px", fontSize: 16 }}>新報帳單</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div>
              <label style={labelStyle}>買手姓名 *</label>
              <input required value={form.buyer_name} onChange={(e) => setForm((f) => ({ ...f, buyer_name: e.target.value }))} style={inputStyle} placeholder="e.g. 陳大文" />
            </div>
            <div>
              <label style={labelStyle}>金額 *</label>
              <div style={{ display: "flex", gap: 6 }}>
                <select value={form.currency} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))} style={{ ...inputStyle, width: 80 }}>
                  {["HKD", "CNY", "USD", "EUR", "GBP"].map((c) => <option key={c}>{c}</option>)}
                </select>
                <input required type="number" min="0.01" step="0.01" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} style={{ ...inputStyle, flex: 1 }} placeholder="0.00" />
              </div>
            </div>
            <div>
              <label style={labelStyle}>類別</label>
              <select value={form.category} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))} style={inputStyle}>
                {CATEGORIES.map((c) => <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>收據連結（可選）</label>
              <input type="url" value={form.receipt_url} onChange={(e) => setForm((f) => ({ ...f, receipt_url: e.target.value }))} style={inputStyle} placeholder="https://…" />
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={labelStyle}>說明 *</label>
              <textarea required rows={3} value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} style={{ ...inputStyle, resize: "vertical", height: 72 }} placeholder="費用說明，例如：廣州採購差旅費" />
            </div>
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
            <button type="submit" style={btnPrimary} disabled={loading}>{loading ? "提交中…" : "提交報帳"}</button>
            <button type="button" onClick={() => setShowForm(false)} style={btnSecondary}>取消</button>
          </div>
        </form>
      )}

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} style={{ ...inputStyle, width: 130 }}>
          <option value="">所有狀態</option>
          <option value="pending">待審批</option>
          <option value="approved">已批准</option>
          <option value="rejected">已拒絕</option>
        </select>
        <input
          placeholder="搜尋買手姓名"
          value={filterBuyer}
          onChange={(e) => setFilterBuyer(e.target.value)}
          style={{ ...inputStyle, width: 180 }}
        />
      </div>

      {/* Claims table */}
      {claims.length === 0 && !loading ? (
        <p style={{ color: "#999", textAlign: "center", padding: "40px 0" }}>暫無報帳記錄</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f0f0f0", textAlign: "left" }}>
                {["買手", "金額", "類別", "說明", "狀態", "提交時間", "操作"].map((h) => (
                  <th key={h} style={{ padding: "8px 10px", borderBottom: "2px solid #ddd", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {claims.map((c, i) => (
                <tr key={c.id} style={{ background: i % 2 === 0 ? "#fff" : "#fafafa", verticalAlign: "top" }}>
                  <td style={tdStyle}>{c.buyer_name}</td>
                  <td style={{ ...tdStyle, whiteSpace: "nowrap", fontVariantNumeric: "tabular-nums" }}>{fmtAmount(c.amount, c.currency)}</td>
                  <td style={tdStyle}>{CATEGORY_LABELS[c.category] ?? c.category}</td>
                  <td style={{ ...tdStyle, maxWidth: 220, wordBreak: "break-word" }}>
                    {c.description}
                    {c.receipt_url && (
                      <><br /><a href={c.receipt_url} target="_blank" rel="noreferrer" style={{ color: "#1565c0", fontSize: 12 }}>收據 ↗</a></>
                    )}
                    {c.reviewer_note && (
                      <><br /><span style={{ color: "#666", fontSize: 12 }}>備注：{c.reviewer_note}</span></>
                    )}
                  </td>
                  <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>
                    <span style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 12,
                      fontSize: 12,
                      fontWeight: 600,
                      color: "#fff",
                      background: STATUS_COLORS[c.status] ?? "#888",
                    }}>
                      {STATUS_LABELS[c.status] ?? c.status}
                    </span>
                    {c.reviewer && <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>by {c.reviewer}</div>}
                  </td>
                  <td style={{ ...tdStyle, whiteSpace: "nowrap", fontSize: 12, color: "#555" }}>{fmtDate(c.submitted_at)}</td>
                  <td style={tdStyle}>
                    {c.status === "pending" && (
                      <button
                        onClick={() => { setReviewTarget(c); setReviewNote(""); setReviewer(""); }}
                        style={{ ...btnSecondary, padding: "4px 10px", fontSize: 12 }}
                      >
                        審批
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Review modal */}
      {reviewTarget && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 999,
        }}
          onClick={(e) => { if (e.target === e.currentTarget) setReviewTarget(null); }}
        >
          <div style={{ background: "#fff", borderRadius: 10, padding: 24, width: 420, maxWidth: "90vw", boxShadow: "0 8px 32px rgba(0,0,0,0.18)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16 }}>審批報帳單</h3>
            <div style={{ fontSize: 13, marginBottom: 12, color: "#444" }}>
              <strong>{reviewTarget.buyer_name}</strong> — {fmtAmount(reviewTarget.amount, reviewTarget.currency)}<br />
              <span style={{ color: "#666" }}>{reviewTarget.description}</span>
            </div>
            <div style={{ marginBottom: 10 }}>
              <label style={labelStyle}>審批人</label>
              <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} style={inputStyle} placeholder="你的姓名" />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>備注（可選）</label>
              <textarea rows={2} value={reviewNote} onChange={(e) => setReviewNote(e.target.value)} style={{ ...inputStyle, resize: "vertical" }} placeholder="例如：金額偏高，需補充收據" />
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => handleReview("approved")} style={{ ...btnPrimary, background: "#2e7d32" }} disabled={loading}>
                ✓ 批准
              </button>
              <button onClick={() => handleReview("rejected")} style={{ ...btnPrimary, background: "#c62828" }} disabled={loading}>
                ✕ 拒絕
              </button>
              <button onClick={() => setReviewTarget(null)} style={btnSecondary}>取消</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "7px 10px",
  border: "1px solid #ccc",
  borderRadius: 5,
  fontSize: 13,
  boxSizing: "border-box",
  outline: "none",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  color: "#555",
  marginBottom: 4,
};

const btnPrimary: React.CSSProperties = {
  padding: "8px 16px",
  background: "#1a237e",
  color: "#fff",
  border: "none",
  borderRadius: 5,
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 600,
};

const btnSecondary: React.CSSProperties = {
  padding: "8px 16px",
  background: "#fff",
  color: "#333",
  border: "1px solid #ccc",
  borderRadius: 5,
  cursor: "pointer",
  fontSize: 13,
};

const tdStyle: React.CSSProperties = {
  padding: "9px 10px",
  borderBottom: "1px solid #eee",
};
