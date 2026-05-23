/**
 * Edge Function: audit-log
 * supabase/functions/audit-log/index.ts
 *
 * 審計日誌 API
 * GET /functions/v1/audit-log          — 日誌列表（分頁）
 * GET /functions/v1/audit-log/summary   — 日誌摘要統計
 * GET /functions/v1/audit-log/export    — CSV 導出
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

    if (url.pathname.endsWith('/export')) {
      return await exportCsv(req);
    }
    if (url.pathname.endsWith('/summary')) {
      return await getSummary();
    }
    return await listLogs(req);
  } catch (err) {
    console.error('audit-log API error:', err);
    return errorResponse('INTERNAL_ERROR', 'Internal error',
      500, err instanceof Error ? err.message : String(err));
  }
});

const PAGE_SIZE = 50;

async function listLogs(req: Request) {
  const url = new URL(req.url);
  const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1'));
  const table = url.searchParams.get('table') ?? '';
  const action = url.searchParams.get('action') ?? '';
  const role = url.searchParams.get('role') ?? '';
  const fromDate = url.searchParams.get('from') ?? '';
  const toDate = url.searchParams.get('to') ?? '';
  const search = url.searchParams.get('search') ?? '';
  const offset = (page - 1) * PAGE_SIZE;

  let query = supabase
    .from('audit_log')
    .select('*', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range(offset, offset + PAGE_SIZE - 1);

  if (table) query = query.eq('table_name', table);
  if (action) query = query.eq('action', action);
  if (role) query = query.eq('changed_by_role', role);
  if (fromDate) query = query.gte('created_at', fromDate + 'T00:00:00Z');
  if (toDate) query = query.lte('created_at', toDate + 'T23:59:59Z');

  const { data, error, count } = await query;

  if (error) return errorResponse('DB_ERROR', 'Failed to fetch audit log', 500, error);

  let filtered = data ?? [];
  if (search) {
    const q = search.toLowerCase();
    filtered = filtered.filter(r =>
      r.table_name?.toLowerCase().includes(q) ||
      r.changed_by_name?.toLowerCase().includes(q) ||
      r.reason?.toLowerCase().includes(q) ||
      r.row_id?.toLowerCase().includes(q)
    );
  }

  return jsonResponse({
    data: filtered,
    meta: {
      page,
      pageSize: PAGE_SIZE,
      total: count ?? 0,
      totalPages: Math.ceil((count ?? 0) / PAGE_SIZE),
    },
    tables: ['orders', 'buyers', 'customers', 'transactions', 'refunds', 'settlements'],
    actions: ['INSERT', 'UPDATE', 'DELETE'],
    roles: ['owner', 'admin', 'manager', 'supervisor', 'staff', 'buyer', 'customer', 'system'],
  });
}

async function getSummary() {
  // 今日、本週、本月的操作統計
  const [todayResult, weekResult, monthResult, byTableResult] = await Promise.all([
    supabase.from('audit_log').select('*', { count: 'exact', head: true })
      .gte('created_at', new Date(new Date().setHours(0, 0, 0, 0)).toISOString()),
    supabase.from('audit_log').select('*', { count: 'exact', head: true })
      .gte('created_at', new Date(Date.now() - 7 * 86400000).toISOString()),
    supabase.from('audit_log').select('*', { count: 'exact', head: true })
      .gte('created_at', new Date(Date.now() - 30 * 86400000).toISOString()),
    supabase.rpc('audit_log_by_table', {}).select('table_name, count').order('count', { ascending: false }).limit(10),
  ]);

  // 最近24小時的按小時統計
  const { data: hourlyData } = await supabase
    .from('audit_log')
    .select('created_at, action')
    .gte('created_at', new Date(Date.now() - 24 * 3600000).toISOString())
    .order('created_at');

  const hourlyStats: Record<string, { insert: number; update: number; delete: number }> = {};
  if (hourlyData) {
    for (const row of hourlyData) {
      const hour = new Date(row.created_at).getHours().toString().padStart(2, '0') + ':00';
      if (!hourlyStats[hour]) hourlyStats[hour] = { insert: 0, update: 0, delete: 0 };
      const a = row.action?.toLowerCase();
      if (a === 'insert') hourlyStats[hour].insert++;
      else if (a === 'update') hourlyStats[hour].update++;
      else if (a === 'delete') hourlyStats[hour].delete++;
    }
  }

  return jsonResponse({
    counts: {
      today: todayResult.count ?? 0,
      thisWeek: weekResult.count ?? 0,
      thisMonth: monthResult.count ?? 0,
    },
    byTable: byTableResult.data ?? [],
    hourlyStats: Object.entries(hourlyStats).map(([hour, counts]) => ({ hour, ...counts })),
  });
}

async function exportCsv(req: Request) {
  const url = new URL(req.url);
  const table = url.searchParams.get('table') ?? '';
  const fromDate = url.searchParams.get('from') ?? '';
  const toDate = url.searchParams.get('to') ?? '';
  const limit = Math.min(10000, parseInt(url.searchParams.get('limit') ?? '1000'));

  let query = supabase
    .from('audit_log')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit);

  if (table) query = query.eq('table_name', table);
  if (fromDate) query = query.gte('created_at', fromDate + 'T00:00:00Z');
  if (toDate) query = query.lte('created_at', toDate + 'T23:59:59Z');

  const { data, error } = await query;
  if (error) return errorResponse('DB_ERROR', 'Failed to export', 500, error);

  const headers = ['時間', '操作', '資料表', '記錄ID', '角色', '用戶', '原因', '舊數據', '新數據'];
  const rows = (data ?? []).map(r => [
    new Date(r.created_at).toLocaleString('zh-HK'),
    r.action,
    r.table_name,
    r.row_id,
    r.changed_by_role ?? '',
    r.changed_by_name ?? '',
    r.reason ?? '',
    JSON.stringify(r.old_data ?? {}),
    JSON.stringify(r.new_data ?? {}),
  ]);

  const csvContent = [
    headers.join(','),
    ...rows.map(row => row.map(cell =>
      `"${String(cell).replace(/"/g, '""')}"`
    ).join(',')),
  ].join('\n');

  const headers_ = new Headers();
  headers_.set('Content-Type', 'text/csv; charset=utf-8');
  headers_.set('Content-Disposition', `attachment; filename="audit_log_${new Date().toISOString().slice(0, 10)}.csv"`);

  return new Response('\ufeff' + csvContent, { status: 200, headers: headers_ });
}
