import requests


class OllamaClient:
    """Small client for the local Ollama HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 900,
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
        num_predict: int | None = None,
    ) -> str:
        """Send a chat completion request.

        ``json_mode`` requests Ollama's grammar-constrained JSON output
        (``format: "json"``). Ollama 0.32.6 correctly separates a
        reasoning model's <think> trace into a distinct ``thinking``
        field from the constrained ``content`` field (confirmed live with
        qwen3:8b), so this is *not* the source of reasoning-model
        slowness some earlier investigation suspected. Disabling it for
        deepseek-r1:8b specifically was tried and made things worse (a
        hard 500 from Ollama) -- leave this on unless you've verified
        otherwise for your model.

        ``num_predict`` caps the maximum number of tokens generated
        (Ollama's ``options.num_predict``), bounding worst-case latency.
        Reasoning models scale their <think> length with task difficulty
        and can otherwise run for a very long time on modest hardware --
        observed live with deepseek-r1:8b generating 335 tokens of
        reasoning for the prompt "ping" alone. Left unset (no cap) by
        default; callers doing anything latency-sensitive should set one.
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

        if num_predict is not None:
            payload["options"] = {"num_predict": num_predict}

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
