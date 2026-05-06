import flet as ft

def create_text_field(label, value="", keyboard_type=None, width=None):
    return ft.TextField(
        label=label,
        value=value,
        keyboard_type=keyboard_type,
        width=width
    )

def create_dropdown(label, options, width=None):
    return ft.Dropdown(
        label=label,
        options=options,
        width=width
    )
