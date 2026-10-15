"""Checks for metadata hashing used by clean-clone verification."""

from scripts.validate_experiment_outputs import sha256


class ByteSource:
    def __init__(self, payload: bytes):
        self.payload = payload

    def read_bytes(self) -> bytes:
        return self.payload


def test_text_hash_ignores_platform_line_endings():
    lf_file = ByteSource(b"first\nsecond\n")
    crlf_file = ByteSource(b"first\r\nsecond\r\n")

    assert sha256(lf_file, text=True) == sha256(crlf_file, text=True)
    assert sha256(lf_file) != sha256(crlf_file)
