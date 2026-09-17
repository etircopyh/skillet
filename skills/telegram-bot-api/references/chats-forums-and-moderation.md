# Chats, Forum Topics & Moderation

This reference details chat administration, forum topic management in supergroups, member moderation (bans, mutes, restrictions), join request approval, and message reactions.

---

## 1. Chat Types & Identification

| Type | `Chat.type` | ID Format | Features |
| :--- | :--- | :--- | :--- |
| **Private Chat** | `"private"` | Positive 64-bit integer (`123456789`) | 1-on-1 direct message between user and bot. |
| **Group (Basic)** | `"group"` | Negative integer (`-123456789`) | Legacy group (max 200 members). Upgrades to supergroup on configuration. |
| **Supergroup** | `"supergroup"` | Negative 64-bit with `-100` prefix (`-1001234567890`) | Up to 200,000 members, forum topics, custom permissions, admin logs. |
| **Channel** | `"channel"` | Negative 64-bit with `-100` prefix (`-1009876543210`) | Broadcast channel; bot only interacts if granted administrator rights. |

---

## 2. Forum Topics Management (Supergroups)

Supergroups with `is_forum: true` support threads/topics.

### Creating and Managing Topics
```http
POST https://api.telegram.org/bot<token>/createForumTopic
Content-Type: application/json

{
  "chat_id": -1001234567890,
  "name": "🚀 General Announcements",
  "icon_color": 7322096,
  "icon_custom_emoji_id": "5368324170671202286"
}
```
*Returns `ForumTopic` with `message_thread_id`.*

- **Edit Topic**: `editForumTopic(chat_id, message_thread_id, name, icon_custom_emoji_id)`
- **Close/Reopen**: `closeForumTopic`, `reopenForumTopic`
- **Delete**: `deleteForumTopic(chat_id, message_thread_id)` (permanently deletes all topic messages).
- **Unpin Messages**: `unpinAllForumTopicMessages(chat_id, message_thread_id)`.

### Sending Messages to Specific Topics
Pass `message_thread_id` to route messages directly into that topic:

```http
POST https://api.telegram.org/bot<token>/sendMessage
Content-Type: application/json

{
  "chat_id": -1001234567890,
  "message_thread_id": 42,
  "text": "Hello topic subscribers!"
}
```

---

## 3. Moderation: Mutes, Bans, and Permissions

### Inspecting Member Permissions (`getChatMember`)
Returns one of: `ChatMemberOwner`, `ChatMemberAdministrator`, `ChatMemberMember`, `ChatMemberRestricted`, `ChatMemberLeft`, `ChatMemberBanned`.

### Restricting / Muting a Member (`restrictChatMember`)
```http
POST https://api.telegram.org/bot<token>/restrictChatMember
Content-Type: application/json

{
  "chat_id": -1001234567890,
  "user_id": 987654321,
  "until_date": 1711886400,
  "use_independent_chat_permissions": true,
  "permissions": {
    "can_send_messages": false,
    "can_send_media_messages": false,
    "can_send_polls": false,
    "can_send_other_messages": false,
    "can_add_web_page_previews": false,
    "can_change_info": false,
    "can_invite_users": false,
    "can_pin_messages": false
  }
}
```
*`until_date`: Unix timestamp. If less than 30 seconds or greater than 366 days, user is restricted forever.*

### Banning & Unbanning (`banChatMember` / `unbanChatMember`)
- **Ban**: `banChatMember(chat_id, user_id, until_date, revoke_messages=true)`
- **Unban (soft unban / kick without permanent blacklist)**:
  `unbanChatMember(chat_id, user_id, only_if_banned=true)`

---

## 4. Join Request Management

When private groups/channels use join-request invite links:

1. Bot receives `chat_join_request` update containing `ChatJoinRequest` (`chat`, `from`, `user_chat_id`, `date`, `bio`, `invite_link`).
2. Bot can verify the user (e.g. captcha or subscription check in `user_chat_id`).
3. Bot approves or declines:
   - `approveChatJoinRequest(chat_id, user_id)`
   - `declineChatJoinRequest(chat_id, user_id)`

---

## 5. Message Reactions

### Setting Reactions Programmatically (`setMessageReaction`)
```http
POST https://api.telegram.org/bot<token>/setMessageReaction
Content-Type: application/json

{
  "chat_id": -1001234567890,
  "message_id": 1042,
  "reaction": [
    { "type": "emoji", "emoji": "🔥" }
  ],
  "is_big": false
}
```

---

## 6. Member Custom Tags (Bot API 9.5+)

Assign custom text badges/tags to regular members in groups and supergroups (e.g. "VIP", "Moderator", "Support"):

```http
POST https://api.telegram.org/bot<token>/setChatMemberTag
Content-Type: application/json

{
  "chat_id": -1001234567890,
  "user_id": 987654321,
  "tag": "💎 VIP Member"
}
```

- **Requirements**: Bot must be admin with `can_manage_tags: true`.
- **Message Attribute**: Incoming `Message.sender_tag` reflects the tag at the time the message was sent.
- **Member Inspection**: `ChatMemberMember.tag` and `ChatMemberRestricted.tag`.

---

## 7. Topics in Private 1-on-1 Chats (Bot API 9.3+)

Users and bots can enable forum topic threads inside 1-on-1 private direct messages.

- **Check Capability**: `User.has_topics_enabled` indicates whether topic mode is enabled.
- **`createForumTopic` in Private Chats**: Create threads inside private DM by passing the target `user_id` as `chat_id`.
- **BotFather Permission**: `User.allows_users_to_create_topics` (configured via BotFather Mini App).
- **Routing**: Pass `message_thread_id` to `sendMessage`, `sendPhoto`, etc.

---

## 8. Modern Administrator Rights & Story Management

When promoting admins via `promoteChatMember` or inspecting `ChatAdministratorRights`:

| Right | API Field | Description |
| :--- | :--- | :--- |
| **Manage Tags** | `can_manage_tags` | Assign and remove member custom tags. |
| **Welcome Messages** | `can_send_welcome_messages` | Send automated welcome messages to new joiners. |
| **Manage Topics** | `can_manage_topics` | Create, rename, close, and delete forum topics. |
| **Post Stories** | `can_post_stories` | Post stories on behalf of the channel/chat. |
| **Edit Stories** | `can_edit_stories` | Edit stories posted by other admins. |
| **Delete Stories** | `can_delete_stories` | Delete stories posted in the channel. |
| **Manage Video Chats** | `can_manage_video_chats` | Start, pause, or manage live streams. |

---

## 9. General Forum Topic Management

Supergroup forums possess a default "General" topic with distinct lifecycle controls:

- **Edit Title**: `editGeneralForumTopic(chat_id, name)`
- **Close / Reopen**: `closeGeneralForumTopic(chat_id)`, `reopenGeneralForumTopic(chat_id)`
- **Hide / Unhide**: `hideGeneralForumTopic(chat_id)`, `unhideGeneralForumTopic(chat_id)`
- **Unpin Messages**: `unpinAllGeneralForumTopicMessages(chat_id)`

---

## 10. Invite Links & Member Verification

Bots with `can_invite_users` administrator rights can create tracked invite links:

```http
POST https://api.telegram.org/bot<token>/createChatInviteLink
Content-Type: application/json

{
  "chat_id": -1001234567890,
  "name": "Twitter Campaign 2026",
  "expire_date": 1712880000,
  "member_limit": 50,
  "creates_join_request": false
}
```

- **`creates_join_request: true`**: Creates an approval-gate link requiring admin review.
- **Revoking**: `revokeChatInviteLink(chat_id, invite_link)`.
- **Primary Link**: `exportChatInviteLink(chat_id)`.

---

## 11. Admin Custom Titles & Channel Senders

- **Custom Title**: Assign a custom badge to administrators (`setChatAdministratorCustomTitle(chat_id, user_id, custom_title: String)`). Appears next to the admin's name in group messages (0–16 characters).
- **Banning Anonymous Channel Senders**: If users post in supergroups using a channel identity, ban or unban the specific channel:
  - `banChatSenderChat(chat_id, sender_chat_id)`
  - `unbanChatSenderChat(chat_id, sender_chat_id)`

---

## 12. Live Location Management

Bots can stream or track real-time locations:

- **Start Live Location**: Call `sendLocation` with `live_period` (60–86400 seconds), optional `heading` (1–360°), and `proximity_alert_radius`.
- **Edit Live Location**:
  ```http
  POST https://api.telegram.org/bot<token>/editMessageLiveLocation
  Content-Type: application/json

  {
    "chat_id": 123456789,
    "message_id": 105,
    "latitude": 37.7752,
    "longitude": -122.4190,
    "heading": 90
  }
  ```
- **Stop Live Location**: `stopMessageLiveLocation(chat_id, message_id)`.

---

## 13. Channel Suggested Posts (Bot API 9.x+)

Channel administrators can enable suggested posts where users submit posts for review, optionally attaching a price in Telegram Stars:

- **`approveSuggestedPost(chat_id, message_id, send_date)`**: Approves and publishes or schedules a suggested post.
- **`declineSuggestedPost(chat_id, message_id)`**: Rejects a submitted post.
- Updates: `SuggestedPostApproved`, `SuggestedPostDeclined`, `SuggestedPostPaid`, `SuggestedPostRefunded`.
---

## 14. Comprehensive Chat Administration & Boost Schemas

### Chat Management Methods
```typescript
setChatPermissions(params: { chat_id: number | string; permissions: ChatPermissions; use_independent_chat_permissions?: boolean }): Promise<boolean>;
editChatInviteLink(params: { chat_id: number | string; invite_link: string; name?: string; expire_date?: number; member_limit?: number; creates_join_request?: boolean }): Promise<ChatInviteLink>;
answerChatJoinRequestQuery(params: { chat_id: number | string; user_id: number; approve: boolean }): Promise<boolean>;
sendChatJoinRequestWebApp(params: { chat_id: number | string; user_id: number; web_app: WebAppInfo }): Promise<boolean>;

setChatPhoto(params: { chat_id: number | string; photo: InputFile }): Promise<boolean>;
deleteChatPhoto(params: { chat_id: number | string }): Promise<boolean>;
setChatTitle(params: { chat_id: number | string; title: string }): Promise<boolean>;
setChatDescription(params: { chat_id: number | string; description?: string }): Promise<boolean>;

pinChatMessage(params: { chat_id: number | string; message_id: number; disable_notification?: boolean; business_connection_id?: string }): Promise<boolean>;
unpinChatMessage(params: { chat_id: number | string; message_id?: number; business_connection_id?: string }): Promise<boolean>;
unpinAllChatMessages(params: { chat_id: number | string }): Promise<boolean>;
leaveChat(params: { chat_id: number | string }): Promise<boolean>;

getChatAdministrators(params: { chat_id: number | string }): Promise<ChatMemberAdministrator[]>;
getChatMemberCount(params: { chat_id: number | string }): Promise<number>;
getUserPersonalChatMessages(params: { chat_id: number | string; user_id: number; offset?: number; limit?: number }): Promise<Message[]>;

setChatStickerSet(params: { chat_id: number | string; sticker_set_name: string }): Promise<boolean>;
deleteChatStickerSet(params: { chat_id: number | string }): Promise<boolean>;
getForumTopicIconStickers(): Promise<Sticker[]>;
getUserChatBoosts(params: { chat_id: number | string; user_id: number }): Promise<UserChatBoosts>;
```

### Chat Types, Boost Sources & Forum Events
```typescript
interface ChatPhoto { small_file_id: string; small_file_unique_id: string; big_file_id: string; big_file_unique_id: string; }
interface ChatLocation { location: Location; address: string; }
interface UserChatBoosts { boosts: ChatBoost[]; }

type ChatBoostSource = ChatBoostSourcePremium | ChatBoostSourceGiftCode | ChatBoostSourceGiveaway;
interface ChatBoostSourcePremium { source: 'premium'; user: User; }
interface ChatBoostSourceGiftCode { source: 'gift_code'; user: User; }
interface ChatBoostSourceGiveaway { source: 'giveaway'; giveaway_message_id: number; user?: User; prize_star_count?: number; is_unclaimed?: boolean; }

interface ChatOwnerLeft { /* Emitted when chat owner leaves */ }
interface ChatOwnerChanged { new_owner: User; }
interface ForumTopicCreated { name: string; icon_color: number; icon_custom_emoji_id?: string; }
interface ForumTopicClosed { /* Emitted when topic closed */ }
interface ForumTopicEdited { name?: string; icon_custom_emoji_id?: string; }
interface ForumTopicReopened { /* Emitted when topic reopened */ }
interface GeneralForumTopicHidden { /* Emitted when general topic hidden */ }
interface GeneralForumTopicUnhidden { /* Emitted when general topic unhidden */ }
interface CommunityChatAdded { chat: Chat; }
interface CommunityChatJoined { chat: Chat; }
interface CommunityChatRemoved { chat: Chat; }

interface SuggestedPostPrice { currency: string; amount: number; }
interface SuggestedPostInfo { price?: SuggestedPostPrice; state: 'pending' | 'approved' | 'rejected'; }
interface SuggestedPostParameters { price?: SuggestedPostPrice; }
interface SuggestedPostApprovalFailed { reason: string; }
```
