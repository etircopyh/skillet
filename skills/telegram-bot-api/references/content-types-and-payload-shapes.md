# Content Types, Incoming Media & API Payload Shapes

This reference details the exact JSON schemas for incoming Telegram messages, media detection patterns, the file retrieval pipeline (`getFile`), and the request shapes for sending media via JSON or `multipart/form-data`.

---

## 1. Incoming Content Type Detection Matrix

An incoming `Message` object contains common metadata (`message_id`, `from`, `chat`, `date`) and **at most ONE** primary content field.

Use this field presence check to classify the message:

| Primary Field on `Message` | Content Type | Accompanying Fields |
| :--- | :--- | :--- |
| **`text`** | Plain text / command | `entities` (`MessageEntity[]`), `link_preview_options` |
| **`sticker`** | Sticker (static, animated, video, custom emoji) | - |
| **`photo`** | Photo album or single image | `photo` (`PhotoSize[]`), `caption`, `caption_entities`, `has_spoiler`, `show_caption_above_media` |
| **`animation`** | GIF or silent animation loop (MP4) | `thumbnail`, `caption`, `caption_entities`, `has_spoiler` |
| **`audio`** | Music file (.mp3, .m4a) | `duration`, `performer`, `title`, `thumbnail`, `caption` |
| **`voice`** | Voice note (OGG OPUS) | `duration`, `mime_type`, `caption` |
| **`video`** | Standard video with audio (.mp4) | `duration`, `width`, `height`, `thumbnail`, `caption`, `has_spoiler` |
| **`video_note`** | Camera bubble video note (1:1 round) | `length` (diameter), `duration`, `thumbnail` |
| **`document`** | General file (PDF, ZIP, APK, etc.) | `file_name`, `mime_type`, `thumbnail`, `caption` |
| **`contact`** | Phone contact card | `phone_number`, `first_name`, `last_name`, `user_id`, `vcard` |
| **`location`** | Geographic coordinate | `latitude`, `longitude`, `horizontal_accuracy`, `live_period`, `heading` |
| **`venue`** | Venue with address | `location`, `title`, `address`, `foursquare_id`, `google_place_id` |
| **`poll`** | Native poll / quiz | `Poll` object (`question`, `options`, `correct_option_ids`, etc.) |
| **`dice`** | Animated dice roll | `emoji`, `value` (1–6, or 1–64 for slot machine) |
| **`game`** | Interactive game | `title`, `description`, `photo`, `animation`, `text` |
| **`story`** | Forwarded story | `chat`, `id` |
| **`paid_media`** | Paid media block | `star_count`, `paid_media` (`PaidMedia[]`) |
| **`checklist`** | Interactive checklist | `Checklist` object (`title`, `tasks`) |

---

### Python Pattern Matching Example
```python
def classify_message(message: dict) -> str:
    for content_type in [
        "text", "sticker", "photo", "animation", "audio", "voice",
        "video", "video_note", "document", "contact", "location",
        "venue", "poll", "dice", "game", "story", "paid_media", "checklist"
    ]:
        if content_type in message:
            return content_type
    return "service_message"
```

---

## 2. Incoming Media Payload Schemas

### 2.1. Sticker (`Message.sticker`)
Stickers can be static (`.webp`), animated (`.tgs` Lottie), video (`.webm`), or custom emoji stickers.

```json
{
  "message_id": 101,
  "from": { "id": 123456789, "is_bot": false, "first_name": "Alex" },
  "chat": { "id": 123456789, "type": "private" },
  "date": 1711880000,
  "sticker": {
    "file_id": "CAACAgIAAxkBAAI...",
    "file_unique_id": "AQADa-IxGy4EwUk",
    "type": "regular",
    "width": 512,
    "height": 512,
    "is_animated": false,
    "is_video": true,
    "emoji": "🎉",
    "set_name": "PartyAnimals",
    "file_size": 34820,
    "thumbnail": {
      "file_id": "AAMCAgADGQE...",
      "file_unique_id": "AQADG_IxGy4EwUl",
      "width": 320,
      "height": 320,
      "file_size": 8940
    }
  }
}
```

- **`type`**: `"regular"`, `"mask"`, or `"custom_emoji"`.
- **`is_animated`**: `true` if Lottie vector `.tgs`.
- **`is_video`**: `true` if WEBM VP9 video sticker.
- **`custom_emoji_id`**: Present if `type == "custom_emoji"`.
- **`emoji`**: Emoji associated with the sticker.
- **`set_name`**: Name of the sticker set to which the sticker belongs.

---

### 2.2. Photo (`Message.photo`)
Telegram always delivers photos as an **array of `PhotoSize` objects**, sorted by resolution from lowest to highest.

```json
{
  "message_id": 102,
  "chat": { "id": 123456789, "type": "private" },
  "photo": [
    { "file_id": "AgACAgI..._s", "file_unique_id": "AQADs", "width": 90, "height": 67, "file_size": 1420 },
    { "file_id": "AgACAgI..._m", "file_unique_id": "AQADm", "width": 320, "height": 240, "file_size": 18450 },
    { "file_id": "AgACAgI..._x", "file_unique_id": "AQADx", "width": 800, "height": 600, "file_size": 75200 },
    { "file_id": "AgACAgI..._y", "file_unique_id": "AQADy", "width": 1280, "height": 960, "file_size": 182400 }
  ],
  "caption": "Check this sunset view! 🌅",
  "has_spoiler": false
}
```

> [!IMPORTANT]
> **Highest Resolution Invariant**: To get the original full-size photo, always select the **last element** in the array:
> `const originalPhoto = message.photo[message.photo.length - 1];`

---

### 2.3. Animation / GIF (`Message.animation`)
Animations are MPEG4 videos without sound (or converted GIFs).

```json
{
  "animation": {
    "file_id": "CgACAgIAAxkBAAI...",
    "file_unique_id": "AQADawIxGy4EwUk",
    "width": 480,
    "height": 480,
    "duration": 3,
    "file_name": "celebration.mp4",
    "mime_type": "video/mp4",
    "file_size": 420100,
    "thumbnail": {
      "file_id": "AAMCAgAD...",
      "width": 320,
      "height": 320,
      "file_size": 9400
    }
  },
  "document": {
    "file_id": "CgACAgIAAxkBAAI...",
    "mime_type": "video/mp4"
  }
}
```
*Note: Telegram often includes a duplicate `document` field on animation messages for backward compatibility.*

---

### 2.4. Voice Note (`Message.voice`) vs Audio Track (`Message.audio`)

| Field | Voice Note (`voice`) | Music / Audio Track (`audio`) |
| :--- | :--- | :--- |
| **Codec / Format** | OGG with OPUS codec | MP3, M4A, FLAC |
| **UI Presentation** | Circular waveform player | Standard music player bar |
| **Payload Schema** | ```json { "file_id": "AwACAg...", "duration": 8, "mime_type": "audio/ogg", "file_size": 16400 } ``` | ```json { "file_id": "CQACAg...", "duration": 214, "performer": "Daft Punk", "title": "Get Lucky", "file_name": "track.mp3", "mime_type": "audio/mpeg", "file_size": 8420000, "thumbnail": { ... } } ``` |

---

### 2.5. Video (`Message.video`) vs Video Note (`Message.video_note`)

- **Video Note (`video_note`)**: Circular camera bubble recorded directly in Telegram:
  ```json
  {
    "video_note": {
      "file_id": "DQACAgIAAxkBAAI...",
      "file_unique_id": "AQAD...",
      "length": 384,
      "duration": 14,
      "file_size": 2105400,
      "thumbnail": { "file_id": "AAMC...", "width": 320, "height": 320, "file_size": 12400 }
    }
  }
  ```
  *`length`: Both width and height in pixels (always square 1:1 aspect ratio).*

- **Standard Video (`video`)**:
  ```json
  {
    "video": {
      "file_id": "BAACAgIAAxkBAAI...",
      "file_unique_id": "AQAD...",
      "width": 1920,
      "height": 1080,
      "duration": 45,
      "file_name": "demo.mp4",
      "mime_type": "video/mp4",
      "file_size": 15400200,
      "thumbnail": { "file_id": "AAMC...", "width": 320, "height": 180, "file_size": 8900 }
    },
    "caption": "Walkthrough video"
  }
  ```

---

### 2.6. Document (`Message.document`)
Represents any general file attachment:

```json
{
  "document": {
    "file_id": "BQACAgIAAxkBAAI...",
    "file_unique_id": "AQAD...",
    "file_name": "quarterly_financials.pdf",
    "mime_type": "application/pdf",
    "file_size": 1245900,
    "thumbnail": { "file_id": "AAMC...", "width": 226, "height": 320, "file_size": 14200 }
  },
  "caption": "Please review page 4."
}
```

---

### 2.7. Contact, Location & Venue

- **Contact (`Message.contact`)**:
  ```json
  {
    "contact": {
      "phone_number": "+1234567890",
      "first_name": "John",
      "last_name": "Doe",
      "user_id": 987654321,
      "vcard": "BEGIN:VCARD\nVERSION:3.0\nN:Doe;John;;;\nFN:John Doe\nTEL;TYPE=CELL:+1234567890\nEND:VCARD"
    }
  }
  ```

- **Location (`Message.location`)**:
  ```json
  {
    "location": {
      "latitude": 37.774929,
      "longitude": -122.419416,
      "horizontal_accuracy": 4.5,
      "live_period": 3600,
      "heading": 180
    }
  }
  ```

- **Venue (`Message.venue`)**:
  ```json
  {
    "venue": {
      "location": { "latitude": 37.774929, "longitude": -122.419416 },
      "title": "Union Square",
      "address": "333 Post St, San Francisco, CA 94108",
      "foursquare_id": "4a737f5ff964a520..."
    }
  }
  ```

---

### 2.8. Dice & Games (`Message.dice`)

```json
{
  "dice": {
    "emoji": "🎲",
    "value": 6
  }
}
```

*Value ranges by emoji:*
- 🎲 / 🎯 : `1` to `6`
- 🏀 / ⚽ : `1` to `5`
- 🎳 : `1` to `6`
- 🎰 : `1` to `64` (values 1, 22, 43, 64 represent winning combinations)

---

### 2.9. Quotes & Replies (`Message.quote` & `Message.reply_to_message`)

When a user replies to a specific quote of a previous message:

```json
{
  "message_id": 205,
  "reply_to_message": {
    "message_id": 198,
    "text": "Antigravity CLI is ready for deployment across all regions."
  },
  "quote": {
    "text": "ready for deployment",
    "position": 20,
    "entities": [],
    "is_manual": true
  },
  "text": "Which cloud provider are we using?"
}
```

*For complete message origin tracking (`forward_origin`), cross-chat replies (`external_reply`), discussion group mirrors (`is_automatic_forward`), and outbound `ReplyParameters`, see [`message-provenance-replies-and-origins.md`](./message-provenance-replies-and-origins.md).*

---

## 3. The File Retrieval Pipeline (`getFile`)

When media arrives, Telegram provides a `file_id`. The file binary is not inside the `Update` payload.

```
[Incoming Update with file_id]
             │
             ▼
[1. Call getFile(file_id)]
             │
             ▼
[2. Telegram returns File object with file_path]
             │
             ▼
[3. Download binary from https://api.telegram.org/file/bot<token>/<file_path>]
```

### Step 1: Request `getFile`
```http
POST https://api.telegram.org/bot<token>/getFile
Content-Type: application/json

{
  "file_id": "CAACAgIAAxkBAAI..."
}
```

### Step 2: Response `File` Object
```json
{
  "ok": true,
  "result": {
    "file_id": "CAACAgIAAxkBAAI...",
    "file_unique_id": "AQADa-IxGy4EwUk",
    "file_size": 34820,
    "file_path": "stickers/file_42.webm"
  }
}
```

### Step 3: Direct Download URL
```
https://api.telegram.org/file/bot<token>/stickers/file_42.webm
```

### File Retrieval Invariants
- **Download Limit**: Bots can download files up to **20 MB**. For files > 20 MB (up to 2,000 MB), you must host your own [Local Bot API Server](https://core.telegram.org/bots/api#using-a-local-bot-api-server).
- **Expiration**: `file_path` is guaranteed valid for at least **1 hour**. Do not cache `file_path`; call `getFile` afresh or store the downloaded file in your own S3/storage.
- **`file_id` vs `file_unique_id`**:
  - `file_id`: Can be used to download or re-send the file. Unique per bot token (two different bots will see different `file_id` strings for the same file).
  - `file_unique_id`: Consistent across all bot tokens. Cannot be used to download, but ideal for database deduplication, caching, and idempotency checks.

---

## 4. Outgoing Media API Call Shapes

### 4.1. Sending a Sticker (`sendSticker`)

#### Option A: By `file_id` (JSON)
```http
POST https://api.telegram.org/bot<token>/sendSticker
Content-Type: application/json

{
  "chat_id": 123456789,
  "sticker": "CAACAgIAAxkBAAI...",
  "emoji": "🎉"
}
```

#### Option B: Uploading New Sticker File (`multipart/form-data`)
```http
POST https://api.telegram.org/bot<token>/sendSticker
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="chat_id"

123456789
------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="sticker"; filename="sticker.webp"
Content-Type: image/webp

<binary bytes>
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

---

### 4.2. Sending Media Group Album with Mixed Attachments
When uploading multiple new files in `sendMediaGroup`, use the `attach://<field_name>` referencing pattern:

```http
POST https://api.telegram.org/bot<token>/sendMediaGroup
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="chat_id"

123456789
------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="media"

[
  {
    "type": "photo",
    "media": "attach://photo_upload_1",
    "caption": "First slide"
  },
  {
    "type": "photo",
    "media": "attach://photo_upload_2",
    "caption": "Second slide"
  }
]
------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="photo_upload_1"; filename="cover.jpg"
Content-Type: image/jpeg

<binary bytes for photo 1>
------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="photo_upload_2"; filename="diagram.png"
Content-Type: image/png

<binary bytes for photo 2>
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```
---

## 5. Service Messages, Chat Backgrounds, Giveaways & Event Payloads

```typescript
interface LocationAddress {
  country_code: string;
  state?: string;
  city?: string;
  street_line1?: string;
  street_line2?: string;
  postal_code?: string;
}

interface MessageId { message_id: number; }
interface InaccessibleMessage { chat: Chat; message_id: 0; date: 0; }
interface DirectMessagesTopic { topic_id: number; title: string; }

interface ChatBackground {
  type: BackgroundType;
}

type BackgroundType =
  | BackgroundTypeFill
  | BackgroundTypeWallpaper
  | BackgroundTypePattern
  | BackgroundTypeChatTheme;

interface BackgroundTypeFill { type: 'fill'; fill: BackgroundFill; dark_theme_dimming: number; }
interface BackgroundTypeWallpaper { type: 'wallpaper'; document: Document; dark_theme_dimming: number; is_blurred?: boolean; is_moving?: boolean; }
interface BackgroundTypePattern { type: 'pattern'; document: Document; fill: BackgroundFill; intensity: number; is_inverted?: boolean; is_moving?: boolean; }
interface BackgroundTypeChatTheme { type: 'chat_theme'; theme_name: string; }

type BackgroundFill = BackgroundFillSolid | BackgroundFillGradient | BackgroundFillFreeformGradient;
interface BackgroundFillSolid { type: 'solid'; color: number; }
interface BackgroundFillGradient { type: 'gradient'; top_color: number; bottom_color: number; rotation_angle: number; }
interface BackgroundFillFreeformGradient { type: 'freeform_gradient'; colors: number[]; }

// Event & Service Message Updates
interface ProximityAlertTriggered { traveler: User; watcher: User; distance: number; }
interface MessageAutoDeleteTimerChanged { message_auto_delete_time: number; }
interface PollOptionAdded { poll_id: string; option_id: string; text: string; }
interface PollOptionDeleted { poll_id: string; option_id: string; }
interface ChatBoostAdded { boost_count: number; }
interface WriteAccessAllowed { from_request?: boolean; web_app_name?: string; from_attachment_menu?: boolean; }

// Video Chat Service Events
interface VideoChatScheduled { start_date: number; }
interface VideoChatStarted { /* Emitted when live video chat starts */ }
interface VideoChatEnded { duration: number; }
interface VideoChatParticipantsInvited { users: User[]; }

// Paid & Direct Messaging Price Updates
interface PaidMessagePriceChanged { star_count: number; }
interface DirectMessagePriceChanged { star_count: number; }

// Telegram Premium Giveaways
interface GiveawayCreated { prize_star_count?: number; }
interface Giveaway { chats: Chat[]; winners_selection_date: number; winner_count: number; only_new_members?: boolean; prize_star_count?: number; }
interface GiveawayWinners { chat: Chat; giveaway_message_id: number; winners_selection_date: number; winner_count: number; winners: User[]; }
interface GiveawayCompleted { winner_count: number; unclaimed_prize_count?: number; giveaway_message?: Message; }

interface SentWebAppMessage { inline_message_id?: string; }
interface ResponseParameters { migrate_to_chat_id?: number; retry_after?: number; }
```
