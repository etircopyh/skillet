# Telegram Mini Apps (TMA) & WebApp Verification

This reference details the Telegram Mini Apps (TMA) architecture, launch points, cryptographic backend verification of `initData` (HMAC-SHA256), and viewport/native UI controls.

---

## 1. Mini App Launch Points

Mini Apps can be opened through four distinct mechanisms:

1. **Inline Button**: `InlineKeyboardButton` with `web_app: { "url": "https://..." }`
2. **Keyboard Button**: `KeyboardButton` with `web_app: { "url": "https://..." }`
3. **Menu Button**: `setChatMenuButton` configured as `MenuButtonWebApp`
4. **Direct Link**: `https://t.me/botusername/appname?startapp=command_payload`

---

## 2. Server-Side `initData` Cryptographic Verification

When a Mini App opens, Telegram injects `window.Telegram.WebApp.initData` (a URL-encoded query string containing user info, chat info, `auth_date`, and `hash`).

**Security Gate**: Never trust `initData` on your backend without verifying the HMAC-SHA256 signature against your `BOT_TOKEN`.

### Verification Algorithm
1. Parse `initData` query string into key-value pairs.
2. Extract and remove the `hash` field.
3. Sort all remaining key-value pairs alphabetically by key.
4. Format sorted pairs as `key=value` joined by `\n` (`data_check_string`).
5. Compute HMAC-SHA256 signature using the string `"WebAppData"` as key and `BOT_TOKEN` as data:
   `secret_key = HMAC_SHA256(key="WebAppData", data=BOT_TOKEN)`
6. Compute HMAC-SHA256 hex digest of `data_check_string` using `secret_key`:
   `calculated_hash = HMAC_SHA256_HEX(key=secret_key, data=data_check_string)`
7. Compare `calculated_hash` with incoming `hash` using **timing-safe comparison**.
8. Verify `auth_date` is not expired (e.g. within 24 hours / 86400 seconds).

---

### Reference Implementation: TypeScript / Node.js
```typescript
import crypto from 'node:crypto';

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
}

export function verifyTelegramInitData(
  rawInitData: string,
  botToken: string,
  maxAgeSeconds = 86400
): { isValid: boolean; user?: TelegramUser } {
  const urlParams = new URLSearchParams(rawInitData);
  const hash = urlParams.get('hash');
  if (!hash) return { isValid: false };

  urlParams.delete('hash');

  // Sort and build data_check_string
  const params: string[] = [];
  Array.from(urlParams.keys())
    .sort()
    .forEach((key) => {
      params.push(`${key}=${urlParams.get(key)}`);
    });
  const dataCheckString = params.join('\n');

  // Compute secret key: HMAC-SHA256("WebAppData", botToken)
  const secretKey = crypto
    .createHmac('sha256', 'WebAppData')
    .update(botToken)
    .digest();

  // Compute expected hash: HMAC-SHA256(secretKey, dataCheckString)
  const expectedHash = crypto
    .createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');

  // Constant-time comparison
  const isValid = crypto.timingSafeEqual(
    Buffer.from(expectedHash, 'hex'),
    Buffer.from(hash, 'hex')
  );

  if (!isValid) return { isValid: false };

  // Validate auth_date freshness
  const authDate = Number(urlParams.get('auth_date') || 0);
  const now = Math.floor(Date.now() / 1000);
  if (now - authDate > maxAgeSeconds) {
    return { isValid: false }; // Expired session
  }

  const rawUser = urlParams.get('user');
  const user: TelegramUser | undefined = rawUser ? JSON.parse(rawUser) : undefined;

  return { isValid: true, user };
}
```

---

### Reference Implementation: Python
```python
import hmac
import hashlib
import json
import time
from urllib.parse import parse_qsl

def verify_telegram_init_data(raw_init_data: str, bot_token: str, max_age_seconds: int = 86400) -> tuple[bool, dict | None]:
    parsed_data = dict(parse_qsl(raw_init_data, keep_blank_values=True))
    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        return False, None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
    
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return False, None

    auth_date = int(parsed_data.get("auth_date", 0))
    if time.time() - auth_date > max_age_seconds:
        return False, None

    user = json.loads(parsed_data["user"]) if "user" in parsed_data else None
    return True, user
```

---

## 3. Native UI & Screen Controls

Telegram Mini Apps provide native integration APIs on the `window.Telegram.WebApp` object:

### Viewport & Screen Management
- `WebApp.requestFullscreen()`: Opens app in immersive fullscreen mode (Bot API 8.0+).
- `WebApp.exitFullscreen()`: Returns to standard modal view.
- `WebApp.lockOrientation('portrait' | 'landscape')`: Locks device orientation.
- `WebApp.safeAreaInset` & `WebApp.contentSafeAreaInset`: Returns top, right, bottom, left padding to avoid device notches and navigation bars.

### Native UI Components
- **`WebApp.MainButton`**: Bottom action button (e.g. `MainButton.setText("Submit").show()`).
- **`WebApp.SecondaryButton`**: Supplemental action button adjacent to the Main Button.
- **`WebApp.BackButton`**: Native header back button (`BackButton.show()`, `BackButton.onClick(...)`).
- **`WebApp.HapticFeedback`**: Trigger vibration patterns (`impactOccurred('light'|'medium'|'heavy')`, `notificationOccurred('success'|'error')`).
- **`WebApp.CloudStorage`**: Key-value cloud storage synced across user devices.
- **`WebApp.BiometricManager`**: Biometric authentication (Face ID / Touch ID / Fingerprint).

---

## 4. Closing & Sending Data Back

| Trigger Mechanism | How to Return Data | Notes |
| :--- | :--- | :--- |
| **Opened via `KeyboardButton` (Reply Keyboard)** | `Telegram.WebApp.sendData(string)` | Sends `web_app_data` to bot. Closes Mini App. **Only works for Reply Keyboard buttons.** |
| **Opened via `InlineKeyboardButton` (Inline Query)** | `bot.answerWebAppQuery(web_app_query_id, result)` | Injects an inline message into the chat on behalf of the user. |
| **Opened via Direct Link / Menu Button** | Direct standard HTTPS API request from TMA frontend to backend | Authenticate via `initData` in `Authorization: tma <rawInitData>` header. |

---

## 5. Prepared Messages & User Status Integration

### 5.1. Prepared Inline Messages (`savePreparedInlineMessage`)
Allows a Mini App to pre-stage an inline message on the server, returning a `PreparedInlineMessage` ID (`id`, `expiration_date`) that the client can prompt the user to send into any chat:

```http
POST https://api.telegram.org/bot<token>/savePreparedInlineMessage
Content-Type: application/json

{
  "user_id": 123456789,
  "result": {
    "type": "article",
    "id": "match_invite_1",
    "title": "Join My Multiplayer Game",
    "input_message_content": {
      "message_text": "🎮 I challenge you to a match!"
    }
  },
  "allow_user_chats": true,
  "allow_group_chats": true
}
```

### 5.2. Prepared Keyboard Buttons (`savePreparedKeyboardButton`)
Prepares custom keyboard requests (e.g. requesting users or chats) from within a Mini App session.

### 5.3. Managing User Emoji Status (`setUserEmojiStatus`)
When a user grants the bot permission via `WebApp.requestEmojiStatusAccess()`:

```http
POST https://api.telegram.org/bot<token>/setUserEmojiStatus
Content-Type: application/json

{
  "user_id": 123456789,
  "emoji_status_custom_emoji_id": "5368324170671202286",
  "emoji_status_expiration_date": 1712880000
}
```
*Pass an empty string `""` to remove the emoji status.*

