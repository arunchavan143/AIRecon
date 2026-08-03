import pytest
from recon.sanitize import clean_hostname

def test_markdown_wrapped_hostname():
    """Test that markdown-link-wrapped hostnames are correctly extracted and cleaned."""
    raw = "[www.example.com](https://www.example.com)"
    assert clean_hostname(raw) == "www.example.com"

def test_clean_hostname_passes_unchanged():
    """Test that a normally valid hostname passes through untouched."""
    raw = "api.staging.example.co.uk"
    assert clean_hostname(raw) == "api.staging.example.co.uk"

def test_invalid_characters_rejected():
    """Test that hostnames with invalid characters like spaces or symbols return None."""
    # Spaces inside
    assert clean_hostname("invalid domain.com") is None
    # Script injection or weird characters
    assert clean_hostname("<script>alert(1)</script>") is None
    # Just weird symbols
    assert clean_hostname("example!.com") is None

def test_empty_or_whitespace_rejected():
    """Test that empty or just whitespace inputs return None."""
    assert clean_hostname("") is None
    assert clean_hostname("   ") is None
    assert clean_hostname(None) is None
