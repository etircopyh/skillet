# Message Provenance, Replies & Content Origins

This reference details how to track where incoming Telegram content originated (forwards, cross-chat replies, quotes, channels, inline bots, stories) and how to configure structured outbound replies (`ReplyParameters`).

---

## 1. Content Origin & Forwarding (`MessageOrigin`)

In modern Bot API (v7.0+), Telegram unified all forward tracking into the `forward_origin` field, represented by the `MessageOrigin` tagged union.

> [!WARNING]
> **Legacy Fields Deprecated**: Do not rely on legacy `forward_from`, `forward_from_chat`, `forward_from_message_id`, or `forward_sender_name`. Modern bots inspect `Message.forward_origin`.

### The 4 `MessageOrigin` Variants

```typescript
type MessageOrigin =
  | MessageOriginUser
  | MessageOriginHiddenUser
  | MessageOriginChat
  | MessageOriginChannel;
```

#### 1. `MessageOriginUser`
Forwarded from a public user profile who allows links to their account:
```json
{
  "forward_origin": {
    "type": "user",
    "date": 1711880000,
    "sender_user": {
      "id": 987654321,
      "is_bot": false,
      "first_name": "Alice",
      "username": "alice_dev"
    }
  }
}
```

#### 2. `MessageOriginHiddenUser`
Forwarded from a user who enabled **"Forwarded Messages: Nobody"** privacy setting. No user ID or link is available:
```json
{
  "forward_origin": {
    "type": "hidden_user",
    "date": 1711880000,
    "sender_user_name": "Alice"
  }
}
```

#### 3. `MessageOriginChat`
Forwarded on behalf of a group, supergroup, or anonymous admin:
```json
{
  "forward_origin": {
    "type": "chat",
    "date": 1711880000,
    "sender_chat": {
      "id": -1001234567890,
      "title": "Developers Community",
      "type": "supergroup"
    },
    "author_signature": "Lead Architect"
  }
}
```

#### 4. `MessageOriginChannel`
Forwarded directly from a broadcast channel:
```json
{
  "forward_origin": {
    "type": "channel",
    "date": 1711880000,
    "chat": {
      "id": -1009876543210,
      "title": "Tech News Digest",
      "type": "channel",
      "username": "technews"
    },
    "message_id": 451,
    "author_signature": "News Desk"
  }
}
```

---

### Python Helper: Extracting Forward Origin Safely
```python
def get_forward_source_label(message: dict) -> str:
    origin = message.get("forward_origin")
    if not origin:
        return "Not forwarded (original post)"

    origin_type = origin.get("type")
    if origin_type == "user":
        user = origin["sender_user"]
        return f"User: {user.get('first_name')} (@{user.get('username', 'no_username')})"
    elif origin_type == "hidden_user":
        return f"Private User: {origin.get('sender_user_name')}"
    elif origin_type == "chat":
        return f"Chat: {origin['sender_chat'].get('title')}"
    elif origin_type == "channel":
        return f"Channel: {origin['chat'].get('title')} (Msg #{origin.get('message_id')})"
    return "Unknown origin"
```

---

## 2. Sender Identity Paths (Who Sent the Message?)

In Telegram groups and channels, the sender is not always a direct user.

| Scenario | `from` Field | `sender_chat` Field | Description |
| :--- | :--- | :--- | :--- |
| **Standard User Message** | `User` object | `null` | Sent by an identifiable user. |
| **Channel Post** | `null` (or bot user) | `Chat` (channel) | Message published in a channel. |
| **Anonymous Admin in Group** | `User` (Telegram service: ID `1087968824` / GroupAnonymousBot) | `Chat` (group chat) | Group admin posting under group name. |
| **Linked Channel Post in Discussion Group** | Service bot (`777000` / Telegram) | `Chat` (source channel) | Auto-forwarded channel post to linked group. |
| **Posting as Owned Channel** | `User` (optional or system) | `Chat` (sender channel) | User chose to speak on behalf of their public channel. |

> [!IMPORTANT]
> **Channel Post Null Check**: In channel posts (`channel_post` update), **`message.from` is usually `null`**. Always check `message.chat` or `message.sender_chat` when handling channel events.

---

## 3. Replies, Quotes & External Cross-Chat Context

Modern Telegram allows users to reply not just to messages in the current chat, but across channels, topics, and specific text highlights.

### 3.1. Standard In-Chat Reply (`reply_to_message`)
When a user replies to an earlier message in the same chat:
```json
{
  "message_id": 412,
  "reply_to_message": {
    "message_id": 405,
    "from": { "id": 987654321, "first_name": "Bob" },
    "text": "Does this support Webhooks?"
  },
  "text": "Yes, full SSL support is included."
}
```

---

### 3.2. External Reply (`external_reply: ExternalReplyInfo`)
Occurs when a user replies to a message from a **different chat, channel, or topic**:

```json
{
  "message_id": 502,
  "text": "I agree with this roadmap item.",
  "external_reply": {
    "origin": {
      "type": "channel",
      "date": 1711870000,
      "chat": {
        "id": -1009876543210,
        "title": "Announcements Channel"
      },
      "message_id": 88
    },
    "chat": {
      "id": -1009876543210,
      "title": "Announcements Channel"
    },
    "message_id": 88,
    "link_preview_options": {
      "is_disabled": false,
      "url": "https://example.com/spec"
    }
  }
}
```

- If the original external message contained media, `external_reply` includes lightweight previews (`photo`, `video`, `document`, `has_media_spoiler`).

---

### 3.3. Text Highlight Quotes (`quote: TextQuote`)
When a user highlights a specific snippet of text in a message and hits "Quote":

```json
{
  "message_id": 503,
  "reply_to_message": {
    "message_id": 405,
    "text": "The migration starts at 02:00 UTC and will last for 30 minutes."
  },
  "quote": {
    "text": "starts at 02:00 UTC",
    "entities": [],
    "position": 14,
    "is_manual": true
  },
  "text": "Can we postpone to 04:00 UTC?"
}
```

- **`text`**: The quoted excerpt.
- **`position`**: 0-indexed character offset where the quote starts in the original text.
- **`is_manual`**: `true` if manually highlighted by user; `false` if auto-selected by client.

---

### 3.4. Replying to Stories (`reply_to_story`)
When a user replies to a story posted by a channel or user:
```json
{
  "message_id": 601,
  "text": "Awesome photo!",
  "reply_to_story": {
    "chat": { "id": -1009876543210, "type": "channel" },
    "id": 14
  }
}
```

---

## 4. Via Bot & Inline Origins (`via_bot`)

When a user sends a message using another bot's inline query (e.g. `@gif cat` or `@sticker happy`):

```json
{
  "message_id": 701,
  "via_bot": {
    "id": 1234567,
    "is_bot": true,
    "first_name": "GIF Search Bot",
    "username": "gif"
  },
  "animation": { ... }
}
```
*Allows bots to track attribution or prevent recursive processing of other inline bot messages.*

---

## 5. Linked Discussion Groups (`is_automatic_forward`)

When a public channel is linked to a supergroup discussion group:
1. Every post in the channel is automatically forwarded to the group by Telegram.
2. The forwarded message in the group has:
   - `is_automatic_forward: true`
   - `from`: Telegram service account (`777000`)
   - `sender_chat`: The channel object
3. Subsequent member comments in the thread have `reply_to_message` pointing to this automatic forward.

---

## 6. Outbound Structured Replies (`ReplyParameters`)

To reply accurately, quote specific text, or reply across chats, pass `reply_parameters` to `sendMessage`, `sendPhoto`, etc.:

```http
POST https://api.telegram.org/bot<token>/sendMessage
Content-Type: application/json

{
  "chat_id": -1001234567890,
  "text": "We cannot change the deployment window.",
  "reply_parameters": {
    "message_id": 405,
    "chat_id": -1001234567890,
    "allow_sending_without_reply": true,
    "quote": "starts at 02:00 UTC",
    "quote_position": 14
  }
}
```

### `ReplyParameters` Fields

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`message_id`** | `Integer` | **Yes\*** | Target message ID to reply to (\*optional only if `ephemeral_message_id` is set). |
| **`chat_id`** | `Integer` / `String` | No | Chat where target message lives (enables cross-chat quoting). |
| **`allow_sending_without_reply`** | `Boolean` | No | If `true`, sends message even if original message was deleted. |
| **`quote`** | `String` | No | Specific text excerpt to display inside the quote banner (0–1024 characters). |
| **`quote_parse_mode`** | `String` | No | Parse mode for `quote` (`"HTML"` / `"MarkdownV2"`). |
| **`quote_entities`** | `MessageEntity[]` | No | Programmatic entities for the quote text. |
| **`quote_position`** | `Integer` | No | Character offset in original message where quote begins. |
| **`checklist_task_id`** | `Integer` | No | Target task ID if replying to a checklist item. |
| **`poll_option_id`** | `String` | No | Target option ID if replying to a specific poll option. |
| **`ephemeral_message_id`** | `Integer` | No | Target ephemeral message ID if replying to an ephemeral message. |
