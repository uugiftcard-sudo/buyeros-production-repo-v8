/**
 * Edge Function: dashboard
 * supabase/functions/dashboard/index.ts
 *
 * 儀表板 API — 給 Admin Web UI 和 Bot 使用
 * GET /functions/v1/dashboard/summary      — 總覽數據
 * GET /functions/v1/dashboard/buyers       — 買手列表（含結算狀態）
 * GET /functions/v1/dashboard/financials   — 財務報表
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { jsonResponse, errorResponse } from '../_shared/index.ts';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204 });
  if (req.method !== 'GET') {
    return errorResponse('METHOD_NOT_ALLOWED', 'Only GET is supported', 405);
  }

  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split('/').filter(Boolean);
    const resource = pathParts[pathParts.length - 1] ?? 'summary';

    switch (resource) {
      case 'summary': return await getSummary();
      case 'buyers': return await getBuyersDashboard();
      case 'financials': return await getFinancials(url);
      default: {
        // Support /dashboard/buyers/:id — extract id from pathParts[pathParts.length - 2]
        const pathParts = url.pathname.split('/').filter(Boolean);
        const secondLast = pathParts[pathParts.length - 2];
        if (secondLast === 'buyers') {
          const id = pathParts[pathParts.length - 1];
          return await getBuyerById(id);
        }
        return errorResponse('NOT_FOUND', `Unknown resource: ${resource}`, 404);
      }
    }
  } catch (err) {
    console.error('dashboard API error:', err);
    return errorResponse('INTERNAL_ERROR', 'An internal error occurred', 500,
      err instanceof Error ? err.message : String(err));
  }
});

// ─── GET /functions/v1/dashboard/summary ──────────────────────────────────────

async function getSummary() {
  // 平行查詢多個聚合
  const [
    { count: totalOrders },
    { count: pendingOrders },
    { count: activeBuyers },
    { count: activeCustomers },
    txnResult,
    refundResult,
  ] = await Promise.all([
    supabase.from('orders').select('*', { count: 'exact', head: true }),
    supabase.from('orders').select('*', { count: 'exact', head: true }).eq('status', 'pending'),
    supabase.from('buyers').select('*', { count: 'exact', head: true }).eq('status', 'active'),
    supabase.from('customers').select('*', { count: 'exact', head: true }).eq('status', 'active'),
    supabase.from('transactions').select('amount_cents, type, status')
      .eq('status', 'confirmed')
      .in('type', ['payment', 'deposit', 'balance']),
    supabase.from('refunds').select('amount_cents, status')
      .in('status', ['completed', 'approved']),
  ]);

  const totalRevenue = (txnResult.data ?? []).reduce((s, t) => s + t.amount_cents, 0);
  const totalRefunds = (refundResult.data ?? []).reduce((s, r) => s + r.amount_cents, 0);
  const netRevenue = totalRevenue - totalRefunds;

  return jsonResponse({
    orders: {
      total: totalOrders ?? 0,
      pending: pendingOrders ?? 0,
    },
    buyers: {
      active: activeBuyers ?? 0,
    },
    customers: {
      active: activeCustomers ?? 0,
    },
    financials: {
      total_revenue_cents: totalRevenue,
      total_refunds_cents: totalRefunds,
      net_revenue_cents: netRevenue,
      total_revenue_hkd: `HK$${(totalRevenue / 100).toFixed(2)}`,
      net_revenue_hkd: `HK$${(netRevenue / 100).toFixed(2)}`,
    },
    generated_at: new Date().toISOString(),
  });
}

// ─── GET /functions/v1/dashboard/buyers ────────────────────────────────────────
// Also handles GET /functions/v1/dashboard/buyers/:id

async function getBuyersDashboard() {
  const { data, error } = await supabase
    .from('buyers')
    .select(`
      id,
      display_name,
      phone,
      status,
      rating_avg,
      rating_count,
      commission_rate,
      created_at,
      orders:orders(count),
      settlements:settlements(
        id, status, total_sales_cents, commission_amount_cents, period_start, period_end
      )
    `)
    .eq('status', 'active')
    .order('rating_avg', { ascending: false });

  if (error) return errorResponse('DB_ERROR', 'Failed to fetch buyers', 500, error);

  return jsonResponse(data ?? []);
}

async function getBuyerById(id: string) {
  const { data, error } = await supabase
    .from('buyers')
    .select(`
      *,
      orders:orders(
        id, order_number, status, total_amount_cents, created_at,
        customer:customers(display_name)
      ),
      settlements:settlements(
        id, settlement_number, status, total_sales_cents,
        commission_amount_cents, period_start, period_end, created_at
      )
    `)
    .eq('id', id)
    .single();

  if (error || !data) {
    return errorResponse('NOT_FOUND', 'Buyer not found', 404);
  }

  return jsonResponse(data);
}

// ─── GET /functions/v1/dashboard/financials ────────────────────────────────────

async function getFinancials(url: URL) {
  const period = url.searchParams.get('period') ?? new Date().toISOString().slice(0, 7); // YYYY-MM

  // 嘗試使用已存在的視圖
  const { data: pnlData, error: pnlError } = await supabase
    .from('v_pnl_summary')
    .select('*')
    .eq('period', period);

  const { data: trialData, error: trialError } = await supabase
    .from('v_trial_balance')
    .select('*');

  if (pnlError || trialError) {
    // Fallback: 手動計算
    const { data: txnData } = await supabase
      .from('transactions')
      .select('amount_cents, type, created_at')
      .eq('status', 'confirmed');

    const { data: refundData } = await supabase
      .from('refunds')
      .select('amount_cents, status, created_at')
      .in('status', ['completed', 'approved']);

    return jsonResponse({
      period,
      revenue_cents: (txnData ?? []).reduce((s, t) => s + t.amount_cents, 0),
      refunds_cents: (refundData ?? []).reduce((s, r) => s + r.amount_cents, 0),
      note: 'Calculated from raw data (views not available)',
    });
  }

  return jsonResponse({
    period,
    pnl: pnlData ?? [],
    trial_balance: trialData ?? [],
  });
}
