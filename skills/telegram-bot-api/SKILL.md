---
name: telegram-bot-api
description: "Comprehensive, up-to-date Telegram Bot API development and troubleshooting guide. Covers updates (webhooks & long polling), messages & formatting (HTML/MarkdownV2/Entities/Drafts/Ephemeral), interactive keyboards, Telegram Stars & payments, Mini Apps & initData validation, Telegram Business & guest mode, forum topics & moderation, rate limits, and BotFather configurations. Use whenever designing, implementing, debugging, or reviewing Telegram bots. Triggers: 'telegram bot', 'telegram bot api', 'telegram webhook', 'telegram stars', 'telegram inline keyboard', 'telegram mini app', 'aiogram', 'grammY', 'telegraf', 'python-telegram-bot'."
---

# Telegram Bot API Skill

A dense, modular reference and decision guide for building, securing, and debugging bots on the Telegram Bot API (supporting versions through Bot API 10.x / 9.x / 8.x / 7.x).

This skill uses **progressive disclosure**: `SKILL.md` defines core protocol invariants, quick-decision matrices, and common pitfall diagnostics, routing to specialized, dense reference files in `references/` for detailed implementation schemas and payloads.

---

## 1. Progressive Disclosure Routing Map

When working on a specific subsystem, read the dedicated reference file instead of guessing:

| Subsystem / Topic | Reference Document | When to Load |
| :--- | :--- | :--- |
| **Updates & Webhooks** | [`references/updates-and-webhooks.md`](./references/updates-and-webhooks.md) | Setting up `setWebhook` / `getUpdates`, webhook secret tokens, payload verification, update types (`message`, `callback_query`, `chat_member`, etc.), drop pending updates. |
| **Rich Messages & Ephemeral (10.x)** | [`references/rich-messages-and-ephemeral.md`](./references/rich-messages-and-ephemeral.md) | Structured AST blocks (`sendRichMessage`), AI `thinking` blocks, tables, collages, Ephemeral messages in groups, live AI draft streaming (`sendRichMessageDraft`, `can_stop`). |
| **Messages, Media & Formatting** | [`references/messages-formatting-and-media.md`](./references/messages-formatting-and-media.md) | `sendMessage`, `sendPhoto`, `sendMediaGroup`, HTML vs MarkdownV2 escaping rules, `MessageEntity`, file uploads (`InputFile` / `file_id`). |
| **Keyboards & Interactive UI** | [`references/keyboards-and-interactive-ui.md`](./references/keyboards-and-interactive-ui.md) | `InlineKeyboardMarkup`, `ReplyKeyboardMarkup`, `ForceReply`, `answerCallbackQuery` timeout SLA, 64-byte `callback_data` limit, button styles & custom emoji. |
| **Telegram Stars & Payments** | [`references/payments-and-telegram-stars.md`](./references/payments-and-telegram-stars.md) | Telegram Stars (`XTR`), digital goods, `sendInvoice`, `createInvoiceLink`, `pre_checkout_query` 10-second SLA, star refunds, paid media, star subscriptions. |
| **Mini Apps (TMA) & WebApps** | [`references/mini-apps-and-webapps.md`](./references/mini-apps-and-webapps.md) | Telegram Mini Apps initialization, HMAC-SHA256 `initData` server-side validation, fullscreen/orientation, communication protocols, safe area insets. |
| **Business Bots & Guest Mode** | [`references/business-and-guest-bots.md`](./references/business-and-guest-bots.md) | Telegram Business connection (`business_connection_id`, `business_message`), Guest mode (`guest_message`, `answerGuestQuery`), bot-to-bot messaging, managed bots. |
| **Chats, Forums & Moderation** | [`references/chats-forums-and-moderation.md`](./references/chats-forums-and-moderation.md) | Forum topics (`createForumTopic`, `message_thread_id`), chat permissions (`ChatPermissions`), join requests, member bans/mutes, message reactions. |
| **Rate Limits & Error Handling** | [`references/rate-limits-and-error-handling.md`](./references/rate-limits-and-error-handling.md) | 30 msg/s global limit, 1 msg/s chat limit, 20 msg/min group limit, 429 `retry_after`, 400 Bad Request error catalog, supergroup migration (`migrate_to_chat_id`). |
| **Bot Configuration & BotFather** | [`references/botfather-and-configuration.md`](./references/botfather-and-configuration.md) | `setMyCommands` and `BotCommandScope`, descriptions, menu buttons, BotFather settings (Privacy Mode, Group Admin rights, Inline mode). |

---

## 2. Core Protocol Invariants

All Bot API integrations must obey these universal rules:

1. **Base URL Structure**:
   `https://api.telegram.org/bot<token>/<methodName>` (or `https://api.telegram.org/file/bot<token>/<file_path>` for downloads).
2. **HTTP Methods & Headers**:
   - `GET` or `POST` supported; `POST` with `Content-Type: application/json` is recommended for all JSON payloads.
   - Use `multipart/form-data` ONLY when uploading new binary files via `InputFile`.
3. **Response Schema**:
   - Always returns JSON:
     ```json
     {
       "ok": true,
       "result": { ... }
     }
     ```
   - On error:
     ```json
     {
       "ok": false,
       "error_code": 400,
       "description": "Bad Request: chat not found",
       "parameters": {
         "retry_after": 12,
         "migrate_to_chat_id": -1001234567890
       }
     }
     ```
4. **64-bit Integer Safety**:
   - User IDs (`user_id`), Chat IDs (`chat_id`), and Message IDs can exceed $2^{31}-1$ (and supergroup chat IDs are negative 64-bit integers like `-100...`).
   - In JavaScript/JSON parsers, preserve 64-bit integers (`BigInt` or strings) to prevent truncation.

---

## 3. Quick Decision Trees

### Transport Architecture: Long Polling vs Webhook
```
Is your bot in local development or behind strict NAT/firewalls without public HTTPS?
  ├─► YES: Use Long Polling (getUpdates with timeout=30, offset=last_id+1)
  └─► NO (Production):
        Is the bot handling high traffic (>100 updates/sec) or running on serverless/FaaS?
          ├─► YES: Use Webhooks (setWebhook + secret_token + reverse proxy + drop_pending_updates on deploy)
          └─► Standard Server: Either webhook or long-polling worker cluster is viable.
```

### Text Formatting: HTML vs MarkdownV2 vs MessageEntity
```
Is message text dynamically generated / user-provided?
  ├─► YES: Prefer HTML (with html-escaping on dynamic variables: & < > ")
  │        OR MessageEntity array (programmatic offset/length, zero escaping risks).
  └─► Static / Templated:
        ├─► MarkdownV2: Requires strict escaping of 18 special chars: _ * [ ] ( ) ~ ` > # + - = | { } . ! \
        └─► HTML: Simple tags: <b>, <i>, <code>, <pre>, <a href="...">, <tg-spoiler>, <blockquote expandable>.
```

### Monetization: Telegram Stars (`XTR`) vs Traditional Payments
```
Are you selling digital goods, bot features, premium content, or subscriptions?
  ├─► MUST use Telegram Stars (currency="XTR", prices in integer stars) per Apple/Google/Telegram TOS.
Are you selling physical goods or offline services?
  └─► Use fiat currency provider tokens (e.g., Stripe) with sendInvoice.
```

---

## 4. Top 8 Telegram Bot Gotchas & Fixes

| Symptom / Error | Root Cause | Immediate Remedy |
| :--- | :--- | :--- |
| **Perpetual spinner on inline buttons** | Bot did not answer the callback query. | Call `answerCallbackQuery(callback_query_id)` immediately on receiving every `callback_query`. |
| **`400: Bad Request: can't parse entities`** | Unescaped character in `MarkdownV2` or unclosed tag in `HTML`. | Use HTML with proper escaping for variables, or use helper escaping utilities for all 18 MarkdownV2 symbols. |
| **`429: Too Many Requests`** | Exceeded 30 msg/s global, 1 msg/s private, or 20 msg/min group rate limits. | Inspect `parameters.retry_after`, pause execution, and implement a leaky-bucket queue for outgoing messages. |
| **`400: Bad Request: message is not modified`** | Called `editMessageText` or `editMessageReplyMarkup` with identical content. | Catch and ignore this specific error description, or diff before sending edits. |
| **Group messages not received** | Bot Privacy Mode is enabled in BotFather. | Send `/setprivacy` -> `Disable` in [@BotFather](https://t.me/BotFather) if the bot needs all group messages, or make bot an admin. |
| **`pre_checkout_query` fails / times out** | Response not sent within 10 seconds. | Call `answerPreCheckoutQuery(pre_checkout_query_id, ok=True/False)` within **10 seconds** SLA. |
| **`400: BUTTON_DATA_INVALID`** | `callback_data` exceeds 64 bytes. | `callback_data` is limited to 1-64 UTF-8 bytes. Store large state in database/Redis and pass a short key/UUID in `callback_data`. |
| **Supergroup messages fail after upgrade** | Group converted to supergroup, ID changed. | Check `parameters.migrate_to_chat_id` from error and migrate your database record from old `-xxx` to new `-100xxx`. |

---

## 5. Development & Verification Checklist

When building or reviewing a Telegram Bot implementation:

- [ ] **Secret Token Verification**: Webhook endpoints validate the `X-Telegram-Bot-Api-Secret-Token` header.
- [ ] **Callback Queries Answered**: Every `callback_query` handler calls `answerCallbackQuery`.
- [ ] **Pre-checkout SLA**: `pre_checkout_query` handlers resolve within 10 seconds.
- [ ] **Escaping Hygiene**: Dynamic user text in formatted messages is sanitised before string interpolation.
- [ ] **Rate Limiter & Queue**: Outgoing broadcasts adhere to the 30 msg/s ceiling and back off on `retry_after`.
- [ ] **State Machine Safety**: Conversation state stores user/chat IDs as 64-bit safe numbers/strings.
- [ ] **Allowed Updates Scoped**: `setWebhook` / `getUpdates` specifies `allowed_updates` to avoid unhandled update backlogs.
- [ ] **Graceful Shutdown**: On process exit, webhook/polling connections cleanly close without dropping active in-flight jobs.
