# Bot Configuration & BotFather Settings

This reference details programmatic bot configuration via Bot API (`setMyCommands`, scopes, names, descriptions, menu buttons) and manual BotFather configuration (Privacy Mode, Inline Mode, Admin Rights).

---

## 1. Bot Commands & Scopes (`setMyCommands`)

Bot commands appear in the autocomplete popup when users type `/` in the input field.

### Scoped Commands Architecture
Different commands can be exposed depending on context (private chats, group admins, specific chats, or languages).

```http
POST https://api.telegram.org/bot<token>/setMyCommands
Content-Type: application/json

{
  "commands": [
    { "command": "start", "description": "Start the assistant" },
    { "command": "help", "description": "View available tools" },
    { "command": "settings", "description": "Configure preferences" }
  ],
  "scope": {
    "type": "all_private_chats"
  },
  "language_code": "en"
}
```

### `BotCommandScope` Types

| Scope Type | `type` Field | Description |
| :--- | :--- | :--- |
| **Default** | `"default"` | Fallback commands for all users in all chats. |
| **All Private Chats** | `"all_private_chats"` | Commands displayed in 1-on-1 private DMs. |
| **All Group Chats** | `"all_group_chats"` | Commands displayed in basic groups and supergroups. |
| **All Chat Administrators** | `"all_chat_administrators"` | Commands shown to admins in all groups/supergroups. |
| **Specific Chat** | `"chat"` | Commands for a single target `chat_id`. |
| **Chat Administrators** | `"chat_administrators"` | Commands for administrators of a specific `chat_id`. |
| **Specific Chat Member** | `"chat_member"` | Commands for a specific user within a specific group. |

---

## 2. Bot Profile & Metadata Methods

Configure bot presentation dynamically via API:

```http
POST https://api.telegram.org/bot<token>/setMyDescription
Content-Type: application/json

{
  "description": "🚀 Fast, AI-powered coding assistant.\nClick 'Start' to begin pair programming!",
  "language_code": "en"
}
```

- **`setMyName(name, language_code)`**: Changes bot display name (0–64 chars).
- **`setMyDescription(description, language_code)`**: Text shown on the empty chat screen before user presses "Start" (0–512 chars).
- **`setMyShortDescription(short_description, language_code)`**: Text shown on the bot's profile page and share links (0–120 chars).
- **`setMyProfilePhoto(photo)`**: Uploads bot avatar directly via API (Bot API 9.4+).
- **`removeMyProfilePhoto()`**: Clears bot avatar.

---

## 3. Menu Button Configuration (`setChatMenuButton`)

The Menu Button sits beside the message input field in private chats.

```http
POST https://api.telegram.org/bot<token>/setChatMenuButton
Content-Type: application/json

{
  "chat_id": 123456789,
  "menu_button": {
    "type": "web_app",
    "text": "Launch Dashboard",
    "web_app": {
      "url": "https://dashboard.example.com"
    }
  }
}
```

- **`MenuButtonCommands`** (`{ "type": "commands" }`): Opens commands list.
- **`MenuButtonWebApp`** (`{ "type": "web_app", "text": "...", "web_app": { "url": "..." } }`): Opens Mini App.
- **`MenuButtonDefault`** (`{ "type": "default" }`): Inherits global default menu button.

---

## 4. BotFather Configuration Reference

Key administrative settings managed via [@BotFather](https://t.me/BotFather):

### 1. Group Privacy Mode (`/setprivacy`)
- **Enabled (Default)**: Bot receives ONLY:
  - Commands beginning with `/` (e.g. `/help@botname`).
  - Direct replies to the bot's own messages.
  - Mentions of the bot (`@botname`).
  - Service messages (member joins/leaves).
- **Disabled**: Bot receives **EVERY message** sent in groups.
  *(Use when building moderation, auto-tagging, or passive logging bots).*

### 2. Group Permissions (`/setjoingroups`)
- Controls whether users can add the bot to groups and channels.

### 3. Inline Mode (`/setinline`)
- Enables inline query mode where users type `@botname <query>` in any chat.
- Configure placeholder text (e.g., "Search database...").

### 4. Mini App / Web App Registration (`/newapp` & `/editapp`)
- Configure short name for direct deep links (`t.me/botusername/appname`).
- Upload app icon, screenshots, and specify launch URL.
---

## 5. Bot Identity, Profile, Commands & Scopes Reference

### Admin & Lifecycle Methods
```typescript
getMe(): Promise<User>;
logOut(): Promise<boolean>; // Cloud server logout before running local Bot API
close(): Promise<boolean>;  // Close instance before moving between local servers
```

### Command & Description Configuration
```typescript
deleteMyCommands(params?: { scope?: BotCommandScope; language_code?: string }): Promise<boolean>;
getMyCommands(params?: { scope?: BotCommandScope; language_code?: string }): Promise<BotCommand[]>;

getMyName(params?: { language_code?: string }): Promise<BotName>;
getMyDescription(params?: { language_code?: string }): Promise<BotDescription>;
getMyShortDescription(params?: { language_code?: string }): Promise<BotShortDescription>;

getChatMenuButton(params?: { chat_id?: number }): Promise<MenuButton>;
setMyDefaultAdministratorRights(params?: { rights?: ChatAdministratorRights; for_channels?: boolean }): Promise<boolean>;
getMyDefaultAdministratorRights(params?: { for_channels?: boolean }): Promise<ChatAdministratorRights>;

getUserProfilePhotos(params: { user_id: number; offset?: number; limit?: number }): Promise<UserProfilePhotos>;
getUserProfileAudios(params: { user_id: number; offset?: number; limit?: number }): Promise<UserProfileAudios>;
```

### Command Scope Types & Profile Containers
```typescript
type BotCommandScope =
  | BotCommandScopeDefault
  | BotCommandScopeAllPrivateChats
  | BotCommandScopeAllGroupChats
  | BotCommandScopeAllChatAdministrators
  | BotCommandScopeChat
  | BotCommandScopeChatAdministrators
  | BotCommandScopeChatMember;

interface BotCommandScopeDefault { type: 'default'; }
interface BotCommandScopeAllPrivateChats { type: 'all_private_chats'; }
interface BotCommandScopeAllGroupChats { type: 'all_group_chats'; }
interface BotCommandScopeAllChatAdministrators { type: 'all_chat_administrators'; }
interface BotCommandScopeChat { type: 'chat'; chat_id: number | string; }
interface BotCommandScopeChatAdministrators { type: 'chat_administrators'; chat_id: number | string; }
interface BotCommandScopeChatMember { type: 'chat_member'; chat_id: number | string; user_id: number; }

interface BotName { name: string; }
interface BotDescription { description: string; }
interface BotShortDescription { short_description: string; }
interface UserProfilePhotos { total_count: number; photos: PhotoSize[][]; }
interface UserProfileAudios { total_count: number; audios: Audio[]; }
```
