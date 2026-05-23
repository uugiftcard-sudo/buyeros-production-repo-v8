/**
 * Edge Function: customers
 * supabase/functions/customers/index.ts
 *
 * 客戶管理 API
 * GET    /functions/v1/customers        — 列表（支援分頁、搜索）
 * POST   /functions/v1/customers        — 新增客戶
 * GET    /functions/v1/customers/:id    — 取得單一客戶
 * PATCH  /functions/v1/customers/:id   — 更新客戶
 * DELETE /functions/v1/customers/:id    — 刪除（軟刪除：設為 inactive）
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import {
  jsonResponse,
  errorResponse,
  paginatedResponse,
  validateRequired,
  isValidUUID,
} from '../_shared/index.ts';

// ─── Environment ────────────────────────────────────────────────────────────────

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const botApiKey = Deno.env.get('BOT_API_KEY') ?? '';

// ─── Supabase Client ───────────────────────────────────────────────────────────

const supabase = createClient(supabaseUrl, supabaseServiceKey);

// ─── Main Handler ──────────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204 });
  }

  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split('/').filter(Boolean);

    // /functions/v1/customers[/:id]
    const id = pathParts[pathParts.length - 1] !== 'customers'
      ? pathParts[pathParts.length - 1]
      : null;

    switch (req.method) {
      case 'GET':
        if (id) {
          return await getCustomer(id);
        }
        return await listCustomers(url);

      case 'POST':
        return await createCustomer(await req.json());

      case 'PATCH':
        if (!id) return errorResponse('MISSING_ID', 'Customer ID is required', 400);
        return await updateCustomer(id, await req.json());

      case 'DELETE':
        if (!id) return errorResponse('MISSING_ID', 'Customer ID is required', 400);
        return await deleteCustomer(id);

      default:
        return errorResponse(
          'METHOD_NOT_ALLOWED',
          `Method ${req.method} is not supported`,
          405
        );
    }
  } catch (err) {
    console.error('customers API error:', err);
    return errorResponse(
      'INTERNAL_ERROR',
      'An internal error occurred',
      500,
      err instanceof Error ? err.message : String(err)
    );
  }
});

// ─── GET /functions/v1/customers ─────────────────────────────────────────────

async function listCustomers(url: URL) {
  const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1'));
  const pageSize = Math.min(100, Math.max(1, parseInt(url.searchParams.get('pageSize') ?? '20')));
  const offset = (page - 1) * pageSize;
  const search = url.searchParams.get('search')?.trim() ?? '';
  const status = url.searchParams.get('status') ?? '';

  let query = supabase
    .from('customers')
    .select('*', { count: 'exact' });

  // 搜索：display_name 或 phone
  if (search) {
    query = query.or(
      `display_name.ilike.%${search}%,phone.ilike.%${search}%,email.ilike.%${search}%`
    );
  }

  // 狀態過濾
  if (status) {
    query = query.eq('status', status);
  }

  query = query
    .order('created_at', { ascending: false })
    .range(offset, offset + pageSize - 1);

  const { data, error, count } = await query;

  if (error) {
    return errorResponse('DB_ERROR', 'Failed to fetch customers', 500, error);
  }

  return paginatedResponse(data ?? [], count ?? 0, page, pageSize);
}

// ─── GET /functions/v1/customers/:id ─────────────────────────────────────────

async function getCustomer(id: string) {
  if (!isValidUUID(id)) {
    return errorResponse('INVALID_ID', 'Invalid customer ID format', 400);
  }

  const { data, error } = await supabase
    .from('customers')
    .select('*')
    .eq('id', id)
    .single();

  if (error || !data) {
    return errorResponse('NOT_FOUND', 'Customer not found', 404);
  }

  // 取得關聯的訂單
  const { data: orders } = await supabase
    .from('orders')
    .select('id, order_number, status, total_amount_cents, created_at')
    .eq('customer_id', id)
    .order('created_at', { ascending: false })
    .limit(10);

  return jsonResponse({ ...data, recent_orders: orders ?? [] });
}

// ─── POST /functions/v1/customers ─────────────────────────────────────────────

async function createCustomer(body: Record<string, unknown>) {
  // 必填欄位驗證
  const required = ['display_name'];
  const missing = validateRequired(body, required);
  if (missing) {
    return errorResponse('VALIDATION_ERROR', missing, 400);
  }

  // Telegram ID 唯一性檢查
  if (body.telegram_user_id) {
    const { data: existing } = await supabase
      .from('customers')
      .select('id')
      .eq('telegram_user_id', body.telegram_user_id)
      .single();

    if (existing) {
      return errorResponse(
        'DUPLICATE_TELEGRAM_ID',
        'A customer with this Telegram ID already exists',
        409
      );
    }
  }

  const { data, error } = await supabase
    .from('customers')
    .insert({
      display_name: body.display_name,
      telegram_user_id: body.telegram_user_id ?? null,
      phone: body.phone ?? null,
      email: body.email ?? null,
      status: body.status ?? 'active',
      notes: body.notes ?? null,
    })
    .select()
    .single();

  if (error) {
    return errorResponse('DB_ERROR', 'Failed to create customer', 500, error);
  }

  return jsonResponse(data, 201);
}

// ─── PATCH /functions/v1/customers/:id ──────────────────────────────────────

async function updateCustomer(id: string, body: Record<string, unknown>) {
  if (!isValidUUID(id)) {
    return errorResponse('INVALID_ID', 'Invalid customer ID format', 400);
  }

  // 只允許更新特定欄位
  const allowedFields = [
    'display_name',
    'phone',
    'email',
    'status',
    'notes',
  ];
  const updates: Record<string, unknown> = {};
  for (const field of allowedFields) {
    if (body[field] !== undefined) {
      updates[field] = body[field];
    }
  }

  if (Object.keys(updates).length === 0) {
    return errorResponse('NO_UPDATES', 'No valid fields to update', 400);
  }

  const { data, error } = await supabase
    .from('customers')
    .update(updates)
    .eq('id', id)
    .select()
    .single();

  if (error || !data) {
    return errorResponse('NOT_FOUND', 'Customer not found', 404);
  }

  return jsonResponse(data);
}

// ─── DELETE /functions/v1/customers/:id ───────────────────────────────────────

async function deleteCustomer(id: string) {
  if (!isValidUUID(id)) {
    return errorResponse('INVALID_ID', 'Invalid customer ID format', 400);
  }

  // 軟刪除：設為 inactive
  const { error } = await supabase
    .from('customers')
    .update({ status: 'inactive' })
    .eq('id', id);

  if (error) {
    return errorResponse('DB_ERROR', 'Failed to deactivate customer', 500, error);
  }

  return jsonResponse({ id, status: 'inactive' });
}
