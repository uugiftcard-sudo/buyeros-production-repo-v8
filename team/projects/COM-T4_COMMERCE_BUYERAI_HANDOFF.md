# COM-T4: Commerce → BuyerOS Data Handoff Contract

**Document version:** 1.0
**Date:** 2026-05-28
**Source:** CLOTH (`/Users/rubykan/Documents/CLOTH`) + BuyerOS (`/Users/rubykan/Downloads/buyeros-production-repo-v8`)
**Owner:** commerce (CLOTH), buyer_ai (BuyerOS)
**Status:** DRAFT — needs user review

> **Purpose:** Define the exact payload shapes CLOTH sends to BuyerOS for cross-line data handoff. BuyerOS owns reconciliation; CLOTH only supplies data.

---

## Architecture

```
CLOTH (commerce)                    BuyerOS (buyer_ai)
┌─────────────────────┐            ┌─────────────────────┐
│ Orders, Inventory,  │ ──push──►  │ Refund matching,    │
│ Support, Finance    │            │ OCR posting,        │
│                     │            │ Manual review,      │
│                     │            │ Buyer report        │
└─────────────────────┘            └─────────────────────┘
```

**Rule:** CLOTH must never mutate BuyerOS state directly. All handoff is via API push or polling.

---

## 1. Order Handoff

### Source
- `POST /api/orders` in CLOTH creates an order
- `PUT /api/orders/:id` updates order status

### CLOTH Order Shape (internal)

```typescript
interface Order {
  id: string;           // "o_xxxxx"
  productId: string;    // "p001"
  buyerInfo: {
    name: string;       // "張小明"
    phone: string;      // "13812345678"
    address: string;    // "香港中環..."
  };
  status: '待付款' | '待发货' | '已发货' | '已完成' | '已取消';
  totalPrice: number;   // CNY
  createdAt: string;    // ISO 8601
  updatedAt?: string;
}

interface OrderWithProduct extends Order {
  product: Product;     // Joined product data
}
```

### Handoff Payload (CLOTH → BuyerOS)

```json
{
  "event": "order.created",
  "source": "commerce",
  "timestamp": "2026-05-28T12:00:00.000Z",
  "payload": {
    "orderId": "o_a1b2c3",
    "productId": "p001",
    "productTitle": "Gucci GG Marmont 链条斜挎包 黑色",
    "brand": "Gucci",
    "category": "包袋",
    "market": "HK",
    "totalPrice": 6800,
    "currency": "CNY",
    "paymentStatus": "pending",
    "fulfillmentStatus": "unfulfilled",
    "buyer": {
      "name": "張小明",
      "phone": "13812345678",
      "region": "HK"
    },
    "relatedOrderId": null,
    "traceId": "trace_cloth_o_a1b2c3"
  }
}
```

### BuyerOS Trigger Points

| CLOTH Action | Trigger | BuyerOS Expected Behavior |
|---|---|---|
| `POST /api/orders` (new order) | Order created | Log to buyer_ai task feed; optional: dispatch refund-check task |
| `PUT /api/orders/:id` → `已完成` | Order fulfilled | Close fulfillment loop in buyer_ai |
| `PUT /api/orders/:id` → `已取消` | Order cancelled | Trigger refund-check task in buyer_ai |
| `PUT /api/orders/:id` → `已发货` | Order shipped | Update buyer_ai trace with shipping ref |

### BuyerOS API (receiving)

```
POST /api/commerce/order
Content-Type: application/json
Authorization: Bearer <BUYEROS_API_KEY>

{ ...handoff payload above... }
```

---

## 2. Payment / Refund Handoff

### Source
CLOTH has no payment gateway implemented yet (payment is simulated). When Stripe/PayPal is wired, payment events are the trigger.

### Handoff Payload (CLOTH → BuyerOS)

```json
{
  "event": "payment.captured",
  "source": "commerce",
  "timestamp": "2026-05-28T12:00:00.000Z",
  "payload": {
    "orderId": "o_a1b2c3",
    "paymentRef": "pi_stripe_xxxxx",
    "paymentMethod": "card",
    "amount": 6800,
    "currency": "CNY",
    "status": "captured",
    "buyerEmail": "zhangxm@email.com",
    "relatedRefundId": null
  }
}
```

```json
{
  "event": "refund.initiated",
  "source": "commerce",
  "timestamp": "2026-05-28T14:00:00.000Z",
  "payload": {
    "orderId": "o_a1b2c3",
    "refundRef": "re_cloth_xxxxx",
    "paymentRef": "pi_stripe_xxxxx",
    "amount": 6800,
    "currency": "CNY",
    "reason": "customer_request",
    "reasonDetail": "商品與圖片不符",
    "relatedSupportTicketId": "TKT-2024-002",
    "status": "pending_buyer_ai_review"
  }
}
```

### Ownership Boundary

| CLOTH does | BuyerOS does |
|---|---|
| Records payment/refund intent | Matches refund to original order/payment |
| Creates refund record with reason | Runs OCR on refund documents |
| Links support ticket | Posts to accounting system |
| Shows refund status to customer | Generates buyer report with refund ROI |
| **Never** reconciles refunds | **Never** creates CLOTH orders |

---

## 3. Inventory Movement Handoff

### Source
- `POST /api/inventory/:id/inbound` — stock comes in
- `POST /api/inventory/:id/outbound` — stock goes out
- `PUT /api/inventory/:id` — manual adjustment

### Inventory Item Shape (internal)

```typescript
interface InventoryItem {
  id: string;                    // "inv001"
  sku: string;                   // "GUCCI-MARMONT-001"
  productId?: string;            // "p001" (links to CLOTH product)
  productName: string;           // "Gucci GG Marmont 链条斜挎包 黑色"
  brand?: string;                // "Gucci"
  category?: string;             // "包袋"
  currentStock: number;
  minStockThreshold: number;
  unitCost?: number;             // CNY
  unitPrice?: number;            // CNY
  location?: string;              // "CN-WH-A-01"
  supplier?: string;             // "Vestiaire Collective"
  status: 'in_stock' | 'low_stock' | 'out_of_stock';
}
```

### Transaction Shape

```typescript
interface InventoryTransaction {
  id: string;                    // "tx_xxxxx"
  inventoryId: string;           // "inv001"
  sku: string;
  type: 'inbound' | 'outbound' | 'adjustment' | 'return';
  quantity: number;              // positive for inbound, negative for outbound
  referenceNo?: string;          // PO number, return RMA, etc.
  notes?: string;
  operator?: string;
  createdAt: string;            // ISO 8601
}
```

### Handoff Payload (CLOTH → BuyerOS)

**Inbound:**
```json
{
  "event": "inventory.inbound",
  "source": "commerce",
  "timestamp": "2026-05-28T10:00:00.000Z",
  "payload": {
    "inventoryId": "inv001",
    "sku": "GUCCI-MARMONT-001",
    "productId": "p001",
    "productName": "Gucci GG Marmont 链条斜挎包 黑色",
    "quantity": 2,
    "unitCost": 3200,
    "totalCost": 6400,
    "currency": "CNY",
    "referenceNo": "PO-2026-051",
    "supplier": "Vestiaire Collective",
    "location": "CN-WH-A-01",
    "operator": "admin",
    "traceId": "trace_cloth_inv_inb_001"
  }
}
```

**Outbound (sale-triggered):**
```json
{
  "event": "inventory.outbound",
  "source": "commerce",
  "timestamp": "2026-05-28T12:00:00.000Z",
  "payload": {
    "inventoryId": "inv001",
    "sku": "GUCCI-MARMONT-001",
    "productId": "p001",
    "productName": "Gucci GG Marmont 链条斜挎包 黑色",
    "quantity": -1,
    "unitPrice": 6800,
    "reason": "sale",
    "orderId": "o_a1b2c3",
    "location": "CN-WH-A-01",
    "operator": "system",
    "traceId": "trace_cloth_inv_out_001"
  }
}
```

**Low stock alert:**
```json
{
  "event": "inventory.low_stock",
  "source": "commerce",
  "timestamp": "2026-05-28T09:00:00.000Z",
  "payload": {
    "inventoryId": "inv005",
    "sku": "CELINE-TRIOMPHE-001",
    "productName": "Celine Triomphe 豆腐包 焦糖色",
    "currentStock": 0,
    "minStockThreshold": 1,
    "unitCost": 4200,
    "lastInboundDate": "2024-01-22T10:40:00Z",
    "supplier": "欧洲旅游采购",
    "recommendedAction": "reorder",
    "traceId": "trace_cloth_inv_alert_005"
  }
}
```

### BuyerOS Trigger Points

| CLOTH Action | Trigger | BuyerOS Expected Behavior |
|---|---|---|
| `POST /api/inventory/:id/inbound` | Stock received | Record purchase cost; update procurement ROI |
| `POST /api/inventory/:id/outbound` | Stock leaves | Match to sale; close inventory loop |
| `PUT /api/inventory/:id` (stock=0) | Out of stock | Alert buyer_ai for reorder decision |
| Low stock alert | Stock ≤ threshold | Dispatch reorder task to buyer_ai |

---

## 4. Support Case Handoff

### Source
- `POST /api/support/tickets` — new ticket created
- `POST /api/support/tickets/:id/messages` — new message
- `PUT /api/support/tickets/:id` — ticket status change

### Support Ticket Shape (internal)

```typescript
interface SupportTicket {
  id: string;                    // "st001"
  ticketNo: string;              // "TKT-2024-001"
  type: 'inquiry' | 'return' | 'exchange' | 'repair';
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  subject: string;
  description: string;
  orderId?: string;              // links to CLOTH order
  priority: 'low' | 'normal' | 'high' | 'urgent';
  customerName: string;
  customerEmail: string;
  customerPhone?: string;
  adminReply?: string;
  createdAt: string;
  updatedAt?: string;
}
```

### Handoff Payload (CLOTH → BuyerOS)

```json
{
  "event": "support.ticket.created",
  "source": "commerce",
  "timestamp": "2026-05-28T14:00:00.000Z",
  "payload": {
    "ticketId": "st002",
    "ticketNo": "TKT-2024-002",
    "type": "return",
    "subject": "Hermès Birkin 需要申请退货",
    "priority": "high",
    "status": "open",
    "orderId": "o002",
    "productTitle": "Hermès Birkin 25 黑色Togo皮",
    "productId": "p006",
    "customer": {
      "name": "李婷婷",
      "email": "litt@email.com",
      "phone": null
    },
    "description": "购买的爱马仕铂金包，收到后发现皮质颜色与图片有差异，请问可以申请退货吗？",
    "traceId": "trace_cloth_st_002"
  }
}
```

### BuyerOS Trigger Points

| CLOTH Action | Trigger | BuyerOS Expected Behavior |
|---|---|---|
| Ticket `type=return`, `priority=urgent` | Urgent return | Start OCR refund workflow immediately |
| Ticket `type=exchange` | Exchange request | Check inventory availability for swap |
| Ticket linked to `orderId` | Ticket with order | Link to buyer report for that order |
| Ticket status → `resolved` | Ticket closed | Log resolution in buyer_ai trace |

---

## 5. Implementation Notes

### Current State
- CLOTH does NOT currently push events to BuyerOS — this is a **future integration contract**
- CLOTH → BuyerOS communication is currently **one-way**: BuyerOS dispatches tasks to CLOTH via the `/api/projects/dispatch` workflow
- Reverse push (CLOTH → BuyerOS) requires BuyerOS to expose a receiving endpoint and CLOTH to add a webhook/http-post layer

### Implementation Order
1. **Phase 1 (M1):** BuyerOS adds `POST /api/commerce/order` and `POST /api/commerce/event` endpoints
2. **Phase 2 (M2):** CLOTH adds a lightweight event emitter service (`api/src/services/eventEmitter.ts`)
3. **Phase 3 (M3):** Wire up order.created → buyer_ai event in CLOTH
4. **Phase 4 (M4):** Wire up refund.initiated → buyer_ai event
5. **Phase 5 (M5):** Wire up inventory.low_stock → buyer_ai event

### Forbidden Mutations
- CLOTH must **never** call `POST /api/tasks/*` on BuyerOS directly
- CLOTH must **never** write to BuyerOS Redis/memory state
- CLOTH must **never** trigger buyer_ai refund workflows without going through the contract API
- BuyerOS must **never** update CLOTH order status directly

### API Keys
- CLOTH uses `BUYEROS_API_KEY` env var to authenticate when calling BuyerOS endpoints
- BuyerOS validates this key in `Authorization: Bearer <key>` header
- Both repos have `.env.example` documenting this key

---

## 6. Verification Checklist

- [ ] BuyerOS exposes `POST /api/commerce/order` and logs the event
- [ ] BuyerOS exposes `POST /api/commerce/event` for generic events
- [ ] CLOTH event emitter service created at `api/src/services/eventEmitter.ts`
- [ ] Order creation in CLOTH triggers `order.created` event
- [ ] Order cancellation triggers `refund.initiated` event
- [ ] Inventory inbound triggers `inventory.inbound` event
- [ ] Low stock triggers `inventory.low_stock` alert
- [ ] Support ticket creation triggers `support.ticket.created` event
- [ ] BuyerOS buyer report shows incoming commerce events
- [ ] COM-T4 checkbox in `FUNCTION_COMPLETION_PROJECT.md` marked ✅
