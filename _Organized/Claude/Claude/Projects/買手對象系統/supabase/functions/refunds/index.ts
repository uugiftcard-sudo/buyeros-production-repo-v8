/**
 * Edge Function: refunds
 * supabase/functions/refunds/index.ts
 *
 * 退款管理 API
 * GET    /functions/v1/refunds             — 退款列表
 * POST   /functions/v1/refunds             — 申請退款
 * GET    /functions/v1/refunds/:id         — 取得退款詳情
 * PATCH  /functions/v1/refunds/:id        — 更新退款狀態（審批/處理/完成）
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import {
  jsonResponse,
  errorResponse,
  paginatedResponse,
  validateRequired,
  isValidUUID,
  generateRefundNumber,
} from '../_shared/index.ts';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

const VALID_STATUSES = ['pending', 'approved', 'processing', 'completed', 'rejected'];

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204 });

  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split('/').filter(Boolean);
    const id = pathParts[pathParts.length - 1] !== 'refunds'
      ? pathParts[pathParts.length - 1]
      : null;

    switch (req.method) {
      case 'GET':
        if (id) return await getRefund(id);
        return await listRefunds(url);

      case 'POST':
        return await createRefund(await req.json());

      case 'PATCH':
        if (!id) return errorResponse('MISSING_ID', 'Refund ID required', 400);
        return await updateRefund(id, await req.json());

      default:
        return errorResponse('METHOD_NOT_ALLOWED', `Method ${req.method} not supported`, 405);
    }
  } catch (err) {
    console.error('refunds API error:', err);
    return errorResponse(
      'INTERNAL_ERROR',
      'An internal error occurred',
      500,
      err instanceof Error ? err.message : String(err)
    );
  }
});

// ─── GET /functions/v1/refunds ─────────────────────────────────────────────────

async function listRefunds(url: URL) {
  const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1'));
  const pageSize = Math.min(100, Math.max(1, parseInt(url.searchParams.get('pageSize') ?? '20')));
  const offset = (page - 1) * pageSize;
  const status = url.searchParams.get('status') ?? '';
  const orderId = url.searchParams.get('order_id') ?? '';

  let query = supabase
    .from('refunds')
    .select(`
      *,
      customer:customers!refunds_customer_id_fkey(id, display_name),
      transaction:transactions!refunds_transaction_id_fkey(id, transaction_number, amount_cents)
    `, { count: 'exact' });

  if (status) query = query.eq('status', status);
  if (orderId && isValidUUID(orderId)) query = query.eq('order_id', orderId);

  query = query
    .order('created_at', { ascending: false })
    .range(offset, offset + pageSize - 1);

  const { data, error, count } = await query;
  if (error) return errorResponse('DB_ERROR', 'Failed to fetch refunds', 500, error);

  return paginatedResponse(data ?? [], count ?? 0, page, pageSize);
}

// ─── GET /functions/v1/refunds/:id ────────────────────────────────────────────

async function getRefund(id: string) {
  if (!isValidUUID(id)) return errorResponse('INVALID_ID', 'Invalid refund ID', 400);

  const { data, error } = await supabase
    .from('refunds')
    .select(`
      *,
      customer:customers!refunds_customer_id_fkey(*),
      order:orders!refunds_order_id_fkey(*),
      transaction:transactions!refunds_transaction_id_fkey(*)
    `)
    .eq('id', id)
    .single();

  if (error || !data) return errorResponse('NOT_FOUND', 'Refund not found', 404);

  return jsonResponse(data);
}

// ─── POST /functions/v1/refunds ───────────────────────────────────────────────

async function createRefund(body: Record<string, unknown>) {
  const missing = validateRequired(body, ['transaction_id', 'amount_cents']);
  if (missing) return errorResponse('VALIDATION_ERROR', missing, 400);

  if (!isValidUUID(String(body.transaction_id))) {
    return errorResponse('INVALID_ID', 'Invalid transaction_id format', 400);
  }

  const amountCents = Number(body.amount_cents);
  if (!Number.isInteger(amountCents) || amountCents <= 0) {
    return errorResponse('INVALID_AMOUNT', 'amount_cents must be a positive integer', 400);
  }

  // 確認原始交易存在且狀態為 confirmed
  const { data: txn, error: txnError } = await supabase
    .from('transactions')
    .select('id, amount_cents, customer_id, order_id, status')
    .eq('id', body.transaction_id)
    .single();

  if (txnError || !txn) return errorResponse('NOT_FOUND', 'Original transaction not found', 404);
  if (txn.status !== 'confirmed') {
    return errorResponse('INVALID_STATUS', 'Can only refund confirmed transactions', 400);
  }
  if (amountCents > txn.amount_cents) {
    return errorResponse('AMOUNT_TOO_LARGE', 'Refund amount exceeds original transaction amount', 400);
  }

  const refundNumber = await generateRefundNumber(supabase);

  const { data, error } = await supabase
    .from('refunds')
    .insert({
      refund_number: refundNumber,
      transaction_id: body.transaction_id,
      order_id: txn.order_id ?? null,
      customer_id: txn.customer_id,
      amount_cents: amountCents,
      reason: body.reason ?? null,
      reason_detail: body.reason_detail ?? null,
      status: 'pending',
      notes: body.notes ?? null,
    })
    .select()
    .single();

  if (error) return errorResponse('DB_ERROR', 'Failed to create refund', 500, error);

  return jsonResponse(data, 201);
}

// ─── PATCH /functions/v1/refunds/:id ─────────────────────────────────────────

async function updateRefund(id: string, body: Record<string, unknown>) {
  if (!isValidUUID(id)) return errorResponse('INVALID_ID', 'Invalid refund ID', 400);

  const { data: existing } = await supabase
    .from('refunds')
    .select('id, status')
    .eq('id', id)
    .single();

  if (!existing) return errorResponse('NOT_FOUND', 'Refund not found', 404);

  const updates: Record<string, unknown> = {};

  // status 更新（狀態機）
  if (body.status !== undefined) {
    const newStatus = String(body.status);
    if (!VALID_STATUSES.includes(newStatus)) {
      return errorResponse('INVALID_STATUS', `status must be one of: ${VALID_STATUSES.join(', ')}`, 400);
    }
    // 狀態機驗證
    const allowedTransitions: Record<string, string[]> = {
      pending: ['approved', 'rejected'],
      approved: ['processing'],
      processing: ['completed'],
      completed: [],
      rejected: [],
    };
    const allowed = allowedTransitions[existing.status] ?? [];
    if (!allowed.includes(newStatus)) {
      return errorResponse(
        'INVALID_TRANSITION',
        `Cannot change status from '${existing.status}' to '${newStatus}'`,
        400
      );
    }
    updates.status = newStatus;

    if (newStatus === 'approved') {
      updates.approved_at = new Date().toISOString();
      updates.approved_by = body.approved_by ?? null;
    }
    if (newStatus === 'processing' || newStatus === 'completed') {
      updates.processed_at = new Date().toISOString();
    }
  }

  if (body.reason !== undefined) updates.reason = body.reason;
  if (body.reason_detail !== undefined) updates.reason_detail = body.reason_detail;
  if (body.notes !== undefined) updates.notes = body.notes;

  if (Object.keys(updates).length === 0) {
    return errorResponse('NO_UPDATES', 'No valid fields to update', 400);
  }

  const { data, error } = await supabase
    .from('refunds')
    .update(updates)
    .eq('id', id)
    .select()
    .single();

  if (error || !data) return errorResponse('NOT_FOUND', 'Refund not found', 404);

  return jsonResponse(data);
}
