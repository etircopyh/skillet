# Messages, Formatting & Media Handling

This reference details message transmission, formatting parse modes (HTML vs MarkdownV2 vs MessageEntity), media uploads, albums (`sendMediaGroup`), message streaming drafts, and ephemeral messages.

---

## 1. Message Sending Methods & Limits

| Method | Key Parameters | Payload Limits |
| :--- | :--- | :--- |
| **`sendMessage`** | `chat_id`, `text`, `parse_mode`, `reply_markup`, `reply_parameters`, `message_thread_id`, `link_preview_options` | `text`: 1–4096 UTF-8 characters. |
| **`sendPhoto`** | `chat_id`, `photo` (InputFile/file_id/URL), `caption`, `show_caption_above_media`, `has_spoiler` | `caption`: 0–1024 characters; file: max 10MB via standard upload. |
| **`sendAudio`** | `chat_id`, `audio`, `caption`, `duration`, `performer`, `title`, `thumbnail` | `caption`: 0–1024 characters; file: max 50MB (`.mp3`/`.m4a`). |
| **`sendDocument`**| `chat_id`, `document`, `caption`, `thumbnail`, `disable_content_type_detection` | `caption`: 0–1024 characters; file: max 50MB (any file format). |
| **`sendVideo`** | `chat_id`, `video`, `duration`, `width`, `height`, `thumbnail`, `supports_streaming`, `has_spoiler` | `caption`: 0–1024 characters; file: max 50MB (`.mp4`). |
| **`sendAnimation`**| `chat_id`, `animation` (GIF/H.264 video without sound), `caption`, `has_spoiler` | `caption`: 0–1024 characters; file: max 50MB. |
| **`sendVoice`** | `chat_id`, `voice` (OGG encoded with OPUS), `caption`, `duration` | `caption`: 0–1024 characters; file: max 50MB. |
| **`sendVideoNote`**| `chat_id`, `video_note` (rounded square video, max 1 min), `duration`, `length` | Max 50MB (`.mp4`, 1:1 aspect ratio). |
| **`sendMediaGroup`**| `chat_id`, `media` (JSON array of `InputMediaPhoto`, `InputMediaVideo`, etc.) | 2–10 media items in one album. |
| **`sendPaidMedia`** | `chat_id`, `star_count`, `media` (`InputPaidMediaPhoto`/`InputPaidMediaVideo`), `caption` | Max 10 paid media items; paid in Telegram Stars. |
| **`sendLocation`** | `chat_id`, `latitude`, `longitude`, `horizontal_accuracy`, `live_period`, `proximity_alert_radius` | Live period: 60–86400 seconds. |
| **`sendContact`** | `chat_id`, `phone_number`, `first_name`, `last_name`, `vcard` | vCard string up to 2048 bytes. |
| **`sendLivePhoto`**| `chat_id`, `live_photo` (InputMediaLivePhoto/file_id), `caption`, `has_spoiler` | Photo with embedded motion video (Bot API 10.0+). |
| **`sendPoll`** | `chat_id`, `question`, `options` (`InputPollOption[]`), `media` (`InputPollMedia`), `allows_revoting`, `correct_option_ids` | Options: 1–10 options; media in poll & options supported. |
| **`sendDice`** | `chat_id`, `emoji` (🎲, 🎯, 🏀, ⚽, 🎳, 🎰) | Returns dice value 1–6 (or 1–64 for slot machine). |
| **`sendChatAction`**| `chat_id`, `action` (`typing`, `upload_photo`, `record_video`, `upload_document`, `find_location`) | Action lasts ~5 seconds or until message is sent. |

---

## 2. Text Formatting Parse Modes

When sending text or media captions, format with `HTML` or `MarkdownV2`.

### Mode 1: HTML (Recommended for Dynamic Content)
Use HTML because escaping variables only requires replacing `&`, `<`, `>` and `"`.

```html
<b>bold</b>, <strong>bold</strong>
<i>italic</i>, <em>italic</em>
<u>underline</u>, <ins>underline</ins>
<s>strikethrough</s>, <strike>strikethrough</strike>, <del>strikethrough</del>
<tg-spoiler>spoiler</tg-spoiler>
<b>inline fixed-width code</b>: <code>const x = 10;</code>
<pre><code class="language-python">
def hello():
    print("Hello, World!")
</code></pre>
<a href="https://example.com">inline URL</a>
<a href="tg://user?id=123456789">inline mention of user</a>
<tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>
<blockquote>Expandable blockquote</blockquote>
<blockquote expandable>Long text that collapses by default...</blockquote>
```

#### Safe HTML Sanitizer Helper
```python
def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
```

---

### Mode 2: MarkdownV2 (Strict Character Escaping)
In `MarkdownV2`, **all 18 special characters must be escaped with `\`** if they are not part of formatting tags:
`_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`

```markdown
*bold text*
_italic text_
__underline__
~strikethrough~
||spoiler||
*bold _nested italic_ bold*
[inline URL](http://www.example.com/)
[inline mention of user](tg://user?id=123456789)
`inline fixed-width code`
```python
# Inside pre/code blocks, ONLY ` and \ must be escaped
def add(a, b):
    return a + b
```
>Blockquote
**>Expandable blockquote||
```

#### Safe MarkdownV2 Sanitizer Helper
```typescript
function escapeMarkdownV2(text: string): string {
  return text.replace(/([_*[\]()~`>#+\-=|{}.!\\])/g, '\\$1');
}
```

---

### Mode 3: `MessageEntity` Programmatic Formatting (Zero-Escaping Risk)
Instead of `parse_mode`, provide explicit entity offsets and lengths. Offsets and lengths are calculated in **UTF-16 code units** (not bytes, and not unicode code points).

```json
{
  "chat_id": 123456789,
  "text": "Hello John! Check this link.",
  "entities": [
    { "type": "bold", "offset": 0, "length": 5 },
    { "type": "text_mention", "offset": 6, "length": 4, "user": { "id": 987654321 } },
    { "type": "text_link", "offset": 19, "length": 9, "url": "https://example.com" }
  ]
}
```

---

## 3. Media Upload Methods & Invariants

You can supply files in three ways:

1. **`file_id` (Fastest, zero bandwidth overhead)**:
   Pass the `file_id` string from an existing `Message.photo`, `Message.document`, etc.
   - Example: `"photo": "AgACAgIAAxkBAAI..."`
   - Valid across all chats for the same bot token.
2. **HTTP/HTTPS URL**:
   Pass a publicly accessible URL string.
   - Telegram servers download the file (photos max 5MB, other files max 20MB).
   - Example: `"photo": "https://images.example.com/item.png"`
3. **`InputFile` (Direct Multipart Upload)**:
   Send `multipart/form-data` with the file attached:
   - Max file size: **50 MB** (upload) / **20 MB** (download via bot API).
   - Use `attach://<field_name>` syntax when referencing nested files in `sendMediaGroup` or thumbnails.

### Sending Media Album (`sendMediaGroup`)
```json
// POST /sendMediaGroup
{
  "chat_id": 123456789,
  "media": [
    {
      "type": "photo",
      "media": "attach://photo_1",
      "caption": "Album cover",
      "parse_mode": "HTML"
    },
    {
      "type": "video",
      "media": "attach://video_1",
      "has_spoiler": true
    }
  ]
}
```

---

## 4. Live Streaming & Drafting (`sendMessageDraft`)

For real-time AI responses or progressive updates (Bot API 9.3+ / 10.x):

- **Draft Streaming**: Call `sendMessageDraft` or `sendRichMessageDraft` to stream partial text or structured AST blocks pinned to the bottom of the chat without notifications.
- **Stop Action**: Handle `stopped_message_generation` updates if the user clicks the native Stop button (`can_stop: true`).
- **Traditional Edits**: If editing standard messages in-place with `editMessageText`, adhere to the **1 edit/second per message** limit and catch `400 Bad Request: message is not modified`.
- *For complete AST block structures (`thinking`, `table`, `expandable_block_quotation`), see [`rich-messages-and-ephemeral.md`](./rich-messages-and-ephemeral.md).*

---

## 5. Ephemeral Messages (Bot API 10.2+)

Ephemeral messages allow bots in group chats to send messages and command responses visible **only to a single target user** and the bot, eliminating public chat noise.

Pass `ephemeral_message_parameters: { "receiver_user_id": 12345, "replace_callback_query_message": true }` to `sendMessage`, `sendPhoto`, etc.

- *For the complete ephemeral lifecycle (`editEphemeralMessageText`, `deleteEphemeralMessage`, `is_ephemeral` commands), see [`rich-messages-and-ephemeral.md`](./rich-messages-and-ephemeral.md).*
- *For incoming media payloads and `getFile`, see [`content-types-and-payload-shapes.md`](./content-types-and-payload-shapes.md).*
- *For message origins, quotes, and structured replies (`ReplyParameters`), see [`message-provenance-replies-and-origins.md`](./message-provenance-replies-and-origins.md).*


---

## 6. Interactive Checklists (Bot API 9.1+)

Checklists allow bots and users to create interactive to-do lists within messages where members can complete or add items.

- **Creating Checklist**: Attach `InputChecklist` to message containing `InputChecklistTask[]`.
- **`ChecklistTask` Structure**: Contains `id`, `text`, `entities`, `completed_by_user`, `completed_date`.
- **Service Updates**:
  - `checklist_tasks_added`: Tasks appended to checklist.
  - `checklist_tasks_done`: Tasks completed by users.

---

## 7. Enhanced Polls & Quizzes (Bot API 9.6 / 10.0+)

Modern polls support media attachments and flexible quiz evaluation:

- **Media in Polls (`InputPollMedia` / `PollMedia`)**: Add photos, stickers, or videos directly into poll headers, question descriptions, and individual answer options.
- **Multiple Correct Quiz Answers**: Pass `correct_option_ids: Integer[]` and `allows_multiple_answers: true` in `sendPoll`.
- **Persistent Option IDs**: Use `persistent_id` on `PollOption` for reliable tracking when options are shuffled or added.
- **Poll Controls**:
  - `allows_revoting: true` (allows users to change their votes).
  - `shuffle_options: true` (randomizes answer display order).
  - `hide_results_until_closes: true` (keeps voting private until poll terminates).
  - `open_period`: Maximum automated closure extended up to 30 days (2,628,000 seconds).
---

## 8. Message Copying, Editing & InputMedia Schemas

### Copying, Forwarding & Message Modification Methods
```typescript
forwardMessage(params: { chat_id: number | string; from_chat_id: number | string; message_id: number; message_thread_id?: number; disable_notification?: boolean; protect_content?: boolean }): Promise<Message>;
forwardMessages(params: { chat_id: number | string; from_chat_id: number | string; message_ids: number[]; message_thread_id?: number; disable_notification?: boolean; protect_content?: boolean }): Promise<MessageId[]>;
copyMessage(params: { chat_id: number | string; from_chat_id: number | string; message_id: number; message_thread_id?: number; caption?: string; parse_mode?: string; reply_markup?: InlineKeyboardMarkup }): Promise<MessageId>;
copyMessages(params: { chat_id: number | string; from_chat_id: number | string; message_ids: number[]; message_thread_id?: number }): Promise<MessageId[]>;

sendVenue(params: { chat_id: number | string; latitude: number; longitude: number; title: string; address: string; foursquare_id?: string; google_place_id?: string }): Promise<Message>;

editMessageCaption(params: { chat_id?: number | string; message_id?: number; inline_message_id?: string; caption?: string; parse_mode?: string; reply_markup?: InlineKeyboardMarkup }): Promise<Message | boolean>;
editMessageMedia(params: { chat_id?: number | string; message_id?: number; inline_message_id?: string; media: InputMedia; reply_markup?: InlineKeyboardMarkup }): Promise<Message | boolean>;

stopPoll(params: { chat_id: number | string; message_id: number; reply_markup?: InlineKeyboardMarkup }): Promise<Poll>;
deleteMessage(params: { chat_id: number | string; message_id: number }): Promise<boolean>;
deleteMessages(params: { chat_id: number | string; message_ids: number[] }): Promise<boolean>;

deleteMessageReaction(params: { chat_id: number | string; message_id: number }): Promise<boolean>;
deleteAllMessageReactions(params: { chat_id: number | string; message_id: number }): Promise<boolean>;
```

### Link Previews, Input Media & Reaction Schemas
```typescript
interface LinkPreviewOptions {
  is_disabled?: boolean;
  url?: string;
  prefer_small_media?: boolean;
  prefer_large_media?: boolean;
  show_above_text?: boolean;
}

type InputMedia =
  | InputMediaAnimation
  | InputMediaAudio
  | InputMediaDocument
  | InputMediaPhoto
  | InputMediaVideo
  | InputMediaLink
  | InputMediaLocation
  | InputMediaSticker
  | InputMediaVenue
  | InputMediaVoiceNote;

interface InputMediaAnimation { type: 'animation'; media: string; thumbnail?: InputFile | string; caption?: string; parse_mode?: string; width?: number; height?: number; duration?: number; has_spoiler?: boolean; }
interface InputMediaAudio { type: 'audio'; media: string; thumbnail?: InputFile | string; caption?: string; parse_mode?: string; duration?: number; performer?: string; title?: string; }
interface InputMediaDocument { type: 'document'; media: string; thumbnail?: InputFile | string; caption?: string; parse_mode?: string; disable_content_type_detection?: boolean; }
interface InputMediaLink { type: 'link'; url: string; }
interface InputMediaLocation { type: 'location'; latitude: number; longitude: number; }
interface InputMediaSticker { type: 'sticker'; media: string; }
interface InputMediaVenue { type: 'venue'; latitude: number; longitude: number; title: string; address: string; }
interface InputMediaVoiceNote { type: 'voice_note'; media: string; duration?: number; }
interface InputPaidMediaLivePhoto { type: 'live_photo'; photo: string; video: string; }

type ReactionType = ReactionTypeEmoji | ReactionTypeCustomEmoji | ReactionTypePaid;
interface ReactionTypeEmoji { type: 'emoji'; emoji: string; }
interface ReactionTypeCustomEmoji { type: 'custom_emoji'; custom_emoji_id: string; }
interface ReactionTypePaid { type: 'paid'; }

interface PaidMediaInfo { star_count: number; paid_media: PaidMedia[]; }
interface PaidMediaLivePhoto { type: 'live_photo'; photo: PhotoSize[]; video: Video; }
interface PaidMediaPreview { type: 'preview'; width?: number; height?: number; duration?: number; }
interface InputPollOptionMedia { media: string; parse_mode?: string; }
interface VideoQuality { resolution: number; codec: string; }
```
