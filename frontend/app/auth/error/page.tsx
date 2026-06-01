"use client";
import { useRouter } from "next/navigation";

export default function AuthErrorPage() {
  const router = useRouter();
  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0a0a0f", color: "#f0f0f5" }}>
      <div style={{ textAlign: "center", maxWidth: 400 }}>
        <h1 style={{ fontSize: "2rem", marginBottom: "1rem" }}>認證錯誤</h1>
        <p style={{ color: "#888", marginBottom: "2rem" }}>登入過程中發生錯誤。請重試或聯繫管理員。</p>
        <button
          onClick={() => router.push("/auth/signin")}
          style={{ padding: "0.7rem 2rem", background: "#3b82f6", border: "none", borderRadius: 6, color: "#fff", fontWeight: 600, cursor: "pointer" }}
        >
          返回登入
        </button>
      </div>
    </main>
  );
}
