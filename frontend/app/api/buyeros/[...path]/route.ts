import { NextRequest, NextResponse } from "next/server";

type RouteContext = {
  params: Promise<{ path?: string[] }>;
};

const backendUrl = process.env.BUYEROS_BACKEND_URL || process.env.NEXT_PUBLIC_BUYEROS_API_URL || "http://backend:8000";
const fallbackBackendUrls = [
  backendUrl,
  "http://backend:8000",
  "http://127.0.0.1:8000",
];

const uniqOrderedBackendUrls = Array.from(new Set(fallbackBackendUrls.filter((value) => Boolean(value))));

async function proxy(request: NextRequest, context: RouteContext) {
  const params = await context.params;
  const path = (params.path || []).join("/");
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  // Server-side secret injection only — the key NEVER leaves the server.
  // Remove URL param fallback after confirming production uses BUYEROS_API_KEY env var.
  const envApiKey = process.env.BUYEROS_API_KEY;
  const uiApiKey = request.headers.get("x-buyeros-api-key");
  const apiKey = envApiKey || uiApiKey;  // uiApiKey only in local dev (no env var set)
  if (apiKey) headers.set("authorization", `Bearer ${apiKey}`);

  const method = request.method.toUpperCase();
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();
  let response: Response | null = null;
  let responseText = "";
  let lastError: Error | null = null;

  for (const base of uniqOrderedBackendUrls) {
    const target = new URL(`/${path}`, String(base).replace(/\/+$/, ""));
    target.search = request.nextUrl.search;
    try {
      response = await fetch(target, {
        method,
        headers,
        body,
        cache: "no-store"
      });
      responseText = await response.text();
      break;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
    }
  }

  if (!response) {
    return NextResponse.json(
      { ok: false, error: "backend_unreachable", message: lastError?.message || "backend proxy failed" },
      { status: 502 }
    );
  }
  return new NextResponse(responseText, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") || "application/json"
    }
  });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
