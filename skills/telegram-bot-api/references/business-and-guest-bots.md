# Telegram Business & Guest Mode

This reference details advanced bot integration modes: Telegram Business bot connections, acting on behalf of business accounts, Guest Mode, Bot-to-Bot messaging, and Managed Bots.

---

## 1. Telegram Business Bot Connection (Bot API 7.2+)

Telegram Business users can connect a bot to their personal account to manage customer chats, automate replies, and process orders.

### The `business_connection` Update
When a user connects or disconnects your bot in their Telegram Business settings:

```json
{
  "update_id": 10001,
  "business_connection": {
    "id": "bc_abc1234567",
    "user": {
      "id": 987654321,
      "is_bot": false,
      "first_name": "Alice Business",
      "username": "alice_biz"
    },
    "user_chat_id": 987654321,
    "date": 1711800000,
    "can_reply": true,
    "is_enabled": true
  }
}
```

- **`can_reply`** (`Boolean`): Indicates if the bot has permission to send messages on behalf of the business account.
- **`is_enabled`** (`Boolean`): Set to `false` when the connection is terminated by the user.

---

## 2. Business Messages Pipeline

When customers message the connected business account:

### 1. Receiving Incoming Business Messages (`business_message`)
The `Update` arrives with `business_message` (a standard `Message` object containing `business_connection_id`).

### 2. Sending Messages on Behalf of Business Account
To reply to customer chats, pass `business_connection_id` in sending methods:

```http
POST https://api.telegram.org/bot<token>/sendMessage
Content-Type: application/json

{
  "business_connection_id": "bc_abc1234567",
  "chat_id": 555444333,
  "text": "Hello! Welcome to Alice's Store. How can we help you today?"
}
```

### 3. Business Message Edits and Deletions
- **`edited_business_message`**: Arrives when customer or business edits a message.
- **`deleted_business_messages`**: Arrives as `BusinessMessagesDeleted` (`business_connection_id`, `chat`, `message_ids: Integer[]`).

---

## 3. Guest Mode (Bot API 10.0+)

Guest Mode allows bots to process commands and deliver replies in group chats **without requiring the bot to be added as a permanent group member**.

### Flow
1. User mentions `@botusername` or sends a guest-enabled command in a group.
2. Bot receives a `guest_message` update containing `guest_query_id`.
3. Bot responds using `answerGuestQuery`:

```http
POST https://api.telegram.org/bot<token>/answerGuestQuery
Content-Type: application/json

{
  "guest_query_id": "gq_99887766",
  "result": {
    "type": "article",
    "id": "res_1",
    "title": "Stock Quote: AAPL",
    "input_message_content": {
      "message_text": "📊 AAPL: $245.50 (+1.8%)"
    }
  }
}
```

---

## 4. Bot-to-Bot Communication (Bot API 10.0+)

By default, bots ignore messages from other bots to prevent infinite loops. Bots can explicitly opt in:

- Enable in [@BotFather](https://t.me/BotFather) settings (`/setbotmessages` -> Enable).
- Bots can exchange structured updates, invoke specialized agentic sub-bots, or forward requests between microservice bots.

---

## 5. Managed Bots (Bot API 9.6+)

Enables "Manager Bots" to dynamically spawn and control child bots on behalf of users without requiring manual BotFather token copying.

- **`KeyboardButtonRequestManagedBot`**: Request user to authorize creation of a managed bot.
- **`getManagedBotToken(user_id)`**: Retrieve token for the spawned managed bot.
- **`replaceManagedBotToken(user_id)`**: Rotate compromised tokens for managed bots.
