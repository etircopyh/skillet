# Telegram Stars & Payments Architecture

This reference details monetization on Telegram: Telegram Stars (`XTR`) for digital goods, fiat payments for physical goods, invoice generation, the mandatory 10-second `pre_checkout_query` SLA, refunds, and paid media.

---

## 1. Digital Goods vs Physical Goods Policy

Telegram enforces strict payment routing rules based on platform app store policies (Apple App Store / Google Play):

| Product Type | Allowed Currency | `provider_token` | Method |
| :--- | :--- | :--- | :--- |
| **Digital Goods / Services / Bot Access / Mini App Purchases** | **`XTR` (Telegram Stars)** | Empty string `""` (do not specify) | `sendInvoice` or `createInvoiceLink` |
| **Physical Goods / Offline Services** | Fiat currencies (USD, EUR, etc.) | Connect payment provider via [@BotFather](https://t.me/BotFather) | `sendInvoice` or `createInvoiceLink` |

---

## 2. Invoices: `sendInvoice` and `createInvoiceLink`

### Creating a Telegram Stars Invoice Link
```http
POST https://api.telegram.org/bot<token>/createInvoiceLink
Content-Type: application/json

{
  "title": "VIP Subscription (1 Month)",
  "description": "Unlock AI generation features for 30 days.",
  "payload": "user_id_123:vip_sub_30d:order_9981",
  "currency": "XTR",
  "prices": [
    { "label": "VIP Pass", "amount": 250 }
  ]
}
```
*Note for `XTR`: `amount` is the exact integer number of Telegram Stars (e.g. `250` = 250 Stars). For fiat currencies (like `USD`), `amount` is in the smallest unit (e.g. `2500` = $25.00).*

### Sending an In-Chat Invoice (`sendInvoice`)
```json
{
  "chat_id": 123456789,
  "title": "E-Book: Mastery of Bots",
  "description": "Instant PDF download link.",
  "payload": "ebook_download_uuid_456",
  "currency": "XTR",
  "prices": [
    { "label": "E-Book", "amount": 100 }
  ],
  "start_parameter": "buy_ebook",
  "protect_content": true
}
```

---

## 3. The 4-Step Payment Lifecycle

```
[1. User clicks Pay in client]
              │
              ▼
[2. Telegram sends update: `pre_checkout_query`]
              │
              ▼
[3. Bot calls `answerPreCheckoutQuery` (MUST respond within 10s)]
       ├── ok: false ──► [Transaction cancelled, user shown error_message]
       └── ok: true  ──► [Telegram charges Stars / Card]
                                │
                                ▼
               [4. Telegram sends Message with `successful_payment`]
                                │
                                ▼
               [Bot fulfills order / delivers digital goods]
```

### The 10-Second Pre-Checkout SLA
When receiving a `pre_checkout_query`, your backend **MUST** answer within **10 seconds**, verifying inventory and price consistency:

```typescript
// Fastify / Express handler
async function handlePreCheckoutQuery(query: PreCheckoutQuery) {
  const isAvailable = await checkInventory(query.invoice_payload);
  
  if (!isAvailable) {
    await bot.answerPreCheckoutQuery({
      pre_checkout_query_id: query.id,
      ok: false,
      error_message: "Item is currently out of stock. You have not been charged."
    });
    return;
  }

  // Approve payment
  await bot.answerPreCheckoutQuery({
    pre_checkout_query_id: query.id,
    ok: true
  });
}
```

---

## 4. Fulfilling `successful_payment`

Once Telegram completes the charge, a `Message` containing `successful_payment` arrives:

```json
{
  "successful_payment": {
    "currency": "XTR",
    "total_amount": 250,
    "invoice_payload": "user_id_123:vip_sub_30d:order_9981",
    "telegram_payment_charge_id": "charge_id_abc12345",
    "provider_payment_charge_id": "xtr_charge_xyz"
  }
}
```

**Fulfillment Rule**: Persist `telegram_payment_charge_id` in your database as the idempotent key for order delivery.

---

## 5. Telegram Stars Refunds & Ledger Auditing

### Refunding Telegram Stars (`refundStarPayment`)
If an order cannot be fulfilled or a refund is requested:

```http
POST https://api.telegram.org/bot<token>/refundStarPayment
Content-Type: application/json

{
  "user_id": 123456789,
  "telegram_payment_charge_id": "charge_id_abc12345"
}
```

### Checking Bot Star Balance (`getMyStarBalance`)
```http
POST https://api.telegram.org/bot<token>/getMyStarBalance
```
*Requires no parameters. Returns `StarAmount` (`amount: Integer`, `nanostar_amount: Integer`).*

### Fetching Star Transaction Ledger (`getStarTransactions`)
Returns incoming and outgoing Telegram Star transactions for financial reconciliation:

```http
POST https://api.telegram.org/bot<token>/getStarTransactions
Content-Type: application/json

{
  "offset": 0,
  "limit": 100
}
```
*Returns `StarTransactions`. Each `StarTransaction` has `id`, `amount`, `date`, and `source`/`receiver` typed as `TransactionPartner` (`TransactionPartnerUser`, `TransactionPartnerChat`, `TransactionPartnerAffiliateProgram`, `TransactionPartnerFragment`, `TransactionPartnerTelegramAds`, `TransactionPartnerTelegramApi`, `TransactionPartnerOther`).*

---

## 6. Paid Media Channels & Posts (`sendPaidMedia`)

Allow bots to send blurred/locked media albums in channels or groups that unlock when users pay in Telegram Stars:

```json
// POST /sendPaidMedia
{
  "chat_id": -1001234567890,
  "star_count": 50,
  "media": [
    {
      "type": "photo",
      "media": "attach://photo_exclusive_1"
    },
    {
      "type": "video",
      "media": "attach://video_exclusive_2"
    }
  ],
  "caption": "Unlock premium dataset download and video breakdown."
}
```

When a user unlocks paid media, your bot receives a `purchased_paid_media` update containing `PaidMediaPurchased` (`from: User`, `paid_media_payload: String`).

---

## 7. Telegram Star Subscriptions (Bot API 8.0+)

Bots can sell recurring monthly subscriptions paid automatically in Telegram Stars:

```http
POST https://api.telegram.org/bot<token>/createInvoiceLink
Content-Type: application/json

{
  "title": "Pro Tier Monthly",
  "description": "Monthly subscription to Pro features.",
  "payload": "sub:user_123:pro_monthly",
  "currency": "XTR",
  "prices": [{ "label": "Monthly Sub", "amount": 300 }],
  "subscription_period": 2592000
}
```
*`subscription_period`: Number of seconds between subscription charges (currently `2592000` = 30 days).*

### Tracking Subscription Lifecycle (`BotSubscriptionUpdated`)
Listen for the `subscription` update field in `Update`:
- `subscription.is_canceled`: User canceled auto-renewal.
- `subscription.until_date`: Expiry Unix timestamp.

### Editing User Subscription (`editUserStarSubscription`)
Allows canceling or extending an active Telegram Star subscription:
```http
POST https://api.telegram.org/bot<token>/editUserStarSubscription
Content-Type: application/json

{
  "user_id": 123456789,
  "telegram_payment_charge_id": "charge_id_abc12345",
  "is_canceled": true
}
```

### Channel Subscription Invite Links (`createChatSubscriptionInviteLink`)
Create invite links to private channels that automatically charge a recurring monthly Telegram Star subscription:
```http
POST https://api.telegram.org/bot<token>/createChatSubscriptionInviteLink
Content-Type: application/json

{
  "chat_id": -1009876543210,
  "name": "VIP Signals Monthly",
  "subscription_period": 2592000,
  "subscription_price": 500
}
```
*`editChatSubscriptionInviteLink` allows modifying the name of existing subscription links.*

---

## 8. Gifts & Digital Collectibles (Bot API 9.2 - 9.4 / 10.3)

Bots can send, inspect, transfer, upgrade, and receive Telegram Gifts and blockchain-backed Unique Gifts:

### Available Gifts & Sending
- **`getAvailableGifts()`**: Fetches the list of gifts currently available for purchase from Telegram. Returns `Gifts`.
- **Sending Gifts (`sendGift`)**:
  ```http
  POST https://api.telegram.org/bot<token>/sendGift
  Content-Type: application/json

  {
    "user_id": 123456789,
    "gift_id": "gift_abc123",
    "text": "Happy coding!",
    "pay_for_upgrade": true
  }
  ```
- **Gifting Telegram Premium**: `giftPremiumSubscription(user_id, month_count, star_count, text)`.

### Managing & Converting Gifts
- **Querying Gifts**:
  - `getUserGifts(user_id)`: Fetches gifts owned by a specific user.
  - `getChatGifts(chat_id)`: Fetches gifts received by a channel or chat.
  - `getBusinessAccountGifts(business_connection_id)`: Fetches gifts received by business accounts.
- **Convert Gift to Stars (`convertGiftToStars`)**: Convert an un-upgraded regular gift into Telegram Stars (`user_id`, `owned_gift_id`).
- **Upgrade Gift (`upgradeGift`)**: Pay to upgrade a gift to a unique collectible (`user_id`, `owned_gift_id`, `keep_original_details`).
- **Transfer Gift (`transferGift`)**: Transfer an upgraded unique gift to another user or channel (`user_id`, `owned_gift_id`, `new_owner_chat_id`, `star_count`).
- **`UniqueGift` & Collectibles**: Includes `gift_id`, `rarity`, `is_burned`, `is_from_blockchain` (TON blockchain integration).
---

## 9. Invoices, Shipping, Star Settlements & Digital Gifts

### Shipping Query Handling
```typescript
// Must be answered within 10 seconds SLA
answerShippingQuery(params: {
  shipping_query_id: string;
  ok: boolean;
  shipping_options?: ShippingOption[];
  error_message?: string;
}): Promise<boolean>;
```

### Invoice & Transaction Data Types
```typescript
interface LabeledPrice { label: string; amount: number; } // In smallest currency units (cents or integer stars)
interface ShippingAddress { country_code: string; state: string; city: string; street_line1: string; street_line2: string; post_code: string; }
interface OrderInfo { name?: string; phone_number?: string; email?: string; shipping_address?: ShippingAddress; }
interface ShippingOption { id: string; title: string; prices: LabeledPrice[]; }
interface SuccessfulPayment {
  currency: string;
  total_amount: number;
  invoice_payload: string;
  subscription_expiration_date?: number;
  is_recurring?: boolean;
  is_first_recurring?: boolean;
  shipping_option_id?: string;
  order_info?: OrderInfo;
  telegram_payment_charge_id: string;
  provider_payment_charge_id: string;
}
interface RefundedPayment {
  currency: string;
  total_amount: number;
  invoice_payload: string;
  telegram_payment_charge_id: string;
  provider_payment_charge_id?: string;
}
interface AffiliateInfo {
  commission_per_mille: number; // 1-1000
  amount: number;
  nanostar_amount?: number;
  affiliate_user?: User;
  affiliate_chat?: Chat;
}

type RevenueWithdrawalState =
  | RevenueWithdrawalStatePending
  | RevenueWithdrawalStateSucceeded
  | RevenueWithdrawalStateFailed;

interface RevenueWithdrawalStatePending { type: 'pending'; }
interface RevenueWithdrawalStateSucceeded { type: 'succeeded'; date: number; url: string; }
interface RevenueWithdrawalStateFailed { type: 'failed'; }
```

### Unique & Regular Gifts Architecture (Bot API 9.2 - 10.3)
```typescript
interface GiftBackground { fill: BackgroundFill; }
interface UniqueGiftModel { name: string; document: Document; rarity_per_mille: number; }
interface UniqueGiftSymbol { name: string; document: Document; rarity_per_mille: number; }
interface UniqueGiftBackdropColors { center_color: number; edge_color: number; pattern_color: number; text_color: number; }
interface UniqueGiftBackdrop { name: string; colors: UniqueGiftBackdropColors; rarity_per_mille: number; }
interface UniqueGiftColors { model_color?: number; symbol_color?: number; }
interface GiftInfo { gift: Gift; send_date: number; text?: string; is_anonymous?: boolean; }
interface UniqueGiftInfo { gift: UniqueGift; send_date: number; is_origin?: boolean; }

type OwnedGift = OwnedGiftRegular | OwnedGiftUnique;
interface OwnedGiftRegular { type: 'regular'; gift: Gift; send_date: number; text?: string; is_anonymous?: boolean; can_be_upgraded?: boolean; }
interface OwnedGiftUnique { type: 'unique'; gift: UniqueGift; send_date: number; is_origin?: boolean; }
interface OwnedGifts { total_count: number; gifts: OwnedGift[]; next_offset?: string; }
interface AcceptedGiftTypes { allow_regular_gifts?: boolean; allow_unique_gifts?: boolean; }
```
