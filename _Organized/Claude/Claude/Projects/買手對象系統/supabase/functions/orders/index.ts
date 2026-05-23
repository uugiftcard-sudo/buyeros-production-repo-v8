/**
 * Edge Function: orders
 * supabase/functions/orders/index.ts
 *
 * 訂單管理 API
 * GET    /functions/v1/orders              — 訂單列表（支援分頁、狀態過濾）
 * POST   /functions/v1/orders              — 建立新訂單
 * GET    /functions/v1/orders/:id          — 取得單一訂單（含明細）
 * PATCH  /functions/v1/orders/:id          — 更新訂單（狀態、分配買手等）
 * POST   /functions/v1/orders/:id/items     — 新增訂單明細
 * PATCH  /functions/v1/orders/:id/assign   — 分配買手
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import {
  jsonResponse,
  errorResponse,
  paginatedResponse,
  validateRequired,
  isValidUUID,
  generateOrderNumber,
} from '../_shared/index.ts';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

// ─── Order State Machine ───────────────────────────────────────────────────────
// Valid transitions: from_status → [allowed next statuses]
const ORDER_TRANSITIONS: Record<string, string[]> = {
  pending:        ['assigned', 'cancelled'],
  assigned:       ['in_procurement', 'cancelled'],
  in_procurement: ['received', 'cancelled'],
  received:       ['delivered'],
  delivered:      ['completed'],
  completed:      [],
  cancelled:      [],
};

type OrderStatus = keyof typeof ORDER_TRANSITIONS;

function getValidNextStatuses(currentStatus: string): string[] {
  return ORDER_TRANSITIONS[currentStatus] ?? [];
}

function isValidTransition(currentStatus: string, nextStatus: string): boolean {
  const allowed = ORDER_TRANSITIONS[currentStatus];
  if (!allowed) return false;
  return allowed.includes(nextStatus);
}

function getTransitionError(
  currentStatus: string,
  nextStatus: string
): string {
  const allowed = getValidNextStatuses(currentStatus);
  if (allowed.length === 0) {
    return `Order is '${currentStatus}' — no further transitions allowed.`;
  }
  return `Cannot transition from '${currentStatus}' to '${nextStatus}'. ` +
    `Allowed next statuses: [${allowed.join(', ')}].`;
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204 });
  }

  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split('/').filter(Boolean);

    // /functions/v1/orders[/extra[/...]]
    const extra = pathParts.slice(pathParts.indexOf('orders') + 1);
    const id = extra[0] ?? null;
    const subRoute = extra[1] ?? null;

    switch (req.method) {
      case 'GET':
        if (id && !subRoute) return await getOrder(id);
        if (id === 'stats') return await getOrderStats();
        return await listOrders(url);

      case 'POST':
        if (id === 'items' && !subRoute) {
          return errorResponse('MISSING_ORDER_ID', 'Order ID required', 400);
        }
        return await createOrder(await req.json());

      case 'PATCH':
        if (!id) return errorResponse('MISSING_ID', 'Order ID required', 400);
        if (subRoute === 'assign') return await assignBuyer(id, await req.json());
        return await updateOrder(id, await req.json());

      case 'DELETE':
        if (!id) return errorResponse('MISSING_ID', 'Order ID required', 400);
        return await cancelOrder(id);

      default:
        return errorResponse('METHOD_NOT_ALLOWED', `Method ${req.method} not supported`, 405);
    }
  } catch (err) {
    console.error('orders API error:', err);
    return errorResponse(
      'INTERNAL_ERROR',
      'An internal error occurred',
      500,
      err instanceof Error ? err.message : String(err)
    );
  }
});

// ─── GET /functions/v1/orders ─────────────────────────────────────────────────

async function listOrders(url: URL) {
  const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1'));
  const pageSize = Math.min(100, Math.max(1, parseInt(url.searchParams.get('pageSize') ?? '20')));
  const offset = (page - 1) * pageSize;
  const status = url.searchParams.get('status') ?? '';
  const buyerId = url.searchParams.get('buyer_id') ?? '';
  const customerId = url.searchParams.get('customer_id') ?? '';

  let query = supabase
    .from('orders')
    .select(`
      *,
      customer:customers(id, display_name, phone),
      buyer:buyers(id, display_name)
    `, { count: 'exact' });

  if (status) query = query.eq('status', status);
  if (buyerId) query = query.eq('assigned_buyer_id', buyerId);
  if (customerId) query = query.eq('customer_id', customerId);

  query = query
    .order('created_at', { ascending: false })
    .range(offset, offset + pageSize - 1);

  const { data, error, count } = await query;
  if (error) return errorResponse('DB_ERROR', 'Failed to fetch orders', 500, error);

  return paginatedResponse(data ?? [], count ?? 0, page, pageSize);
}

// ─── GET /functions/v1/orders/:id ────────────────────────────────────────────

async function getOrder(id: string) {
  if (!isValidUUID(id)) return errorResponse('INVALID_ID', 'Invalid order ID', 400);

  const { data, error } = await supabase
    .from('orders')
    .select(`
      *,
      customer:customers!orders_customer_id_fkey(*),
      buyer:buyers!orders_assigned_buyer_id_fkey(*),
      items:order_items(*),
      transactions(id, transaction_number, type, amount_cents, status, paid_at)
    `)
    .eq('id', id)
    .single();

  if (error || !data) return errorResponse('NOT_FOUND', 'Order not found', 404);

  return jsonResponse(data);
}

// ─── GET /functions/v1/orders/stats ──────────────────────────────────────────

async function getOrderStats() {
  const { data, error } = await supabase
    .from('orders')
    .select('status');

  if (error) return errorResponse('DB_ERROR', 'Failed to fetch stats', 500, error);

  const stats = (data ?? []).reduce(
    (acc, o) => {
      acc[o.status] = (acc[o.status] ?? 0) + 1;
      acc.total++;
      return acc;
    },
    { total: 0 } as Record<string, number>
  );

  return jsonResponse(stats);
}

// ─── POST /functions/v1/orders ───────────────────────────────────────────────

async function createOrder(body: Record<string, unknown>) {
  const missing = validateRequired(body, ['customer_id', 'total_amount_cents']);
  if (missing) return errorResponse('VALIDATION_ERROR', missing, 400);

  if (!isValidUUID(String(body.customer_id))) {
    return errorResponse('INVALID_ID', 'Invalid customer_id format', 400);
  }

  const orderNumber = await generateOrderNumber(supabase);

  const { data, error } = await supabase
    .from('orders')
    .insert({
      order_number: orderNumber,
      customer_id: body.customer_id,
      status: 'pending',
      total_amount_cents: body.total_amount_cents,
      deposit_paid_cents: 0,
      balance_due_cents: body.total_amount_cents,
      delivery_address: body.delivery_address ?? null,
      notes: body.notes ?? null,
      source_channel: body.source_channel ?? 'api',
    })
    .select()
    .single();

  if (error) return errorResponse('DB_ERROR', 'Failed to create order', 500, error);

  // 如果有 order_items，一併建立
  if (Array.isArray(body.items) && body.items.length > 0) {
    const items = body.items.map((item: Record<string, unknown>) => ({
      order_id: data.id,
      product_name: item.product_name,
      product_url: item.product_url ?? null,
      quantity: item.quantity ?? 1,
      unit_price_cents: item.unit_price_cents,
      notes: item.notes ?? null,
    }));

    const { error: itemsError } = await supabase
      .from('order_items')
      .insert(items);

    if (itemsError) {
      console.warn('Failed to insert order items:', itemsError);
    } else {
      // 重新查詢以包含 items
      const { data: fullOrder } = await supabase
        .from('orders')
        .select('*, items:order_items(*)')
        .eq('id', data.id)
        .single();
      return jsonResponse(fullOrder ?? data, 201);
    }
  }

  return jsonResponse(data, 201);
}

// ─── PATCH /functions/v1/orders/:id ──────────────────────────────────────────

async function updateOrder(id: string, body: Record<string, unknown>) {
  if (!isValidUUID(id)) return errorResponse('INVALID_ID', 'Invalid order ID', 400);

  // Fetch current order
  const { data: existing, error: fetchError } = await supabase
    .from('orders')
    .select('id, status, assigned_buyer_id, deposit_paid_cents, delivery_proof_url')
    .eq('id', id)
    .single();

  if (fetchError || !existing) {
    return errorResponse('NOT_FOUND', 'Order not found', 404);
  }

  const nextStatus = body.status as string | undefined;

  // ── State machine validation ──────────────────────────────────────────────
  if (nextStatus !== undefined && nextStatus !== existing.status) {
    if (!isValidTransition(existing.status, nextStatus)) {
      return errorResponse(
        'INVALID_STATUS_TRANSITION',
        getTransitionError(existing.status, nextStatus),
        400
      );
    }

    // Guard: assigning → must have a buyer
    if (nextStatus === 'assigned' && !body.assigned_buyer_id) {
      return errorResponse(
        'MISSING_BUYER',
        'Transitioning to "assigned" requires assigned_buyer_id',
        400
      );
    }

    // Guard: delivered → delivery_proof_url required
    if (nextStatus === 'delivered' && !body.delivery_proof_url) {
      return errorResponse(
        'MISSING_DELIVERY_PROOF',
        'Transitioning to "delivered" requires delivery_proof_url',
        400
      );
    }

    // Guard: completed → deposit must be paid
    if (nextStatus === 'completed' && existing.deposit_paid_cents <= 0) {
      return errorResponse(
        'NO_DEPOSIT_PAID',
        'Cannot complete order without any deposit payment',
        400
      );
    }
  }
  // ── End state machine validation ─────────────────────────────────────────

  const allowedFields = [
    'status',
    'assigned_buyer_id',
    'total_amount_cents',
    'deposit_paid_cents',
    'balance_due_cents',
    'delivery_address',
    'delivery_fee_cents',
    'notes',
    'delivered_at',
    'delivery_proof_url',
  ];
  const updates: Record<string, unknown> = {};
  for (const field of allowedFields) {
    if (body[field] !== undefined) updates[field] = body[field];
  }

  // When transitioning to assigned, also set assigned_at
  if (nextStatus === 'assigned' && body.assigned_buyer_id) {
    updates['assigned_at'] = new Date().toISOString();
  }

  if (Object.keys(updates).length === 0) {
    return errorResponse('NO_UPDATES', 'No valid fields to update', 400);
  }

  const { data, error } = await supabase
    .from('orders')
    .update(updates)
    .eq('id', id)
    .select()
    .single();

  if (error || !data) return errorResponse('NOT_FOUND', 'Order not found', 404);

  return jsonResponse(data);
}

// ─── POST /functions/v1/orders/:id/assign ────────────────────────────────────

async function assignBuyer(orderId: string, body: Record<string, unknown>) {
  if (!isValidUUID(orderId)) return errorResponse('INVALID_ID', 'Invalid order ID', 400);

  const missing = validateRequired(body, ['buyer_id']);
  if (missing) return errorResponse('VALIDATION_ERROR', missing, 400);

  if (!isValidUUID(String(body.buyer_id))) {
    return errorResponse('INVALID_ID', 'Invalid buyer_id format', 400);
  }

  // Fetch order to validate state machine
  const { data: order, error: orderError } = await supabase
    .from('orders')
    .select('id, status')
    .eq('id', orderId)
    .single();

  if (orderError || !order) return errorResponse('NOT_FOUND', 'Order not found', 404);
  if (!isValidTransition(order.status, 'assigned')) {
    return errorResponse(
      'INVALID_STATUS_TRANSITION',
      `Cannot assign buyer to an order with status '${order.status}'. Only 'pending' orders can be assigned.`,
      400
    );
  }

  // 確認買手存在且狀態為 active
  const { data: buyer, error: buyerError } = await supabase
    .from('buyers')
    .select('id, display_name, status')
    .eq('id', body.buyer_id)
    .single();

  if (buyerError || !buyer) {
    return errorResponse('NOT_FOUND', 'Buyer not found', 404);
  }
  if (buyer.status !== 'active') {
    return errorResponse('BUYER_INACTIVE', 'Buyer is not active', 400);
  }

  const { data, error } = await supabase
    .from('orders')
    .update({
      assigned_buyer_id: body.buyer_id,
      assigned_at: new Date().toISOString(),
      status: 'assigned',
    })
    .eq('id', orderId)
    .select()
    .single();

  if (error || !data) return errorResponse('NOT_FOUND', 'Order not found', 404);

  return jsonResponse({ ...data, assigned_buyer_name: buyer.display_name });
}

// ─── DELETE /functions/v1/orders/:id ─────────────────────────────────────────

async function cancelOrder(id: string) {
  if (!isValidUUID(id)) return errorResponse('INVALID_ID', 'Invalid order ID', 400);

  // 只允許取消 pending / assigned 狀態的訂單
  const { data: existing } = await supabase
    .from('orders')
    .select('id, status')
    .eq('id', id)
    .single();

  if (!existing) return errorResponse('NOT_FOUND', 'Order not found', 404);
  if (!['pending', 'assigned'].includes(existing.status)) {
    return errorResponse(
      'INVALID_STATUS',
      `Cannot cancel order with status '${existing.status}'. Only 'pending' or 'assigned' can be cancelled.`,
      400
    );
  }

  const { data, error } = await supabase
    .from('orders')
    .update({ status: 'cancelled' })
    .eq('id', id)
    .select()
    .single();

  if (error) return errorResponse('DB_ERROR', 'Failed to cancel order', 500, error);

  return jsonResponse(data);
}
