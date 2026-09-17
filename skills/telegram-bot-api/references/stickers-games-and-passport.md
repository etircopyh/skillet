# Stickers, Games & Telegram Passport

This reference details sticker set creation and management, the HTML5 Games platform, and Telegram Passport identity verification.

---

## 1. Sticker Sets Management API

Bots can dynamically create, update, and manage sticker packs on behalf of users.

### 1.1. Technical Format Requirements

| Format | Extension / Codec | Dimensions | Constraints |
| :--- | :--- | :--- | :--- |
| **Static** | `.webp` or `.png` | 512×512 (one side exactly 512px, other ≤ 512px) | Max **512 KB**; transparent background recommended. |
| **Animated** | `.tgs` (gzip-compressed Lottie JSON) | 512×512 square | Max **64 KB**; exactly 60 FPS; max **3 seconds** duration; must loop seamlessly. |
| **Video** | `.webm` (VP9 video codec) | 512×512 (one side 512px, other ≤ 512px) | Max **256 KB**; max 30 FPS; max **3 seconds**; **no audio stream**. |
| **Custom Emoji** | `.webp`, `.tgs`, or `.webm` | **100×100 square** | Max 512 KB (static) / 64 KB (animated) / 256 KB (video). |

---

### 1.2. Creating a Sticker Set (`createNewStickerSet`)

```http
POST https://api.telegram.org/bot<token>/createNewStickerSet
Content-Type: application/json

{
  "user_id": 123456789,
  "name": "dev_stickers_by_mybot",
  "title": "Developer Moods",
  "sticker_type": "regular",
  "stickers": [
    {
      "sticker": "CAACAgIAAxkBAAI...",
      "format": "static",
      "emoji_list": ["💻", "👨‍💻"],
      "keywords": ["code", "developer", "terminal"]
    }
  ]
}
```

### Critical Invariants
- **Naming Rule**: `name` must be 1–64 characters, contain only `a-z`, `0-9`, and `_`, and **MUST end with `_by_<bot_username>`** (e.g. `animals_by_samplebot`).
- **`user_id`**: The Telegram user ID who will be designated as the pack owner.
- **`sticker_type`**: `"regular"`, `"mask"`, or `"custom_emoji"` (default `"regular"`).
- **`stickers`**: Array of 1–50 `InputSticker` objects.

---

### 1.3. `InputSticker` Schema

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`sticker`** | `InputFile` or `String` | **Yes** | File uploaded via multipart `attach://<name>`, existing `file_id`, or public HTTP URL. |
| **`format`** | `String` | **Yes** | Format of sticker: `"static"`, `"animated"`, or `"video"`. |
| **`emoji_list`** | `String[]` | **Yes** | 1–20 emoji associated with this sticker. |
| **`mask_position`** | `MaskPosition` | No | Positioning metadata if `sticker_type == "mask"`. |
| **`keywords`** | `String[]` | No | Search keywords (up to 20 keywords, max 64 chars each). |

---

### 1.4. Sticker Set Mutation Methods

- **`addStickerToSet(user_id, name, sticker: InputSticker)`**: Appends a sticker to an existing pack.
- **`deleteStickerFromSet(sticker: file_id)`**: Deletes a sticker from a set.
- **`setStickerPositionInSet(sticker: file_id, position: Integer)`**: Moves sticker to a 0-indexed position.
- **`replaceStickerInSet(user_id, name, old_sticker, sticker: InputSticker)`**: Replaces an existing sticker with a new file.
- **`setStickerEmojiList(sticker: file_id, emoji_list: String[])`**: Updates associated emoji.
- **`setStickerKeywords(sticker: file_id, keywords: String[])`**: Updates search keywords.
- **`setStickerSetThumbnail(name, user_id, format, thumbnail)`**: Updates pack cover thumbnail.
- **`setCustomEmojiStickerSetThumbnail(name, custom_emoji_id)`**: Sets thumbnail from a custom emoji.
- **`deleteStickerSet(name)`**: Permanently deletes a sticker set created by the bot.

---

## 2. HTML5 Games Platform

Telegram bots can host interactive HTML5 games rendered inside client webviews with leaderboards.

### 2.1. Creating & Sending a Game
1. Register the game via [@BotFather](https://t.me/BotFather) (`/newgame`) to obtain a `game_short_name`.
2. Send the game message:

```http
POST https://api.telegram.org/bot<token>/sendGame
Content-Type: application/json

{
  "chat_id": 123456789,
  "game_short_name": "spacewar",
  "reply_markup": {
    "inline_keyboard": [
      [
        { "text": "🎮 Play SpaceWar", "callback_game": {} }
      ],
      [
        { "text": "🏆 Leaderboard", "callback_data": "leaderboard:spacewar" }
      ]
    ]
  }
}
```

- **`callback_game`**: Special placeholder object `{}`. It **must always be the first button in the first row**. Clicking it sends a `callback_query` with `game_short_name`.
- When the bot receives the game `callback_query`, call `answerCallbackQuery` with the `url` parameter pointing to the game URL:

```http
POST https://api.telegram.org/bot<token>/answerCallbackQuery
Content-Type: application/json

{
  "callback_query_id": "4382bf356aa1056",
  "url": "https://games.example.com/spacewar/?user=123456789&token=secure_jwt"
}
```

---

### 2.2. Setting & Reading High Scores

#### Setting High Score (`setGameScore`)
```http
POST https://api.telegram.org/bot<token>/setGameScore
Content-Type: application/json

{
  "user_id": 123456789,
  "score": 1540,
  "force": false,
  "chat_id": 123456789,
  "message_id": 405
}
```
- **`force`**: If `false`, will not allow score reduction.
- **`disable_edit_message`**: If `true`, the game message will not automatically update its leaderboard text.

#### Reading Leaderboard (`getGameHighScores`)
```http
POST https://api.telegram.org/bot<token>/getGameHighScores
Content-Type: application/json

{
  "user_id": 123456789,
  "chat_id": 123456789,
  "message_id": 405
}
```
*Returns an array of `GameHighScore` objects (`position`, `user`, `score`).*

---

## 3. Telegram Passport

Telegram Passport is a unified authorization method for services requiring real-world identity verification (KYC, financial apps).

### 3.1. Incoming `passport_data`
When a user authorizes data sharing, a `Message` arrives containing `passport_data`:

```json
{
  "message_id": 501,
  "chat": { "id": 123456789, "type": "private" },
  "passport_data": {
    "data": [
      {
        "type": "personal_details",
        "data": "base64_encrypted_payload...",
        "hash": "base64_sha256_hash..."
      },
      {
        "type": "passport",
        "front_side": {
          "file_id": "BQACAgI...",
          "file_date": 1711880000
        },
        "hash": "base64_sha256_hash..."
      }
    ],
    "credentials": {
      "data": "base64_encrypted_credentials...",
      "hash": "base64_hash...",
      "secret": "rsa_encrypted_secret..."
    }
  }
}
```

### 3.2. Decryption Workflow
1. Decrypt `credentials.secret` using your bot's private RSA-2048 key.
2. Derive AES key and IV from the decrypted secret and `credentials.hash`.
3. Decrypt `credentials.data` using AES-256-CBC.
4. Extract the per-element secret and IV from decrypted credentials to decrypt each `EncryptedPassportElement`.

---

### 3.3. Reporting Validation Errors (`setPassportDataErrors`)
If a submitted passport photo is blurred or details do not match:

```http
POST https://api.telegram.org/bot<token>/setPassportDataErrors
Content-Type: application/json

{
  "user_id": 123456789,
  "errors": [
    {
      "source": "file",
      "type": "passport",
      "file_hash": "base64_hash...",
      "message": "The passport photo is blurry. Please upload a clear photo in good lighting."
    }
  ]
}
```
*The user's Telegram client will highlight the affected field and prompt them to re-upload.*
---

## 4. Sticker Set Management & Passport Verification Schemas

### Sticker Management Methods
```typescript
getStickerSet(params: { name: string }): Promise<StickerSet>;
getCustomEmojiStickers(params: { custom_emoji_ids: string[] }): Promise<Sticker[]>;
uploadStickerFile(params: { user_id: number; sticker: InputFile; sticker_format: 'static' | 'animated' | 'video' }): Promise<File>;
setStickerMaskPosition(params: { sticker: string; mask_position?: MaskPosition }): Promise<boolean>;
setStickerSetTitle(params: { name: string; title: string }): Promise<boolean>;
```

### Telegram Passport Error Decryption Pipeline
```typescript
setPassportDataErrors(params: { user_id: number; errors: PassportElementError[] }): Promise<boolean>;

type PassportElementError =
  | PassportElementErrorDataField
  | PassportElementErrorFrontSide
  | PassportElementErrorReverseSide
  | PassportElementErrorSelfie
  | PassportElementErrorFile
  | PassportElementErrorFiles
  | PassportElementErrorTranslationFile
  | PassportElementErrorTranslationFiles
  | PassportElementErrorUnspecified;

interface PassportFile { file_id: string; file_unique_id: string; file_size: number; file_date: number; }
interface EncryptedCredentials { data: string; hash: string; secret: string; }
interface CallbackGame { /* Placeholder game callback context */ }

interface PassportElementErrorDataField { source: 'data'; type: string; field_name: string; data_hash: string; message: string; }
interface PassportElementErrorFrontSide { source: 'front_side'; type: string; file_hash: string; message: string; }
interface PassportElementErrorReverseSide { source: 'reverse_side'; type: string; file_hash: string; message: string; }
interface PassportElementErrorSelfie { source: 'selfie'; type: string; file_hash: string; message: string; }
interface PassportElementErrorFile { source: 'file'; type: string; file_hash: string; message: string; }
interface PassportElementErrorFiles { source: 'files'; type: string; file_hashes: string[]; message: string; }
interface PassportElementErrorTranslationFile { source: 'translation_file'; type: string; file_hash: string; message: string; }
interface PassportElementErrorTranslationFiles { source: 'translation_files'; type: string; file_hashes: string[]; message: string; }
interface PassportElementErrorUnspecified { source: 'unspecified'; type: string; element_hash: string; message: string; }
```
