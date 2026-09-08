# Updates, Webhooks & Long Polling

This reference details the mechanics of ingesting Telegram updates via Webhooks and Long Polling, handling the `Update` object taxonomy, securing webhook endpoints, and preventing update drops or backlogs.

---

## 1. The Update Pipeline

Every interaction with a Telegram bot arrives wrapped in an `Update` object with a unique, monotonically increasing `update_id`.

### Ingestion Methods Comparison

| Feature | Long Polling (`getUpdates`) | Webhook (`setWebhook`) |
| :--- | :--- | :--- |
| **Hosting Requirement** | Any machine with outbound internet access (NAT/VPN/Local). | Public IPv4/IPv6 address, valid SSL/TLS certificate (HTTPS only). |
| **Latency** | 0–500ms (depending on polling timeout). | Real-time push (<50ms). |
| **Resource Usage** | Continuous open HTTP connection. | Event-driven per incoming batch. |
| **Concurrency & Scale** | Single consumer worker or partition by `update_id`. | Scale horizontally behind an HTTP load balancer. |
| **Best For** | Local development, staging, simple worker setups. | High-throughput production, serverless (AWS Lambda, Cloudflare Workers). |

---

## 2. Long Polling: `getUpdates`

### Method Signature & Parameters
```http
POST https://api.telegram.org/bot<token>/getUpdates
Content-Type: application/json

{
  "offset": 123456789,
  "limit": 100,
  "timeout": 30,
  "allowed_updates": ["message", "callback_query", "chat_member"]
}
```

- **`offset`** (`Integer`, optional): Identifier of the first update to be returned. Must be `last_processed_update_id + 1`. Setting this confirms receipt of all previous updates.
- **`limit`** (`Integer`, optional): Number of updates to retrieve (1–100, default 100).
- **`timeout`** (`Integer`, optional): Timeout in seconds for long polling (0–50, default 0). Use `30` or `50` to maintain an active long-poll connection and avoid hammering the server.
- **`allowed_updates`** (`Array of String`, optional): Explicit list of update types to receive. **If omitted, `chat_member`, `message_reaction`, and certain other updates will NOT be received by default.**

### Long Polling Loop Invariant
```python
offset = 0
while running:
    try:
        updates = await bot.get_updates(offset=offset, timeout=30, allowed_updates=["message", "callback_query", "my_chat_member"])
        for update in updates:
            await process_update(update)
            offset = update.update_id + 1
    except NetworkError:
        await asyncio.sleep(1)
```

---

## 3. Webhooks: `setWebhook`, `deleteWebhook`, `getWebhookInfo`

### `setWebhook` Parameters
```http
POST https://api.telegram.org/bot<token>/setWebhook
Content-Type: application/json

{
  "url": "https://bot.example.com/api/telegram/webhook",
  "max_connections": 40,
  "allowed_updates": ["message", "callback_query", "pre_checkout_query", "my_chat_member"],
  "drop_pending_updates": true,
  "secret_token": "a-z0-9_-RandomSecureSecretTokenString123"
}
```

- **`url`** (`String`, required): HTTPS URL to send updates to. Use an empty string `""` to remove webhook.
- **`certificate`** (`InputFile`, optional): Public key certificate for self-signed certificates.
- **`ip_address`** (`String`, optional): Explicit IP address to bypass DNS lookups.
- **`max_connections`** (`Integer`, optional): Maximum allowed concurrent HTTPS connections (1–100, default 40).
- **`allowed_updates`** (`Array of String`, optional): JSON-serialized list of update types to deliver.
- **`drop_pending_updates`** (`Boolean`, optional): Pass `true` during deployment or redeployment to discard accumulated backlog updates that occurred while the bot was offline.
- **`secret_token`** (`String`, optional): 1–256 characters (`[A-Za-z0-9_-]`). Telegram sends this in the `X-Telegram-Bot-Api-Secret-Token` header with every request.

### `deleteWebhook`
```http
POST https://api.telegram.org/bot<token>/deleteWebhook
Content-Type: application/json

{
  "drop_pending_updates": false
}
```

### `getWebhookInfo`
Returns the current webhook status, including `url`, `has_custom_certificate`, `pending_update_count`, `last_error_date`, `last_error_message`, `last_synchronization_error_date`, `max_connections`, and `allowed_updates`.

---

## 4. Webhook Security & Request Verification

Never process webhook payloads without verifying their origin.

### Verification Strategy 1: Secret Token Header (Recommended)
When registering with `secret_token`, check the incoming header:
```typescript
// Fastify / Express / Node.js
function handleWebhook(req: Request, res: Response) {
  const secretHeader = req.headers['x-telegram-bot-api-secret-token'];
  if (secretHeader !== process.env.TELEGRAM_WEBHOOK_SECRET) {
    return res.status(401).send('Unauthorized');
  }
  
  // Immediately return 200 OK to Telegram, dispatch work asynchronously
  res.status(200).send({ ok: true });
  queue.push(req.body);
}
```

### Verification Strategy 2: Telegram Subnet Whitelisting
Telegram delivers webhook requests from `149.154.160.0/20` and `91.108.4.0/22`. Configure your reverse proxy (Nginx, Caddy, Cloudflare, AWS ALB) to restrict traffic.

---

## 5. Webhook HTTP Response Contract

- **200 OK SLA**: Telegram expects an HTTP `200 OK` response within **10–30 seconds**. If your endpoint times out or returns `5xx`/`4xx`, Telegram marks the webhook unhealthy and retries with exponential backoff.
- **Async Processing Pattern**:
  1. Receive HTTP POST.
  2. Validate secret token.
  3. Push update to an in-memory queue, Redis (BullMQ/Celery), or worker pool.
  4. Return `200 OK` immediately.
  5. Process update logic in worker thread/process.
- **Webhook Response Shortcuts**: You can reply directly to the update by returning a method payload in the HTTP response JSON (e.g., `{"method": "sendMessage", "chat_id": 123, "text": "Hello"}`). However, this is discouraged in production because it prevents error inspection and retry handling.

---

## 6. Update Object Taxonomy

An `Update` contains **at most ONE** of the following optional fields (plus `update_id`):

| Update Field | Payload Type | Trigger Condition |
| :--- | :--- | :--- |
| `message` | `Message` | New incoming text, media, command, or service message in private/group chat. |
| `edited_message` | `Message` | Existing message was edited. |
| `channel_post` | `Message` | New message posted in a channel where the bot is administrator. |
| `edited_channel_post` | `Message` | Channel post was edited. |
| `business_connection` | `BusinessConnection` | Bot was connected or disconnected from a Telegram Business account. |
| `business_message` | `Message` | New message in a Telegram Business chat managed by the bot. |
| `edited_business_message`| `Message` | Edited message in a Telegram Business chat. |
| `deleted_business_messages`| `BusinessMessagesDeleted`| Messages deleted from a Telegram Business chat. |
| `message_reaction` | `MessageReactionUpdated` | User changed their reaction on a message (requires explicit `allowed_updates`). |
| `message_reaction_count` | `MessageReactionCountUpdated`| Anonymous reaction counts updated on a message. |
| `inline_query` | `InlineQuery` | User typed `@botusername query` in any chat. |
| `chosen_inline_result` | `ChosenInlineResult` | User selected a result from an inline query. |
| `callback_query` | `CallbackQuery` | User pressed an `InlineKeyboardButton` with `callback_data`. |
| `shipping_query` | `ShippingQuery` | User provided shipping address for a physical invoice. |
| `pre_checkout_query` | `PreCheckoutQuery` | User clicked final confirmation to pay an invoice / Telegram Stars. |
| `purchased_paid_media` | `PaidMediaPurchased` | User bought paid media sent by the bot. |
| `poll` | `Poll` | Poll state changed (votes, closure). |
| `poll_answer` | `PollAnswer` | User voted in a non-anonymous poll. |
| `my_chat_member` | `ChatMemberUpdated` | Bot's own membership status or permissions changed (added/kicked/promoted). |
| `chat_member` | `ChatMemberUpdated` | Another user's status changed in a chat (requires explicit `allowed_updates`). |
| `chat_join_request` | `ChatJoinRequest` | User requested to join a private group/channel with join request link. |
| `chat_boost` | `ChatBoostUpdated` | Chat was boosted by a user. |
| `removed_chat_boost` | `ChatBoostRemoved` | Chat boost expired or was removed. |
| `guest_message` | `Message` | Message sent to a guest bot in a group chat. |
| `stopped_message_generation` | `MessageGenerationStopped`| User stopped bot's streaming draft response. |
| `subscription` | `BotSubscriptionUpdated` | User payment subscription created, renewed, or expired. |
| `managed_bot` | `ManagedBotUpdated` | Managed bot created or token refreshed. |
