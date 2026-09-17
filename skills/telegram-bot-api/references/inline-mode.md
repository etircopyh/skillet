# Inline Mode Architecture & Query Handling

This reference details Telegram's Inline Mode: the incoming `InlineQuery` update, the `answerInlineQuery` response contract, the complete `InlineQueryResult` type taxonomy, `InputMessageContent` payloads, pagination via `next_offset`, and feedback collection (`ChosenInlineResult`).

---

## 1. Inline Mode Workflow

When a user types `@botusername <query>` in any chat (private, group, supergroup, channel):

```
[User types '@bot query' in chat input]
                  │
                  ▼
[Telegram sends `inline_query` update to bot]
                  │
                  ▼
[Bot responds via `answerInlineQuery` with list of results]
                  │
                  ▼
[Client displays popup results gallery above input field]
                  │
                  ▼
[User taps a result -> Telegram sends chosen message to chat]
                  │
                  ▼ (Optional: if /setinlinefeedback is enabled)
[Telegram sends `chosen_inline_result` update to bot]
```

*Prerequisite*: Inline mode must be enabled via [@BotFather](https://t.me/BotFather) using `/setinline`.

---

## 2. Incoming `InlineQuery` Update Schema

The `Update` object arrives with the `inline_query` field populated:

```json
{
  "update_id": 9901001,
  "inline_query": {
    "id": "283749283749283",
    "from": {
      "id": 123456789,
      "is_bot": false,
      "first_name": "Alice",
      "username": "alice_dev",
      "language_code": "en"
    },
    "query": "documentation",
    "offset": "",
    "chat_type": "supergroup",
    "location": {
      "latitude": 37.7749,
      "longitude": -122.4194
    }
  }
}
```

- **`id`** (`String`): Unique query identifier. Must be passed back to `answerInlineQuery`.
- **`query`** (`String`): Current text typed by user after `@botusername ` (0–256 characters).
- **`offset`** (`String`): Offset string for paginated results (empty string `""` on first page).
- **`chat_type`** (`String`, optional): Context where the query was typed (`"sender"`, `"private"`, `"group"`, `"supergroup"`, or `"channel"`).
- **`location`** (`Location`, optional): Sender's geographic location (only if location access is requested via BotFather).

---

## 3. Answering Inline Queries (`answerInlineQuery`)

```http
POST https://api.telegram.org/bot<token>/answerInlineQuery
Content-Type: application/json

{
  "inline_query_id": "283749283749283",
  "results": [ ... ],
  "cache_time": 300,
  "is_personal": true,
  "next_offset": "20",
  "button": {
    "text": "🔎 Advanced Search in WebApp",
    "web_app": {
      "url": "https://search.example.com"
    }
  }
}
```

### Parameter Reference

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`inline_query_id`** | `String` | **Yes** | ID from the incoming `InlineQuery`. |
| **`results`** | `InlineQueryResult[]` | **Yes** | Array of results to display (max **50 items** per response). |
| **`cache_time`** | `Integer` | No | Max time in seconds results can be cached client/server-side (default 300). |
| **`is_personal`** | `Boolean` | No | `true` if results depend on user ID (e.g. personal notes, account balance). |
| **`next_offset`** | `String` | No | Offset passed in next query when user scrolls to bottom. |
| **`button`** | `InlineQueryResultsButton` | No | Special button pinned above results (can open WebApp or switch to PM with `start_parameter`). |

---

## 4. `InlineQueryResult` Types (Complete Taxonomy)

Each result item MUST have a unique `id` (1–64 characters) and a `type` string.

### 4.1. Standard Results (Hosted by URL / External Media)

| Type String | Object Class | Key Required Fields |
| :--- | :--- | :--- |
| `"article"` | `InlineQueryResultArticle` | `id`, `title`, `input_message_content` (Note: `article` has no media of its own; it requires `input_message_content`). |
| `"photo"` | `InlineQueryResultPhoto` | `id`, `photo_url`, `thumbnail_url`. |
| `"gif"` | `InlineQueryResultGif` | `id`, `gif_url`, `thumbnail_url`. |
| `"mpeg4_gif"` | `InlineQueryResultMpeg4Gif` | `id`, `mpeg4_url`, `thumbnail_url` (silent MP4 video). |
| `"video"` | `InlineQueryResultVideo` | `id`, `video_url`, `mime_type` (`video/mp4` or `text/html`), `thumbnail_url`, `title`. |
| `"audio"` | `InlineQueryResultAudio` | `id`, `audio_url`, `title`. |
| `"voice"` | `InlineQueryResultVoice` | `id`, `voice_url`, `title`. |
| `"document"` | `InlineQueryResultDocument`| `id`, `title`, `document_url`, `mime_type` (`application/pdf` or `application/zip`), `thumbnail_url`. |
| `"location"` | `InlineQueryResultLocation`| `id`, `latitude`, `longitude`, `title`. |
| `"venue"` | `InlineQueryResultVenue` | `id`, `latitude`, `longitude`, `title`, `address`. |
| `"contact"` | `InlineQueryResultContact` | `id`, `phone_number`, `first_name`. |
| `"game"` | `InlineQueryResultGame` | `id`, `game_short_name`. |

---

### 4.2. Cached Results (Using Existing Telegram `file_id`)
Cached variants do NOT require external HTTP downloads; Telegram sends the existing file directly from its CDN.

| Type String | Object Class | Key Required Field |
| :--- | :--- | :--- |
| `"photo"` | `InlineQueryResultCachedPhoto` | `photo_file_id`, `title` |
| `"gif"` | `InlineQueryResultCachedGif` | `gif_file_id`, `title` |
| `"mpeg4_gif"` | `InlineQueryResultCachedMpeg4Gif` | `mpeg4_file_id`, `title` |
| `"sticker"` | `InlineQueryResultCachedSticker` | `sticker_file_id` |
| `"document"` | `InlineQueryResultCachedDocument` | `document_file_id`, `title` |
| `"video"` | `InlineQueryResultCachedVideo` | `video_file_id`, `title` |
| `"voice"` | `InlineQueryResultCachedVoice` | `voice_file_id`, `title` |
| `"audio"` | `InlineQueryResultCachedAudio` | `audio_file_id` |

---

## 5. `InputMessageContent` Payloads

When a user selects an inline result, Telegram sends the message content defined in `input_message_content`.

### 1. `InputTextMessageContent` (Most Common)
```json
{
  "type": "article",
  "id": "res_101",
  "title": "API Specification",
  "description": "Click to send full API specification",
  "thumbnail_url": "https://example.com/icon.png",
  "input_message_content": {
    "message_text": "📖 <b>Telegram Bot API Spec</b>\nVersion: 10.3",
    "parse_mode": "HTML",
    "link_preview_options": { "is_disabled": true }
  },
  "reply_markup": {
    "inline_keyboard": [
      [{ "text": "Open Docs", "url": "https://core.telegram.org/bots/api" }]
    ]
  }
}
```

### 2. `InputLocationMessageContent`
```json
{
  "latitude": 37.7749,
  "longitude": -122.4194,
  "horizontal_accuracy": 5.0,
  "live_period": 1800
}
```

### 3. `InputVenueMessageContent`
```json
{
  "latitude": 37.7749,
  "longitude": -122.4194,
  "title": "HQ Office",
  "address": "100 Market St, San Francisco"
}
```

### 4. `InputContactMessageContent`
```json
{
  "phone_number": "+1234567890",
  "first_name": "Support",
  "last_name": "Desk"
}
```

### 5. `InputInvoiceMessageContent`
Sends an actionable payment invoice directly into the chat via inline result.

---

## 6. Paginated Inline Results Pattern (`next_offset`)

When results exceed the max batch size (up to 50 results):

```typescript
// Incoming query: { query: "apple", offset: "" }
const PAGE_SIZE = 20;
const currentOffset = parseInt(inlineQuery.offset || "0", 10);
const results = getItems(inlineQuery.query, currentOffset, PAGE_SIZE);
const hasMore = currentOffset + PAGE_SIZE < totalMatches;

await bot.answerInlineQuery({
  inline_query_id: inlineQuery.id,
  results: results.map(formatResult),
  next_offset: hasMore ? String(currentOffset + PAGE_SIZE) : "",
  cache_time: 60
});
```

---

## 7. Tracking Selections (`ChosenInlineResult`)

To collect metrics or edit messages sent via inline query:
1. Run `/setinlinefeedback` in [@BotFather](https://t.me/BotFather) and select `100%` (or a percentage).
2. The bot will receive a `chosen_inline_result` update:

```json
{
  "update_id": 9901002,
  "chosen_inline_result": {
    "result_id": "res_101",
    "from": { "id": 123456789, "first_name": "Alice" },
    "query": "documentation",
    "inline_message_id": "AgAAAL...",
    "location": { "latitude": 37.7749, "longitude": -122.4194 }
  }
}
```

- **`inline_message_id`**: Identifier of the sent message. Use this with `editMessageText` or `editMessageReplyMarkup` by passing `inline_message_id` (leaving `chat_id` and `message_id` empty).
