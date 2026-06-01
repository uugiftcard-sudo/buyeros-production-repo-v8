export default function Loading() {
  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      background: "#0a0a0f",
      color: "#888",
      fontFamily: "system-ui, sans-serif",
      gap: "1rem",
    }}>
      <div style={{
        width: 40, height: 40,
        border: "3px solid #1e1e2e",
        borderTopColor: "#3b82f6",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <p style={{ fontSize: "0.9rem", letterSpacing: "0.05em" }}>BuyerOS 載入中…</p>
    </div>
  );
}
