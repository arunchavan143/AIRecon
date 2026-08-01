from abc import ABC, abstractmethod

class SubdomainTool(ABC):
    """Any tool that takes a domain and returns a list of discovered subdomains."""
    @abstractmethod
    def run(self, domain: str, timeout: int = 60) -> list[str]:
        ...

class HTTPProbeTool(ABC):
    """Any tool that takes hostnames and returns structured alive-host data."""
    @abstractmethod
    def run(self, hostnames: list[str], timeout: int = 60) -> list[dict]:
        ...
