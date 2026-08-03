import re

# Defensively strip markdown link syntax if present: e.g. [www.example.com](https://www.example.com)
md_link_pattern = re.compile(r'^\[(.*?)\]\(.*?\)$')

# Basic valid hostname pattern (no spaces, no weird characters)
valid_hostname_pattern = re.compile(r'^[a-zA-Z0-9.-]+$')

def clean_hostname(raw_hostname: str) -> str | None:
    """
    Strips markdown formatting if present and validates the resulting hostname.
    Returns the clean hostname if valid, or None if malformed/invalid.
    """
    if not raw_hostname:
        return None
        
    line = raw_hostname.strip()
    if not line:
        return None
        
    match = md_link_pattern.match(line)
    if match:
        line = match.group(1).strip()
        
    if valid_hostname_pattern.match(line):
        return line
        
    return None
