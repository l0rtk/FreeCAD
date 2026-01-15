# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Claude Code Backend - Uses Claude Code CLI in headless mode for LLM communication.

This backend replaces the HTTP API with subprocess calls to the Claude Code CLI,
giving access to richer context through file reading and project-specific CLAUDE.md.

Official documentation: https://code.claude.com/docs/en/headless
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional
import FreeCAD


# System prompt used when no project CLAUDE.md exists
FREECAD_SYSTEM_PROMPT = """You are a FreeCAD AI assistant helping design 3D models.

Response format:
- To CREATE/MODIFY objects: Return ONLY executable Python code (no markdown, no explanations)
- To ANSWER questions: Return clear text

Code rules:
- Use: doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Design")
- End with doc.recompute()
- Use millimeters for dimensions
- Use descriptive Labels
- Read .freecad_ai/source.py to understand existing objects
- Do NOT recreate existing elements
- Use object Names (not Labels) when referencing objects in code
- To delete: doc.removeObject('ObjectName')"""


class ClaudeCodeBackend:
    """LLM backend using Claude Code CLI in headless mode.

    Benefits over HTTP API:
    - Claude can read project files on-demand (source.py, snapshots/)
    - Project-specific CLAUDE.md for custom instructions
    - Session continuity via --resume
    - Tool access (Glob, Grep, Read) for intelligent context gathering
    """

    def __init__(self, project_dir: str = None):
        """Initialize the Claude Code backend.

        Args:
            project_dir: Working directory for Claude Code. If set, Claude will
                        load CLAUDE.md from this directory and can read project files.
        """
        self.project_dir = project_dir
        self._session_id: Optional[str] = None

        # Model identifier (matches LLMBackend interface)
        self.model = "claude-code"
        self.api_url = "claude-code-cli"  # Matches LLMBackend interface

        # Debug info (matches LLMBackend interface)
        self.last_duration_ms = 0
        self.last_cost = 0.0
        self.last_system_prompt = ""
        self.last_context = ""
        self.last_conversation = []

    def chat(
        self,
        user_message: str,
        context: str = "",
        history: list = None,
        screenshot: str = None,
    ) -> str:
        """Send message to Claude Code CLI and get response.

        Args:
            user_message: The user's natural language request
            context: Optional document context string (passed in prompt if no CLAUDE.md)
            history: Optional conversation history (not used - Claude Code manages sessions)
            screenshot: Optional base64-encoded PNG screenshot (saved to temp file)

        Returns:
            Generated response (Python code or text answer)
        """
        # Store for debugging
        self.last_context = context
        self.last_conversation = history[-6:] if history else []

        # Handle screenshot - save to temp file for Claude to read
        screenshot_path = None
        if screenshot:
            screenshot_path = self._save_screenshot(screenshot)

        # Build the prompt
        prompt = self._build_prompt(user_message, context, screenshot_path)

        # Build command
        cmd = ["claude", "-p", "--output-format", "json"]

        # Restrict to read-only tools for safety
        cmd.extend(["--allowedTools", "Read,Glob,Grep"])

        # Add system prompt if no project CLAUDE.md exists
        if not self._has_claude_md():
            cmd.extend(["--append-system-prompt", FREECAD_SYSTEM_PROMPT])
            self.last_system_prompt = FREECAD_SYSTEM_PROMPT
        else:
            self.last_system_prompt = "(Using project CLAUDE.md)"

        # Resume session if we have one (for multi-turn conversations)
        if self._session_id:
            cmd.extend(["--resume", self._session_id])

        # NOTE: Prompt is passed via stdin, not as command line argument
        # This avoids shell escaping issues with special characters

        # Set working directory to project folder
        cwd = self.project_dir or os.getcwd()

        FreeCAD.Console.PrintMessage(f"AIAssistant: Calling Claude Code in {cwd}\n")

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                input=prompt,  # Pass prompt via stdin
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=180,
                env={**os.environ}  # Inherit ANTHROPIC_API_KEY
            )

            self.last_duration_ms = (time.time() - start_time) * 1000

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                FreeCAD.Console.PrintError(f"AIAssistant: Claude Code error: {error_msg}\n")
                return f"# Error: {error_msg}"

            # Parse JSON response
            response_data = json.loads(result.stdout)

            # Check for error
            if response_data.get("is_error", False):
                error_msg = response_data.get("result", "Unknown error")
                FreeCAD.Console.PrintError(f"AIAssistant: Claude Code returned error: {error_msg}\n")
                return f"# Error: {error_msg}"

            # Store session ID for continuity
            if "session_id" in response_data:
                self._session_id = response_data["session_id"]

            # Track cost (handle multiple formats from different Claude Code versions)
            cost_data = response_data.get("cost", {})
            self.last_cost = (
                response_data.get("total_cost_usd")
                or cost_data.get("total_cost")
                or cost_data.get("total_cost_usd")
                or 0
            )

            # Get the response text
            response_text = response_data.get("result", "")

            FreeCAD.Console.PrintMessage(
                f"AIAssistant: Claude Code response received "
                f"({self.last_duration_ms:.0f}ms, ${self.last_cost:.4f})\n"
            )

            return self._clean_response(response_text)

        except subprocess.TimeoutExpired:
            self.last_duration_ms = (time.time() - start_time) * 1000
            FreeCAD.Console.PrintError("AIAssistant: Claude Code request timed out\n")
            return "# Error: Request timed out"

        except json.JSONDecodeError as e:
            FreeCAD.Console.PrintError(f"AIAssistant: Failed to parse Claude Code response: {e}\n")
            return f"# Error: Failed to parse response: {e}"

        except FileNotFoundError:
            FreeCAD.Console.PrintError("AIAssistant: Claude Code CLI not found. Is it installed?\n")
            return "# Error: Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"

        except Exception as e:
            FreeCAD.Console.PrintError(f"AIAssistant: Claude Code error: {e}\n")
            return f"# Error: {e}"

        finally:
            # Clean up screenshot temp file
            if screenshot_path:
                try:
                    os.unlink(screenshot_path)
                except Exception:
                    pass

    def _build_prompt(self, message: str, context: str, screenshot_path: str = None) -> str:
        """Build the prompt for Claude Code.

        If running in a project directory with CLAUDE.md, Claude will read that file.
        Otherwise, we include context directly in the prompt.
        """
        parts = []

        # If no project CLAUDE.md exists, include context directly
        if self.project_dir:
            claude_md_path = Path(self.project_dir) / "CLAUDE.md"
            if not claude_md_path.exists() and context:
                parts.append(f"CURRENT DOCUMENT STATE:\n{context}\n")
        elif context:
            parts.append(f"CURRENT DOCUMENT STATE:\n{context}\n")

        # Add screenshot reference if provided
        if screenshot_path:
            parts.append(f"[Screenshot of current viewport: {screenshot_path}]\n")

        parts.append(message)

        return "\n".join(parts)

    def _save_screenshot(self, base64_data: str) -> str:
        """Save base64 screenshot to temp file for Claude to read.

        Args:
            base64_data: Base64-encoded PNG image

        Returns:
            Path to temporary file
        """
        import base64
        import tempfile

        try:
            image_data = base64.b64decode(base64_data)
            fd, path = tempfile.mkstemp(suffix=".png", prefix="freecad_viewport_")
            os.write(fd, image_data)
            os.close(fd)
            return path
        except Exception as e:
            FreeCAD.Console.PrintWarning(f"AIAssistant: Failed to save screenshot: {e}\n")
            return None

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

    def _has_claude_md(self) -> bool:
        """Check if project has CLAUDE.md file.

        If CLAUDE.md exists in the project directory, Claude Code will
        automatically load it as context instructions.
        """
        if self.project_dir:
            return (Path(self.project_dir) / "CLAUDE.md").exists()
        return False

    def clear_session(self):
        """Clear the current session (start fresh conversation)."""
        self._session_id = None
        FreeCAD.Console.PrintMessage("AIAssistant: Claude Code session cleared\n")

    def get_session_id(self) -> Optional[str]:
        """Get the current session ID for persistence."""
        return self._session_id

    def set_session_id(self, session_id: str):
        """Restore a session ID (for resuming conversations)."""
        self._session_id = session_id
