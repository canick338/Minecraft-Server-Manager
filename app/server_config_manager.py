import os
import json

from Server.server import Server


class ServerConfigManager:
    def __init__(self, config_file, servers):
        self.config_file = config_file
        self.servers = servers

    def load_servers_from_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                data = json.load(file)
                if isinstance(data, dict) and "servers" in data:
                    for server_data in data["servers"]:
                        server = Server(
                            server_data["name"],
                            server_data["server_path"],
                            server_data["server_file_name"],
                            server_data["max_ram"],
                            server_data["is_proxy"],
                        )
                        self.servers.append(server)
                else:
                    print("Некорректный формат конфигурационного файла.")

    def save_servers_to_config(self):
        data = {
            "servers": [server.to_dict() for server in self.servers]
        }
        with open(self.config_file, 'w') as file:
            json.dump(data, file, indent=4)
