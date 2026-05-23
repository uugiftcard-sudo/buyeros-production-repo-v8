// apps/admin/lib/financials.ts
// TypeScript interfaces + formatters for the Financials Dashboard

export type AccountType = 'asset' | 'liability' | 'equity' | 'revenue' | 'expense';
export type PeriodStatus = 'open' | 'closed' | 'archived';
export type ARBucket = 'current' | '30' | '60' | '90' | '90plus';
export type TabId = 'pnl' | 'trial-balance' | 'balance-sheet' | 'ar-aging';

export interface TrialBalanceRow {
  account_code: string;
  account_name: string;
  type: string;
  total_debit_cents: number;
  total_credit_cents: number;
  balance_cents: number;
}

export interface MonthlyPnLRow {
  month: string;
  type: string;
  account_name: string;
  amount_cents: number;
}

export interface PnLSummaryRow {
  period: string;
  label: string;
  amount_cents: number;
  sort_order: number;
}

export interface BalanceSheetRow {
  account_code: string;
  account_name: string;
  type: 'asset' | 'liability' | 'equity';
  balance_cents: number;
}

export interface ARAgingRow {
  customer_id: string;
  customer_name: string;
  order_id: string;
  amount_cents: number;
  days_overdue: number;
  bucket: string;
}

export interface FinancialsSummary {
  totalRevenueCents: number;
  totalExpenseCents: number;
  netProfitCents: number;
}

export interface FinancialsData {
  period: string;
  periodStatus: PeriodStatus;
  summary: FinancialsSummary;
  trialBalance: TrialBalanceRow[];
  monthlyPnL: MonthlyPnLRow[];
  balanceSheet: BalanceSheetRow[];
  arAging: ARAgingRow[];
  generatedAt: string;
}

export interface ClosePeriodResponse {
  success: boolean;
  period: string;
  periodId?: string;
  closedAt: string;
  closingEntryId: string | null;
  totalDebit?: number;
  totalCredit?: number;
  balanced?: boolean;
  note?: string;
}

// ─── Formatters ───────────────────────────────────────────────────────────────

export function formatCents(cents: number): string {
  return `HK$${(cents / 100).toFixed(2)}`;
}

export function formatCentsShort(cents: number): string {
  const abs = Math.abs(cents);
  const sign = cents < 0 ? '-' : '';
  if (abs >= 1_000_000) return `${sign}HK$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}HK$${(abs / 1_000).toFixed(0)}K`;
  return `${sign}HK$${abs.toFixed(0)}`;
}

export function formatCentsLabel(cents: number): string {
  const abs = Math.abs(cents);
  const sign = cents < 0 ? '-' : '';
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

export function formatMonth(monthStr: string): string {
  const [year, month] = monthStr.split('-');
  const date = new Date(parseInt(year), parseInt(month) - 1);
  return date.toLocaleDateString('zh-HK', { year: 'numeric', month: 'short' });
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-HK', {
    year: 'numeric', month: '2-digit', day: '2-digit',
  });
}

export function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`;
}

export function getAccountTypeLabel(type: string): string {
  const map: Record<string, string> = {
    asset: '資產',
    liability: '負債',
    equity: '權益',
    revenue: '收入',
    expense: '支出',
  };
  return map[type] ?? type;
}

export function getARBucketLabel(bucket: string): string {
  const map: Record<string, string> = {
    current: '未逾期',
    '30': '逾期 1-30 天',
    '60': '逾期 31-60 天',
    '90': '逾期 61-90 天',
    '90plus': '逾期 90+ 天',
  };
  return map[bucket] ?? bucket;
}

export function getARBucketColor(bucket: string): string {
  const map: Record<string, string> = {
    current: '#059669',
    '30': '#d97706',
    '60': '#ea580c',
    '90': '#dc2626',
    '90plus': '#991b1b',
  };
  return map[bucket] ?? '#6b7280';
}

export function getPeriodStatusColor(status: string): string {
  const map: Record<string, string> = {
    open: '#059669',
    closed: '#6b7280',
    archived: '#94a5b8',
  };
  return map[status] ?? '#6b7280';
}

// ─── CSV Export ──────────────────────────────────────────────────────────────

export function downloadCsv(rows: Record<string, unknown>[], filename: string): void {
  if (rows.length === 0) return;
  const headers = Object.keys(rows[0]);
  const csv = [
    headers.map(h => `"${h}"`).join(','),
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

export function exportPnLCsv(
  monthlyPnL: MonthlyPnLRow[],
  pnlSummary: { label: string; amount_cents: number }[],
  period: string
): void {
  const rows: Record<string, unknown>[] = [];

  // Summary section
  for (const s of pnlSummary) {
    rows.push({ 期間: period, 類別: s.label, 科目: '', 金額_HKD: formatCents(s.amount_cents) });
  }

  // Monthly detail
  for (const r of monthlyPnL) {
    rows.push({ 期間: r.month, 類別: r.type === 'revenue' ? '收入' : '支出', 科目: r.account_name, 金額_HKD: formatCents(r.amount_cents) });
  }

  downloadCsv(rows, `pnl_${period}`);
}

export function exportTrialBalanceCsv(rows: TrialBalanceRow[]): void {
  const formatted = rows.map(r => ({
    科目編碼: r.account_code,
    科目名稱: r.account_name,
    類型: getAccountTypeLabel(r.type),
    借方_HKD: r.total_debit_cents > 0 ? formatCents(r.total_debit_cents) : '',
    貸方_HKD: r.total_credit_cents > 0 ? formatCents(r.total_credit_cents) : '',
    餘額_HKD: formatCents(r.balance_cents),
  }));
  downloadCsv(formatted, 'trial_balance');
}

export function exportARAgingCsv(rows: ARAgingRow[]): void {
  const formatted = rows.map(r => ({
    客戶: r.customer_name,
    訂單: r.order_id,
    逾期天數: r.days_overdue,
    帳齡: getARBucketLabel(r.bucket),
    金額_HKD: formatCents(r.amount_cents),
  }));
  downloadCsv(formatted, 'ar_aging');
}
