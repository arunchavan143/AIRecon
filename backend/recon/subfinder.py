import subprocess
import shutil
import re
import logging
from .base import SubdomainTool
from .sanitize import clean_hostname

class Subfinder(SubdomainTool):
    def run(self, domain: str, timeout: int = 60) -> list[str]:
        """
        Runs subfinder against the given domain, returns a list of discovered subdomains.
        Uses subprocess to call: subfinder -d <domain> -silent
        """
        # We must call it as 'subfinder' as requested
        cmd = ["subfinder", "-d", domain, "-silent"]
        
        # Pre-check if subfinder is in PATH to throw the specific error requested
        if not shutil.which("subfinder"):
            raise RuntimeError("subfinder not found - ensure it's installed and on PATH")
            
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        except FileNotFoundError:
            raise RuntimeError("subfinder not found - ensure it's installed and on PATH")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"subfinder command timed out after {timeout} seconds")
            
        if result.returncode != 0:
            raise RuntimeError(f"subfinder failed with exit code {result.returncode}. Stderr: {result.stderr}")
            
        lines = result.stdout.splitlines()
        subdomains = []
        
        for line in lines:
            cleaned = clean_hostname(line)
            if cleaned:
                subdomains.append(cleaned)
            else:
                logging.warning(f"Subfinder produced malformed/invalid hostname, skipping: {line.strip()}")
        
        return subdomains
