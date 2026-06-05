from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔮 Analizar Ahora", callback_data="analyze_now"),
                InlineKeyboardButton("📊 Ver Estado", callback_data="view_status"),
            ],
            [
                InlineKeyboardButton("⚙️ Configuración", callback_data="settings"),
                InlineKeyboardButton("📜 Historial", callback_data="history"),
            ],
        ]
    )


def settings_menu(current_window: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("12h", callback_data="set_window_12"),
                InlineKeyboardButton("24h", callback_data="set_window_24"),
                InlineKeyboardButton("48h", callback_data="set_window_48"),
            ],
            [
                InlineKeyboardButton("🔙 Volver", callback_data="main_menu"),
            ],
        ]
    )


def back_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Volver", callback_data="main_menu")]]
    )


def refresh_status() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 Actualizar", callback_data="view_status"),
                InlineKeyboardButton("🔙 Volver", callback_data="main_menu"),
            ]
        ]
    )
