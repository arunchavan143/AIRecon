import subprocess
import shutil
import logging
from urllib.parse import urlparse
from .base import URLDiscoveryTool

class Katana(URLDiscoveryTool):
    def run(self, hostnames: list[str], timeout: int = 120) -> list[dict]:
        """
        Takes a list of alive hostnames, runs katana against them to discover URLs.
        Uses: katana -silent -jc -d 2
        Input is piped via stdin, one hostname per line.
        Output is one URL per line in plain text.
        """
        if not hostnames:
            return []

        if not shutil.which("katana"):
            raise RuntimeError("katana not found - ensure it's installed and on PATH")

        cmd = ["katana", "-silent", "-jc", "-d", "2"]
        input_data = "\n".join(hostnames)
        
        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        except FileNotFoundError:
            raise RuntimeError("katana not found - ensure it's installed and on PATH")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"katana command timed out after {timeout} seconds")
            
        if result.returncode != 0:
            raise RuntimeError(f"katana failed with exit code {result.returncode}. Stderr: {result.stderr}")
            
        valid_hosts = {h.lower() for h in hostnames}
        results = []
        
        for line in result.stdout.splitlines():
            url = line.strip()
            if not url:
                continue
                
            try:
                parsed = urlparse(url)
                # urlparse('http://example.com:80').hostname returns 'example.com'
                url_host = parsed.hostname
                
                # Try exact match or match if katana somehow prepended www or something
                # We'll strictly match against the provided input hostnames.
                if url_host and url_host.lower() in valid_hosts:
                    results.append({
                        "hostname": url_host.lower(),
                        "url": url
                    })
                else:
                    # Some tools might drop the port or keep the port, but parsed.hostname handles ports cleanly.
                    logging.warning(f"Katana produced URL not matching any input hostname, skipping: {url}")
            except Exception as e:
                logging.warning(f"Failed to parse URL from katana: {url} - {e}")
                
        return results
