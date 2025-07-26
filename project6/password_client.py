import socket
from password_checkup_protocol import PasswordCheckupProtocol, User, Network
from typing import List

class PasswordClient:
    def __init__(self, server_address: tuple, server_port: int):
        self.server_address = server_address
        self.server_port = server_port
        self.protocol = PasswordCheckupProtocol()
        self.user = None

    def set_user_passwords(self, password_hashes: List[bytes]):
        """设置用户密码哈希列表"""
        self.user = User(self.protocol, password_hashes)

    def perform_checkup(self) -> int:
        """执行密码检查协议"""
        if not self.user:
            raise ValueError("用户密码未设置")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # 连接服务器
            s.connect((self.server_address, self.server_port))

            # 1. 获取服务器的Paillier公钥
            s.sendall(Network.send_object({"type": "REQUEST_PAILLIER_KEY"}))
            response = Network.receive_object(s.recv(4096))
            if response["type"] != "PAILLIER_KEY":
                raise Exception("未能获取Paillier公钥")

            self.user.set_paillier_public_key(response["data"])

            # 2. 执行第一轮：发送加密的用户哈希
            round1_msg = self.user.round1()
            s.sendall(Network.send_object({"type": "ROUND1", "data": round1_msg}))

            # 3. 接收第二轮消息
            response = Network.receive_object(s.recv(8192))  # 增加缓冲区大小
            if response["type"] != "ROUND2":
                raise Exception("未能获取第二轮消息")

            p2_msg1, p2_msg2 = response["data"]

            # 4. 执行第三轮：计算交集和并发送结果
            encrypted_sum = self.user.round3(p2_msg1, p2_msg2)
            s.sendall(Network.send_object({"type": "ROUND3", "data": encrypted_sum}))

            # 5. 接收最终结果
            response = Network.receive_object(s.recv(4096))
            if response["type"] != "RESULT":
                raise Exception("未能获取检查结果")

            return response["data"]


# 示例使用
if __name__ == "__main__":
    # 假设我们已经有了用户密码的哈希值
    user_passwords = [
        b"user_password_hash_1",
        b"leaked_password_hash"  # 假设这是一个泄露的密码哈希
    ]

    client = PasswordClient("localhost", 12345)
    client.set_user_passwords(user_passwords)

    try:
        result = client.perform_checkup()
        print(f"泄露密码数量：{result}")
        if result > 0:
            print("警告：您的部分密码已泄露！")
        else:
            print("安全：您的密码未在泄露集合中。")
    except Exception as e:
        print(f"检查过程中发生错误：{e}")