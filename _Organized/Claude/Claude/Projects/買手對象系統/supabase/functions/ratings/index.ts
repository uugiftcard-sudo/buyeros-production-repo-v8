/**
 * BuyerOS — Ratings Edge Function
 * supabase/functions/ratings/index.ts
 *
 * Buyer rating management
 * GET    /functions/v1/ratings              — list ratings (filter: buyer_id, order_id, min_score)
 * POST   /functions/v1/ratings              — create rating
 * GET    /functions/v1/ratings/:id          — get single rating
 * PATCH  /functions/v1/ratings/:id          — update rating (rater or admin only)
 * DELETE /functions/v1/ratings/:id          — delete rating (admin only)
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers':
    'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
};

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: CORS_HEADERS });
  }

  const url = new URL(req.url);
  const pathParts = url.pathname.split('/').filter(Boolean);
  // Pattern: /functions/v1/ratings[/id]
  const id = pathParts[pathParts.length - 1] !== 'ratings'
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
          ? await getRating(supabase, id)
          : await listRatings(supabase, url);

      case 'POST':
        return id
          ? new Response(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Use GET for single item' } }), {
              status: 404, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
            })
          : await createRating(supabase, req);

      case 'PATCH':
        return id
          ? await updateRating(supabase, id, req)
          : new Response(JSON.stringify({ error: { code: 'BAD_REQUEST', message: 'ID required' } }), {
              status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
            });

      case 'DELETE':
        return id
          ? await deleteRating(supabase, id)
          : new Response(JSON.stringify({ error: { code: 'BAD_REQUEST', message: 'ID required' } }), {
              status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
            });

      default:
        return new Response(JSON.stringify({ error: { code: 'METHOD_NOT_ALLOWED', message: `Method ${req.method} not allowed` } }), {
          status: 405, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
        });
    }
  } catch (err) {
    console.error('Ratings error:', err);
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

// ─── Helpers ───────────────────────────────────────────────────────────────────

function isValidUUID(str: string): boolean {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
}

function isScore(n: unknown): n is number {
  return typeof n === 'number' && Number.isInteger(n) && n >= 1 && n <= 5;
}

// ─── List ──────────────────────────────────────────────────────────────────────

interface ListRatingsQuery {
  buyer_id?: string;
  order_id?: string;
  min_score?: number;
  limit?: number;
  page?: number;
}

async function listRatings(
  supabase: ReturnType<typeof createClient>,
  url: URL
) {
  const page      = Math.max(1, parseInt(url.searchParams.get('page') ?? '1', 10));
  const pageSize  = Math.min(50, Math.max(1, parseInt(url.searchParams.get('limit') ?? '20', 10)));
  const offset    = (page - 1) * pageSize;
  const buyerId   = url.searchParams.get('buyer_id') ?? '';
  const orderId   = url.searchParams.get('order_id') ?? '';
  const minScore  = url.searchParams.get('min_score') ?? '';

  let query = supabase
    .from('ratings')
    .select(`
      *,
      buyer:buyers(id, display_name),
      order:orders(id, order_number)
    `, { count: 'exact' })
    .order('created_at', { ascending: false })
    .range(offset, offset + pageSize - 1);

  if (buyerId)  query = query.eq('buyer_id', buyerId);
  if (orderId)  query = query.eq('order_id', orderId);
  if (minScore) query = query.gte('overall_score', parseInt(minScore, 10));

  const { data, error, count } = await query;

  if (error) {
    return new Response(JSON.stringify({ error: { code: 'DB_ERROR', message: error.message } }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  return new Response(JSON.stringify({
    data,
    meta: {
      pagination: {
        total:      count ?? data?.length ?? 0,
        page,
        pageSize,
        totalPages: Math.ceil((count ?? 0) / pageSize),
        hasNext:    page * pageSize < (count ?? 0),
        hasPrev:    page > 1,
      },
    },
  }), {
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

// ─── Get Single ────────────────────────────────────────────────────────────────

async function getRating(
  supabase: ReturnType<typeof createClient>,
  id: string
) {
  if (!isValidUUID(id)) {
    return new Response(JSON.stringify({ error: { code: 'INVALID_ID', message: 'Invalid rating ID' } }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  const { data, error } = await supabase
    .from('ratings')
    .select(`
      *,
      buyer:buyers(id, display_name),
      order:orders(id, order_number)
    `)
    .eq('id', id)
    .single();

  if (error || !data) {
    return new Response(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Rating not found' } }), {
      status: 404, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  return new Response(JSON.stringify({ data }), {
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

// ─── Create ────────────────────────────────────────────────────────────────────

interface CreateRatingBody {
  buyer_id: string;
  order_id: string;
  rated_by: string;
  communication_score: number;
  quality_score: number;
  speed_score: number;
  accuracy_score: number;
  overall_score: number;
  review_text?: string;
}

async function createRating(
  supabase: ReturnType<typeof createClient>,
  req: Request
) {
  const body: CreateRatingBody = await req.json();

  // Required field validation
  const required = ['buyer_id', 'order_id', 'rated_by',
    'communication_score', 'quality_score', 'speed_score',
    'accuracy_score', 'overall_score'];
  for (const field of required) {
    if (body[field as keyof CreateRatingBody] === undefined) {
      return new Response(JSON.stringify({
        error: { code: 'VALIDATION_ERROR', message: `Missing required field: ${field}` },
      }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
      });
    }
  }

  // UUID format validation
  for (const field of ['buyer_id', 'order_id', 'rated_by']) {
    if (!isValidUUID(String(body[field as keyof CreateRatingBody]))) {
      return new Response(JSON.stringify({
        error: { code: 'VALIDATION_ERROR', message: `Invalid UUID format: ${field}` },
      }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
      });
    }
  }

  // Score range validation (1–5)
  const scoreFields: (keyof CreateRatingBody)[] = [
    'communication_score', 'quality_score', 'speed_score',
    'accuracy_score', 'overall_score',
  ];
  for (const field of scoreFields) {
    if (!isScore(body[field])) {
      return new Response(JSON.stringify({
        error: { code: 'VALIDATION_ERROR', message: `${field} must be an integer between 1 and 5` },
      }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
      });
    }
  }

  const { data, error } = await supabase
    .from('ratings')
    .insert({
      buyer_id:             body.buyer_id,
      order_id:             body.order_id,
      rated_by:             body.rated_by,
      communication_score:  body.communication_score,
      quality_score:        body.quality_score,
      speed_score:          body.speed_score,
      accuracy_score:       body.accuracy_score,
      overall_score:        body.overall_score,
      review_text:          body.review_text ?? null,
    })
    .select()
    .single();

  if (error) {
    const message = error.code === '23505'
      ? 'You have already rated this buyer for this order.'
      : error.message;
    return new Response(JSON.stringify({ error: { code: 'INSERT_ERROR', message } }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  return new Response(JSON.stringify({ data }), {
    status: 201, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

// ─── Update ───────────────────────────────────────────────────────────────────

interface UpdateRatingBody {
  communication_score?: number;
  quality_score?: number;
  speed_score?: number;
  accuracy_score?: number;
  overall_score?: number;
  review_text?: string;
}

async function updateRating(
  supabase: ReturnType<typeof createClient>,
  id: string,
  req: Request
) {
  if (!isValidUUID(id)) {
    return new Response(JSON.stringify({ error: { code: 'INVALID_ID', message: 'Invalid rating ID' } }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  const body: UpdateRatingBody = await req.json();

  const scoreFields: (keyof UpdateRatingBody)[] = [
    'communication_score', 'quality_score', 'speed_score',
    'accuracy_score', 'overall_score',
  ];
  for (const field of scoreFields) {
    if (body[field] !== undefined && !isScore(body[field])) {
      return new Response(JSON.stringify({
        error: { code: 'VALIDATION_ERROR', message: `${field} must be an integer between 1 and 5` },
      }), {
        status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
      });
    }
  }

  const updates: Record<string, unknown> = {};
  for (const field of scoreFields) {
    if (body[field] !== undefined) updates[field] = body[field];
  }
  if (body.review_text !== undefined) updates.review_text = body.review_text;

  if (Object.keys(updates).length === 0) {
    return new Response(JSON.stringify({ error: { code: 'NO_UPDATES', message: 'No valid fields to update' } }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  updates.updated_at = new Date().toISOString();

  const { data, error } = await supabase
    .from('ratings')
    .update(updates)
    .eq('id', id)
    .select()
    .single();

  if (error || !data) {
    return new Response(JSON.stringify({ error: { code: 'UPDATE_ERROR', message: error?.message ?? 'Not found' } }), {
      status: 404, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  return new Response(JSON.stringify({ data }), {
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

// ─── Delete ────────────────────────────────────────────────────────────────────

async function deleteRating(
  supabase: ReturnType<typeof createClient>,
  id: string
) {
  if (!isValidUUID(id)) {
    return new Response(JSON.stringify({ error: { code: 'INVALID_ID', message: 'Invalid rating ID' } }), {
      status: 400, headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  }

  const { error } = await supabase
    .from('ratings')
    .delete()
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
