from __future__ import annotations

import hmac
import os
from hashlib import sha256


def load_key() -> bytes:
    env = os.environ.get("TIMING_ATTACKS_KEY_HEX")
    if env:
        return bytes.fromhex(env)
    return sha256(b"timing-attacks-demo-key").digest()


def hmac_sha256_tag(key: bytes, message: bytes) -> bytes:
    return hmac.new(key, message, sha256).digest()


def parse_tag_hex(tag_hex: str) -> bytes:
    tag_hex = (tag_hex or "").strip().lower()
    if tag_hex.startswith("0x"):
        tag_hex = tag_hex[2:]
    if len(tag_hex) % 2 != 0:
        raise ValueError("tag_hex must have even length")
    return bytes.fromhex(tag_hex)
