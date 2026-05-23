// lib/supabase.ts — Supabase Browser Client (client-side)
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY env vars'
  );
}

/** 用於客戶端組件（瀏覽器） */
export const supabase = createClient(supabaseUrl, supabaseAnonKey);

/** 用於 Server Components 和 API Routes */
export async function createServerClient() {
  const { createServerClient: createServer } = await import('@supabase/ssr');
  return createServer(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() { return []; },
      setAll() {},
    },
  });
}
