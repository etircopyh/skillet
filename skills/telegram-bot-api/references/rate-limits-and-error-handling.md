# Rate Limits & Error Handling

This reference details Telegram Bot API rate limits, the complete error code catalog, retry-after backoff strategies, and supergroup ID migrations.

---

## 1. Telegram Bot API Rate Limits

Violating rate limits triggers `429 Too Many Requests`. Exceeding limits persistently risks temporary bot bans.

| Target / Context | Strict Rate Limit | Notes |
| :--- | :--- | :--- |
| **Global Outgoing (All Chats)** | **30 messages / second** | Hard limit across all API calls for a single bot token. |
| **Same Private Chat (`user_id`)** | **1 message / second** | Short bursts allowed; sustained traffic throttles to 1 msg/s. |
| **Same Group / Supergroup** | **20 messages / minute** | Shared across all messages sent to that group. |
| **Same Channel Post** | **20 messages / minute** | Broadcast channel posting limit. |
| **Message Edits (`editMessageText`)**| **1 edit / second** | Per individual message. |
| **Bulk Broadcasts (Mass DMs)** | Spread across time | Broadcasts must use a worker queue rate-limited to ~25 msg/s. |

---

## 2. Handling `429 Too Many Requests`

Telegram responses for 429 include a `parameters.retry_after` field indicating the number of seconds to wait before repeating the request.

```json
{
  "ok": false,
  "error_code": 429,
  "description": "Too Many Requests: retry after 8",
  "parameters": {
    "retry_after": 8
  }
}
```

### Exponential Backoff with Jitter Strategy
```typescript
async function executeWithRetry<T>(fn: () => Promise<T>, maxRetries = 5): Promise<T> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err: any) {
      if (err.response?.status === 429) {
        const retryAfter = err.response.data?.parameters?.retry_after || Math.pow(2, attempt);
        const jitter = Math.random() * 0.5;
        const waitMs = (retryAfter + jitter) * 1000;
        await new Promise((resolve) => setTimeout(resolve, waitMs));
        continue;
      }
      throw err;
    }
  }
  throw new Error("Max retries exceeded");
}
```

---

## 3. Comprehensive Error Code Catalog

### `400 Bad Request` Errors

| Error Description | Root Cause | Fix / Handling |
| :--- | :--- | :--- |
| `message is not modified` | Sent `editMessageText` or `editMessageReplyMarkup` with identical text/markup. | Safe to catch and silently ignore. |
| `can't parse entities` | Unclosed HTML tag or unescaped character in `MarkdownV2`. | Sanitize input or switch to programmatic `entities` array. |
| `BUTTON_DATA_INVALID` | `callback_data` exceeded 64 UTF-8 bytes. | Compress payload; store state in Redis and pass short key. |
| `chat not found` | Invalid `chat_id` or user has never initiated conversation with bot. | User must send `/start` first; bot cannot initiate contact. |
| `message can't be deleted` | Message older than 48h (for non-admins) or already deleted. | Catch and proceed. |
| `group chat was upgraded to a supergroup chat` | Basic group was upgraded to supergroup; `chat_id` changed. | Inspect `parameters.migrate_to_chat_id` and update database. |
| `IMAGE_PROCESS_FAILED` | Corrupted image file or unsupported resolution/aspect ratio. | Re-encode image before sending. |

---

### `403 Forbidden` Errors

| Error Description | Root Cause | Fix / Handling |
| :--- | :--- | :--- |
| `bot was blocked by the user` | User manually blocked or stopped the bot. | Mark user `status = 'blocked'` in database; cease broadcasts. |
| `bot was kicked from the group chat` | Bot was removed from the group. | Mark group inactive in database. |
| `user is deactivated` | Telegram account was permanently deleted. | Delete or deactivate user record. |
| `not enough rights to send text messages` | Group admin restricted bot's sending permissions. | Request admin promotion or notify owner. |

---

## 4. Supergroup ID Migration (`migrate_to_chat_id`)

When a basic group converts to a supergroup (e.g. enabling topics or adding >200 members), its negative `chat_id` (e.g. `-55443322`) changes to a `-100` supergroup ID (e.g. `-100155443322`).

### Auto-Migration Pattern
```python
try:
    await bot.send_message(chat_id=old_chat_id, text="Hello group")
except TelegramBadRequest as e:
    if e.parameters and e.parameters.migrate_to_chat_id:
        new_chat_id = e.parameters.migrate_to_chat_id
        await update_database_chat_id(old_id=old_chat_id, new_id=new_chat_id)
        await bot.send_message(chat_id=new_chat_id, text="Hello group")
```
