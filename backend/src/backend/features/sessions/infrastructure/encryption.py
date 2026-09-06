import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class AuthenticationStateCipher:
    """Encrypt authentication state at the persistence boundary."""

    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode("ascii"))
        except (UnicodeEncodeError, ValueError) as error:
            raise ValueError(
                "BACKEND_AUTHENTICATION_STATE_ENCRYPTION_KEY must be a Fernet key"
            ) from error

    def encrypt(self, state: dict[str, Any]) -> bytes:
        plaintext = json.dumps(
            state,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return self._fernet.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> dict[str, Any]:
        try:
            plaintext = self._fernet.decrypt(ciphertext)
        except InvalidToken as error:
            raise ValueError("Authentication state could not be decrypted") from error
        state = json.loads(plaintext)
        if not isinstance(state, dict):
            raise ValueError("Decrypted authentication state is not an object")
        return state
