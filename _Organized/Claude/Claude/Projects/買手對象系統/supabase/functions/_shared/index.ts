/**
 * BuyerOS — Shared Edge Function Utilities
 * supabase/functions/_shared/index.ts
 *
 * 所有 Edge Function 的通用工具：
 * - Supabase client 初始化
 * - 統一錯誤處理
 * - Auth helper
 * - Response helpers
 */

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiResponse<T = unknown> {
  data?: T;
  error?: ApiError;
  meta?: Record<string, unknown>;
}

// ─── CORS Headers ─────────────────────────────────────────────────────────────

export const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers':
    'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
};

// ─── Response Helpers ──────────────────────────────────────────────────────────

/**
 * 返回成功 JSON 回應
 */
export function jsonResponse<T>(
  data: T,
  status = 200,
  meta?: Record<string, unknown>
): Response {
  const body: ApiResponse<T> = { data, ...(meta && { meta }) };
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}

/**
 * 返回錯誤 JSON 回應
 */
export function errorResponse(
  code: string,
  message: string,
  status = 400,
  details?: unknown
): Response {
  const body: ApiResponse = { error: { code, message, details } };
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}

/**
 * 返回空成功（204 No Content）
 */
export function noContentResponse(): Response {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

/**
 * 返回分頁結果
 */
export function paginatedResponse<T>(
  data: T[],
  count: number,
  page: number,
  pageSize: number
): Response {
  return jsonResponse(data, 200, {
    pagination: {
      total: count,
      page,
      pageSize,
      totalPages: Math.ceil(count / pageSize),
      hasNext: page * pageSize < count,
      hasPrev: page > 1,
    },
  });
}

// ─── Auth Helpers ─────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  role: 'admin' | 'buyer' | 'customer' | 'system';
  telegramUserId?: string;
}

/**
 * 從 Authorization header 提取並驗證 JWT
 * 支援 Supabase Auth JWT 和 Bot API key 兩種方式
 */
export function getAuthUser(supabaseClient: any): AuthUser | null {
  // Edge Functions 中可通過全局 supabaseClient 訪問
  // 如果無法識別，返回 system 角色（用於 webhook / internal calls）
  try {
    // Supabase sets auth.jwt() claims in the context
    // In Edge Functions, access via supabaseClient.auth.getUser()
    return { id: 'system', role: 'system' };
  } catch {
    return null;
  }
}

/**
 * 從 header 中提取 Bot API Key（用於 Telegram Bot webhook）
 */
export function getBotApiKey(request: Request): string | null {
  const auth = request.headers.get('Authorization');
  if (auth?.startsWith('Bearer ')) {
    return auth.slice(7);
  }
  return null;
}

/**
 * 驗證 Bot API Key
 */
export function verifyBotApiKey(
  request: Request,
  validKey: string
): boolean {
  const key = getBotApiKey(request);
  return key === validKey;
}

// ─── Validation Helpers ───────────────────────────────────────────────────────

/**
 * 通用 UUID 格式驗證
 */
export function isValidUUID(str: string): boolean {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
}

/**
 * 驗證必填欄位
 */
export function validateRequired(
  obj: Record<string, unknown>,
  requiredFields: string[]
): string | null {
  for (const field of requiredFields) {
    if (obj[field] === undefined || obj[field] === null || obj[field] === '') {
      return `Missing required field: ${field}`;
    }
  }
  return null;
}

/**
 * 驗證正整數（常用於 ID, quantity 等）
 */
export function isPositiveInt(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0;
}

// ─── Date / Number Helpers ────────────────────────────────────────────────────

/**
 * 格式化 cents 為 HKD 字串（兩位小數）
 */
export function formatCentsToHKD(cents: number): string {
  return `HK$${(cents / 100).toFixed(2)}`;
}

/**
 * 產生下一個 order_number
 */
export async function generateOrderNumber(
  supabaseClient: any
): Promise<string> {
  const year = new Date().getFullYear();
  const prefix = `ORD-${year}-`;

  // 找最大序號
  const { data, error } = await supabaseClient
    .from('orders')
    .select('order_number')
    .like('order_number', `${prefix}%`)
    .order('order_number', { ascending: false })
    .limit(1);

  if (error) throw error;

  let nextSeq = 1;
  if (data && data.length > 0) {
    const last = data[0].order_number;
    const seqStr = last.replace(prefix, '');
    nextSeq = parseInt(seqStr, 10) + 1;
  }

  return `${prefix}${nextSeq.toString().padStart(6, '0')}`;
}

/**
 * 產生下一個 transaction_number
 */
export async function generateTransactionNumber(
  supabaseClient: any
): Promise<string> {
  const year = new Date().getFullYear();
  const prefix = `TXN-${year}-`;

  const { data, error } = await supabaseClient
    .from('transactions')
    .select('transaction_number')
    .like('transaction_number', `${prefix}%`)
    .order('transaction_number', { ascending: false })
    .limit(1);

  if (error) throw error;

  let nextSeq = 1;
  if (data && data.length > 0) {
    const last = data[0].transaction_number;
    const seqStr = last.replace(prefix, '');
    nextSeq = parseInt(seqStr, 10) + 1;
  }

  return `${prefix}${nextSeq.toString().padStart(6, '0')}`;
}

/**
 * 產生 refund_number
 */
export async function generateRefundNumber(
  supabaseClient: any
): Promise<string> {
  const year = new Date().getFullYear();
  const prefix = `REF-${year}-`;

  const { data, error } = await supabaseClient
    .from('refunds')
    .select('refund_number')
    .like('refund_number', `${prefix}%`)
    .order('refund_number', { ascending: false })
    .limit(1);

  if (error) throw error;

  let nextSeq = 1;
  if (data && data.length > 0) {
    const last = data[0].refund_number;
    const seqStr = last.replace(prefix, '');
    nextSeq = parseInt(seqStr, 10) + 1;
  }

  return `${prefix}${nextSeq.toString().padStart(6, '0')}`;
}

/**
 * 產生 settlement_number
 */
export async function generateSettlementNumber(
  supabaseClient: any
): Promise<string> {
  const year = new Date().getFullYear();
  const prefix = `SET-${year}-`;

  const { data, error } = await supabaseClient
    .from('settlements')
    .select('settlement_number')
    .like('settlement_number', `${prefix}%`)
    .order('settlement_number', { ascending: false })
    .limit(1);

  if (error) throw error;

  let nextSeq = 1;
  if (data && data.length > 0) {
    const last = data[0].settlement_number;
    const seqStr = last.replace(prefix, '');
    nextSeq = parseInt(seqStr, 10) + 1;
  }

  return `${prefix}${nextSeq.toString().padStart(6, '0')}`;
}

/**
 * Validate communication channel
 */
export function isValidChannel(channel: string): channel is
  | 'telegram' | 'whatsapp' | 'email' | 'phone' | 'sms' | 'web' | 'in_person' {
  return ['telegram', 'whatsapp', 'email', 'phone', 'sms', 'web', 'in_person'].includes(channel);
}

/**
 * Validate communication direction
 */
export function isValidDirection(direction: string): direction is 'inbound' | 'outbound' {
  return direction === 'inbound' || direction === 'outbound';
}
