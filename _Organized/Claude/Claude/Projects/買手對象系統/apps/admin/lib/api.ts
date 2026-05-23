// lib/api.ts — API Client for Edge Functions
// 所有對 Edge Functions 的請求都通過這裡

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

async function apiFetch<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ data?: T; error?: { code: string; message: string } }> {
  const url = `${SUPABASE_URL}/functions/v1/${endpoint}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${ANON_KEY}`,
      ...options.headers,
    },
  });

  const json = await res.json();

  if (!res.ok) {
    const jsonErr = json as { error?: unknown; message?: unknown };
    const err = jsonErr.error as { code?: string; message?: string } | undefined;
    return {
      error: {
        code: err?.code ?? 'REQUEST_FAILED',
        message: err?.message ?? (jsonErr.message as string) ?? `HTTP ${res.status}`,
      },
    };
  }

  const jsonData = json as { data?: T };
  return { data: jsonData.data };
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export async function getDashboardSummary() {
  return apiFetch<{
    orders: { total: number; pending: number };
    buyers: { active: number };
    customers: { active: number };
    financials: {
      total_revenue_cents: number;
      total_refunds_cents: number;
      net_revenue_cents: number;
      net_revenue_hkd: string;
    };
  }>('dashboard/summary');
}

// ─── Customers ────────────────────────────────────────────────────────────────

export interface Customer {
  id: string;
  telegram_user_id?: number | null;
  display_name: string;
  phone: string | null;
  email: string | null;
  status: string;
  notes: string | null;
  created_at: string;
  recent_orders?: { id: string; order_number: string; status: string; total_amount_cents: number }[];
}

export async function getCustomers(params?: { page?: number; search?: string; status?: string }) {
  const qs = new URLSearchParams();
  if (params?.page) qs.set('page', String(params.page));
  if (params?.search) qs.set('search', params.search);
  if (params?.status) qs.set('status', params.status);

  const qsStr = qs.toString();
  return apiFetch<{ data?: Customer[]; meta?: { pagination: { total: number; page: number; pageSize: number; totalPages: number } } }>(
    `customers${qsStr ? `?${qsStr}` : ''}`
  );
}

export async function createCustomer(data: Partial<Customer>) {
  return apiFetch<Customer>('customers', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCustomer(id: string, data: Partial<Customer>) {
  return apiFetch<Customer>(`customers/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ─── Orders ─────────────────────────────────────────────────────────────────

export interface Order {
  id: string;
  order_number: string;
  customer_id: string;
  status: string;
  assigned_buyer_id: string | null;
  assigned_at?: string | null;
  total_amount_cents: number;
  deposit_paid_cents: number;
  balance_due_cents: number;
  delivery_address?: string | null;
  notes?: string | null;
  source_channel?: string;
  customer?: { id: string; display_name: string; phone?: string | null };
  buyer?: { id: string; display_name: string };
  items?: OrderItem[];
  created_at: string;
}

export interface OrderItem {
  id: string;
  order_id: string;
  product_name: string;
  product_url?: string | null;
  quantity: number;
  unit_price_cents: number;
  status: string;
  notes?: string | null;
}

export interface OrderListResponse {
  data?: Order[];
  meta?: { pagination: { total: number; page: number; pageSize: number; totalPages: number } };
}

export async function getOrders(params?: {
  page?: number;
  status?: string;
  buyer_id?: string;
  customer_id?: string;
}) {
  const qs = new URLSearchParams();
  if (params?.page) qs.set('page', String(params.page));
  if (params?.status) qs.set('status', params.status);
  if (params?.buyer_id) qs.set('buyer_id', params.buyer_id);
  if (params?.customer_id) qs.set('customer_id', params.customer_id);

  const qsStr = qs.toString();
  return apiFetch<OrderListResponse>(`orders${qsStr ? `?${qsStr}` : ''}`);
}

export async function getOrder(id: string) {
  return apiFetch<Order>(`orders/${id}`);
}

export async function assignBuyer(orderId: string, buyerId: string) {
  return apiFetch<Order>(`orders/${orderId}/assign`, {
    method: 'PATCH',
    body: JSON.stringify({ buyer_id: buyerId }),
  });
}

export async function updateOrder(id: string, data: Partial<Order>) {
  return apiFetch<Order>(`orders/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ─── Transactions ────────────────────────────────────────────────────────────

export interface Transaction {
  id: string;
  transaction_number: string;
  order_id: string | null;
  customer_id: string | null;
  type: string;
  amount_cents: number;
  currency: string;
  payment_method: string | null;
  status: string;
  paid_at?: string | null;
  created_at: string;
}

export async function getTransactions(params?: {
  page?: number;
  type?: string;
  status?: string;
  order_id?: string;
}) {
  const qs = new URLSearchParams();
  if (params?.page) qs.set('page', String(params.page));
  if (params?.type) qs.set('type', params.type);
  if (params?.status) qs.set('status', params.status);
  if (params?.order_id) qs.set('order_id', params.order_id);

  const qsStr = qs.toString();
  return apiFetch<{ data?: Transaction[]; meta?: { pagination: { total: number; page: number; pageSize: number; totalPages: number } } }>(`transactions${qsStr ? `?${qsStr}` : ''}`);
}

// ─── Refunds ────────────────────────────────────────────────────────────────

export interface Refund {
  id: string;
  refund_number: string;
  transaction_id: string;
  amount_cents: number;
  reason: string | null;
  reason_detail?: string | null;
  status: string;
  notes?: string | null;
  customer?: { id: string; display_name: string };
  created_at?: string;
}

export async function getRefunds(params?: { page?: number; status?: string }) {
  const qs = new URLSearchParams();
  if (params?.page) qs.set('page', String(params.page));
  if (params?.status) qs.set('status', params.status);

  const qsStr = qs.toString();
  return apiFetch<{ data?: Refund[]; meta?: { pagination: { total: number; page: number; pageSize: number; totalPages: number } } }>(`refunds${qsStr ? `?${qsStr}` : ''}`);
}

export async function updateRefund(id: string, data: { status: string; notes?: string }) {
  return apiFetch<Refund>(`refunds/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ─── Helpers ────────────────────────────────────────────────────────────────

export function formatCents(cents: number): string {
  return `HK$${(cents / 100).toFixed(2)}`;
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-HK', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

// ─── Buyers ────────────────────────────────────────────────────────────────

export interface Buyer {
  id: string;
  display_name: string;
  phone: string | null;
  status: string;
  rating_avg: number;
  rating_count: number;
  commission_rate: number | null;
  created_at: string;
  notes: string | null;
}

export async function getBuyers() {
  const result = await apiFetch<Buyer[]>('dashboard/buyers');
  return result;
}

// ─── Teams ────────────────────────────────────────────────────────────

export interface Team {
  id: string;
  team_name: string;
  team_code: string;
  description: string | null;
  manager_id: string | null;
  is_active: boolean;
  color: string;
  target_orders_monthly: number;
  target_revenue_monthly_cents: number;
  member_count: number;
  created_at: string;
  manager?: { id: string; display_name: string; email: string };
  members?: Array<{
    id: string;
    role: string;
    joined_at: string;
    is_active: boolean;
    buyer: Buyer;
  }>;
}

export interface TeamPerformance {
  team_id: string;
  team_name: string;
  team_code: string;
  member_count: number;
  total_orders: number;
  completed_orders: number;
  total_revenue_cents: number;
  avg_order_value_cents: number;
  monthly_orders: number;
  monthly_revenue_cents: number;
  target_orders_monthly: number;
  target_revenue_monthly_cents: number;
  monthly_orders_pct: number;
  monthly_revenue_pct: number;
}

export async function getTeams() {
  return apiFetch<Team[]>('teams');
}

export async function getTeam(id: string) {
  return apiFetch<Team>(`teams/${id}`);
}

export async function createTeam(data: Partial<Team>) {
  return apiFetch<Team>('teams', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateTeam(id: string, data: Partial<Team>) {
  return apiFetch<Team>(`teams/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function getTeamPerformance() {
  return apiFetch<TeamPerformance[]>('teams/performance');
}

// ─── Admin Users ─────────────────────────────────────────────────────

export interface AdminUser {
  id: string;
  display_name: string;
  email: string | null;
  phone: string | null;
  role: 'owner' | 'admin' | 'manager' | 'supervisor' | 'staff';
  team_id: string | null;
  is_active: boolean;
  last_login_at: string | null;
  permissions: string[];
  avatar_url: string | null;
  notes: string | null;
  created_at: string;
  stats?: { orders: number };
}

export async function getAdminUsers(params?: { page?: number; role?: string; search?: string }) {
  const qs = new URLSearchParams();
  if (params?.page) qs.set('page', String(params.page));
  if (params?.role) qs.set('role', params.role);
  if (params?.search) qs.set('search', params.search);
  const qsStr = qs.toString();
  return apiFetch<{ data?: AdminUser[]; meta?: { pagination: { total: number; page: number; pageSize: number; totalPages: number } }; roles: string[] }>(
    `admin-users${qsStr ? `?${qsStr}` : ''}`
  );
}

export async function createAdminUser(data: Partial<AdminUser>) {
  return apiFetch<AdminUser>('admin-users', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateAdminUser(id: string, data: Partial<AdminUser>) {
  return apiFetch<AdminUser>(`admin-users/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
}

// ─── Audit Log ──────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: string;
  created_at: string;
  table_name: string;
  row_id: string;
  action: 'INSERT' | 'UPDATE' | 'DELETE';
  old_data: Record<string, unknown> | null;
  new_data: Record<string, unknown> | null;
  changed_by: string | null;
  changed_by_role: string | null;
  changed_by_name: string | null;
  reason: string | null;
  ip_address: string | null;
}

export interface AuditLogResponse {
  data?: AuditLogEntry[];
  meta?: { page: number; pageSize: number; total: number; totalPages: number };
  tables: string[];
  actions: string[];
  roles: string[];
}

export interface AuditSummary {
  counts: { today: number; thisWeek: number; thisMonth: number };
  byTable: Array<{ table_name: string; count: number }>;
  hourlyStats: Array<{ hour: string; insert: number; update: number; delete: number }>;
}

export async function getAuditLog(params?: {
  page?: number; table?: string; action?: string; role?: string;
  from?: string; to?: string; search?: string;
}) {
  const qs = new URLSearchParams();
  if (params?.page) qs.set('page', String(params.page));
  if (params?.table) qs.set('table', params.table);
  if (params?.action) qs.set('action', params.action);
  if (params?.role) qs.set('role', params.role);
  if (params?.from) qs.set('from', params.from);
  if (params?.to) qs.set('to', params.to);
  if (params?.search) qs.set('search', params.search);
  const qsStr = qs.toString();
  return apiFetch<AuditLogResponse>(`audit-log${qsStr ? `?${qsStr}` : ''}`);
}

export async function getAuditSummary() {
  return apiFetch<AuditSummary>('audit-log/summary');
}

export async function exportAuditCsv(params?: { table?: string; from?: string; to?: string }) {
  const qs = new URLSearchParams();
  if (params?.table) qs.set('table', params.table);
  if (params?.from) qs.set('from', params.from);
  if (params?.to) qs.set('to', params.to);
  const qsStr = qs.toString();
  const res = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/functions/v1/audit-log/export${qsStr ? `?${qsStr}` : ''}`, {
    headers: {
      'Content-Type': 'application/json',
      'apikey': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      'Authorization': `Bearer ${process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY}`,
    },
  });
  const text = await res.text();
  const blob = new Blob(['\ufeff' + text], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `audit_log_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Batch Operations ────────────────────────────────────────────────

export interface BatchUpdateResult {
  updated: number;
  failed: number;
  errors: string[];
}

export async function batchUpdateOrders(ids: string[], data: Partial<Order>) {
  const results = await Promise.allSettled(
    ids.map(id => updateOrder(id, data))
  );
  const errors: string[] = [];
  let updated = 0;
  for (const r of results) {
    if (r.status === 'fulfilled' && !r.value.error) updated++;
    else errors.push(r.status === 'rejected' ? r.reason : 'Update failed');
  }
  return { data: { updated, failed: ids.length - updated, errors } };
}

export async function batchAssignBuyer(orderIds: string[], buyerId: string) {
  const results = await Promise.allSettled(
    orderIds.map(id => assignBuyer(id, buyerId))
  );
  const errors: string[] = [];
  let updated = 0;
  for (const r of results) {
    if (r.status === 'fulfilled' && !r.value.error) updated++;
    else errors.push(r.status === 'rejected' ? r.reason : 'Assignment failed');
  }
  return { data: { updated, failed: orderIds.length - updated, errors } };
}

// ─── CSV Export Helpers ──────────────────────────────────────────────

export function downloadCsv<T extends Record<string, unknown>>(rows: T[], filename: string) {
  if (rows.length === 0) return;
  const headers = Object.keys(rows[0]);
  const csv = [
    headers.join(','),
    ...rows.map(row =>
      headers.map(h => `"${String(row[h] ?? '').replace(/"/g, '""')}"`).join(',')
    ),
  ].join('\n');
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function exportOrdersCsv(params?: { status?: string; buyer_id?: string }) {
  const { data } = await getOrders(params);
  if (!data?.data) return;
  const rows = data.data.map(o => ({
    訂單號: o.order_number,
    客戶: o.customer?.display_name ?? '',
    買手: o.buyer?.display_name ?? '',
    狀態: o.status,
    總額: formatCents(o.total_amount_cents),
    已付: formatCents(o.deposit_paid_cents),
    尚欠: formatCents(o.balance_due_cents),
    建立日期: formatDate(o.created_at),
  }));
  downloadCsv(rows, 'orders');
}

export async function exportCustomersCsv() {
  const { data } = await getCustomers({ page: 1 });
  if (!data?.data) return;
  const rows = data.data.map(c => ({
    姓名: c.display_name,
    電話: c.phone ?? '',
    電郵: c.email ?? '',
    狀態: c.status,
    建立日期: formatDate(c.created_at),
  }));
  downloadCsv(rows, 'customers');
}

export async function exportBuyersCsv() {
  const result = await getBuyers();
  const rows = (result.data ?? []).map(b => ({
    名稱: b.display_name,
    電話: b.phone ?? '',
    狀態: b.status,
    評分: b.rating_avg > 0 ? b.rating_avg.toFixed(1) : '',
    評分次數: b.rating_count,
    佣金率: b.commission_rate != null ? `${(b.commission_rate * 100).toFixed(1)}%` : '',
    建立日期: formatDate(b.created_at),
  }));
  downloadCsv(rows, 'buyers');
}

