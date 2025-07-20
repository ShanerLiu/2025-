from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import phe  # Paillier同态加密库
import secrets
import random
from typing import List, Tuple
import pickle


class PasswordCheckupProtocol:
    def __init__(self):
        # 初始化DDH安全群（prime256v1椭圆曲线，满足DDH假设）
        self.curve = ec.SECP256R1()  # NIST P-256，论文中使用的prime256v1
        self.gen = self.curve.generator  # 生成元g
        self.order = self.gen.order  # 群阶（质数）

    def hash_to_curve(self, x: bytes) -> ec.EllipticCurvePublicKey:
        """将输入（密码哈希）映射到椭圆曲线上的点（论文中H函数）"""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'password-checkup-hash-to-curve',
        )
        key_material = hkdf.derive(x)
        priv = ec.derive_private_key(int.from_bytes(key_material, 'big') % self.order, self.curve)
        return priv.public_key()

    def generate_private_key(self) -> int:
        """生成DDH协议中的私钥k（1~order-1的随机数）"""
        return secrets.randbelow(self.order - 1) + 1

    def exponentiate(self, point: ec.EllipticCurvePublicKey, exponent: int) -> ec.EllipticCurvePublicKey:
        """椭圆曲线点的指数运算（g^k）"""
        return point.public_numbers().multiply(exponent)

    def serialize_point(self, point: ec.EllipticCurvePublicKey) -> bytes:
        """将椭圆曲线点序列化为字节"""
        return point.public_numbers().encode_point()

    def deserialize_point(self, data: bytes) -> ec.EllipticCurvePublicKey:
        """从字节反序列化为椭圆曲线点"""
        x, y = int.from_bytes(data[1:33], 'big'), int.from_bytes(data[33:65], 'big')
        return ec.EllipticCurvePublicNumbers(x, y, self.curve).public_key()


class User:
    def __init__(self, protocol: PasswordCheckupProtocol, user_password_hashes: List[bytes]):
        self.protocol = protocol
        self.user_hashes = user_password_hashes  # 用户的密码哈希列表（P1的输入V）
        self.k1 = protocol.generate_private_key()  # P1的私钥k1
        self.paillier_pub = None  # 由服务器提供的Paillier公钥

    def set_paillier_public_key(self, pub_key: phe.PaillierPublicKey):
        """设置从服务器获取的Paillier公钥"""
        self.paillier_pub = pub_key

    def round1(self) -> List[bytes]:
        """第一轮：将用户哈希映射到曲线并以k1加密，打乱后发送给P2"""
        hashed_points = [self.protocol.hash_to_curve(hash_val) for hash_val in self.user_hashes]
        encrypted_points = [self.protocol.exponentiate(p, self.k1) for p in hashed_points]
        random.shuffle(encrypted_points)
        return [self.protocol.serialize_point(p) for p in encrypted_points]

    def round3(self, p2_round2_msg1: List[bytes],
               p2_round2_msg2: List[Tuple[bytes, int]]) -> int:
        """第三轮：计算交集并同态求和，返回加密的交集和"""
        # 反序列化消息
        p2_msg1_points = [self.protocol.deserialize_point(p) for p in p2_round2_msg1]
        p2_msg2_points = [(self.protocol.deserialize_point(p), enc_t) for p, enc_t in p2_round2_msg2]

        # 将P2的H(w_j)^k2用k1加密为H(w_j)^k1k2
        p2_hashes_encrypted = [
            self.protocol.exponentiate(p, self.k1)
            for p, _ in p2_msg2_points
        ]
        p2_encrypted_values = [enc_val for _, enc_val in p2_msg2_points]

        # 计算交集
        z_set = {self.protocol.serialize_point(point) for point in p2_msg1_points}
        intersection_indices = [
            i for i, p in enumerate(p2_hashes_encrypted)
            if self.protocol.serialize_point(p) in z_set
        ]

        # 同态求和
        if not intersection_indices:
            # 返回零的加密（使用公钥加密0）
            return self.paillier_pub.encrypt(0)
        sum_enc = self.paillier_pub.encrypt(0)
        for i in intersection_indices:
            sum_enc += p2_encrypted_values[i]
        return sum_enc


class Server:
    def __init__(self, protocol: PasswordCheckupProtocol, leaked_password_hashes: List[bytes]):
        self.protocol = protocol
        self.leaked_hashes = leaked_password_hashes  # 泄露的密码哈希列表（P2的输入W）
        self.k2 = protocol.generate_private_key()  # P2的私钥k2
        # 生成Paillier同态加密密钥对
        self.paillier_pub, self.paillier_priv = phe.generate_paillier_keypair()

    def get_paillier_public_key(self) -> phe.PaillierPublicKey:
        """提供Paillier公钥给P1"""
        return self.paillier_pub

    def round2(self, p1_round1_msg: List[bytes]) -> Tuple[List[bytes], List[Tuple[bytes, int]]]:
        """第二轮：处理P1的消息，返回两个子消息给P1"""
        # 反序列化P1的消息
        p1_points = [self.protocol.deserialize_point(p) for p in p1_round1_msg]

        # 子消息1：用k2加密P1的消息，得到Z = {H(v_i)^k1k2}
        z = [self.protocol.exponentiate(p, self.k2) for p in p1_points]
        z_bytes = [self.protocol.serialize_point(p) for p in z]
        random.shuffle(z_bytes)

        # 子消息2：处理P2自己的泄露哈希，生成{(H(w_j)^k2, AEnc(t_j))}
        p2_encrypted = []
        for hash_val in self.leaked_hashes:
            hashed_point = self.protocol.hash_to_curve(hash_val)
            encrypted_point = self.protocol.exponentiate(hashed_point, self.k2)
            encrypted_t = self.paillier_pub.encrypt(1)  # t_j=1 表示泄露
            p2_encrypted.append((self.protocol.serialize_point(encrypted_point), encrypted_t))
        random.shuffle(p2_encrypted)

        return z_bytes, p2_encrypted

    def decrypt_result(self, encrypted_sum: int) -> int:
        """解密交集和，判断是否有泄露"""
        return self.paillier_priv.decrypt(encrypted_sum)


# 网络通信辅助类（模拟客户端-服务器通信）
class Network:
    @staticmethod
    def send_object(obj) -> bytes:
        """序列化对象用于网络传输"""
        return pickle.dumps(obj)

    @staticmethod
    def receive_object(data: bytes):
        """从网络数据反序列化为对象"""
        return pickle.loads(data)