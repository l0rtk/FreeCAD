# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Session Manager - Persists chat sessions and debug data to local JSON files.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import FreeCAD


def get_sessions_dir() -> Path:
    """Get the sessions directory, creating it if needed."""
    # Use FreeCAD's user config directory
    config_dir = Path(FreeCAD.getUserAppDataDir())
    sessions_dir = config_dir / "AIAssistant" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


class SessionManager:
    """Manages chat session persistence to JSON files."""

    def __init__(self, sessions_dir: str = None):
        """
        Initialize the session manager.

        Args:
            sessions_dir: Optional custom directory for sessions.
                         Defaults to ~/.config/FreeCAD/AIAssistant/sessions/
        """
        self._sessions_dir = Path(sessions_dir) if sessions_dir else get_sessions_dir()
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._current_session_id: Optional[str] = None
        self._current_session_data: Optional[dict] = None

    def new_session(self, document_name: str = None) -> str:
        """
        Create a new session.

        Args:
            document_name: Optional FreeCAD document name to associate.

        Returns:
            The new session ID (timestamp-based).
        """
        now = datetime.now()
        session_id = now.strftime("%Y-%m-%d_%H-%M-%S")

        self._current_session_id = session_id
        self._current_session_data = {
            "session_id": session_id,
            "created": now.isoformat(),
            "updated": now.isoformat(),
            "document_name": document_name or "",
            "messages": [],
            "llm_requests": []  # Debug: full LLM request/response data
        }

        self._save_current_session()
        return session_id

    def save_message(self, message) -> None:
        """
        Save a message to the current session.

        Args:
            message: ChatMessage object to save.
        """
        # Auto-create session if none exists
        if self._current_session_id is None:
            doc_name = None
            try:
                if FreeCAD.ActiveDocument:
                    doc_name = FreeCAD.ActiveDocument.Name
            except Exception:
                pass
            self.new_session(doc_name)

        # Convert message to dict
        message_dict = {
            "timestamp": message.timestamp.isoformat(),
            "role": message.role,
            "text": message.text,
            "code_blocks": [
                {
                    "language": cb.language,
                    "code": cb.code,
                    "start_pos": cb.start_pos,
                    "end_pos": cb.end_pos
                }
                for cb in message.code_blocks
            ]
        }

        # Append to current session
        self._current_session_data["messages"].append(message_dict)
        self._current_session_data["updated"] = datetime.now().isoformat()

        self._save_current_session()

    def log_llm_request(
        self,
        user_message: str,
        system_prompt: str,
        context: str,
        conversation_history: List[dict],
        response: str,
        model: str = "",
        api_url: str = "",
        duration_ms: float = 0,
        success: bool = True,
        error: str = ""
    ) -> None:
        """
        Log a complete LLM request/response for debugging.

        Args:
            user_message: The user's input message
            system_prompt: Full system prompt sent to LLM
            context: Document context string
            conversation_history: Previous messages sent for context
            response: LLM response (or error message)
            model: Model name used
            api_url: API endpoint URL
            duration_ms: Request duration in milliseconds
            success: Whether the request succeeded
            error: Error message if failed
        """
        # Auto-create session if none exists
        if self._current_session_id is None:
            doc_name = None
            try:
                if FreeCAD.ActiveDocument:
                    doc_name = FreeCAD.ActiveDocument.Name
            except Exception:
                pass
            self.new_session(doc_name)

        # Build debug entry
        debug_entry = {
            "timestamp": datetime.now().isoformat(),
            "request": {
                "user_message": user_message,
                "system_prompt": system_prompt,
                "context": context,
                "conversation_history": conversation_history,
                "model": model,
                "api_url": api_url
            },
            "response": {
                "content": response,
                "success": success,
                "error": error,
                "duration_ms": duration_ms
            }
        }

        # Ensure llm_requests exists (for older sessions)
        if "llm_requests" not in self._current_session_data:
            self._current_session_data["llm_requests"] = []

        self._current_session_data["llm_requests"].append(debug_entry)
        self._current_session_data["updated"] = datetime.now().isoformat()

        self._save_current_session()

    def load_session(self, session_id: str) -> List[dict]:
        """
        Load messages from a session file.

        Args:
            session_id: The session ID to load.

        Returns:
            List of message dictionaries.
        """
        session_path = self._sessions_dir / f"{session_id}.json"

        if not session_path.exists():
            return []

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._current_session_id = session_id
                self._current_session_data = data
                return data.get("messages", [])
        except Exception as e:
            FreeCAD.Console.PrintError(f"AIAssistant: Failed to load session: {e}\n")
            return []

    def list_sessions(self) -> List[dict]:
        """
        List all available sessions.

        Returns:
            List of session summaries: {session_id, created, message_count, document_name}
        """
        sessions = []

        for session_file in sorted(self._sessions_dir.glob("*.json"), reverse=True):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append({
                        "session_id": data.get("session_id", session_file.stem),
                        "created": data.get("created", ""),
                        "updated": data.get("updated", ""),
                        "message_count": len(data.get("messages", [])),
                        "document_name": data.get("document_name", ""),
                        "preview": self._get_preview(data.get("messages", []))
                    })
            except Exception:
                # Skip corrupted files
                continue

        return sessions

    def get_current_session_id(self) -> Optional[str]:
        """Get the current active session ID."""
        return self._current_session_id

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session file.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if deleted successfully.
        """
        session_path = self._sessions_dir / f"{session_id}.json"

        try:
            if session_path.exists():
                session_path.unlink()

                # Clear current session if it was deleted
                if self._current_session_id == session_id:
                    self._current_session_id = None
                    self._current_session_data = None

                return True
        except Exception as e:
            FreeCAD.Console.PrintError(f"AIAssistant: Failed to delete session: {e}\n")

        return False

    def clear_current_session(self) -> None:
        """Clear the current session (start fresh)."""
        self._current_session_id = None
        self._current_session_data = None

    def _save_current_session(self) -> None:
        """Save current session data to disk."""
        if not self._current_session_id or not self._current_session_data:
            return

        session_path = self._sessions_dir / f"{self._current_session_id}.json"

        try:
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(self._current_session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            FreeCAD.Console.PrintError(f"AIAssistant: Failed to save session: {e}\n")

    def _get_preview(self, messages: List[dict], max_length: int = 50) -> str:
        """Get a preview of the first user message."""
        for msg in messages:
            if msg.get("role") == "user":
                text = msg.get("text", "")
                if len(text) > max_length:
                    return text[:max_length] + "..."
                return text
        return ""
