"use client";
import { Component, ReactNode } from "react";

interface Props { children: ReactNode; fallback?: ReactNode; }
interface State { hasError: boolean; message: string; }

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[BuyerOS ErrorBoundary]", error, info.componentStack);
    if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
      fetch("/api/buyeros/system/capabilities", { method: "GET" }).catch(() => {});
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div style={{ padding: "2rem", background: "#1a0000", border: "1px solid #7f1d1d", borderRadius: 8, color: "#fca5a5", fontFamily: "monospace" }}>
          <strong>⚠ BuyerOS UI Error</strong>
          <pre style={{ fontSize: "0.75rem", marginTop: "0.5rem", whiteSpace: "pre-wrap" }}>
            {this.state.message}
          </pre>
          <button
            onClick={() => this.setState({ hasError: false, message: "" })}
            style={{ marginTop: "1rem", padding: "0.4rem 1rem", background: "#991b1b", border: "none", borderRadius: 4, color: "#fff", cursor: "pointer" }}
          >
            重試
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
