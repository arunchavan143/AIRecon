from .subfinder import Subfinder
from .httpx_toolkit import HttpxToolkit

import os

def run_full_pipeline(domain: str) -> list[dict]:
    # Default to 180s, configurable via TIMEOUT env var
    timeout = int(os.environ.get("TIMEOUT", 180))
    
    subdomains = Subfinder().run(domain, timeout=timeout)
    if not subdomains:
        return []
    return HttpxToolkit().run(subdomains, timeout=timeout)

if __name__ == "__main__":
    results = run_full_pipeline("hackerone.com")
    for r in results:
        print(r)
