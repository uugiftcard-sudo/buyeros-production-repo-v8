/**
 * Edge Function: admin-users
 * supabase/functions/admin-users/index.ts
 *
 * 管理員用戶 API
 * GET  /functions/v1/admin-users        — 用戶列表
 * POST /functions/v1/admin-users        — 創建用戶
 * GET  /functions/v1/admin-users/:id    — 用戶詳情
 * PATCH /functions/v1/admin-users/:id   — 更新用戶
 * DELETE /functions/v1/admin-users/:id  — 停用用戶
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { jsonResponse, errorResponse } from '../_shared/index.ts';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204 });

  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split('/').filter(Boolean);
    const extra = pathParts.slice(pathParts.indexOf('admin-users') + 1);
    const id = extra[0];

    switch (req.method) {
      case 'GET': return id ? await getUser(id) : await listUsers(req);
      case 'POST': return await createUser(req);
      case 'PATCH': {
        if (!id) return errorResponse('BAD_REQUEST', 'User ID required', 400);
        return await updateUser(id, req);
      }
      case 'DELETE': {
        if (!id) return errorResponse('BAD_REQUEST', 'User ID required', 400);
        return await deactivateUser(id);
      }
      default: return errorResponse('METHOD_NOT_ALLOWED', 'Invalid method', 405);
    }
  } catch (err) {
    console.error('admin-users API error:', err);
    return errorResponse('INTERNAL_ERROR', 'Internal error',
      500, err instanceof Error ? err.message : String(err));
  }
});

const ROLES = ['owner', 'admin', 'manager', 'supervisor', 'staff'];
const PAGE_SIZE = 30;

async function listUsers(req: Request) {
  const url = new URL(req.url);
  const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1'));
  const role = url.searchParams.get('role') ?? '';
  const search = url.searchParams.get('search') ?? '';
  const offset = (page - 1) * PAGE_SIZE;

  let query = supabase
    .from('admin_users')
    .select('*', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range(offset, offset + PAGE_SIZE - 1);

  if (role) query = query.eq('role', role);
  query = query.eq('is_active', true);

  const { data, error, count } = await query;
  if (error) return errorResponse('DB_ERROR', 'Failed to list users', 500, error);

  let filtered = data ?? [];
  if (search) {
    const q = search.toLowerCase();
    filtered = filtered.filter(u =>
      u.display_name?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      u.phone?.toLowerCase().includes(q)
    );
  }

  // Fetch stats per user
  const withStats = await Promise.all(filtered.map(async (u) => {
    const { count: orderCount } = await supabase
      .from('orders')
      .select('*', { count: 'exact', head: true })
      .eq('customer_id', u.id);
    return { ...u, stats: { orders: orderCount ?? 0 } };
  }));

  return jsonResponse({
    data: withStats,
    meta: {
      page, pageSize: PAGE_SIZE, total: count ?? 0,
      totalPages: Math.ceil((count ?? 0) / PAGE_SIZE),
    },
    roles: ROLES,
  });
}

async function getUser(id: string) {
  const { data, error } = await supabase
    .from('admin_users')
    .select('*')
    .eq('id', id)
    .single();

  if (error || !data) return errorResponse('NOT_FOUND', 'User not found', 404);
  return jsonResponse(data);
}

async function createUser(req: Request) {
  const body = await req.json();
  const { telegram_user_id, email, display_name, role = 'staff', team_id, phone, permissions } = body;

  if (!display_name?.trim()) return errorResponse('VALIDATION_ERROR', 'display_name required', 400);
  if (role && !ROLES.includes(role)) return errorResponse('VALIDATION_ERROR', `role must be one of: ${ROLES.join(', ')}`, 400);

  const { data, error } = await supabase
    .from('admin_users')
    .insert({
      display_name: display_name.trim(),
      telegram_user_id: telegram_user_id ?? null,
      email: email?.trim() ?? null,
      phone: phone?.trim() ?? null,
      role,
      team_id: team_id ?? null,
      permissions: permissions ?? [],
      is_active: true,
    })
    .select()
    .single();

  if (error) return errorResponse('DB_ERROR', 'Failed to create user', 500, error);
  return jsonResponse(data, 201);
}

async function updateUser(id: string, req: Request) {
  const body = await req.json();
  const allowed = ['display_name', 'role', 'team_id', 'phone', 'permissions', 'email', 'avatar_url', 'notes'];
  const updates: Record<string, unknown> = {};
  for (const key of allowed) {
    if (key in body) updates[key] = body[key];
  }
  updates.updated_at = new Date().toISOString();

  if (body.role && !ROLES.includes(body.role)) {
    return errorResponse('VALIDATION_ERROR', `role must be one of: ${ROLES.join(', ')}`, 400);
  }

  const { data, error } = await supabase
    .from('admin_users')
    .update(updates)
    .eq('id', id)
    .select()
    .single();

  if (error) return errorResponse('DB_ERROR', 'Failed to update user', 500, error);
  return jsonResponse(data);
}

async function deactivateUser(id: string) {
  const { error } = await supabase
    .from('admin_users')
    .update({ is_active: false, updated_at: new Date().toISOString() })
    .eq('id', id);

  if (error) return errorResponse('DB_ERROR', 'Failed to deactivate user', 500, error);
  return jsonResponse({ success: true });
}
