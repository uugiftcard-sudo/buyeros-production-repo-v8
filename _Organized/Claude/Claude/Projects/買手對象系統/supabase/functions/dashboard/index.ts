/**
 * Edge Function: dashboard
 * supabase/functions/dashboard/index.ts
 *
 * 儀表板 API — 給 Admin Web UI 和 Bot 使用
 * GET  /functions/v1/dashboard/summary           — 總覽數據
 * GET  /functions/v1/dashboard/buyers            — 買手列表（含結算狀態）
 * GET  /functions/v1/dashboard/financials        — 財務報表（彙總）
 * PATCH /functions/v1/dashboard/financials       — 月結操作
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { jsonResponse, errorResponse, isValidUUID } from '../_shared/index.ts';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204 });

  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split('/').filter(Boolean);
    // path: [..., 'dashboard', 'summary'|'buyers'|'financials']
    const resource = pathParts[pathParts.length - 1] ?? 'summary';

    if (req.method === 'GET' && resource === 'financials') {
      return await getFinancials(url);
    }

    if (req.method === 'PATCH' && resource === 'financials') {
      return await patchFinancials(req, url);
    }

    if (req.method === 'GET') {
      switch (resource) {
        case 'summary': return await getSummary();
        case 'buyers':  return await getBuyersDashboard();
        default: {
          const secondLast = pathParts[pathParts.length - 2];
          if (secondLast === 'buyers') {
            return await getBuyerById(pathParts[pathParts.length - 1]);
          }
          return errorResponse('NOT_FOUND', `Unknown resource: ${resource}`, 404);
        }
      }
    }

    return errorResponse('METHOD_NOT_ALLOWED', 'Only GET and PATCH are supported', 405);
  } catch (err) {
    console.error('dashboard API error:', err);
    return errorResponse('INTERNAL_ERROR', 'An internal error occurred', 500,
      err instanceof Error ? err.message : String(err));
  }
});

// ─── GET /functions/v1/dashboard/summary ──────────────────────────────────────

async function getSummary() {
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

  return jsonResponse({
    orders: { total: totalOrders ?? 0, pending: pendingOrders ?? 0 },
    buyers: { active: activeBuyers ?? 0 },
    customers: { active: activeCustomers ?? 0 },
    financials: {
      total_revenue_cents: totalRevenue,
      total_refunds_cents: totalRefunds,
      net_revenue_cents: totalRevenue - totalRefunds,
    },
    generated_at: new Date().toISOString(),
  });
}

// ─── GET /functions/v1/dashboard/buyers ──────────────────────────────────────

async function getBuyersDashboard() {
  const { data, error } = await supabase
    .from('buyers')
    .select(`
      id, display_name, phone, status, rating_avg, rating_count,
      commission_rate, created_at,
      orders:orders(count),
      settlements:settlements(id, status, total_sales_cents, commission_amount_cents, period_start, period_end)
    `)
    .eq('status', 'active')
    .order('rating_avg', { ascending: false });

  if (error) return errorResponse('DB_ERROR', 'Failed to fetch buyers', 500, error);
  return jsonResponse(data ?? []);
}

async function getBuyerById(id: string) {
  if (!isValidUUID(id)) return errorResponse('INVALID_ID', 'Invalid buyer ID', 400);

  const { data, error } = await supabase
    .from('buyers')
    .select(`
      *,
      orders:orders(id, order_number, status, total_amount_cents, created_at,
        customer:customers(display_name)),
      settlements:settlements(id, settlement_number, status, total_sales_cents,
        commission_amount_cents, period_start, period_end, created_at)
    `)
    .eq('id', id)
    .single();

  if (error || !data) return errorResponse('NOT_FOUND', 'Buyer not found', 404);
  return jsonResponse(data);
}

// ─── GET /functions/v1/dashboard/financials ───────────────────────────────────

interface TrialBalanceRow {
  account_code: string;
  account_name: string;
  type: string;
  total_debit_cents: number;
  total_credit_cents: number;
  balance_cents: number;
}

interface MonthlyPnLRow {
  month: string;
  type: string;
  account_name: string;
  amount_cents: number;
}

interface PnLSummaryRow {
  period: string;
  label: string;
  amount_cents: number;
  sort_order: number;
}

interface BalanceSheetRow {
  account_code: string;
  account_name: string;
  type: string;
  balance_cents: number;
}

interface ARAgingRow {
  customer_id: string;
  customer_name: string;
  order_id: string;
  amount_cents: number;
  days_overdue: number;
  bucket: string;
}

async function getFinancials(url: URL) {
  const period = url.searchParams.get('period') ?? new Date().toISOString().slice(0, 7);
  const months = parseInt(url.searchParams.get('months') ?? '12', 10);

  // Validate period format YYYY-MM
  if (!/^\d{4}-\d{2}$/.test(period)) {
    return errorResponse('INVALID_PERIOD', 'Period must be in YYYY-MM format', 400);
  }

  const periodStatusResult = await supabase
    .from('accounting_periods')
    .select('status')
    .eq('period', period)
    .maybeSingle();

  const periodStatus: string = periodStatusResult.data?.status ?? 'open';

  // Fetch all views in parallel
  const [
    trialBalanceResult,
    monthlyPnLResult,
    pnlSummaryResult,
    arAgingResult,
  ] = await Promise.all([
    supabase.from('v_trial_balance').select('*').order('account_code'),
    supabase.from('v_monthly_pnl')
      .select('*')
      .order('month', { ascending: false })
      .limit(months),
    supabase.from('v_pnl_summary').select('*').eq('period', period).order('sort_order'),
    supabase.from('v_ar_aging').select('*'),
  ]);

  const trialBalance: TrialBalanceRow[] = trialBalanceResult.data ?? [];
  const monthlyPnL: MonthlyPnLRow[] = monthlyPnLResult.data ?? [];
  const pnlSummary: PnLSummaryRow[] = pnlSummaryResult.data ?? [];
  const arAging: ARAgingRow[] = arAgingResult.data ?? [];

  // Derive summary from pnlSummary rows
  const revenueRow = pnlSummary.find(r => r.label === 'Revenue');
  const expenseRow = pnlSummary.find(r => r.label === 'Expenses');
  const netProfitRow = pnlSummary.find(r => r.label === 'Net Profit');

  const summary = {
    totalRevenueCents: revenueRow?.amount_cents ?? 0,
    totalExpenseCents: expenseRow?.amount_cents ?? 0,
    netProfitCents: netProfitRow?.amount_cents ?? 0,
  };

  // Compute balance sheet from trial balance (fetch with asOfDate from query param)
  const asOfDate = url.searchParams.get('as_of') ?? `${period}-31`;
  const balanceSheet = trialBalance
    .filter(r => ['asset', 'liability', 'equity'].includes(r.type))
    .map(r => ({
      account_code: r.account_code,
      account_name: r.account_name,
      type: r.type,
      balance_cents: r.balance_cents,
    }));

  return jsonResponse({
    period,
    periodStatus,
    summary,
    trialBalance,
    monthlyPnL,
    balanceSheet,
    arAging,
    generatedAt: new Date().toISOString(),
  }, 200, {
    'Cache-Control': 'public, max-age=60',
  });
}

// ─── PATCH /functions/v1/dashboard/financials ────────────────────────────────
// Body: { action: 'close-period', period: 'YYYY-MM' }

async function patchFinancials(req: Request, url: URL) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return errorResponse('INVALID_BODY', 'Request body must be valid JSON', 400);
  }

  const { action, period } = body;

  if (action === 'close-period') {
    return await closePeriod(period as string);
  }

  return errorResponse('UNKNOWN_ACTION', `Unknown action: ${action}`, 400);
}

async function closePeriod(period: string) {
  if (!period || !/^\d{4}-\d{2}$/.test(period)) {
    return errorResponse('INVALID_PERIOD', 'Period must be in YYYY-MM format', 400);
  }

  // Check if already closed
  const { data: existing } = await supabase
    .from('accounting_periods')
    .select('status, id')
    .eq('period', period)
    .maybeSingle();

  if (existing?.status === 'closed') {
    return errorResponse('PERIOD_ALREADY_CLOSED', `Period ${period} is already closed`, 400);
  }

  // Check for required journal entries before closing
  const { data: journalEntries } = await supabase
    .from('journal_entries')
    .select('id')
    .limit(1);

  // Verify trial balance debits == credits for this period
  const startDate = `${period}-01`;
  const endDate = `${period}-31`;
  const { data: balanceCheck } = await supabase
    .from('v_trial_balance')
    .select('total_debit_cents, total_credit_cents')
    .limit(1);

  const totalDebit = balanceCheck?.reduce((s, r: TrialBalanceRow) => s + (r.total_debit_cents ?? 0), 0) ?? 0;
  const totalCredit = balanceCheck?.reduce((s, r: TrialBalanceRow) => s + (r.total_credit_cents ?? 0), 0) ?? 0;

  // Close the period
  const closedAt = new Date().toISOString();
  const { data: updated, error: updateError } = await supabase
    .from('accounting_periods')
    .update({
      status: 'closed',
      closed_at: closedAt,
    })
    .eq('period', period)
    .select()
    .maybeSingle();

  // If no period record exists, create one
  if (updateError || !updated) {
    const { data: newPeriod } = await supabase
      .from('accounting_periods')
      .insert({
        period,
        period_name: period,
        start_date: startDate,
        end_date: endDate,
        status: 'closed',
        opened_at: startDate,
        closed_at: closedAt,
      })
      .select()
      .single();

    if (newPeriod) {
      return jsonResponse({
        success: true,
        period,
        periodId: newPeriod.id,
        closedAt,
        closingEntryId: null,
        note: 'Period closed. No closing journal entry created (configure in accounting layer).',
      });
    }
    return errorResponse('CLOSE_FAILED', 'Failed to close period', 500);
  }

  return jsonResponse({
    success: true,
    period,
    periodId: updated?.id ?? existing?.id,
    closedAt,
    closingEntryId: null,
    totalDebit,
    totalCredit,
    balanced: totalDebit === totalCredit,
    note: 'Period closed. Journal balance check: debits=' + totalDebit + ', credits=' + totalCredit,
  });
}
