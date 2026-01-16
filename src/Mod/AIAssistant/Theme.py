# SPDX-License-Identifier: LGPL-2.1-or-later
"""
Theme - Centralized design tokens for the AI Assistant UI.
Modern, Cursor-inspired dark theme with blue accents.
"""

# =============================================================================
# COLOR PALETTE
# =============================================================================

COLORS = {
    # Background colors (ultra-dark, refined)
    "bg_primary": "#09090b",      # Main background
    "bg_secondary": "#0f0f11",    # Cards, panels
    "bg_tertiary": "#18181b",     # Elevated surfaces
    "bg_input": "#0c0c0e",        # Input field background
    "bg_hover": "#1f1f23",        # Hover state

    # Border colors
    "border_subtle": "#1c1c1f",   # Very subtle borders
    "border_default": "#27272a",  # Standard borders
    "border_focus": "#3b82f6",    # Focus state (blue)
    "border_hover": "#3f3f46",    # Hover state

    # Text colors
    "text_primary": "#fafafa",    # Primary text (nearly white)
    "text_secondary": "#a1a1aa",  # Secondary text
    "text_muted": "#52525b",      # Muted/disabled text
    "text_placeholder": "#71717a", # Placeholder text

    # Accent colors
    "accent_primary": "#3b82f6",  # Primary accent (blue)
    "accent_primary_hover": "#2563eb",  # Blue hover
    "accent_success": "#22c55e",  # Success/created (green)
    "accent_success_hover": "#16a34a",
    "accent_error": "#ef4444",    # Error (red)
    "accent_error_hover": "#dc2626",
    "accent_warning": "#f59e0b",  # Warning (amber)
    "accent_info": "#3b82f6",     # Info (blue)

    # Message-specific colors
    "user_msg_text": "#fafafa",
    "assistant_card_bg": "#0f0f11",
    "assistant_card_border": "#1c1c1f",
    "assistant_text": "#e4e4e7",
    "system_text": "#71717a",
    "error_bg": "rgba(239, 68, 68, 0.08)",
    "error_border": "#7f1d1d",
    "error_text": "#fca5a5",

    # Code block colors
    "code_bg": "#09090b",
    "code_border": "#1c1c1f",
    "code_header_bg": "#0f0f11",
    "code_text": "#e4e4e7",

    # Preview widget colors
    "preview_bg": "rgba(59, 130, 246, 0.05)",
    "preview_border": "rgba(59, 130, 246, 0.2)",
    "preview_text": "#93c5fd",

    # Change widget colors
    "change_created": "#22c55e",
    "change_created_bg": "rgba(34, 197, 94, 0.08)",
    "change_modified": "#3b82f6",
    "change_modified_bg": "rgba(59, 130, 246, 0.08)",
    "change_deleted": "#ef4444",
    "change_deleted_bg": "rgba(239, 68, 68, 0.08)",

    # Skeleton/loading colors
    "skeleton_base": "#18181b",
    "skeleton_shimmer": "#27272a",

    # Scrollbar colors
    "scrollbar_bg": "transparent",
    "scrollbar_handle": "#27272a",
    "scrollbar_handle_hover": "#3f3f46",

    # Debug panel colors
    "debug_accent": "#3b82f6",
    "debug_bg": "rgba(59, 130, 246, 0.08)",
    "debug_border": "rgba(59, 130, 246, 0.3)",
}

# =============================================================================
# TYPOGRAPHY
# =============================================================================

FONTS = {
    # Font families
    "family_sans": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "family_mono": "'JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', monospace",

    # Font sizes
    "size_xs": "11px",
    "size_sm": "12px",
    "size_base": "14px",
    "size_lg": "16px",
    "size_xl": "18px",

    # Font weights
    "weight_normal": "400",
    "weight_medium": "500",
    "weight_semibold": "600",
    "weight_bold": "700",

    # Line heights
    "line_height_tight": "1.3",
    "line_height_normal": "1.5",
    "line_height_relaxed": "1.7",
}

# =============================================================================
# SPACING
# =============================================================================

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "2xl": 32,
}

# =============================================================================
# BORDER RADIUS
# =============================================================================

RADIUS = {
    "xs": "4px",
    "sm": "6px",
    "md": "10px",
    "lg": "14px",
    "xl": "18px",
    "full": "9999px",
}

# =============================================================================
# ANIMATIONS
# =============================================================================

ANIMATION = {
    "duration_fast": 100,     # ms
    "duration_normal": 150,   # ms
    "duration_slow": 250,     # ms
    "shimmer_duration": 1500, # ms for full shimmer cycle
}

# =============================================================================
# COMPONENT-SPECIFIC STYLES
# =============================================================================

def get_scrollbar_style():
    """Get scrollbar stylesheet."""
    return f"""
        QScrollBar:vertical {{
            background-color: {COLORS['scrollbar_bg']};
            width: 8px;
            border-radius: 4px;
            margin: 4px 2px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {COLORS['scrollbar_handle']};
            border-radius: 4px;
            min-height: 40px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {COLORS['scrollbar_handle_hover']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
    """


def get_button_primary_style():
    """Get primary button stylesheet (blue)."""
    return f"""
        QPushButton {{
            background-color: {COLORS['accent_primary']};
            color: #ffffff;
            border: none;
            border-radius: {RADIUS['md']};
            font-weight: {FONTS['weight_medium']};
            font-size: {FONTS['size_base']};
            padding: 10px 20px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['accent_primary_hover']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['accent_primary']};
        }}
        QPushButton:disabled {{
            background-color: {COLORS['bg_tertiary']};
            color: {COLORS['text_muted']};
        }}
    """


def get_button_ghost_style():
    """Get ghost button stylesheet (transparent with border)."""
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {COLORS['text_secondary']};
            border: 1px solid {COLORS['border_default']};
            border-radius: {RADIUS['sm']};
            font-size: {FONTS['size_sm']};
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['bg_hover']};
            border-color: {COLORS['border_hover']};
            color: {COLORS['text_primary']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['bg_tertiary']};
        }}
    """


def get_button_success_style():
    """Get success button stylesheet (green)."""
    return f"""
        QPushButton {{
            background-color: {COLORS['accent_success']};
            color: #ffffff;
            border: none;
            border-radius: {RADIUS['md']};
            font-weight: {FONTS['weight_medium']};
            font-size: {FONTS['size_base']};
            padding: 10px 20px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['accent_success_hover']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['accent_success']};
        }}
        QPushButton:disabled {{
            background-color: {COLORS['bg_tertiary']};
            color: {COLORS['text_muted']};
        }}
    """


def get_input_frame_style():
    """Get input frame stylesheet."""
    return f"""
        QFrame {{
            background-color: {COLORS['bg_input']};
            border: 1px solid {COLORS['border_default']};
            border-radius: {RADIUS['lg']};
        }}
        QFrame:focus-within {{
            border-color: {COLORS['border_focus']};
        }}
    """


def get_text_input_style():
    """Get text input stylesheet."""
    return f"""
        QTextEdit {{
            background-color: transparent;
            color: {COLORS['text_primary']};
            border: none;
            font-size: {FONTS['size_base']};
            padding: 4px 0;
            selection-background-color: {COLORS['accent_primary']};
        }}
        QTextEdit::placeholder {{
            color: {COLORS['text_placeholder']};
        }}
    """
