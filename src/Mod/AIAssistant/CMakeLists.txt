# SPDX-License-Identifier: LGPL-2.1-or-later

# AIAssistant Module - Natural language CAD modeling assistant

set(AIAssistant_SRCS
    Init.py
    InitGui.py
    __init__.py
    AIPanel.py
    LLMBackend.py
    ContextBuilder.py
    CodeExecutor.py
)

add_custom_target(AIAssistant ALL
    SOURCES ${AIAssistant_SRCS}
)

fc_target_copy_resource(AIAssistant
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_BINARY_DIR}/Mod/AIAssistant
    ${AIAssistant_SRCS}
)

install(
    FILES ${AIAssistant_SRCS}
    DESTINATION Mod/AIAssistant
)

# Install resources if they exist
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/Resources)
    install(
        DIRECTORY Resources
        DESTINATION Mod/AIAssistant
    )
endif()
