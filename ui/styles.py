import flet as ft

# --- COLORS ---
PRIMARY_COLOR = ft.Colors.BLUE_700
PRIMARY_LIGHT = ft.Colors.BLUE_100
SECONDARY_COLOR = ft.Colors.GREY_400
ACCENT_COLOR = ft.Colors.BLUE_ACCENT
SUCCESS_COLOR = ft.Colors.GREEN_600
WARNING_COLOR = ft.Colors.ORANGE_700
DANGER_COLOR = ft.Colors.RED_700
BG_LIGHT = ft.Colors.GREY_50
BG_DARK = ft.Colors.GREY_900
BORDER_COLOR = ft.Colors.OUTLINE

# --- DIMENSIONS ---
PADDING_SMALL = 5
PADDING_MEDIUM = 10
PADDING_LARGE = 20
BORDER_RADIUS_SMALL = 8
BORDER_RADIUS_MEDIUM = 12

# --- COMMON STYLES ---

# Container style for "Cards"
CARD_STYLE = {
    "padding": PADDING_MEDIUM,
    "border_radius": BORDER_RADIUS_MEDIUM,
    "border": ft.Border.all(1, BORDER_COLOR),
    "bgcolor": ft.Colors.GREY_100,
}

# Button Styles
PRIMARY_BTN_STYLE = ft.ButtonStyle(
    color=ft.Colors.WHITE,
    bgcolor=PRIMARY_COLOR,
    shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS_SMALL),
)

SECONDARY_BTN_STYLE = ft.ButtonStyle(
    color=PRIMARY_COLOR,
    bgcolor=ft.Colors.WHITE,
    shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS_SMALL),
    side=ft.BorderSide(1, PRIMARY_COLOR),
)

DANGER_BTN_STYLE = ft.ButtonStyle(
    color=ft.Colors.WHITE,
    bgcolor=DANGER_COLOR,
    shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS_SMALL),
)

SUCCESS_BTN_STYLE = ft.ButtonStyle(
    color=ft.Colors.WHITE,
    bgcolor=SUCCESS_COLOR,
    shape=ft.RoundedRectangleBorder(radius=BORDER_RADIUS_SMALL),
)

# TextField style commonalities
TEXTFIELD_STYLE = {
    "border_radius": BORDER_RADIUS_SMALL,
    "text_size": 14,
    "content_padding": ft.Padding(PADDING_SMALL, PADDING_SMALL),
}
