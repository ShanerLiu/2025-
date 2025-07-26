import socket
from password_checkup_protocol import PasswordCheckupProtocol, Server, Network
from typing import List

class PasswordServer:
    def __init__(self, host: str, port: int, leaked_passwords_path: str = None):
        self.host = host
        self.port = port
        self.protocol = PasswordCheckupProtocol()
        self.leaked_hashes = self._load_leaked_passwords(leaked_passwords_path) if leaked_passwords_path else []
        self.server = None

    def _load_leaked_passwords(self, path: str) -> List[bytes]:
        """从文件加载泄露的密码哈希（每行一个哈希）"""
        try:
            with open(path, 'rb') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"警告：泄露密码文件 {path} 不存在，使用空列表")
            return []

    def set_leaked_passwords(self, password_hashes: List[bytes]):
        """设置泄露的密码哈希列表"""
        self.leaked_hashes = password_hashes

    def start(self):
        """启动服务器"""
        self.server = Server(self.protocol, self.leaked_hashes)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            print(f"服务器在 {self.host}:{self.port} 上启动")

            while True:
                conn, addr = s.accept()
                print(f"接受来自 {addr} 的连接")

                try:
                    self._handle_client(conn)
                except Exception as e:
                    print(f"处理客户端时发生错误：{e}")
                finally:
                    conn.close()

    def _handle_client(self, conn: socket.socket):
        """处理客户端连接"""
        while True:
            data = conn.recv(8192)  # 增加缓冲区大小
            if not data:
                break

            message = Network.receive_object(data)

            if message["type"] == "REQUEST_PAILLIER_KEY":
                # 发送Paillier公钥
                conn.sendall(Network.send_object({
                    "type": "PAILLIER_KEY",
                    "data": self.server.get_paillier_public_key()
                }))

            elif message["type"] == "ROUND1":
                # 处理第一轮消息，发送第二轮消息
                round1_data = message["data"]
                p2_msg1, p2_msg2 = self.server.round2(round1_data)

                conn.sendall(Network.send_object({
                    "type": "ROUND2",
                    "data": (p2_msg1, p2_msg2)
                }))

            elif message["type"] == "ROUND3":
                # 处理第三轮消息，发送结果
                encrypted_sum = message["data"]
                result = self.server.decrypt_result(encrypted_sum)

                conn.sendall(Network.send_object({
                    "type": "RESULT",
                    "data": result
                }))


# 示例使用
if __name__ == "__main__":

    leaked_passwords = [
        b"leaked_password_hash",
        b"another_leaked_hash"
    ]

    server = PasswordServer("localhost", 12345)
    server.set_leaked_passwords(leaked_passwords)

    try:
        print("启动密码检查服务器...")
        server.start()
    except KeyboardInterrupt:
        print("服务器关闭")