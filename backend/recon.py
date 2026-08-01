import subprocess
import shutil
import json
import logging

def run_subfinder(domain: str, timeout: int = 60) -> list[str]:
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
    subdomains = [line.strip() for line in lines if line.strip()]
    
    return subdomains

def run_httpx(hostnames: list[str], timeout: int = 60) -> list[dict]:
    """
    Takes a list of hostnames (e.g. output of run_subfinder), pipes them into httpx,
    and returns structured results.
    Uses: httpx -silent -json -tech-detect -status-code -title
    Input is piped via stdin (echo hostnames joined by newlines into httpx's stdin),
    not passed as CLI args.
    """
    if not hostnames:
        return []

    cmd = ["httpx", "-silent", "-json", "-tech-detect", "-status-code", "-title"]
    
    if not shutil.which("httpx"):
        raise RuntimeError("httpx not found - ensure it's installed and on PATH")
        
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
        raise RuntimeError("httpx not found - ensure it's installed and on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"httpx command timed out after {timeout} seconds")
        
    if result.returncode != 0:
        raise RuntimeError(f"httpx failed with exit code {result.returncode}. Stderr: {result.stderr}")
        
    results = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            hostname = data.get("input") or data.get("host") or ""
            ip = data.get("host") or ""
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
            logging.warning(f"Failed to parse httpx output line as JSON: {line}")
            
    return results

if __name__ == "__main__":
    print("Running subfinder test on hackerone.com...")
    try:
        subdomains = run_subfinder("hackerone.com")
        print(f"Found {len(subdomains)} subdomains. Here are the first 10:")
        for r in subdomains[:10]:
            print(r)
            
        print("\nRunning httpx on discovered subdomains...")
        results = run_httpx(subdomains)
        print(f"Httpx found {len(results)} active endpoints. Here are the first 5:")
        for res in results[:5]:
            print(res)
    except Exception as e:
        print(f"Error: {e}")
