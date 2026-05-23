/**
 * BuyerOS — Communications Edge Function
 * supabase/functions/communications/index.ts
 *
 * Handles all inbound/outbound communications (Telegram, WhatsApp, email, etc.)
 * GET  /functions/v1/communications          — list communications
 * POST /functions/v1/communications        — create new communication
 * GET  /functions/v1/communications/:id     — get single communication
 * PATCH /functions/v1/communications/:id   — update (read, archive, etc.)
 * DELETE /functions/v1/communications/:id   — soft delete
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers':
    'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
};

// ─── Deno.serve handler ────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: CORS_HEADERS });
  }

  const url = new URL(req.url);
  const pathParts = url.pathname.split('/').filter(Boolean);
  // Pattern: /functions/v1/communications[/id]
  const id = pathParts[pathParts.length - 1] !== 'communications'
    ? pathParts[pathParts.length - 1]
    : null;

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  );

  try {
    switch (req.method) {
      case 'GET':
        return id
          ? await getCommunication(supabase, id)
          : await listCommunications(supabase, url);

      case 'POST':
        return id
          ? new Response(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Use GET for single item' } }), {
              status: 404, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
            })
          : await createCommunication(supabase, req);

      case 'PATCH':
        return id
          ? await updateCommunication(supabase, id, req)
          : new Response(JSON.stringify({ error: { code: 'BAD_REQUEST', message: 'ID required' } }), {
              status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
            });

      case 'DELETE':
        return id
          ? await deleteCommunication(supabase, id)
          : new Response(JSON.stringify({ error: { code: 'BAD_REQUEST', message: 'ID required' } }), {
              status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
            });

      default:
        return new Response(JSON.stringify({ error: { code: 'METHOD_NOT_ALLOWED', message: `Method ${req.method} not allowed` } }), {
          status: 405, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
        });
    }
  } catch (err) {
    console.error('Communications error:', err);
    return new Response(JSON.stringify({
      error: {
        code: 'INTERNAL_ERROR',
        message: err instanceof Error ? err.message : 'Internal server error',
      },
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }
});

// ─── List ──────────────────────────────────────────────────────────────────────

async function listCommunications(
  supabase: ReturnType<typeof createClient>,
  url: URL
) {
  const page     = parseInt(url.searchParams.get('page') ?? '1', 10);
  const pageSize = Math.min(parseInt(url.searchParams.get('pageSize') ?? '20', 10), 100);
  const offset   = (page - 1) * pageSize;

  const channel    = url.searchParams.get('channel');
  const direction  = url.searchParams.get('direction');
  const tag        = url.searchParams.get('tag');
  const customerId = url.searchParams.get('customer_id');
  const buyerId    = url.searchParams.get('buyer_id');
  const archived   = url.searchParams.get('archived') === 'true';
  const search     = url.searchParams.get('search');

  let query = supabase
    .from('communications')
    .select(`
      *,
      customer:customers(id, display_name),
      buyer:buyers(id, display_name)
    `, { count: 'exact' })
    .eq('is_archived', archived)
    .is('deleted_at', null)
    .order('created_at', { ascending: false })
    .range(offset, offset + pageSize - 1);

  if (channel)   query = query.eq('channel', channel);
  if (direction) query = query.eq('direction', direction);
  if (customerId) query = query.eq('customer_id', customerId);
  if (buyerId)   query = query.eq('buyer_id', buyerId);

  const { data, error, count } = await query;

  if (error) {
    return new Response(JSON.stringify({ error: { code: 'DB_ERROR', message: error.message } }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  // Tag filter (Postgres array overlap)
  let results = data ?? [];
  if (tag) {
    results = results.filter((r: any) => r.tags?.includes(tag));
  }

  // Search (subject + content)
  if (search) {
    const q = search.toLowerCase();
    results = results.filter((r: any) =>
      r.subject?.toLowerCase().includes(q) ||
      r.content?.toLowerCase().includes(q)
    );
  }

  return new Response(JSON.stringify({
    data: results,
    meta: {
      pagination: {
        total: count ?? results.length,
        page,
        pageSize,
        totalPages: Math.ceil((count ?? results.length) / pageSize),
        hasNext: page * pageSize < (count ?? results.length),
        hasPrev: page > 1,
      },
      filters: { channel, direction, tag, customerId, buyerId, archived, search },
    },
  }), {
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

// ─── Get Single ────────────────────────────────────────────────────────────────

async function getCommunication(
  supabase: ReturnType<typeof createClient>,
  id: string
) {
  const { data, error } = await supabase
    .from('communications')
    .select(`
      *,
      customer:customers(id, display_name, phone),
      buyer:buyers(id, display_name, telegram_user_id)
    `)
    .eq('id', id)
    .single();

  if (error || !data) {
    return new Response(JSON.stringify({
      error: { code: 'NOT_FOUND', message: 'Communication not found' },
    }), {
      status: 404, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  return new Response(JSON.stringify({ data }), {
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

// ─── Create ────────────────────────────────────────────────────────────────────

interface CreateBody {
  customer_id?: string;
  buyer_id?: string;
  order_id?: string;
  channel: string;
  direction: string;
  subject?: string;
  content: string;
  content_html?: string;
  tags?: string[];
  attachments?: string[];
  telegram_message_id?: string;
  telegram_chat_id?: string;
  whatsapp_wa_id?: string;
  whatsapp_from?: string;
  is_read?: boolean;
}

async function createCommunication(
  supabase: ReturnType<typeof createClient>,
  req: Request
) {
  const body: CreateBody = await req.json();

  // Validation
  if (!body.channel || !body.content) {
    return new Response(JSON.stringify({
      error: { code: 'VALIDATION_ERROR', message: 'channel and content are required' },
    }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  const validChannels = ['telegram', 'whatsapp', 'email', 'phone', 'sms', 'web', 'in_person'];
  const validDirections = ['inbound', 'outbound'];

  if (!validChannels.includes(body.channel)) {
    return new Response(JSON.stringify({
      error: { code: 'VALIDATION_ERROR', message: `channel must be one of: ${validChannels.join(', ')}` },
    }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  if (!validDirections.includes(body.direction)) {
    return new Response(JSON.stringify({
      error: { code: 'VALIDATION_ERROR', message: 'direction must be inbound or outbound' },
    }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  const { data, error } = await supabase
    .from('communications')
    .insert({
      customer_id:          body.customer_id ?? null,
      buyer_id:             body.buyer_id ?? null,
      order_id:             body.order_id ?? null,
      channel:              body.channel,
      direction:            body.direction,
      subject:               body.subject ?? null,
      content:              body.content,
      content_html:         body.content_html ?? null,
      tags:                 body.tags ?? [],
      attachments:           body.attachments ?? [],
      is_read:              body.is_read ?? false,
      telegram_message_id:  body.telegram_message_id ?? null,
      telegram_chat_id:     body.telegram_chat_id ?? null,
      whatsapp_wa_id:        body.whatsapp_wa_id ?? null,
      whatsapp_from:        body.whatsapp_from ?? null,
    })
    .select()
    .single();

  if (error) {
    return new Response(JSON.stringify({ error: { code: 'INSERT_ERROR', message: error.message } }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  return new Response(JSON.stringify({ data }), {
    status: 201, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

// ─── Update ──────────────────────────────────────────────────────────────────

interface UpdateBody {
  is_read?: boolean;
  is_archived?: boolean;
  tags?: string[];
  internal_notes?: string;
  subject?: string;
  content?: string;
}

async function updateCommunication(
  supabase: ReturnType<typeof createClient>,
  id: string,
  req: Request
) {
  const body: UpdateBody = await req.json();

  const updates: Record<string, unknown> = {};
  if (body.is_read      !== undefined) updates.is_read       = body.is_read;
  if (body.is_archived !== undefined) updates.is_archived   = body.is_archived;
  if (body.tags         !== undefined) updates.tags          = body.tags;
  if (body.internal_notes !== undefined) updates.internal_notes = body.internal_notes;
  if (body.subject      !== undefined) updates.subject       = body.subject;
  if (body.content      !== undefined) updates.content       = body.content;

  const { data, error } = await supabase
    .from('communications')
    .update(updates)
    .eq('id', id)
    .select()
    .single();

  if (error || !data) {
    return new Response(JSON.stringify({
      error: { code: 'UPDATE_ERROR', message: error?.message ?? 'Not found' },
    }), {
      status: 404, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  return new Response(JSON.stringify({ data }), {
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

// ─── Delete (soft) ───────────────────────────────────────────────────────────

async function deleteCommunication(
  supabase: ReturnType<typeof createClient>,
  id: string
) {
  const { error } = await supabase
    .from('communications')
    .update({ deleted_at: new Date().toISOString() })
    .eq('id', id);

  if (error) {
    return new Response(JSON.stringify({ error: { code: 'DELETE_ERROR', message: error.message } }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  return new Response(JSON.stringify({ data: { id, deleted: true } }), {
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
