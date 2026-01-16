# SPDX-License-Identifier: LGPL-2.1-or-later
"""Qt UI widgets for AI Assistant."""

from .chat import ChatWidget, ChatListWidget, StreamingController
from .message_model import CodeBlock, ChatMessage, MessageRole, ChatMessageModel
from .message_delegate import DebugInfoWidget, MessageCard, ThinkingIndicator
from .code_block import CodeBlockWidget, InlineCodeLabel
from .syntax import PythonHighlighter, MultilineStringHighlighter
from .change import ChangeItemWidget, ChangeWidget, ChangesSummaryWidget
from .preview import PreviewWidget
from .plan import PlanStep, PlanStepWidget, PlanWidget
from .step_preview import StepState, StepPreviewWidget, MultiStepPreviewWidget
from .activity import format_tool_call, ActivityWidget
from .context_selection import ContextMode, ContextSelectionWidget

__all__ = [
    # chat
    "ChatWidget",
    "ChatListWidget",
    "StreamingController",
    # message_model
    "CodeBlock",
    "ChatMessage",
    "MessageRole",
    "ChatMessageModel",
    # message_delegate
    "DebugInfoWidget",
    "MessageCard",
    "ThinkingIndicator",
    # code_block
    "CodeBlockWidget",
    "InlineCodeLabel",
    # syntax
    "PythonHighlighter",
    "MultilineStringHighlighter",
    # change
    "ChangeItemWidget",
    "ChangeWidget",
    "ChangesSummaryWidget",
    # preview
    "PreviewWidget",
    # plan
    "PlanStep",
    "PlanStepWidget",
    "PlanWidget",
    # step_preview
    "StepState",
    "StepPreviewWidget",
    "MultiStepPreviewWidget",
    # activity
    "format_tool_call",
    "ActivityWidget",
    # context_selection
    "ContextMode",
    "ContextSelectionWidget",
]
