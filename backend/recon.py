import subprocess
import shutil

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

if __name__ == "__main__":
    print("Running subfinder test on hackerone.com...")
    try:
        results = run_subfinder("hackerone.com")
        print(f"Found {len(results)} subdomains. Here are the first 10:")
        for r in results[:10]:
            print(r)
    except Exception as e:
        print(f"Error: {e}")
