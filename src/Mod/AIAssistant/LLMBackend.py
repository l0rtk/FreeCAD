# SPDX-License-Identifier: LGPL-2.1-or-later
"""
LLM Backend - Handles communication with AI services.
Supports Nakle API (default), with extensibility for other providers.
"""

import json
import time
import urllib.request
import urllib.error
import FreeCAD

# Default API endpoint (Nakle)
DEFAULT_API_URL = "http://20.64.149.209/chat/completions"
DEFAULT_MODEL = "sonnet"

SYSTEM_PROMPT = """You are a FreeCAD AI assistant that writes Python code to build 3D models from user requests.

RULES:
1. Return ONLY executable Python code - no markdown, no explanations
2. Always use: doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
3. Always end with doc.recompute()
4. Use millimeters for all dimensions (FreeCAD default)
5. Use descriptive object Labels

When CURRENT DOCUMENT STATE is provided, analyze existing objects and modify/add to them as requested.
Do NOT recreate existing elements."""


class LLMBackend:
    """Handles LLM API communication."""

    def __init__(self, api_url: str = None, model: str = None):
        self.api_url = api_url or self._get_pref("ApiUrl", DEFAULT_API_URL)
        self.model = model or self._get_pref("Model", DEFAULT_MODEL)

        # Debug info from last request (for session logging)
        self.last_system_prompt = ""
        self.last_context = ""
        self.last_conversation = []
        self.last_duration_ms = 0

    def _get_pref(self, key: str, default: str) -> str:
        """Get preference value."""
        try:
            return FreeCAD.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/AIAssistant"
            ).GetString(key, default)
        except Exception:
            return default

    def chat(self, user_message: str, context: str = "", history: list = None) -> str:
        """
        Send a message to the LLM and get a response.

        Args:
            user_message: The user's natural language request
            context: Optional document context string
            history: Optional conversation history

        Returns:
            Generated Python code as a string
        """
        # Build system prompt with context
        system = SYSTEM_PROMPT
        if context:
            system += f"\n\nCURRENT DOCUMENT STATE:\n{context}"

        # Store for debugging
        self.last_system_prompt = system
        self.last_context = context
        self.last_conversation = history[-6:] if history else []

        # Build messages array
        messages = [{"role": "system", "content": system}]

        # Add conversation history (last few exchanges)
        if history:
            messages.extend(history[-6:])  # Last 3 exchanges

        # Add current message
        messages.append({"role": "user", "content": user_message})

        # Make API request
        payload = {
            "model": self.model,
            "messages": messages,
            "timeout": 120
        }

        headers = {"Content-Type": "application/json"}

        start_time = time.time()
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.api_url, data=data, headers=headers)

            with urllib.request.urlopen(req, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
                self.last_duration_ms = (time.time() - start_time) * 1000
                return self._clean_response(result["choices"][0]["message"]["content"])

        except urllib.error.HTTPError as e:
            self.last_duration_ms = (time.time() - start_time) * 1000
            error_body = e.read().decode()[:200]
            FreeCAD.Console.PrintError(f"AIAssistant API Error: {e.code} - {error_body}\n")
            return f"# API Error {e.code}: {error_body}"

        except urllib.error.URLError as e:
            self.last_duration_ms = (time.time() - start_time) * 1000
            FreeCAD.Console.PrintError(f"AIAssistant Connection Error: {e.reason}\n")
            return f"# Connection Error: {e.reason}"

        except Exception as e:
            self.last_duration_ms = (time.time() - start_time) * 1000
            FreeCAD.Console.PrintError(f"AIAssistant Error: {e}\n")
            return f"# Error: {e}"

    def _clean_response(self, response: str) -> str:
        """Clean up the response - remove markdown code blocks if present."""
        response = response.strip()

        # Remove markdown code fences
        if response.startswith("```python"):
            response = response[9:]
        elif response.startswith("```"):
            response = response[3:]

        if response.endswith("```"):
            response = response[:-3]

        return response.strip()
