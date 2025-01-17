import flet as ft

from app.server_manager import ServerManagerApp


def main(page: ft.Page):
    page.window_width = 1325
    page.window_height = 725

    page.window_center()

    app = ServerManagerApp()
    app.start(page)

ft.app(target=main)
