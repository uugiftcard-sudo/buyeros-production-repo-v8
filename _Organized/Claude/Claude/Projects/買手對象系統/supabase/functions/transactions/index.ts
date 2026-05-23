/**
 * Edge Function: transactions
 * supabase/functions/transactions/index.ts
 *
 * 交易管理 API
 * GET    /functions/v1/transactions              — 交易列表
 * POST   /functions/v1/transactions              — 記錄新收款（同時自動產生 journal entry）
 * GET    /functions/v1/transactions/:id          — 取得單一交易
 * PATCH  /functions/v1/transactions/:id          — 更新交易狀態
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import {
  jsonResponse,
  errorResponse,
  paginatedResponse,
  validateRequired,
  isValidUUID,
  generateTransactionNumber,
} from '../_shared/index.ts';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

const VALID_TYPES = ['payment', 'deposit', 'balance', 'commission', 'refund'];
const VALID_PAYMENT_METHODS = ['bank_transfer', 'fps', 'cash', 'other'];
const VALID_STATUSES = ['pending', 'confirmed', 'failed', 'reversed'];

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204 });

  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split('/').filter(Boolean);
    const id = pathParts[pathParts.length - 1] !== 'transactions'
      ? pathParts[pathParts.length - 1]
      : null;

    switch (req.method) {
      case 'GET':
        if (id) return await getTransaction(id);
        return await listTransactions(url);

      case 'POST':
        return await createTransaction(await req.json());

      case 'PATCH':
        if (!id) return errorResponse('MISSING_ID', 'Transaction ID required', 400);
        return await updateTransaction(id, await req.json());

      default:
        return errorResponse('METHOD_NOT_ALLOWED', `Method ${req.method} not supported`, 405);
    }
  } catch (err) {
    console.error('transactions API error:', err);
    return errorResponse(
      'INTERNAL_ERROR',
      'An internal error occurred',
      500,
      err instanceof Error ? err.message : String(err)
    );
  }
});

// ─── GET /functions/v1/transactions ──────────────────────────────────────────

async function listTransactions(url: URL) {
  const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1'));
  const pageSize = Math.min(100, Math.max(1, parseInt(url.searchParams.get('pageSize') ?? '20')));
  const offset = (page - 1) * pageSize;
  const type = url.searchParams.get('type') ?? '';
  const status = url.searchParams.get('status') ?? '';
  const orderId = url.searchParams.get('order_id') ?? '';
  const customerId = url.searchParams.get('customer_id') ?? '';

  let query = supabase
    .from('transactions')
    .select(`
      *,
      customer:customers!transactions_customer_id_fkey(id, display_name),
      order:orders!transactions_order_id_fkey(id, order_number, status)
    `, { count: 'exact' });

  if (type) query = query.eq('type', type);
  if (status) query = query.eq('status', status);
  if (orderId && isValidUUID(orderId)) query = query.eq('order_id', orderId);
  if (customerId && isValidUUID(customerId)) query = query.eq('customer_id', customerId);

  query = query
    .order('created_at', { ascending: false })
    .range(offset, offset + pageSize - 1);

  const { data, error, count } = await query;
  if (error) return errorResponse('DB_ERROR', 'Failed to fetch transactions', 500, error);

  return paginatedResponse(data ?? [], count ?? 0, page, pageSize);
}

// ─── GET /functions/v1/transactions/:id ───────────────────────────────────────

async function getTransaction(id: string) {
  if (!isValidUUID(id)) return errorResponse('INVALID_ID', 'Invalid transaction ID', 400);

  const { data, error } = await supabase
    .from('transactions')
    .select(`
      *,
      customer:customers!transactions_customer_id_fkey(*),
      order:orders!transactions_order_id_fkey(*)
    `)
    .eq('id', id)
    .single();

  if (error || !data) return errorResponse('NOT_FOUND', 'Transaction not found', 404);

  return jsonResponse(data);
}

// ─── POST /functions/v1/transactions ─────────────────────────────────────────

async function createTransaction(body: Record<string, unknown>) {
  const missing = validateRequired(body, ['amount_cents', 'type']);
  if (missing) return errorResponse('VALIDATION_ERROR', missing, 400);

  if (!VALID_TYPES.includes(String(body.type))) {
    return errorResponse('INVALID_TYPE', `type must be one of: ${VALID_TYPES.join(', ')}`, 400);
  }

  const amountCents = Number(body.amount_cents);
  if (!Number.isInteger(amountCents) || amountCents <= 0) {
    return errorResponse('INVALID_AMOUNT', 'amount_cents must be a positive integer', 400);
  }

  const transactionNumber = await generateTransactionNumber(supabase);

  const insertData: Record<string, unknown> = {
    transaction_number: transactionNumber,
    type: body.type,
    amount_cents: amountCents,
    currency: body.currency ?? 'HKD',
    payment_method: body.payment_method ?? null,
    payment_reference: body.payment_reference ?? null,
    paid_at: body.paid_at ?? null,
    status: body.status ?? 'pending',
    notes: body.notes ?? null,
    tg_message_id: body.tg_message_id ?? null,
  };

  if (body.order_id && isValidUUID(String(body.order_id))) {
    insertData.order_id = body.order_id;
  }
  if (body.customer_id && isValidUUID(String(body.customer_id))) {
    insertData.customer_id = body.customer_id;
  }

  const { data, error } = await supabase
    .from('transactions')
    .insert(insertData)
    .select()
    .single();

  if (error) {
    console.error('Failed to create transaction:', error);
    return errorResponse('DB_ERROR', 'Failed to create transaction', 500, error);
  }

  // 如果 status 是 confirmed，同時更新 order 的 deposit / balance
  if (data.status === 'confirmed' && data.order_id && data.customer_id) {
    await reconcileOrderPayment(data.order_id);
  }

  return jsonResponse(data, 201);
}

// ─── PATCH /functions/v1/transactions/:id ────────────────────────────────────

async function updateTransaction(id: string, body: Record<string, unknown>) {
  if (!isValidUUID(id)) return errorResponse('INVALID_ID', 'Invalid transaction ID', 400);

  const allowedFields = [
    'status',
    'payment_method',
    'payment_reference',
    'paid_at',
    'notes',
  ];
  const updates: Record<string, unknown> = {};
  for (const field of allowedFields) {
    if (body[field] !== undefined) updates[field] = body[field];
  }

  if (Object.keys(updates).length === 0) {
    return errorResponse('NO_UPDATES', 'No valid fields to update', 400);
  }

  if (updates.status && !VALID_STATUSES.includes(String(updates.status))) {
    return errorResponse('INVALID_STATUS', `status must be one of: ${VALID_STATUSES.join(', ')}`, 400);
  }

  // 取得舊狀態，用於判斷是否需要 reconcile
  const { data: old } = await supabase
    .from('transactions')
    .select('order_id, status')
    .eq('id', id)
    .single();

  const { data, error } = await supabase
    .from('transactions')
    .update(updates)
    .eq('id', id)
    .select()
    .single();

  if (error || !data) return errorResponse('NOT_FOUND', 'Transaction not found', 404);

  // 如果狀態變為 confirmed，重新計算訂單付款
  if (updates.status === 'confirmed' && old?.order_id && old?.status !== 'confirmed') {
    await reconcileOrderPayment(old.order_id);
  }

  return jsonResponse(data);
}

// ─── Helper: 更新訂單的 deposit / balance ─────────────────────────────────────

async function reconcileOrderPayment(orderId: string) {
  // 計算該訂單所有 confirmed 交易的總額
  const { data: confirmedTxns } = await supabase
    .from('transactions')
    .select('amount_cents')
    .eq('order_id', orderId)
    .eq('status', 'confirmed')
    .in('type', ['deposit', 'payment', 'balance']);

  if (!confirmedTxns || confirmedTxns.length === 0) return;

  const totalPaid = confirmedTxns.reduce((sum, t) => sum + t.amount_cents, 0);

  // 取得訂單總額，計算 balance_due
  const { data: order } = await supabase
    .from('orders')
    .select('total_amount_cents, deposit_paid_cents')
    .eq('id', orderId)
    .single();

  if (!order) return;

  const { error } = await supabase
    .from('orders')
    .update({
      deposit_paid_cents: totalPaid,
      balance_due_cents: Math.max(0, order.total_amount_cents - totalPaid),
    })
    .eq('id', orderId);

  if (error) console.warn('Failed to reconcile order payment:', error);
}
