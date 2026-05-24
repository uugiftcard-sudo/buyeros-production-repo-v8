import type { Metadata } from "next";
import "./globals.css";
import { SessionProviderWrapper } from "@/components/SessionProviderWrapper";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { DebugPanel } from "@/components/DebugPanel";

export const metadata: Metadata = {
  title: "BuyerOS 管理台 — 專業版",
  description: "BuyerOS / AIOS shared context operations console — Professional Edition",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant">
      <body>
        <ErrorBoundary>
          <SessionProviderWrapper>
            {children}
            <DebugPanel />
          </SessionProviderWrapper>
        </ErrorBoundary>
      </body>
    </html>
  );
}
