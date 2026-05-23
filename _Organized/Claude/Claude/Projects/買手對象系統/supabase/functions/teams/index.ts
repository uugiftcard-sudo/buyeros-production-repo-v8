/**
 * Edge Function: teams
 * supabase/functions/teams/index.ts
 *
 * 團隊管理 API
 * GET  /functions/v1/teams              — 所有團隊列表
 * POST /functions/v1/teams             — 創建團隊
 * GET  /functions/v1/teams/:id         — 團隊詳情（含成員）
 * PATCH /functions/v1/teams/:id        — 更新團隊
 * DELETE /functions/v1/teams/:id        — 刪除團隊
 * POST /functions/v1/teams/:id/members — 添加成員
 * DELETE /functions/v1/teams/:id/members/:buyerId — 移除成員
 * GET  /functions/v1/teams/performance — 團隊表現數據
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { jsonResponse, errorResponse } from '../_shared/index.ts';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204 });

  try {
    const url = new URL(req.url);
    const pathParts = url.pathname.split('/').filter(Boolean);
    // path: /functions/v1/teams[/extra/...parts]
    const extra = pathParts.slice(pathParts.indexOf('teams') + 1);
    const id = extra[0];
    const sub = extra[1];

    switch (req.method) {
      case 'GET': {
        if (url.pathname.endsWith('/performance')) {
          return await getTeamPerformance();
        }
        if (id) return await getTeamById(id);
        return await listTeams();
      }
      case 'POST': {
        if (id && sub === 'members') return await addMember(id, req);
        if (id) return errorResponse('BAD_REQUEST', 'Use /teams for creation', 400);
        return await createTeam(req);
      }
      case 'PATCH': {
        if (!id) return errorResponse('BAD_REQUEST', 'Team ID required', 400);
        return await updateTeam(id, req);
      }
      case 'DELETE': {
        if (!id) return errorResponse('BAD_REQUEST', 'Team ID required', 400);
        if (sub === 'members' && extra[2]) {
          return await removeMember(id, extra[2]);
        }
        return await deleteTeam(id);
      }
      default:
        return errorResponse('METHOD_NOT_ALLOWED', 'Invalid method', 405);
    }
  } catch (err) {
    console.error('teams API error:', err);
    return errorResponse('INTERNAL_ERROR', 'Internal error',
      500, err instanceof Error ? err.message : String(err));
  }
});

async function listTeams() {
  const { data, error } = await supabase
    .from('buyer_teams')
    .select(`
      *,
      manager:admin_users!buyer_teams_manager_id_fkey(id, display_name, email),
      member_count:buyer_team_members(count)
    `)
    .eq('is_active', true)
    .order('team_name');

  if (error) return errorResponse('DB_ERROR', 'Failed to list teams', 500, error);

  // Flatten member_count (it's an array of {count} objects)
  const teams = (data ?? []).map(t => ({
    ...t,
    member_count: Array.isArray(t.member_count) ? t.member_count[0]?.count ?? 0 : t.member_count,
  }));

  return jsonResponse(teams);
}

async function getTeamById(id: string) {
  const { data: team, error } = await supabase
    .from('buyer_teams')
    .select(`
      *,
      manager:admin_users!buyer_teams_manager_id_fkey(id, display_name, email),
      members:buyer_team_members(
        id, role, joined_at, is_active,
        buyer:buyers(id, display_name, phone, status, rating_avg, commission_rate)
      )
    `)
    .eq('id', id)
    .single();

  if (error || !team) return errorResponse('NOT_FOUND', 'Team not found', 404);
  return jsonResponse(team);
}

async function createTeam(req: Request) {
  const body = await req.json();
  const { team_name, team_code, description, manager_id, color, target_orders_monthly, target_revenue_monthly_cents } = body;

  if (!team_name?.trim() || !team_code?.trim()) {
    return errorResponse('VALIDATION_ERROR', 'team_name and team_code are required', 400);
  }

  const { data, error } = await supabase
    .from('buyer_teams')
    .insert({
      team_name: team_name.trim(),
      team_code: team_code.trim().toUpperCase(),
      description: description?.trim() ?? null,
      manager_id: manager_id ?? null,
      color: color ?? '#4f46e5',
      target_orders_monthly: target_orders_monthly ?? 50,
      target_revenue_monthly_cents: target_revenue_monthly_cents ?? 5000000,
    })
    .select()
    .single();

  if (error) return errorResponse('DB_ERROR', 'Failed to create team', 500, error);
  return jsonResponse(data, 201);
}

async function updateTeam(id: string, req: Request) {
  const body = await req.json();
  const allowed = ['team_name', 'team_code', 'description', 'manager_id', 'color', 'is_active', 'target_orders_monthly', 'target_revenue_monthly_cents', 'notes'];
  const updates: Record<string, unknown> = {};
  for (const key of allowed) {
    if (key in body) updates[key] = body[key];
  }

  const { data, error } = await supabase
    .from('buyer_teams')
    .update(updates)
    .eq('id', id)
    .select()
    .single();

  if (error) return errorResponse('DB_ERROR', 'Failed to update team', 500, error);
  return jsonResponse(data);
}

async function deleteTeam(id: string) {
  const { error } = await supabase
    .from('buyer_teams')
    .update({ is_active: false })
    .eq('id', id);

  if (error) return errorResponse('DB_ERROR', 'Failed to delete team', 500, error);
  return jsonResponse({ success: true });
}

async function addMember(teamId: string, req: Request) {
  const body = await req.json();
  const { buyer_id, role = 'member' } = body;

  if (!buyer_id) return errorResponse('VALIDATION_ERROR', 'buyer_id required', 400);

  const { data, error } = await supabase
    .from('buyer_team_members')
    .upsert({
      team_id: teamId,
      buyer_id,
      role,
      is_active: true,
    }, { onConflict: 'team_id,buyer_id' })
    .select(`
      id, team_id, buyer_id, role, joined_at, is_active,
      buyer:buyers(id, display_name, phone, status)
    `)
    .single();

  if (error) return errorResponse('DB_ERROR', 'Failed to add member', 500, error);
  return jsonResponse(data, 201);
}

async function removeMember(teamId: string, buyerId: string) {
  const { error } = await supabase
    .from('buyer_team_members')
    .update({ is_active: false })
    .eq('team_id', teamId)
    .eq('buyer_id', buyerId);

  if (error) return errorResponse('DB_ERROR', 'Failed to remove member', 500, error);
  return jsonResponse({ success: true });
}

async function getTeamPerformance() {
  const { data, error } = await supabase
    .from('v_team_performance')
    .select('*')
    .order('monthly_revenue_cents', { ascending: false });

  if (error) return errorResponse('DB_ERROR', 'Failed to fetch performance', 500, error);
  return jsonResponse(data ?? []);
}
