# SPDX-License-Identifier: LGPL-2.1-or-later

# AIAssistant Module - Natural language CAD modeling assistant

SET(AIAssistant_SRCS
    Init.py
    InitGui.py
    __init__.py
    AIPanel.py
    LLMBackend.py
    ContextBuilder.py
    CodeExecutor.py
)

SOURCE_GROUP("" FILES ${AIAssistant_SRCS})

ADD_CUSTOM_TARGET(AIAssistant ALL
    SOURCES ${AIAssistant_SRCS}
)

fc_copy_sources(AIAssistant "${CMAKE_BINARY_DIR}/Mod/AIAssistant" ${AIAssistant_SRCS})

INSTALL(
    FILES ${AIAssistant_SRCS}
    DESTINATION Mod/AIAssistant
)
