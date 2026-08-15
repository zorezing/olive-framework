import requests


class OllamaClient:
    """Small client for the local Ollama HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
    ):
        self.base_url = base_url.rstrip("/")

    def chat(
        self,
        model: str,
        system: str,
        prompt: str,
    ) -> str:
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
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
                "format": "json",
            },
            timeout=600,
        )

        response.raise_for_status()

        data = response.json()

        try:
            return data["message"]["content"]
        except KeyError as exc:
            raise RuntimeError(
                "Ollama returned an unexpected response."
            ) from exc
