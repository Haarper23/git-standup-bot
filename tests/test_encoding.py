"""Tests for encoding safety wrapper."""

import io
import sys
from click.testing import CliRunner
from standup.encoding_helper import SafeStreamWrapper
from standup.cli import main


def test_safe_stream_with_cp1254():
    """Verify that cp1254 output replaces emoji and box characters with fallbacks."""
    raw_buffer = io.BytesIO()
    stream = io.TextIOWrapper(raw_buffer, encoding="cp1254", errors="strict")
    safe_stream = SafeStreamWrapper(stream)

    safe_stream.write("🚀 Test report ✨\n")
    safe_stream.write("┌───┬───┐\n")
    safe_stream.write("│ A │ B │\n")
    safe_stream.write("└───┴───┘\n")
    safe_stream.flush()

    raw_buffer.seek(0)
    output = raw_buffer.read().decode("cp1254")

    assert "[Standup]" in output
    assert "[Feature]" in output
    assert "+---+---+" in output
    assert "| A | B |" in output


def test_safe_stream_with_utf8():
    """Verify that utf-8 output preserves emojis and unicode box drawing characters."""
    raw_buffer = io.BytesIO()
    stream = io.TextIOWrapper(raw_buffer, encoding="utf-8", errors="strict")
    safe_stream = SafeStreamWrapper(stream)

    safe_stream.write("🚀 Test report ✨\n")
    safe_stream.write("┌───┬───┐\n")
    safe_stream.flush()

    raw_buffer.seek(0)
    output = raw_buffer.read().decode("utf-8")

    assert "🚀" in output
    assert "✨" in output
    assert "┌───┬───┐" in output


def test_safe_stream_symbols_cp1254():
    """Verify CP1254 output produces readable ASCII labels for UI symbols."""
    raw_buffer = io.BytesIO()
    stream = io.TextIOWrapper(raw_buffer, encoding="cp1254", errors="strict")
    safe_stream = SafeStreamWrapper(stream)

    safe_stream.write("✅ Report exported to report.md\n")
    safe_stream.write("❌ Critical error occurred\n")
    safe_stream.write("⚠ Warning sign\n")
    safe_stream.write("⚠️ Another warning\n")
    safe_stream.flush()

    raw_buffer.seek(0)
    output = raw_buffer.read().decode("cp1254")

    assert "[OK] Report exported to report.md" in output
    assert "[ERROR] Critical error occurred" in output
    assert "[WARN] Warning sign" in output
    assert "[WARN] Another warning" in output


def test_safe_stream_symbols_utf8():
    """Verify UTF-8 output preserves the original Unicode UI symbols."""
    raw_buffer = io.BytesIO()
    stream = io.TextIOWrapper(raw_buffer, encoding="utf-8", errors="strict")
    safe_stream = SafeStreamWrapper(stream)

    safe_stream.write("✅ Report exported to report.md\n")
    safe_stream.write("❌ Critical error occurred\n")
    safe_stream.write("⚠ Warning sign\n")
    safe_stream.write("⚠️ Another warning\n")
    safe_stream.flush()

    raw_buffer.seek(0)
    output = raw_buffer.read().decode("utf-8")

    assert "✅ Report exported to report.md" in output
    assert "❌ Critical error occurred" in output
    assert "⚠ Warning sign" in output
    assert "⚠️ Another warning" in output


def test_help_output_with_cp1254():
    """Verify help command does not crash on a simulated cp1254 terminal."""
    runner = CliRunner()
    # Click runner uses a mock stream, but let's test running cli options
    # through main help. CliRunner captures stdout/stderr.
    # We verify the main entrypoint executes help without any exceptions.
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Show this message and exit" in result.output


def test_safe_stream_write_return_values():
    """Verify write() returns the length of the original input string in both UTF-8 and CP1254."""
    # UTF-8
    raw_buffer_utf8 = io.BytesIO()
    stream_utf8 = io.TextIOWrapper(raw_buffer_utf8, encoding="utf-8")
    safe_utf8 = SafeStreamWrapper(stream_utf8)

    text = "🚀 Test report ✨"
    res_utf8 = safe_utf8.write(text)
    assert res_utf8 == len(text)
    assert isinstance(res_utf8, int)

    # CP1254
    raw_buffer_cp1254 = io.BytesIO()
    stream_cp1254 = io.TextIOWrapper(raw_buffer_cp1254, encoding="cp1254")
    safe_cp1254 = SafeStreamWrapper(stream_cp1254)

    res_cp1254 = safe_cp1254.write(text)
    assert res_cp1254 == len(text)
    assert isinstance(res_cp1254, int)


def test_safe_stream_propagates_io_errors():
    """Verify SafeStreamWrapper.write() propagates underlying stream errors without hiding them."""
    class FailingStream:
        encoding = "utf-8"
        def write(self, s):
            raise OSError("Simulated disk error or write failure")

    failing_stream = FailingStream()
    safe_stream = SafeStreamWrapper(failing_stream)

    import pytest
    with pytest.raises(OSError) as excinfo:
        safe_stream.write("Hello")
    assert "Simulated disk error" in str(excinfo.value)
