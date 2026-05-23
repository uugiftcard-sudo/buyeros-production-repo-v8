/**
 * Edge Function: telegram-webhook
 * supabase/functions/telegram-webhook/index.ts
 *
 * Telegram Bot Webhook Handler
 *
 * 接收 Telegram 的 updates（messages, callbacks, etc.）
 * 轉換為內部業務操作
 *
 * 部署：
 *   1. 在 Telegram BotFather 設定 webhook URL：
 *      https://<project-ref>.supabase.co/functions/v1/telegram-webhook
 *   2. 或者手動設定：
 *      setWebhook via Telegram API
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import {
  jsonResponse,
  errorResponse,
  generateOrderNumber,
} from '../_shared/index.ts';

const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const TELEGRAM_BOT_TOKEN = Deno.env.get('TELEGRAM_BOT_TOKEN')!;
const ADMIN_TG_ID = Deno.env.get('ADMIN_TG_ID') ?? '';

const supabase = createClient(supabaseUrl, supabaseServiceKey);

Deno.serve(async (req: Request) => {
  if (req.method === 'POST') {
    try {
      const body = await req.json();
      await handleUpdate(body);
      return jsonResponse({ ok: true });
    } catch (err) {
      console.error('Webhook error:', err);
      return errorResponse('WEBHOOK_ERROR', 'Failed to process update', 500);
    }
  }

  if (req.method === 'GET') {
    return jsonResponse({
      service: 'BuyerOS Telegram Webhook',
      status: 'running',
      timestamp: new Date().toISOString(),
    });
  }

  return errorResponse('METHOD_NOT_ALLOWED', 'Only POST and GET allowed', 405);
});

// ─── Update Handler ────────────────────────────────────────────────────────────

interface TelegramUpdate {
  update_id: number;
  message?: {
    from: { id: number; first_name?: string; last_name?: string; username?: string };
    chat: { id: number; type: string };
    text?: string;
    photo?: unknown[];
    document?: unknown;
    caption?: string;
  };
  callback_query?: {
    from: { id: number };
    data: string;
    message?: { chat: { id: number } };
  };
}

async function handleUpdate(update: TelegramUpdate) {
  // Callback Query（如 inline keyboard 按鈕）
  if (update.callback_query) {
    return await handleCallbackQuery(update.callback_query);
  }

  // 文字消息
  if (update.message?.text) {
    return await handleMessage(update.message);
  }

  // 圖片（收據）
  if (update.message?.photo) {
    return await handlePhoto(update.message);
  }

  // 文件
  if (update.message?.document) {
    return await handleDocument(update.message);
  }
}

// ─── Message Handler ───────────────────────────────────────────────────────────

async function handleMessage(msg: TelegramUpdate['message']) {
  const tgId = msg!.from.id;
  const chatId = msg!.chat.id;
  const text = msg!.text?.trim() ?? '';

  // 指令路由
  const command = text.split(' ')[0].toLowerCase();
  const args = text.slice(command.length).trim();

  // 檢查是否為 admin
  const isAdmin = String(tgId) === ADMIN_TG_ID;

  switch (command) {
    case '/start':
      await sendMessage(chatId, '👋 歡迎使用 BuyerOS！\n請選擇操作：', getMainMenuKeyboard());
      await handleNewUser(tgId, msg!.from);
      break;

    case '/help':
      await sendHelp(chatId, isAdmin);
      break;

    case '/myorders':
      await showMyOrders(chatId, tgId);
      break;

    case '/balance':
      await showBalance(chatId, tgId);
      break;

    case '/admin_orders':
      if (!isAdmin) { await sendMessage(chatId, '❌ 此指令僅限管理員使用'); return; }
      await showAllOrders(chatId);
      break;

    case '/neworder':
      await sendMessage(chatId, '📝 請告訴我們您想採購的商品：\n格式：\n商品名稱：\n數量：\n預算（可選）：');
      break;

    default:
      // 嘗試處理為新訂單內容
      if (text.length > 5) {
        await handleNewOrderRequest(chatId, tgId, text);
      } else {
        await sendMessage(chatId, '我不理解這個指令，輸入 /help 查看所有指令');
      }
  }
}

// ─── Callback Query Handler ───────────────────────────────────────────────────

async function handleCallbackQuery(cb: TelegramUpdate['callback_query']) {
  const chatId = cb.message?.chat.id ?? cb.from.id;
  const data = cb.data ?? '';
  const tgId = cb.from.id;

  const [action, ...params] = data.split(':');

  switch (action) {
    case 'show_order':
      await showOrderDetail(chatId, params[0]);
      break;
    case 'accept_order':
      await acceptOrder(chatId, tgId, params[0]);
      break;
    case 'status_filter':
      await showOrdersByStatus(chatId, params[0]);
      break;
  }

  // 回答 callback（消除 loading 狀態）
  await answerCallback(cb.id);
}

// ─── Bot Command Functions ─────────────────────────────────────────────────────

async function sendHelp(chatId: number, isAdmin: boolean) {
  let help = `📋 BuyerOS 指令列表：

👤 買手指令：
/myorders — 查看我的訂單
/balance — 查看結算餘額
/neworder — 新下單

🔧 管理員指令（需要權限）：
/admin_orders — 所有訂單管理`;

  if (isAdmin) {
    help += `
/admin_buyers — 買手管理
/admin_refunds — 退款審批
/broadcast — 群發通知`;
  }

  await sendMessage(chatId, help);
}

async function showMyOrders(chatId: number, tgId: number) {
  const { data: buyer } = await supabase
    .from('buyers')
    .select('id, display_name')
    .eq('telegram_user_id', String(tgId))
    .single();

  const { data: customer } = await supabase
    .from('customers')
    .select('id, display_name')
    .eq('telegram_user_id', String(tgId))
    .single();

  if (!buyer && !customer) {
    await sendMessage(chatId, '❌ 未找到您的帳戶，請先點擊 /start 註冊');
    return;
  }

  let orders;
  if (buyer) {
    const result = await supabase
      .from('orders')
      .select('*, customer:customers(display_name), items:order_items(count)')
      .eq('assigned_buyer_id', buyer.id)
      .order('created_at', { ascending: false })
      .limit(10);
    orders = result.data;
  } else {
    const result = await supabase
      .from('orders')
      .select('*, buyer:buyers(display_name), items:order_items(count)')
      .eq('customer_id', customer!.id)
      .order('created_at', { ascending: false })
      .limit(10);
    orders = result.data;
  }

  if (!orders || orders.length === 0) {
    await sendMessage(chatId, '📭 暫無訂單');
    return;
  }

  const lines = orders.map((o: any) => {
    const status = STATUS_EMOJI[o.status] ?? '📦';
    return `${status} ${o.order_number}\n   ${o.customer?.display_name ?? o.buyer?.display_name ?? ''} — HK$${(o.total_amount_cents / 100).toFixed(0)}\n   狀態：${o.status}`;
  });

  await sendMessage(chatId, `📦 您的訂單：\n\n${lines.join('\n\n')}`);
}

async function showBalance(chatId: number, tgId: number) {
  const { data: buyer } = await supabase
    .from('buyers')
    .select('id, display_name')
    .eq('telegram_user_id', String(tgId))
    .single();

  if (!buyer) {
    await sendMessage(chatId, '❌ 未找到買手帳戶');
    return;
  }

  const { data: settlements } = await supabase
    .from('settlements')
    .select('*')
    .eq('buyer_id', buyer.id)
    .order('created_at', { ascending: false })
    .limit(5);

  if (!settlements || settlements.length === 0) {
    await sendMessage(chatId, '📊 暫無結算記錄');
    return;
  }

  const lines = settlements.map((s: any) => {
    const emoji = SETTLEMENT_STATUS_EMOJI[s.status] ?? '📋';
    return `${emoji} ${s.settlement_number}（${s.period_start} ~ ${s.period_end}）\n   佣金：HK$${(s.commission_amount_cents / 100).toFixed(2)} | 狀態：${s.status}`;
  });

  await sendMessage(chatId, `💰 結算記錄：\n\n${lines.join('\n\n')}`);
}

async function showAllOrders(chatId: number) {
  const { data: orders } = await supabase
    .from('orders')
    .select('*, customer:customers(display_name), buyer:buyers(display_name)')
    .order('created_at', { ascending: false })
    .limit(20);

  if (!orders || orders.length === 0) {
    await sendMessage(chatId, '📭 暫無訂單');
    return;
  }

  const lines = orders.map((o: any) => {
    const status = STATUS_EMOJI[o.status] ?? '📦';
    return `${status} ${o.order_number} | ${o.customer?.display_name ?? '未知'}\n   買手：${o.buyer?.display_name ?? '未分配'} | HK$${(o.total_amount_cents / 100).toFixed(0)}`;
  });

  await sendMessage(chatId, `📋 所有訂單：\n\n${lines.join('\n\n')}`);
}

async function showOrderDetail(chatId: number, orderId: string) {
  const { data: order } = await supabase
    .from('orders')
    .select('*, customer:customers(*), buyer:buyers(*), items:order_items(*), transactions(*)')
    .eq('id', orderId)
    .single();

  if (!order) {
    await sendMessage(chatId, '❌ 找不到該訂單');
    return;
  }

  const status = STATUS_EMOJI[order.status] ?? '📦';
  const detail = `${status} 訂單：${order.order_number}
客戶：${order.customer?.display_name ?? '未知'}
買手：${order.buyer?.display_name ?? '未分配'}
狀態：${order.status}
總額：HK$${(order.total_amount_cents / 100).toFixed(2)}
已付：HK$${(order.deposit_paid_cents / 100).toFixed(2)}
尚欠：HK$${(order.balance_due_cents / 100).toFixed(2)}
建立：${order.created_at?.slice(0, 10)}
備註：${order.notes ?? '無'}`;

  await sendMessage(chatId, detail);
}

async function acceptOrder(chatId: number, tgId: number, orderId: string) {
  const { data: buyer } = await supabase
    .from('buyers')
    .select('id, display_name, status')
    .eq('telegram_user_id', String(tgId))
    .single();

  if (!buyer) {
    await sendMessage(chatId, '❌ 未找到買手帳戶');
    return;
  }
  if (buyer.status !== 'active') {
    await sendMessage(chatId, '❌ 您的買手帳戶尚未啟用');
    return;
  }

  const { data: order } = await supabase
    .from('orders')
    .select('id, status, assigned_buyer_id')
    .eq('id', orderId)
    .single();

  if (!order) {
    await sendMessage(chatId, '❌ 找不到該訂單');
    return;
  }
  if (order.status !== 'pending' && order.status !== 'assigned') {
    await sendMessage(chatId, `❌ 該訂單狀態為 ${order.status}，無法接單`);
    return;
  }

  await supabase
    .from('orders')
    .update({
      assigned_buyer_id: buyer.id,
      assigned_at: new Date().toISOString(),
      status: 'assigned',
    })
    .eq('id', orderId);

  await sendMessage(chatId, `✅ 已成功接單！\n訂單：${orderId}\n買手：${buyer.display_name}`);
}

async function handleNewUser(tgId: number, from: TelegramUpdate['message']['from']) {
  // 嘗試查找現有記錄
  const { data: buyer } = await supabase
    .from('buyers').select('id').eq('telegram_user_id', String(tgId)).single();

  const { data: customer } = await supabase
    .from('customers').select('id').eq('telegram_user_id', String(tgId)).single();

  // 尚未綁定，創建新客戶記錄
  if (!buyer && !customer) {
    const displayName = [from.first_name, from.last_name].filter(Boolean).join(' ') || 'TG User';
    await supabase.from('customers').insert({
      telegram_user_id: String(tgId),
      display_name: displayName,
      status: 'active',
    });
  }
}

async function handleNewOrderRequest(chatId: number, tgId: number, text: string) {
  const { data: customer } = await supabase
    .from('customers').select('id').eq('telegram_user_id', String(tgId)).single();

  if (!customer) {
    await sendMessage(chatId, '❌ 請先點擊 /start 註冊');
    return;
  }

  const orderNumber = await generateOrderNumber(supabase);

  // 簡單解析產品名稱
  const productName = text.slice(0, 200);

  const { data: order } = await supabase.from('orders').insert({
    order_number: orderNumber,
    customer_id: customer.id,
    status: 'pending',
    total_amount_cents: 0,
    notes: `Telegram 新單：${productName}`,
    source_channel: 'telegram',
  }).select().single();

  if (order) {
    await sendMessage(chatId,
      `✅ 已收到您的訂單！\n\n📋 訂單號：${orderNumber}\n📝 商品：${productName}\n\n我們的買手稍後會聯繫您確認價格和採購事宜。`);
  }
}

async function handlePhoto(msg: TelegramUpdate['message']) {
  const chatId = msg!.chat.id;
  await sendMessage(chatId, '📷 收到圖片！請稍候，工作人員會儘快確認。');
}

async function handleDocument(msg: TelegramUpdate['message']) {
  const chatId = msg!.chat.id;
  await sendMessage(chatId, '📎 收到文件！請稍候，工作人員會儘快確認。');
}

// ─── Telegram API Helpers ──────────────────────────────────────────────────────

async function sendMessage(chatId: number, text: string, replyMarkup?: unknown) {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
  const payload: Record<string, unknown> = {
    chat_id: chatId,
    text,
    parse_mode: 'Markdown',
  };
  if (replyMarkup) payload.reply_markup = replyMarkup;

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.text();
    console.error('Telegram sendMessage error:', err);
  }
}

async function answerCallback(callbackId: string) {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/answerCallbackQuery`;
  await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ callback_query_id: callbackId }),
  });
}

// ─── Keyboards ────────────────────────────────────────────────────────────────

function getMainMenuKeyboard() {
  return {
    inline_keyboard: [[
      { text: '📦 我的訂單', callback_data: 'menu:myorders' },
      { text: '💰 結算餘額', callback_data: 'menu:balance' },
      { text: '📝 新下單', callback_data: 'menu:neworder' },
    ]],
  };
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_EMOJI: Record<string, string> = {
  pending: '⏳',
  assigned: '👤',
  in_procurement: '🛒',
  received: '📦',
  delivered: '🚚',
  completed: '✅',
  cancelled: '❌',
};

const SETTLEMENT_STATUS_EMOJI: Record<string, string> = {
  pending: '⏳',
  approved: '👍',
  paid: '💸',
  disputed: '⚠️',
};
