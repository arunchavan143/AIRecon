from .subfinder import Subfinder
from .httpx_toolkit import HttpxToolkit

def run_full_pipeline(domain: str) -> list[dict]:
    subdomains = Subfinder().run(domain)
    if not subdomains:
        return []
    return HttpxToolkit().run(subdomains)

if __name__ == "__main__":
    results = run_full_pipeline("hackerone.com")
    for r in results:
        print(r)
