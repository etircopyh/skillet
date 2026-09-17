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

---

## 6. Business Account Profile & Story Management (Bot API 9.0+)

Bots with the `can_change_info` and `can_manage_stories` business bot rights can manage the connected account's public profile and post stories:

### Profile Customization
- **`setBusinessAccountName(business_connection_id, first_name, last_name)`**
- **`setBusinessAccountUsername(business_connection_id, username)`**
- **`setBusinessAccountBio(business_connection_id, bio)`**
- **`setBusinessAccountProfilePhoto(business_connection_id, photo: InputProfilePhoto)`**
- **`removeBusinessAccountProfilePhoto(business_connection_id)`**
- **`setBusinessAccountGiftSettings(business_connection_id, accepted_gift_types)`**
- **`readBusinessMessage(business_connection_id, chat_id, message_id)`**: Marks customer message as read.
- **`deleteBusinessMessages(business_connection_id, message_ids)`**: Deletes messages from business chat.

### Business Stories
- **`postStory(business_connection_id, content: InputStoryContent, active_period, caption, ...)`**: Posts a story (`active_period`: `21600` [6h], `43200` [12h], `86400` [24h], or `172800` [48h]).
- **`repostStory(business_connection_id, from_chat_id, from_story_id, active_period)`**
- **`editStory(business_connection_id, story_id, content, caption, ...)`**
- **`deleteStory(business_connection_id, story_id)`**

---

## 7. Organization & User Verification API (Bot API 8.0+)

Bots representing recognized organizations (e.g. government, corporate, or partner authorities with a custom verification icon) can officially verify third-party channels and users on Telegram:

```http
POST https://api.telegram.org/bot<token>/verifyUser
Content-Type: application/json

{
  "user_id": 123456789,
  "custom_description": "Verified Employee of Acme Corp"
}
```

- **`verifyUser(user_id, custom_description)`**: Verifies a user profile.
- **`verifyChat(chat_id, custom_description)`**: Verifies a channel or group chat.
- **`removeUserVerification(user_id)`**: Revokes verification from user.
- **`removeChatVerification(chat_id)`**: Revokes verification from chat.
---

## 8. Business Connections, Managed Bots & Checklists API

### Business Account Methods
```typescript
getBusinessConnection(params: { business_connection_id: string }): Promise<BusinessConnection>;
getBusinessAccountStarBalance(params: { business_connection_id: string }): Promise<StarBalance>;
transferBusinessAccountStars(params: { business_connection_id: string; star_count: number }): Promise<boolean>;

// Checklists in Business Accounts
sendChecklist(params: { business_connection_id: string; chat_id: number; checklist: InputChecklist; reply_markup?: InlineKeyboardMarkup }): Promise<Message>;
editMessageChecklist(params: { business_connection_id: string; chat_id: number; message_id: number; checklist: InputChecklist; reply_markup?: InlineKeyboardMarkup }): Promise<Message>;

// Managed Bots (Bot API 9.6+)
getManagedBotAccessSettings(params: { bot_user_id: number }): Promise<BotAccessSettings>;
setManagedBotAccessSettings(params: { bot_user_id: number; permissions: BotAccessSettings }): Promise<boolean>;
```

### Business Profile & Story Types
```typescript
interface Birthdate { day: number; month: number; year?: number; }
interface BusinessIntro { title?: string; message?: string; sticker?: Sticker; }
interface BusinessLocation { address: string; location?: Location; }
interface BusinessOpeningHoursInterval { opening_minute: number; closing_minute: number; }
interface BusinessOpeningHours { time_zone_name: string; opening_hours: BusinessOpeningHoursInterval[]; }
interface BotAccessSettings { can_reply?: boolean; can_manage_stories?: boolean; }
interface BusinessBotRights { can_reply: boolean; can_manage_stories: boolean; }
interface ManagedBotCreated { bot: User; }
interface ChecklistTasksDone { tasks_done: string[]; }
interface ChecklistTasksAdded { tasks_added: string[]; }
interface SentGuestMessage { message_id: number; }
interface UserRating { rating: number; }

interface StoryArea { position: StoryAreaPosition; type: StoryAreaType; }
interface StoryAreaPosition { x_percentage: number; y_percentage: number; width_percentage: number; height_percentage: number; rotation_angle: number; }
type StoryAreaType = StoryAreaTypeLocation | StoryAreaTypeSuggestedReaction | StoryAreaTypeLink | StoryAreaTypeWeather | StoryAreaTypeUniqueGift;
interface StoryAreaTypeLocation { type: 'location'; latitude: number; longitude: number; address?: LocationAddress; }
interface StoryAreaTypeSuggestedReaction { type: 'suggested_reaction'; reaction_type: ReactionType; is_dark?: boolean; is_flipped?: boolean; }
interface StoryAreaTypeLink { type: 'link'; url: string; }
interface StoryAreaTypeWeather { type: 'weather'; temperature_c: number; emoji: string; background_color: number; }
interface StoryAreaTypeUniqueGift { type: 'unique_gift'; name: string; }

type InputStoryContent = InputStoryContentPhoto | InputStoryContentVideo;
interface InputStoryContentPhoto { type: 'photo'; photo: InputFile | string; }
interface InputStoryContentVideo { type: 'video'; video: InputFile | string; duration?: number; }
interface InputProfilePhotoStatic { type: 'static'; photo: InputFile | string; }
interface InputProfilePhotoAnimated { type: 'animated'; animation: InputFile | string; }
```
