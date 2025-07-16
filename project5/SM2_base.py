import time
import random
from typing import Tuple, List

# SM2曲线参数
p = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
a = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
b = 0x28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93
n = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123
Gx = 0x32C4AF2C1F1981195F9904466A39C9948FF30B00E980E94E9C9A9A948FF30B0
Gy = 0xBC3736A2F4F6779C59BDCEE36B692153DA9877CC62474002DF32E52139F0A0
G = (Gx, Gy)


# 大数运算基础实现
class BigNumber:
    @staticmethod
    def add(a: int, b: int, mod: int) -> int:
        """大数加法（带模）"""
        return (a + b) % mod

    @staticmethod
    def sub(a: int, b: int, mod: int) -> int:
        """大数减法（带模）"""
        return (a - b + mod) % mod

    @staticmethod
    def mul(a: int, b: int, mod: int) -> int:
        """大数乘法（带模）"""
        return (a * b) % mod

    @staticmethod
    def pow_mod(a: int, exp: int, mod: int) -> int:
        """大数幂模（快速幂）"""
        return pow(a, exp, mod)

    @staticmethod
    def inv(a: int, mod: int) -> int:
        """模逆（费马小定理，mod为素数）"""
        return BigNumber.pow_mod(a, mod - 2, mod)


# 椭圆曲线点运算
class ECPoint:
    @staticmethod
    def is_on_curve(point: Tuple[int, int]) -> bool:
        """验证点是否在曲线上"""
        x, y = point
        return (y * y - (x * x * x + a * x + b)) % p == 0

    @staticmethod
    def double(P: Tuple[int, int]) -> Tuple[int, int]:
        """双倍点运算：Q = 2P"""
        x1, y1 = P
        if x1 == 0 and y1 == 0:  # 无穷远点
            return (0, 0)
        lam = BigNumber.mul(3 * x1 * x1 + a, BigNumber.inv(2 * y1, p), p)
        x3 = BigNumber.sub(BigNumber.mul(lam, lam, p), 2 * x1, p)
        y3 = BigNumber.sub(BigNumber.mul(lam, BigNumber.sub(x1, x3, p), p), y1, p)
        return (x3, y3)

    @staticmethod
    def add(P1: Tuple[int, int], P2: Tuple[int, int]) -> Tuple[int, int]:
        """点加运算：Q = P1 + P2"""
        x1, y1 = P1
        x2, y2 = P2
        if x1 == 0 and y1 == 0:  # P1为无穷远点
            return P2
        if x2 == 0 and y2 == 0:  # P2为无穷远点
            return P1
        if x1 == x2 and y1 != y2:  # 互逆点
            return (0, 0)
        if x1 == x2 and y1 == y2:  # 同点（调用双倍点）
            return ECPoint.double(P1)

        lam = BigNumber.mul(BigNumber.sub(y2, y1, p), BigNumber.inv(BigNumber.sub(x2, x1, p), p), p)
        x3 = BigNumber.sub(BigNumber.sub(BigNumber.mul(lam, lam, p), x1, p), x2, p)
        y3 = BigNumber.sub(BigNumber.mul(lam, BigNumber.sub(x1, x3, p), p), y1, p)
        return (x3, y3)

    @staticmethod
    def mul(k: int, P: Tuple[int, int]) -> Tuple[int, int]:
        """点乘运算：kP（二进制方法）"""
        result = (0, 0)  # 无穷远点
        current = P
        while k > 0:
            if k & 1:
                result = ECPoint.add(result, current)
            current = ECPoint.double(current)
            k >>= 1
        return result


# SM2协议实现
class SM2:
    def __init__(self):
        self.private_key = random.randint(1, n - 1)
        self.public_key = ECPoint.mul(self.private_key, G)

    def sign(self, msg: bytes) -> Tuple[int, int]:
        """签名算法（简化哈希为消息哈希）"""
        e = int.from_bytes(msg, byteorder='big') % n
        k = random.randint(1, n - 1)
        kG = ECPoint.mul(k, G)
        r = (e + kG[0]) % n
        s = BigNumber.mul(BigNumber.add(1, self.private_key, n),
                          BigNumber.inv(k, n), n)
        s = BigNumber.mul(BigNumber.sub(r, BigNumber.mul(self.private_key, r, n), n),
                          s, n)
        return (r, s)

    @staticmethod
    def verify(pub_key: Tuple[int, int], msg: bytes, signature: Tuple[int, int]) -> bool:
        """验签算法"""
        r, s = signature
        e = int.from_bytes(msg, byteorder='big') % n
        t = (r + s) % n
        if t == 0:
            return False
        tG = ECPoint.mul(t, G)
        sP = ECPoint.mul(s, pub_key)
        x1y1 = ECPoint.add(tG, sP)
        return (e + x1y1[0]) % n == r


# 性能测试
def performance_test():
    # 测试参数
    test_times = 100
    msg = b"SM2 Performance Test Message"

    # 初始化实例
    sm2 = SM2()

    # 大数运算性能
    start = time.time()
    for _ in range(test_times):
        a = random.getrandbits(256)
        b = random.getrandbits(256)
        BigNumber.add(a, b, p)
        BigNumber.sub(a, b, p)
        BigNumber.mul(a, b, p)
        BigNumber.inv(a % p, p)
    big_num_time = time.time() - start

    # 点运算性能
    start = time.time()
    P = ECPoint.mul(random.getrandbits(256) % n, G)
    for _ in range(test_times):
        ECPoint.double(P)
        ECPoint.add(P, G)
    point_op_time = time.time() - start

    # 签名验签性能
    start = time.time()
    for _ in range(test_times):
        sig = sm2.sign(msg)
        SM2.verify(sm2.public_key, msg, sig)
    sign_verify_time = time.time() - start

    # 输出结果
    print(f"大数运算({test_times}次)：{big_num_time:.4f}秒")
    print(f"点运算({test_times}次)：{point_op_time:.4f}秒")
    print(f"签名验签({test_times}次)：{sign_verify_time:.4f}秒")


if __name__ == "__main__":
    performance_test()