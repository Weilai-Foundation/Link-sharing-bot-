import base64
import re

def encode_channel_id(channel_id: int) -> str:
    return base64.urlsafe_b64encode(str(channel_id).encode()).decode()

def decode_channel_id(encoded: str) -> int:
    return int(base64.urlsafe_b64decode(encoded.encode()).decode())

def font_style(text: str) -> str:
    if not text:
        return text

    # Regex to match parts that should NOT be styled
    # 1. HTML tags: <...>
    # 2. Mentions: @username
    # 3. Commands: /start
    # 4. Placeholders: {mention}
    # 5. URLs: http://... or https://...
    pattern = r'(<[^>]+>|@[a-zA-Z0-9_]+|/[a-zA-Z0-9_]+|\{[a-zA-Z0-9_]+\}|https?://\S+)'

    parts = re.split(pattern, text)

    styled_parts = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # This part should be styled
            styled_part = ""
            for char in part:
                if 'A' <= char <= 'Z':
                    styled_part += chr(ord(char) - ord('A') + 0x1D5A0)
                elif 'a' <= char <= 'z':
                    styled_part += chr(ord(char) - ord('a') + 0x1D5BA)
                else:
                    styled_part += char
            styled_parts.append(styled_part)
        else:
            # This part should NOT be styled
            styled_parts.append(part)

    return "".join(styled_parts)
