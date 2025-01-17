import flet as ft

class FilePickerHandler:
    def __init__(self, app, file_type):
        self.app = app
        self.file_type = file_type
        self.picker = ft.FilePicker(on_result=self.on_file_picked)

    def pick_files(self, allow_multiple):
        self.picker.pick_files(allow_multiple=allow_multiple)

    def on_file_picked(self, e: ft.FilePickerResultEvent):
        if self.file_type == "server_path":
            self.app.on_server_path_picked(e)
        elif self.file_type == "jar_file":
            self.app.on_jar_file_picked(e)
