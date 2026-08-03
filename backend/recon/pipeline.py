from .subfinder import Subfinder
from .httpx_toolkit import HttpxToolkit
from .katana import Katana
import os

def run_full_pipeline(domain: str) -> dict:
    # Default to 180s, configurable via TIMEOUT env var
    timeout = int(os.environ.get("TIMEOUT", 180))
    
    subdomains = Subfinder().run(domain, timeout=timeout)
    if not subdomains:
        return {"hosts": [], "urls": []}
        
    hosts = HttpxToolkit().run(subdomains, timeout=timeout)
    
    alive_hostnames = [h["hostname"] for h in hosts if h.get("alive", True) or h.get("status_code")]
    if not alive_hostnames:
        alive_hostnames = subdomains  # fallback just in case
        
    urls = Katana().run(alive_hostnames, timeout=timeout)
    
    return {"hosts": hosts, "urls": urls}

if __name__ == "__main__":
    results = run_full_pipeline("hackerone.com")
    for r in results:
        print(r)
