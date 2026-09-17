# Keyboards & Interactive UI Components

This reference details the Telegram keyboard architecture: inline keyboards (`InlineKeyboardMarkup`), reply/custom keyboards (`ReplyKeyboardMarkup`), keyboard removal, force reply, and callback query lifecycle management.

---

## 1. Inline Keyboards (`InlineKeyboardMarkup`)

Inline keyboards appear directly attached to a specific message and persist in chat history.

### Layout & Schema
An `InlineKeyboardMarkup` contains an `inline_keyboard` field which is an **array of button rows** (a 2D array of `InlineKeyboardButton` objects).

```json
{
  "inline_keyboard": [
    [
      { "text": "👍 Upvote", "callback_data": "vote:up:42" },
      { "text": "👎 Downvote", "callback_data": "vote:down:42" }
    ],
    [
      { "text": "🌐 Visit Website", "url": "https://example.com" },
      { "text": "🚀 Open App", "web_app": { "url": "https://app.example.com" } }
    ],
    [
      { "text": "📋 Copy Promo Code", "copy_text": { "text": "SUMMER2026" } }
    ]
  ]
}
```

### `InlineKeyboardButton` Variants (Exactly ONE must be set per button)

| Field | Type | Description |
| :--- | :--- | :--- |
| **`callback_data`** | `String` (1–64 bytes) | Data sent in a `CallbackQuery` update when pressed. |
| **`url`** | `String` | HTTP/HTTPS URL or `tg://` deep-link opened by client. |
| **`web_app`** | `WebAppInfo` | Opens a Telegram Mini App (`{ "url": "https://..." }`). |
| **`login_url`** | `LoginUrl` | Seamless Telegram OAuth login URL. |
| **`switch_inline_query`** | `String` | Prompts user to select a chat and inserts `@bot username <string>`. |
| **`switch_inline_query_current_chat`** | `String` | Inserts `@bot username <string>` directly into the current chat's input field. |
| **`switch_inline_query_chosen_chat`** | `SwitchInlineQueryChosenChat` | Select chat of specific type (user/bot/group/channel). |
| **`copy_text`** | `CopyTextButton` | Copies specified text to user's clipboard (`{ "text": "..." }`). |
| **`pay`** | `Boolean` | Must be `true` for payment invoice messages (must be first button in first row). |

---

## 2. Callback Query Lifecycle & `answerCallbackQuery`

When a user clicks an inline button with `callback_data`, Telegram sends a `callback_query` update.

### The Non-Negotiable Contract
You **MUST** call `answerCallbackQuery` for every `callback_query`. If omitted or delayed:
- The user's Telegram client displays a persistent loading spinner on the button for 30–60 seconds.
- UX feels broken and unresponsive.

```http
POST https://api.telegram.org/bot<token>/answerCallbackQuery
Content-Type: application/json

{
  "callback_query_id": "4382bf356aa1056",
  "text": "Vote recorded!",
  "show_alert": false,
  "cache_time": 0
}
```

### `answerCallbackQuery` Parameters
- **`callback_query_id`** (`String`, required): Unique identifier from the `CallbackQuery`.
- **`text`** (`String`, optional): Notification text (0–200 characters).
- **`show_alert`** (`Boolean`, optional): If `false` (default), shows a brief toast at the top/bottom. If `true`, shows a modal alert dialog with an "OK" button.
- **`url`** (`String`, optional): URL that will be opened by the client (for games or specific deep-links).
- **`cache_time`** (`Integer`, optional): Max time in seconds results can be cached client-side (default 0).

---

## 3. The 64-Byte `callback_data` Limit Pattern

`callback_data` has a strict ceiling of **64 UTF-8 bytes**. Storing JSON or long UUIDs directly will trigger `400 Bad Request: BUTTON_DATA_INVALID`.

### Recommended Encoding Strategy: Compact Colon-Delimited Keys
```typescript
// BAD: Will exceed 64 bytes easily
JSON.stringify({ action: "view_product", id: "550e8400-e29b-41d4-a716-446655440000", page: 3 }) // 82 bytes ❌

// GOOD: Compact delimited syntax
"vp:550e8400:3" // 13 bytes ✅

// BEST FOR HEAVY STATE: Cache in Redis / DB and pass short ID
"s:a9f1b2" // Fetch full payload from Redis key `tg:state:a9f1b2`
```

---

## 4. Reply Keyboards (`ReplyKeyboardMarkup`)

Reply keyboards replace the standard on-screen mobile keyboard with custom buttons.

```json
{
  "keyboard": [
    [
      { "text": "📍 Share Location", "request_location": true },
      { "text": "📞 Share Contact", "request_contact": true }
    ],
    [
      { "text": "👥 Select Channel", "request_chat": { "request_id": 1, "chat_is_channel": true } },
      { "text": "👤 Select User", "request_users": { "request_id": 2, "max_quantity": 1 } }
    ],
    [
      { "text": "❓ Help" },
      { "text": "⚙️ Settings" }
    ]
  ],
  "resize_keyboard": true,
  "one_time_keyboard": false,
  "is_persistent": true,
  "input_field_placeholder": "Choose an option..."
}
```

### Keyboard Parameters
- **`resize_keyboard`** (`Boolean`): Set to `true` so the keyboard shrinks vertically to fit button count instead of taking standard keyboard height.
- **`one_time_keyboard`** (`Boolean`): If `true`, keyboard hides immediately after a button is pressed.
- **`is_persistent`** (`Boolean`): If `true`, keyboard stays open even when standard text input is active.
- **`input_field_placeholder`** (`String`): 1–64 characters placeholder shown in input field when keyboard is visible.
- **`selective`** (`Boolean`): Target only specific users (e.g. users @mentioned in text).

---

## 5. Removing Keyboards & Forcing Replies

### Removing Reply Keyboard (`ReplyKeyboardRemove`)
```json
{
  "chat_id": 123456789,
  "text": "Keyboard dismissed.",
  "reply_markup": {
    "remove_keyboard": true,
    "selective": false
  }
}
```

### Forcing a User Reply (`ForceReply`)
Displays the target message as a quote in the client's reply input, forcing the user to reply directly.
```json
{
  "chat_id": 123456789,
  "text": "Please type your email address:",
  "reply_markup": {
    "force_reply": true,
    "input_field_placeholder": "name@example.com",
    "selective": true
  }
}
```
---

## 6. Keyboard Sharing & Selection Types (Bot API 7.0+)

```typescript
// Request buttons for selecting users or chats
interface KeyboardButtonRequestUsers {
  request_id: number;
  user_is_bot?: boolean;
  user_is_premium?: boolean;
  max_quantity?: number; // 1-10, default 1
  request_name?: boolean;
  request_username?: boolean;
  request_photo?: boolean;
}

interface KeyboardButtonRequestChat {
  request_id: number;
  chat_is_channel: boolean;
  chat_is_forum?: boolean;
  chat_has_username?: boolean;
  chat_is_created?: boolean;
  user_administrator_rights?: ChatAdministratorRights;
  bot_administrator_rights?: ChatAdministratorRights;
  bot_is_member?: boolean;
  request_title?: boolean;
  request_username?: boolean;
  request_photo?: boolean;
}

interface KeyboardButtonPollType {
  type?: 'quiz' | 'regular'; // If omitted, user chooses poll type
}

interface DisabledButton {
  disabled: boolean; // Custom styling for disabled inline buttons
}

// Payloads received on Message when user shares contact/chat
interface UsersShared {
  request_id: number;
  users: SharedUser[];
}

interface SharedUser {
  user_id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo?: PhotoSize[];
}

interface ChatShared {
  request_id: number;
  chat_id: number;
  title?: string;
  username?: string;
  photo?: PhotoSize[];
}
```
