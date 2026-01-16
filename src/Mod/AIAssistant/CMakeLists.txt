# SPDX-License-Identifier: LGPL-2.1-or-later

# AIAssistant Module - Natural language CAD modeling assistant

# Root level files
SET(AIAssistant_SRCS
    Init.py
    InitGui.py
    __init__.py
    AIPanel.py
    Theme.py
    project_claude_template.md
)

# LLM backend implementations
SET(AIAssistant_backends
    backends/__init__.py
    backends/claude_code.py
    backends/http.py
)

# Core business logic
SET(AIAssistant_core
    core/__init__.py
    core/context.py
    core/source.py
    core/snapshot.py
    core/changes.py
    core/executor.py
    core/preview.py
)

# Session and logging persistence
SET(AIAssistant_persistence
    persistence/__init__.py
    persistence/session.py
    persistence/activity.py
)

# Qt UI widgets
SET(AIAssistant_widgets
    widgets/__init__.py
    widgets/chat.py
    widgets/message_model.py
    widgets/message_delegate.py
    widgets/code_block.py
    widgets/syntax.py
    widgets/change.py
    widgets/preview.py
    widgets/plan.py
    widgets/step_preview.py
    widgets/activity.py
    widgets/context_selection.py
)

# External integrations
SET(AIAssistant_integration
    integration/__init__.py
    integration/parts_library.py
)

# Combine all sources for IDE visibility
SET(AIAssistant_ALL_SRCS
    ${AIAssistant_SRCS}
    ${AIAssistant_backends}
    ${AIAssistant_core}
    ${AIAssistant_persistence}
    ${AIAssistant_widgets}
    ${AIAssistant_integration}
)

SOURCE_GROUP("" FILES ${AIAssistant_SRCS})
SOURCE_GROUP("backends" FILES ${AIAssistant_backends})
SOURCE_GROUP("core" FILES ${AIAssistant_core})
SOURCE_GROUP("persistence" FILES ${AIAssistant_persistence})
SOURCE_GROUP("widgets" FILES ${AIAssistant_widgets})
SOURCE_GROUP("integration" FILES ${AIAssistant_integration})

ADD_CUSTOM_TARGET(AIAssistant ALL
    SOURCES ${AIAssistant_ALL_SRCS}
)

fc_copy_sources(AIAssistant "${CMAKE_BINARY_DIR}/Mod/AIAssistant" ${AIAssistant_ALL_SRCS})

# Install with directory structure preserved
INSTALL(FILES ${AIAssistant_SRCS} DESTINATION Mod/AIAssistant)
INSTALL(FILES ${AIAssistant_backends} DESTINATION Mod/AIAssistant/backends)
INSTALL(FILES ${AIAssistant_core} DESTINATION Mod/AIAssistant/core)
INSTALL(FILES ${AIAssistant_persistence} DESTINATION Mod/AIAssistant/persistence)
INSTALL(FILES ${AIAssistant_widgets} DESTINATION Mod/AIAssistant/widgets)
INSTALL(FILES ${AIAssistant_integration} DESTINATION Mod/AIAssistant/integration)
