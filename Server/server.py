import subprocess
import threading

class Server:
    def __init__(self, name, server_path, server_file_name, max_ram, is_proxy=False):
        self.name = name
        self.server_path = server_path
        self.server_file_name = server_file_name
        self.max_ram = max_ram
        self.is_proxy = is_proxy
        self.server = None
        self.thread = None

    def start(self, output_queue):
        if self.server:
            output_queue.put(f"Сервер {self.name} уже запущен.")
            return

        command = ['java', f'-Xms1G', f'-Xmx{self.max_ram}G', '-jar', self.server_file_name, 'nogui']
        self.server = subprocess.Popen(command, cwd=self.server_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE, text=True)

        self.thread = threading.Thread(target=self.read_output, args=(self.server, output_queue), daemon=True)
        self.thread.start()

    def read_output(self, process, output_queue):
        while True:
            output = process.stdout.readline()
            if output:
                output_queue.put(output.strip())
            if process.poll() is not None:
                break

    def stop(self):
        if self.server:
            try:
                self.server.terminate()
                self.server.wait()
                self.server = None
            except Exception as e:
                print(f"Ошибка при остановке сервера: {e}")

    def command(self, cmd):
        if self.server:
            self.server.stdin.write(cmd + "\n")
            self.server.stdin.flush()

    def to_dict(self):
        return {
            "name": self.name,
            "server_path": self.server_path,
            "server_file_name": self.server_file_name,
            "max_ram": self.max_ram,
            "is_proxy": self.is_proxy,
        }
