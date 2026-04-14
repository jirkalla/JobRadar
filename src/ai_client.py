"""AI provider abstraction layer for JobRadar.

All AI calls in the entire project go through this file.
No other file may import google.generativeai, anthropic, or openai directly.

Provider SDKs are imported inside each class __init__ so that a missing
unneeded SDK does not break the whole file.
"""

import json
import os
import re


class GeminiClient:
    """Wraps google.generativeai for use via the common interface."""

    def __init__(self, model: str, api_key: str) -> None:
        """Initialise the Gemini client and configure the API key.

        Args:
            model: Model name (e.g. 'gemini-1.5-flash').
            api_key: Gemini API key read from environment.
        """
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ImportError(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai==0.8.3"
            ) from exc

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)

    def complete(self, prompt: str) -> str:
        """Send a prompt and return the response text."""
        response = self._model.generate_content(prompt)
        return response.text


class ClaudeClient:
    """Wraps the Anthropic SDK for use via the common interface."""

    def __init__(self, model: str, api_key: str) -> None:
        """Initialise the Anthropic client.

        Args:
            model: Model name (e.g. 'claude-3-5-sonnet-20241022').
            api_key: Anthropic API key read from environment.
        """
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic is not installed. "
                "Run: pip install anthropic==0.40.0"
            ) from exc

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, prompt: str) -> str:
        """Send a prompt and return the response text."""
        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


class OpenAIClient:
    """Wraps the OpenAI SDK for use via the common interface."""

    def __init__(self, model: str, api_key: str) -> None:
        """Initialise the OpenAI client.

        Args:
            model: Model name (e.g. 'gpt-4o').
            api_key: OpenAI API key read from environment.
        """
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "openai is not installed. "
                "Run: pip install openai==1.57.0"
            ) from exc

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def complete(self, prompt: str) -> str:
        """Send a prompt and return the response text."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content


type AnyClient = GeminiClient | ClaudeClient | OpenAIClient


def get_client(config: dict) -> AnyClient:
    """Build and return the correct AI client from config.

    Reads config['ai']['provider'], config['ai']['model'], and
    config['ai']['api_key_env']. The API key is read from the environment
    variable named by api_key_env — never from the config file itself.

    Args:
        config: Loaded profile.yaml dict.

    Raises:
        EnvironmentError: If the API key environment variable is not set.
        ValueError: If the provider name is not recognised.
    """
    ai_cfg = config["ai"]
    provider: str = ai_cfg["provider"]
    model: str = ai_cfg["model"]
    key_env: str = ai_cfg["api_key_env"]

    api_key = os.environ.get(key_env)
    if not api_key:
        raise EnvironmentError(
            f"API key not found. Set environment variable: {key_env}\n"
            f"Windows CMD:        set {key_env}=your_key_here\n"
            f"PowerShell:         $env:{key_env}='your_key_here'"
        )

    match provider:
        case "gemini":
            return GeminiClient(model, api_key)
        case "claude":
            return ClaudeClient(model, api_key)
        case "openai":
            return OpenAIClient(model, api_key)
        case _:
            raise ValueError(
                f"Unknown AI provider: '{provider}'. "
                "Supported: gemini, claude, openai"
            )


def complete(client: AnyClient, prompt: str) -> str:
    """Call the provider and return the raw response text.

    Args:
        client: A client object returned by get_client().
        prompt: The full prompt string to send.
    """
    return client.complete(prompt)


def complete_json(client: AnyClient, prompt: str) -> dict:
    """Call the provider, strip markdown fences, and parse JSON.

    Args:
        client: A client object returned by get_client().
        prompt: The full prompt string to send.

    Raises:
        ValueError: If the response cannot be parsed as JSON,
                    with the first 200 chars of the raw response included.
    """
    raw = complete(client, prompt)
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract the outermost {...} block (handles preamble/postamble text)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    snippet = raw[:200]
    raise ValueError(
        f"AI response is not valid JSON.\n"
        f"Response snippet: {snippet!r}"
    )
