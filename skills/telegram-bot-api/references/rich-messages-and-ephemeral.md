# Rich Messages, Ephemeral Messages & AI Streaming (Bot API 10.x)

This reference covers the modern Telegram Bot API features (Bot API 10.0–10.3 and 9.x), including structured **Rich Messages**, **Ephemeral Messages** in group chats, **Live AI Draft Streaming**, and interactive UI enhancements.

---

## 1. Rich Messages (`sendRichMessage` & AST Block Layout)

Rich Messages provide an Abstract Syntax Tree (AST) of structured blocks rather than a flat string. They are purpose-built for AI assistants, reports, tables, collages, and rich documents.

### Method: `sendRichMessage`
```http
POST https://api.telegram.org/bot<token>/sendRichMessage
Content-Type: application/json

{
  "chat_id": 123456789,
  "rich_message": {
    "blocks": [
      {
        "type": "section_heading",
        "text": {
          "text": "📊 Quarterly Performance Report"
        }
      },
      {
        "type": "thinking",
        "text": {
          "text": "Retrieved 1,420 transaction records from database and computed net ARR."
        }
      },
      {
        "type": "paragraph",
        "text": {
          "text": "Revenue grew by 24% compared to Q1.",
          "entities": [
            { "type": "bold", "offset": 0, "length": 12 }
          ]
        }
      },
      {
        "type": "table",
        "is_compact": true,
        "rows": [
          {
            "cells": [
              { "text": { "text": "Metric" } },
              { "text": { "text": "Value" } }
            ]
          },
          {
            "cells": [
              { "text": { "text": "ARR" } },
              { "text": { "text": "$1.2M" } }
            ]
          }
        ]
      },
      {
        "type": "expandable_block_quotation",
        "text": {
          "text": "Disclaimer: Past performance is not indicative of future results."
        }
      }
    ]
  }
}
```

---

### Rich Block Types (`RichBlock` & `InputRichBlock`)

| Block Type | Class Name | Purpose / Visual Presentation |
| :--- | :--- | :--- |
| **`paragraph`** | `InputRichBlockParagraph` | Standard formatted text with rich styling and inline entities. |
| **`section_heading`** | `InputRichBlockSectionHeading` | Prominent header / section title. |
| **`thinking`** | `InputRichBlockThinking` | Native collapsible AI reasoning/thought process block. |
| **`table`** | `InputRichBlockTable` | Formatted multi-column data table (supports `is_compact: true`). |
| **`expandable_block_quotation`** | `InputRichBlockExpandableBlockQuotation` | Collapsible blockquote for caveats, notes, or long quotes. |
| **`block_quotation`** | `InputRichBlockBlockQuotation` | Standard quote block. |
| **`pull_quotation`** | `InputRichBlockPullQuotation` | Highlighted callout / pull-quote banner. |
| **`preformatted`** | `InputRichBlockPreformatted` | Code snippet with optional syntax highlighting. |
| **`list`** | `InputRichBlockList` | Ordered or unordered lists containing `InputRichBlockListItem`. |
| **`details`** | `InputRichBlockDetails` | Accordion/disclosure widget with collapsible body. |
| **`divider`** | `InputRichBlockDivider` | Visual horizontal line separator. |
| **`mathematical_expression`** | `InputRichBlockMathematicalExpression` | LaTeX-style rendered mathematical formula. |
| **`collage` / `slideshow`** | `InputRichBlockCollage` | Inline media grid or swipeable gallery embedded in document. |
| **`buttons`** | `InputRichBlockButtons` | Inline actionable buttons embedded directly between text blocks. |
| **`document`** | `InputRichBlockDocument` | File attachment card embedded within the document flow. |

---

## 2. Ephemeral Messages (`ephemeral_message_parameters`)

Ephemeral messages allow bots in public supergroups and channels to send messages and command outputs that are **visible exclusively to the target user and the bot**.

### Key Use Cases
- Private command outputs (e.g. `/balance`, `/settings`, `/help`) inside busy public groups.
- Authentication prompts and captchas without leaking sensitive links to group members.
- Validation and error messages that do not clutter the group history.

---

### Sending an Ephemeral Message
Pass `ephemeral_message_parameters` in `sendMessage`, `sendPhoto`, `sendDocument`, `sendRichMessage`, etc.:

```http
POST https://api.telegram.org/bot<token>/sendMessage
Content-Type: application/json

{
  "chat_id": -1001234567890,
  "text": "🔒 Your current balance is 540 Stars. This message is visible only to you.",
  "ephemeral_message_parameters": {
    "receiver_user_id": 987654321,
    "replace_callback_query_message": true
  }
}
```

- **`receiver_user_id`** (`Integer`, required): Target `user_id` who can view the message.
- **`replace_callback_query_message`** (`Boolean`, optional): Replaces the original message in the user's client view with this ephemeral response.

---

### Managing Ephemeral Messages
- **Edit Text**: `editEphemeralMessageText(chat_id, ephemeral_message_id, text, ...)`
- **Edit Media**: `editEphemeralMessageMedia(chat_id, ephemeral_message_id, media, ...)`
- **Edit Caption**: `editEphemeralMessageCaption(chat_id, ephemeral_message_id, caption, ...)`
- **Edit Reply Markup**: `editEphemeralMessageReplyMarkup(chat_id, ephemeral_message_id, reply_markup)`
- **Delete**: `deleteEphemeralMessage(chat_id, ephemeral_message_id)`
- **Ephemeral Commands**: Register bot commands with `"is_ephemeral": true` in `BotCommand` so group triggers respond ephemerally by default.

---

## 3. Live AI Draft Streaming (`sendMessageDraft` & `sendRichMessageDraft`)

For real-time generative AI streaming (ChatGPT / Claude / Gemini style), Telegram provides native draft streaming without firing push notifications or generating spammy message edit records.

```
[1. User sends prompt]
        │
        ▼
[2. Bot streams chunks via `sendRichMessageDraft` / `sendMessageDraft`]
   (Draft is pinned to bottom of user's chat window in real-time)
        │
        ├── User clicks native 'Stop' button ──► [Bot receives `stopped_message_generation` update]
        │
        ▼
[3. Bot finishes generation and calls `sendRichMessage` / `sendMessage`]
   (Pinned draft converts into final persistent message in chat history)
```

### Method: `sendRichMessageDraft` / `sendMessageDraft`
```http
POST https://api.telegram.org/bot<token>/sendRichMessageDraft
Content-Type: application/json

{
  "chat_id": 123456789,
  "rich_message": {
    "blocks": [
      {
        "type": "thinking",
        "text": { "text": "Analyzing query..." }
      },
      {
        "type": "paragraph",
        "text": { "text": "Generating draft response chunk 1..." }
      }
    ]
  },
  "can_stop": true,
  "keep_on_stop": true
}
```

- **`can_stop`** (`Boolean`): Renders a native "Stop Generating" button in the user's client interface.
- **`keep_on_stop`** (`Boolean`): If `true`, retains whatever text was already streamed if the user stops generation.
- **`stopped_message_generation`** Update: When the user hits stop, Telegram dispatches `MessageGenerationStopped` (`user: User`, `chat: Chat`).

---

## 4. Modern UI & Keyboard Controls (Bot API 10.3 / 9.x)

### 1. Disabled Buttons (`disabled`)
You can disable an inline button without removing it from the grid layout:

```json
{
  "inline_keyboard": [
    [
      { "text": "⬅️ Previous", "callback_data": "page:1", "disabled": true },
      { "text": "Page 2/10", "callback_data": "noop", "disabled": true },
      { "text": "Next ➡️", "callback_data": "page:3", "disabled": false }
    ]
  ]
}
```

### 2. Button Colors & Custom Emojis (`style` & `icon_custom_emoji_id`)
Customize inline and reply buttons:
- **`style`**: `"primary"` (accent/highlighted), `"danger"` (red/destructive), `"success"` (green/confirmation), `"default"`.
- **`icon_custom_emoji_id`**: Displays custom animated/static Telegram emoji on the button.

### 3. Inline Keyboard `force_reply`
`InlineKeyboardMarkup` and `ReplyKeyboardMarkup` now support `force_reply: true`, triggering immediate user prompt input directly upon clicking an inline button.

---

## 5. Communities Integration (Bot API 10.2+)

Communities link multiple supergroups, channels, and bots together under a single unified ecosystem.

- **`ChatFullInfo.community`**: Returns `Community` object details.
- **Service Updates**:
  - `community_chat_added`: Supergroup or channel added to community.
  - `community_chat_removed`: Chat removed from community.
  - `community_chat_joined`: User joined chat via community directory.
