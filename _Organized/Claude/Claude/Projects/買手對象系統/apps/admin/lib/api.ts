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
  return apiFetch<{ data?: Customer[]; meta?: { pagination: any } }>(
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
  return apiFetch<{ data?: Transaction[]; meta?: any }>(`transactions${qsStr ? `?${qsStr}` : ''}`);
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
  return apiFetch<{ data?: Refund[]; meta?: any }>(`refunds${qsStr ? `?${qsStr}` : ''}`);
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
