"use client";
import { signIn } from "next-auth/react";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";

export default function SignInPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const result = await signIn("credentials", {
      username,
      password,
      redirect: false,
    });
    if (result?.error) {
      setError("無效的登入憑證。請聯繫管理員。");
      setLoading(false);
    } else {
      router.push("/");
      router.refresh();
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0a0a0f", color: "#f0f0f5" }}>
      <div style={{ background: "#13131a", border: "1px solid #2a2a3a", borderRadius: 12, padding: "2.5rem", width: "100%", maxWidth: 400 }}>
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "0.25rem" }}>BuyerOS</h1>
          <p style={{ color: "#888", fontSize: "0.875rem" }}>AI 團隊指揮中心 — 專業版</p>
        </div>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", color: "#aaa", marginBottom: "0.25rem" }}>帳戶名稱</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              style={{ width: "100%", padding: "0.6rem 0.8rem", background: "#1a1a26", border: "1px solid #2a2a3a", borderRadius: 6, color: "#f0f0f5", fontSize: "0.9rem" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", color: "#aaa", marginBottom: "0.25rem" }}>密碼</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={{ width: "100%", padding: "0.6rem 0.8rem", background: "#1a1a26", border: "1px solid #2a2a3a", borderRadius: 6, color: "#f0f0f5", fontSize: "0.9rem" }}
            />
          </div>
          {error && <p style={{ color: "#f87171", fontSize: "0.85rem", margin: 0 }}>{error}</p>}
          <button
            type="submit"
            disabled={loading}
            style={{ padding: "0.7rem", background: "#3b82f6", border: "none", borderRadius: 6, color: "#fff", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1 }}
          >
            {loading ? "登入中..." : "登入"}
          </button>
        </form>
        <p style={{ textAlign: "center", color: "#555", fontSize: "0.75rem", marginTop: "1.5rem" }}>
          BuyerOS v8 — {process.env.NEXT_PUBLIC_VERSION || "Professional Edition"}
        </p>
      </div>
    </main>
  );
}
