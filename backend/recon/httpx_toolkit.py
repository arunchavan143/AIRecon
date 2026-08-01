import subprocess
import shutil
import json
import logging
from .base import HTTPProbeTool

class HttpxToolkit(HTTPProbeTool):
    def run(self, hostnames: list[str], timeout: int = 60) -> list[dict]:
        """
        Takes a list of hostnames (e.g. output of run_subfinder), pipes them into httpx-toolkit,
        and returns structured results.
        Uses: httpx-toolkit -silent -json -tech-detect -status-code -title
        Input is piped via stdin (echo hostnames joined by newlines into httpx-toolkit's stdin),
        not passed as CLI args.
        """
        if not hostnames:
            return []

        cmd = ["httpx-toolkit", "-silent", "-json", "-tech-detect", "-status-code", "-title"]
        
        if not shutil.which("httpx-toolkit"):
            raise RuntimeError("httpx-toolkit not found - ensure it's installed and on PATH")
            
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
            raise RuntimeError("httpx-toolkit not found - ensure it's installed and on PATH")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"httpx-toolkit command timed out after {timeout} seconds")
            
        if result.returncode != 0:
            raise RuntimeError(f"httpx-toolkit failed with exit code {result.returncode}. Stderr: {result.stderr}")
            
        results = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                hostname = data.get("input") or data.get("host") or ""
                
                # Extract IP: Based on httpx JSON schema, the resolved IPs are usually in the 'a' array (A records).
                # Some versions might provide an 'ip' string field. 
                # We check both. Note: this requires manual verification on the Kali VM since we cannot run it locally.
                a_records = data.get("a", [])
                ip = data.get("ip") or (a_records[0] if isinstance(a_records, list) and a_records else "")
                
                status_code = data.get("status_code")
                title = data.get("title", "")
                tech = data.get("tech", [])
                server = data.get("webserver") or data.get("header", {}).get("server", "")
                
                clean_result = {
                    "hostname": hostname,
                    "ip": ip,
                    "status_code": status_code,
                    "title": title,
                    "tech": tech,
                    "server": server
                }
                results.append(clean_result)
            except json.JSONDecodeError:
                logging.warning(f"Failed to parse httpx-toolkit output line as JSON: {line}")
                
        return results
