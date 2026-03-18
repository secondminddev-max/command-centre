"""
Secure Credential Vault Helper
Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
Key stored at vault.key (chmod 600), entries in vault.json.
"""

import json
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet

_BASE = Path(__file__).parent
_KEY_FILE = _BASE / "vault.key"
_VAULT_FILE = _BASE / "vault.json"


def _load_key() -> Fernet:
    if not _KEY_FILE.exists():
        raise FileNotFoundError(f"Vault key not found: {_KEY_FILE}")
    key = _KEY_FILE.read_bytes().strip()
    return Fernet(key)


def _load_vault() -> dict:
    if not _VAULT_FILE.exists():
        return {}
    with open(_VAULT_FILE) as f:
        return json.load(f)


def _save_vault(data: dict) -> None:
    with open(_VAULT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_secret(service: str, field: str) -> str:
    """Decrypt and return a plaintext value from the vault."""
    fernet = _load_key()
    vault = _load_vault()
    entry = vault.get(service)
    if entry is None:
        raise KeyError(f"Service '{service}' not found in vault")
    encrypted = entry.get(field)
    if encrypted is None:
        raise KeyError(f"Field '{field}' not found for service '{service}'")
    return fernet.decrypt(encrypted.encode()).decode()


def set_secret(service: str, field: str, value: str) -> None:
    """Encrypt a value and persist it to vault.json."""
    fernet = _load_key()
    vault = _load_vault()
    if service not in vault:
        vault[service] = {}
    vault[service][field] = fernet.encrypt(value.encode()).decode()
    _save_vault(vault)


def list_services() -> list:
    """Return all service names currently in the vault."""
    return list(_load_vault().keys())
