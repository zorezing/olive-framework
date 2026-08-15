import requests


class OllamaClient:
    """Small client for the local Ollama HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 1800,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_available(self, health_timeout: float = 3.0) -> bool:
        """Quick reachability check, independent of the (long) chat timeout."""

        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=health_timeout
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def chat(
        self,
        model: str,
        system: str,
        prompt: str,
        json_mode: bool = True,
    ) -> str:
        """Send a chat completion request.

        ``json_mode`` requests Ollama's grammar-constrained JSON output
        (``format: "json"``). This is reliable for well-behaved models,
        but was observed live to make deepseek-r1:8b dramatically slower
        (or not respond within an hour at all) -- the constrained decoder
        appears to fight the model's own <think> reasoning tokens, which
        don't fit a strict JSON grammar. Callers with their own robust
        extraction (see olive.workflow.planner_output) can set this to
        False and let the model think freely.
        """

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
        }

        if json_mode:
            payload["format"] = "json"

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        try:
            return data["message"]["content"]
        except KeyError as exc:
            raise RuntimeError(
                "Ollama returned an unexpected response."
            ) from exc
