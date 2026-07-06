"""Helper module to handle terminal output sanitization for encodings like cp1254."""

from __future__ import annotations

import sys
import codecs

EMOJI_FALLBACKS = {
    # Emojis and other Unicode punctuation
    "🚀": "[Standup]",
    "📦": "[Repo]",
    "✨": "[Feature]",
    "🐛": "[Fix]",
    "📝": "[Docs]",
    "🎨": "[Style]",
    "♻️": "[Refactor]",
    "⚡": "[Perf]",
    "🧪": "[Test]",
    "🔧": "[CI/CD]",
    "🔨": "[Chore]",
    "⏪": "[Revert]",
    "📌": "[Other]",
    "🌿": "[Branch]",
    "🤖": "[AI]",
    "🕵️": "[Tech Lead]",
    "📋": "[Next Steps]",
    "—": "-",
    "–": "-",
    "✅": "[OK]",
    "❌": "[ERROR]",
    "⚠": "[WARN]",
    "⚠️": "[WARN]",
    "\ufe0f": "",
    # Horizontals
    "─": "-", "━": "-", "═": "=",
    # Verticals
    "│": "|", "┃": "|", "║": "|",
    # Corners / Intersections
    "┌": "+", "┐": "+", "└": "+", "┘": "+",
    "├": "+", "┤": "+", "┬": "+", "┴": "+", "┼": "+",
    "┏": "+", "┓": "+", "┗": "+", "┛": "+",
    "┣": "+", "┫": "+", "┳": "+", "┻": "+", "╋": "+",
    "┡": "+", "┧": "+", "┩": "+", "┪": "+",
    "╔": "+", "╦": "+", "╗": "+", "╠": "+", "╬": "+", "╣": "+", "╚": "+", "╩": "+", "╝": "+",
    "┯": "+", "┰": "+", "┱": "+", "┲": "+", "┵": "+", "┶": "+", "┷": "+", "┸": "+", "┹": "+", "┺": "+",
    "┠": "+", "┢": "+", "╀": "+", "╁": "+", "╂": "+", "╃": "+", "╄": "+", "╅": "+", "╆": "+", "╇": "+",
    "╈": "+", "╉": "+", "╊": "+", "┧": "+", "┨": "+",
}


def emoji_fallback_handler(error: UnicodeEncodeError) -> tuple[str, int]:
    """Codecs error handler that replaces unsupported chars with their ASCII fallbacks."""
    failing_str = error.object[error.start:error.end]
    replacement = "".join(EMOJI_FALLBACKS.get(c, "?") for c in failing_str)
    return (replacement, error.end)


# Register error handler if not already registered
try:
    codecs.lookup_error("emoji_fallback")
except LookupError:
    codecs.register_error("emoji_fallback", emoji_fallback_handler)


class SafeStreamWrapper:
    """Wraps output streams and sanitizes content for the active encoding."""

    def __init__(self, original_stream):
        self.original_stream = original_stream

    @property
    def encoding(self) -> str:
        """Get target stream encoding, defaulting to utf-8."""
        return self.original_stream.encoding or "utf-8"

    def write(self, s: str) -> int:
        """Write string to the target stream safely, replacing unsupported chars."""
        encoding = self.encoding
        # Encode using the custom codecs error handler, then decode back to string
        sanitized = s.encode(encoding, errors="emoji_fallback").decode(encoding)
        self.original_stream.write(sanitized)
        return len(s)

    def flush(self) -> None:
        """Flush the target stream."""
        self.original_stream.flush()

    def __getattr__(self, name):
        return getattr(self.original_stream, name)


def setup_safe_streams() -> None:
    """Wrap sys.stdout and sys.stderr in SafeStreamWrapper if they cannot encode emojis."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if stream is None:
            continue

        encoding = getattr(stream, "encoding", "utf-8") or "utf-8"
        try:
            "🚀".encode(encoding)
        except UnicodeEncodeError:
            # Wrap the stream in our safe boundary wrapper
            setattr(sys, stream_name, SafeStreamWrapper(stream))
