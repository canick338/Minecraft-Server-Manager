import threading
import queue
import flet as ft
import psutil
from Server.server import Server
from app.file_picker_handler import FilePickerHandler
from app.server_config_manager import ServerConfigManager

class ServerManagerApp:
    def __init__(self):
        self.servers = []
        self.current_server = None
        self.output_queue = queue.Queue()
        self.server_logs = {}
        self.config_manager = ServerConfigManager("config/servers_config.json", self.servers)
        self.page_size = 10
        self.current_page = 0

        self.file_picker_server = FilePickerHandler(self, "server_path")
        self.file_picker_jar = FilePickerHandler(self, "jar_file")

        self.config_manager.load_servers_from_config()

    def start(self, page: ft.Page):
        self.page = page
        self.page.title = "Server Manager"
        self.page.scroll = ft.ScrollMode.ALWAYS
        self.page.overlay.extend([self.file_picker_server.picker, self.file_picker_jar.picker])

        self.server_list = ft.ListView(expand=True)
        self.status_text = ft.Text("Выберите сервер для управления.")
        self.command_input = ft.TextField(label="Введите команду", expand=True)
        self.output_view = ft.ListView(height=200, expand=True)

        self.page.add(
            ft.Column(
                controls=[
                    ft.Text("Список серверов", size=20, weight=ft.FontWeight.BOLD),
                    self.server_list,
                    ft.Row(
                        controls=[
                            ft.FilledButton(text="Запустить сервер", on_click=self.start_server),
                            ft.FilledButton(text="Остановить сервер", on_click=self.stop_server),
                            ft.FilledButton(text="Сохранить конфигурацию", on_click=self.save_servers),
                            ft.FilledButton(text="Добавить сервер", on_click=self.open_add_server_dialog),
                            ft.FilledButton(text="Сканировать порты", on_click=self.scan_ports_dialog),
                        ],
                    ),
                    self.command_input,
                    ft.FilledButton(text="Отправить команду", on_click=self.send_command),
                    self.output_view,
                ],
                expand=True,
            )
        )

        self.refresh_server_list()
        self.page.update()

    def refresh_server_list(self):
        self.server_list.controls.clear()
        for server in self.servers:
            self.server_list.controls.append(
                ft.ListTile(
                    title=ft.Text(f"{server.name} ({server.server_path})"),
                    on_click=lambda e, server=server: self.select_server(server),
                    selected_color=ft.colors.BLUE,
                    selected=self.current_server == server
                )
            )
        self.page.update()

    def select_server(self, server):
        self.current_server = server
        self.status_text.value = f"Текущий сервер: {self.current_server.name}"
        self.clear_output()
        self.load_server_logs(server)
        self.refresh_server_list()
        self.page.update()

    def clear_output(self):
        self.output_view.controls.clear()
        self.page.update()

    def load_server_logs(self, server):
        logs = self.server_logs.get(server.name, [])
        for log in logs:
            self.output_view.controls.append(ft.Text(log))
        self.page.update()

    def append_to_log(self, server, message):
        if server.name not in self.server_logs:
            self.server_logs[server.name] = []
        self.server_logs[server.name].append(message)

    def start_server(self, e):
        if self.current_server:
            self.current_server.start(self.output_queue)
            self.status_text.value = f"Сервер {self.current_server.name} запущен."
            self.update_output_in_background()
        else:
            self.status_text.value = "Выберите сервер для запуска."
        self.page.update()

    def stop_server(self, e):
        if self.current_server:
            self.current_server.stop()
            self.status_text.value = f"Сервер {self.current_server.name} остановлен."
            self.clear_output()
        else:
            self.status_text.value = "Выберите сервер для остановки."
        self.page.update()

    def send_command(self, e):
        if self.current_server:
            command = self.command_input.value
            try:
                self.current_server.command(command)
                self.append_to_log(self.current_server, f"Отправлено: {command}")
            except Exception as err:
                self.append_to_log(self.current_server, f"Ошибка отправки команды: {err}")
        else:
            self.append_to_log(self.current_server, "Выберите сервер для отправки команды.")
        self.page.update()

    def save_servers(self, e):
        self.config_manager.save_servers_to_config()
        self.status_text.value = "Конфигурация сохранена."
        self.page.update()

    def update_output_in_background(self):
        def update():
            while self.current_server and self.current_server.server:
                self.update_output()

        threading.Thread(target=update, daemon=True).start()

    def update_output(self):
        while not self.output_queue.empty():
            output = self.output_queue.get()
            self.output_view.controls.append(ft.Text(output))
            self.append_to_log(self.current_server, output)
        self.page.update()

    def open_add_server_dialog(self, e):
        self.dialog = ft.AlertDialog(
            title=ft.Text("Добавить новый сервер"),
            content=ft.Column([
                ft.TextField(label="Имя сервера", expand=True, key="server_name"),
                ft.Row(controls=[
                    ft.TextField(label="Путь к папке с сервером", expand=True, key="server_path"),
                    ft.IconButton(icon=ft.icons.FOLDER_OPEN,
                                  on_click=lambda _: self.file_picker_server.pick_files(allow_multiple=False))
                ]),
                ft.Row(controls=[
                    ft.TextField(label="Путь к jar-файлу", expand=True, key="jar_file"),
                    ft.IconButton(icon=ft.icons.FOLDER_OPEN,
                                  on_click=lambda _: self.file_picker_jar.pick_files(allow_multiple=False))
                ]),
                ft.TextField(label="ОЗУ (в ГБ)", expand=True, key="ram")
            ], spacing=10),
            actions=[
                ft.TextButton("Добавить", on_click=self.add_new_server),
                ft.TextButton("Отмена", on_click=self.close_dialog)
            ]
        )

        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()

        self.dialog.content.controls[0].focus()

    def on_server_path_picked(self, e: ft.FilePickerResultEvent):
        """Обрабатывает результат выбора папки с сервером."""
        if e.files:
            path = e.files[0].path
            self.dialog.content.controls[1].controls[0].value = path
            self.page.update()
            print(f"Выбрана папка с сервером: {path}")

    def on_jar_file_picked(self, e: ft.FilePickerResultEvent):
        """Обрабатывает результат выбора jar-файла."""
        if e.files:
            path = e.files[0].path
            self.dialog.content.controls[2].controls[0].value = path
            self.page.update()
            print(f"Выбран jar-файл: {path}")

    def close_dialog(self, e):
        """Закрывает диалоговое окно."""
        self.dialog.open = False
        self.page.update()

    def add_new_server(self, e):
        """Добавить новый сервер на основе введенных данных."""
        server_name = self.dialog.content.controls[0].value
        server_path = self.dialog.content.controls[1].controls[0].value
        server_file_name = self.dialog.content.controls[2].controls[0].value
        max_ram = self.dialog.content.controls[3].value

        if server_name and server_path and server_file_name and max_ram:
            new_server = Server(server_name, server_path, server_file_name, int(max_ram))
            self.servers.append(new_server)
            self.config_manager.save_servers_to_config()
            self.refresh_server_list()
            self.close_dialog(e)

    # Сканер портов
    def scan_ports_dialog(self, e):
        """Сканирует открытые порты и создает диалог с чекбоксами для закрытия портов."""
        self.current_page = 0
        port_info = self.scan_ports()
        self.dialog_content = ft.ListView(expand=True)


        java_ports = {port: proc_info for port, proc_info in port_info.items() if "java" in proc_info['name'].lower()}


        for port, proc_info in list(java_ports.items())[
                               self.current_page * self.page_size:(self.current_page + 1) * self.page_size]:
            checkbox = ft.Checkbox(label=f"Порт {port} - {proc_info['name']} (PID: {proc_info['pid']})", value=False,
                                   key=str(port))
            self.dialog_content.controls.append(checkbox)


        self.dialog = ft.AlertDialog(
            title=ft.Text("Открытые порты (Java)"),
            content=self.dialog_content,
            actions=[
                ft.TextButton("Закрыть выбранные порты", on_click=self.close_selected_ports),
                ft.Row(controls=[
                    ft.TextButton("Предыдущая", on_click=self.previous_page),
                    ft.TextButton("Следующая", on_click=self.next_page),
                    ft.TextButton("Закрыть", on_click=self.close_dialog)
                ])
            ]
        )

        self.page.dialog = self.dialog
        self.dialog.open = True
        self.page.update()

    def scan_ports(self):
        """Функция сканирования открытых портов и получения информации о процессах."""
        port_info = {}
        for conn in psutil.net_connections():
            if conn.status == psutil.CONN_LISTEN:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        for p_conn in proc.connections(kind='inet'):
                            if p_conn.laddr.port == conn.laddr.port:
                                port_info[conn.laddr.port] = {'pid': proc.pid, 'name': proc.name()}
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        return port_info

    def close_selected_ports(self, e):
        """Закрывает порты, выбранные пользователем."""
        for port in self.dialog_content.controls:
            if isinstance(port, ft.Checkbox) and port.value:
                port_number = int(port.key)
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        for conn in proc.connections(kind='inet'):
                            if conn.laddr.port == port_number:
                                proc.kill()

                                if self.current_server is not None:
                                    self.append_to_log(self.current_server,
                                                       f"Закрыт порт: {port_number} (PID: {proc.pid}, Процесс: {proc.name()})")
                                else:
                                    print(
                                        f"Закрыт порт: {port_number} (PID: {proc.pid}, Процесс: {proc.name()}) - Текущий сервер не установлен.")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

        self.status_text.value = "Закрыты выбранные порты."
        self.close_dialog(e)

    def previous_page(self, e):
        """Переход на предыдущую страницу портов."""
        if self.current_page > 0:
            self.current_page -= 1
            self.scan_ports_dialog(e)

    def next_page(self, e):
        """Переход на следующую страницу портов."""
        total_java_ports = len(self.scan_ports())
        if (self.current_page + 1) * self.page_size < total_java_ports:
            self.current_page += 1
            self.scan_ports_dialog(e)