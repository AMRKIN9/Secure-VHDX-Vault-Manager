import os
import json
import time
import base64
import hashlib
import hmac
import struct
import secrets
from typing import Optional, Tuple
import logging

CONFIG_DIR = os.path.join(os.environ.get("USERPROFILE", "."), "SecureContainers")
CONFIG_FILE = os.path.join(CONFIG_DIR, ".vault_security.json")

def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)

class SecurityManager:
    """Manages RFC 6238 TOTP Two-Factor Authentication and Security Config."""
    
    def __init__(self):
        ensure_config_dir()
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load security config: {e}")
        return {
            "2fa_enabled": False,
            "totp_secret": None,
            "require_2fa_on_start": False,
            "require_2fa_for_decrypt": True,
            "require_2fa_for_delete": True,
            "custom_vault_dir": CONFIG_DIR
        }

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save security config: {e}")

    @staticmethod
    def generate_secret() -> str:
        """Generates a standard 32-character Base32 secret for TOTP."""
        random_bytes = secrets.token_bytes(20)
        return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")

    @staticmethod
    def get_totp_uri(secret: str, account_name: str = "VaultAdmin", issuer: str = "SecureVHDX") -> str:
        """Returns standard otpauth URI compatible with Google/MS Authenticator."""
        return f"otpauth://totp/{issuer}:{account_name}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"

    @staticmethod
    def get_current_token(secret: str, time_step_offset: int = 0) -> str:
        """Generates 6-digit TOTP token using RFC 6238."""
        if not secret:
            return ""
        pad = '=' * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(secret + pad, casefold=True)
        intervals = int(time.time() // 30) + time_step_offset
        msg = struct.pack(">Q", intervals)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        offset = digest[19] & 15
        binary = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000
        return f"{binary:06d}"

    def verify_token(self, token: str, secret: Optional[str] = None) -> bool:
        """Verifies code with +-1 time-step window (90 second drift tolerance)."""
        sec = secret or self.config.get("totp_secret")
        if not sec:
            return False
        clean_token = token.strip().replace(" ", "").replace("-", "")
        if not (clean_token.isdigit() and len(clean_token) == 6):
            return False
        for offset in (-1, 0, 1):
            if self.get_current_token(sec, offset) == clean_token:
                return True
        return False

    def enable_2fa(self, secret: str, verification_token: str) -> bool:
        """Enables 2FA if verification token matches."""
        if self.verify_token(verification_token, secret):
            self.config["2fa_enabled"] = True
            self.config["totp_secret"] = secret
            self.save_config()
            return True
        return False

    def disable_2fa(self, verification_token: str) -> bool:
        """Disables 2FA if verification token matches."""
        if self.verify_token(verification_token):
            self.config["2fa_enabled"] = False
            self.config["totp_secret"] = None
            self.save_config()
            return True
        return False

    def is_2fa_enabled(self) -> bool:
        return bool(self.config.get("2fa_enabled") and self.config.get("totp_secret"))

    def get_secret(self) -> Optional[str]:
        return self.config.get("totp_secret")

    def generate_qr_image(self, uri: str, size: int = 260):
        """Generates a PIL Image of the QR code with high-contrast Nothing aesthetic."""
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(uri)
            qr.make(fit=True)
            # High-contrast monochrome: Black code on white or crisp inverse
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            return img.resize((size, size))
        except Exception as e:
            logging.error(f"QR code generation failed: {e}")
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (size, size), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((20, size // 2 - 10), "QR Engine Unavailable\nUse Key Below", fill=(0, 0, 0))
            return img
