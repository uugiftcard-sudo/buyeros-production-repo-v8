// lib/supabase.ts — Supabase Browser Client (client-side)
import { createClient, SupabaseClient } from '@supabase/supabase-js';

function getSupabaseUrl(): string {
  return process.env.NEXT_PUBLIC_SUPABASE_URL ?? '';
}

function getSupabaseAnonKey(): string {
  return process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '';
}

/** 用於客戶端組件（瀏覽器）— lazy initialization to survive static pre-rendering */
let _supabase: SupabaseClient | null = null;
export function getSupabaseClient(): SupabaseClient {
  if (!_supabase) {
    const url = getSupabaseUrl();
    const key = getSupabaseAnonKey();
    if (!url || !key) {
      // Return a dummy client during build; runtime will replace it
      _supabase = createClient('https://placeholder.supabase.co', 'placeholder-build-key');
      return _supabase;
    }
    _supabase = createClient(url, key);
  }
  return _supabase;
}

/** Backward-compatible named export — resolves at call time, not module eval time */
export const supabase = {
  get client() { return getSupabaseClient(); },
} as unknown as SupabaseClient;

/** 用於 Server Components 和 API Routes */
export async function createServerClient() {
  const url = getSupabaseUrl();
  const key = getSupabaseAnonKey();
  if (!url || !key) throw new Error('NEXT_PUBLIC_SUPABASE_URL / ANON_KEY not set');
  const { createServerClient: createServer } = await import('@supabase/ssr');
  return createServer(url, key, {
    cookies: {
      getAll() { return []; },
      setAll() {},
    },
  });
}
