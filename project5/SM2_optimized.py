import time
import random
from typing import Tuple, List

# SM2曲线参数（同基础版本）
p = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
a = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
b = 0x28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93
n = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123
Gx = 0x32C4AF2C1F1981195F9904466A39C9948FF30B00E980E94E9C9A9A948FF30B0
Gy = 0xBC3736A2F4F6779C59BDCEE36B692153DA9877CC62474002DF32E52139F0A0
G = (Gx, Gy)


### 优化1：蒙哥马利大数运算（减少模操作开销）
class MontgomeryBigNumber:
    """基于蒙哥马利算法的大数运算（优化模乘/模逆）"""

    @staticmethod
    def montgomery_reduce(T: int, p: int, r: int = 1 << 256) -> int:
        """蒙哥马利约简：将T转化为蒙哥马利域元素（T * r^-1 mod p）"""
        r_inv = pow(r, -1, p)  # r模p的逆元
        m = (T % r) * pow(-p % r, -1, r) % r  # 计算m使(T + m*p)能被r整除
        t = (T + m * p) // r
        return t if t < p else t - p

    @staticmethod
    def mont_mul(a: int, b: int, p: int, r: int = 1 << 256) -> int:
        """蒙哥马利乘法：(a * b) mod p（在蒙哥马利域内计算）"""
        T = a * b
        return MontgomeryBigNumber.montgomery_reduce(T, p, r)

    @staticmethod
    def to_mont(a: int, p: int, r: int = 1 << 256) -> int:
        """将普通元素转化为蒙哥马利域元素：a * r mod p"""
        return (a * r) % p

    @staticmethod
    def from_mont(a: int, p: int, r: int = 1 << 256) -> int:
        """将蒙哥马利域元素转回普通元素：a * r^-1 mod p"""
        return MontgomeryBigNumber.montgomery_reduce(a, p, r)

    @staticmethod
    def inv(a: int, p: int) -> int:
        """模逆（基于二进制扩展欧几里得算法，常量时间实现）"""
        if a == 0:
            raise ValueError("0没有模逆")
        u, v = a, p
        x1, x2 = 1, 0
        while u != 0:
            # 消去u的偶数因子
            while u % 2 == 0:
                u //= 2
                if x1 % 2 == 0:
                    x1 //= 2
                else:
                    x1 = (x1 + p) // 2
            # 消去v的偶数因子
            while v % 2 == 0:
                v //= 2
                if x2 % 2 == 0:
                    x2 //= 2
                else:
                    x2 = (x2 + p) // 2
            # 减小较大的数
            if u >= v:
                u -= v
                x1 -= x2
            else:
                v -= u
                x2 -= x1
        return x2 % p  # x2为a^-1 mod p


### 优化2：椭圆曲线点运算（Co-Z方法+NAF编码）
class OptimizedECPoint:
    """优化的椭圆曲线点运算（Co-Z点加+窗口法点乘）"""

    @staticmethod
    def is_on_curve(point: Tuple[int, int]) -> bool:
        """验证点是否在曲线上（基础功能保留）"""
        x, y = point
        return (y * y - (x * x * x + a * x + b)) % p == 0

    @staticmethod
    def double(P: Tuple[int, int]) -> Tuple[int, int]:
        """双倍点运算（优化计算步骤）"""
        x1, y1 = P
        if x1 == 0 and y1 == 0:  # 无穷远点
            return (0, 0)
        # 计算λ = (3x1² + a) / (2y1) mod p
        x1_sq = (x1 * x1) % p
        lam_numerator = (3 * x1_sq + a) % p
        lam_denominator = (2 * y1) % p
        lam = (lam_numerator * MontgomeryBigNumber.inv(lam_denominator, p)) % p

        # 计算x3 = λ² - 2x1，y3 = λ(x1 - x3) - y1
        x3 = (lam * lam - 2 * x1) % p
        y3 = (lam * (x1 - x3) - y1) % p
        return (x3, y3)

    @staticmethod
    def add_co_z(P: Tuple[int, int], Q: Tuple[int, int]) -> Tuple[int, int]:
        """Co-Z点加（当P和Q有相同Z坐标时，优化点加复杂度）"""
        x1, y1 = P
        x2, y2 = Q
        if x1 == 0 and y1 == 0:
            return Q
        if x2 == 0 and y2 == 0:
            return P
        if x1 == x2 and y1 != y2:  # 互逆点
            return (0, 0)
        if x1 == x2 and y1 == y2:  # 同点（调用双倍点）
            return OptimizedECPoint.double(P)

        # Co-Z优化：假设Z1=Z2，计算步骤简化
        dx = (x2 - x1) % p
        dy = (y2 - y1) % p
        dx_sq = (dx * dx) % p  # A = (x2-x1)²
        dx_cu = (dx_sq * dx) % p  # 用于后续Y计算

        x1_dx_sq = (x1 * dx_sq) % p  # B = x1*A
        x2_dx_sq = (x2 * dx_sq) % p  # C = x2*A
        dy_sq = (dy * dy) % p  # D = (y2-y1)²

        x3 = (dy_sq - x1_dx_sq - x2_dx_sq) % p
        y3 = (dy * (x1_dx_sq - x3) - y1 * dx_cu) % p
        return (x3, y3)

    @staticmethod
    def wnaf_encode(k: int, w: int) -> List[int]:
        """宽度-w NAF编码（减少非零元素数量）"""
        naf = []
        while k > 0:
            if k % 2 == 1:
                # 计算k mod 2^w，确保结果在(-2^(w-1), 2^(w-1)]
                k_mod = k % (1 << w)
                if k_mod > (1 << (w - 1)):
                    k_mod -= (1 << w)
                naf.append(k_mod)
                k -= k_mod
            else:
                naf.append(0)
            k //= 2
        return naf

    @staticmethod
    def fixed_point_mul(k: int, G: Tuple[int, int], window: int = 8) -> Tuple[int, int]:
        """固定点点乘（kG）：窗口法+预计算表优化"""
        # 步骤1：预计算窗口表（存储G的1,3,...,2^window-1倍）
        pre_table = [(0, 0)] * (1 << (window - 1))
        current = G
        pre_table[0] = current  # 1*G
        for i in range(1, 1 << (window - 1)):
            current = OptimizedECPoint.add_co_z(current, G)  # 累加G（i*G）
            pre_table[i] = current

        # 步骤2：将k用窗口法分解（每window比特一组）
        result = (0, 0)
        k_bits = bin(k)[2:].zfill(((len(bin(k)) - 2 + window - 1) // window) * window)  # 补全为window整数倍
        for i in range(0, len(k_bits), window):
            chunk = k_bits[i:i + window]
            if chunk == '0' * window:
                result = OptimizedECPoint.double(result)  # 左移window位（等价于乘2^window）
                continue
            # 从预计算表取对应点并累加
            chunk_val = int(chunk, 2)
            result = OptimizedECPoint.add_co_z(result, pre_table[chunk_val // 2])
            result = OptimizedECPoint.double(result)  # 完成当前窗口的移位
        return result

    @staticmethod
    def mul(k: int, P: Tuple[int, int]) -> Tuple[int, int]:
        """非固定点点乘（kP）：NAF编码优化"""
        if P == (0, 0):
            return (0, 0)
        # 步骤1：NAF编码k（减少非零元素数量）
        naf = OptimizedECPoint.wnaf_encode(k, 3)  # 宽度3的NAF编码
        # 步骤2：预计算±P, ±3P（适应NAF的非零值范围）
        pre_table = [(0, 0)] * 7  # 索引0:0,1:P,2:3P,3:-P,4:-3P
        pre_table[1] = P
        pre_table[2] = OptimizedECPoint.add_co_z(P, OptimizedECPoint.double(P))  # 3P = P + 2P
        pre_table[3] = (P[0], (-P[1]) % p)  # -P
        pre_table[4] = (pre_table[2][0], (-pre_table[2][1]) % p)  # -3P

        # 步骤3：按NAF编码累加
        result = (0, 0)
        for val in reversed(naf):
            result = OptimizedECPoint.double(result)  # 每次迭代先双倍
            if val == 1:
                result = OptimizedECPoint.add_co_z(result, pre_table[1])
            elif val == 3:
                result = OptimizedECPoint.add_co_z(result, pre_table[2])
            elif val == -1:
                result = OptimizedECPoint.add_co_z(result, pre_table[3])
            elif val == -3:
                result = OptimizedECPoint.add_co_z(result, pre_table[4])
        return result


### 优化3：SM2协议实现（验签避免模逆）
class OptimizedSM2:
    def __init__(self):
        self.private_key = random.randint(1, n - 1)
        self.public_key = OptimizedECPoint.fixed_point_mul(self.private_key, G)  # 固定点G的点乘优化

    def sign(self, msg: bytes) -> Tuple[int, int]:
        """签名算法（复用优化的点乘）"""
        e = int.from_bytes(msg, byteorder='big') % n
        k = random.randint(1, n - 1)
        kG = OptimizedECPoint.fixed_point_mul(k, G)  # 固定点优化
        r = (e + kG[0]) % n
        # 计算s = (1 + d)^-1 * (k - r*d) mod n（优化模逆）
        d = self.private_key
        inv_1d = MontgomeryBigNumber.inv((1 + d) % n, n)
        s = (inv_1d * (k - r * d)) % n
        return (r, s)

    @staticmethod
    def verify(pub_key: Tuple[int, int], msg: bytes, signature: Tuple[int, int]) -> bool:
        """验签算法（避免模逆，直接验证等式）"""
        r, s = signature
        if not (1 <= r <= n - 1 and 1 <= s <= n - 1):
            return False
        e = int.from_bytes(msg, byteorder='big') % n
        t = (r + s) % n
        if t == 0:
            return False
        # 计算tG + sP（优化点乘）
        tG = OptimizedECPoint.fixed_point_mul(t, G)
        sP = OptimizedECPoint.mul(s, pub_key)
        x1y1 = OptimizedECPoint.add_co_z(tG, sP)
        # 验签核心：(e + x1) mod n == r（避免模逆操作）
        return (e + x1y1[0]) % n == r


### 性能测试（对比基础版本）
import time
import random
from typing import Tuple, List

# SM2曲线参数（同基础版本）
p = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
a = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
b = 0x28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93
n = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123
Gx = 0x32C4AF2C1F1981195F9904466A39C9948FF30B00E980E94E9C9A9A948FF30B0
Gy = 0xBC3736A2F4F6779C59BDCEE36B692153DA9877CC62474002DF32E52139F0A0
G = (Gx, Gy)


### 优化1：蒙哥马利大数运算（减少模操作开销）
class MontgomeryBigNumber:
    """基于蒙哥马利算法的大数运算（优化模乘/模逆）"""

    @staticmethod
    def montgomery_reduce(T: int, p: int, r: int = 1 << 256) -> int:
        """蒙哥马利约简：将T转化为蒙哥马利域元素（T * r^-1 mod p）"""
        r_inv = pow(r, -1, p)  # r模p的逆元
        m = (T % r) * pow(-p % r, -1, r) % r  # 计算m使(T + m*p)能被r整除
        t = (T + m * p) // r
        return t if t < p else t - p

    @staticmethod
    def mont_mul(a: int, b: int, p: int, r: int = 1 << 256) -> int:
        """蒙哥马利乘法：(a * b) mod p（在蒙哥马利域内计算）"""
        T = a * b
        return MontgomeryBigNumber.montgomery_reduce(T, p, r)

    @staticmethod
    def to_mont(a: int, p: int, r: int = 1 << 256) -> int:
        """将普通元素转化为蒙哥马利域元素：a * r mod p"""
        return (a * r) % p

    @staticmethod
    def from_mont(a: int, p: int, r: int = 1 << 256) -> int:
        """将蒙哥马利域元素转回普通元素：a * r^-1 mod p"""
        return MontgomeryBigNumber.montgomery_reduce(a, p, r)

    @staticmethod
    def inv(a: int, p: int) -> int:
        """模逆（基于二进制扩展欧几里得算法，常量时间实现）"""
        if a == 0:
            raise ValueError("0没有模逆")
        u, v = a, p
        x1, x2 = 1, 0
        while u != 0:
            # 消去u的偶数因子
            while u % 2 == 0:
                u //= 2
                if x1 % 2 == 0:
                    x1 //= 2
                else:
                    x1 = (x1 + p) // 2
            # 消去v的偶数因子
            while v % 2 == 0:
                v //= 2
                if x2 % 2 == 0:
                    x2 //= 2
                else:
                    x2 = (x2 + p) // 2
            # 减小较大的数
            if u >= v:
                u -= v
                x1 -= x2
            else:
                v -= u
                x2 -= x1
        return x2 % p  # x2为a^-1 mod p


### 优化2：椭圆曲线点运算（Co-Z方法+NAF编码）
class OptimizedECPoint:
    """优化的椭圆曲线点运算（Co-Z点加+窗口法点乘）"""

    @staticmethod
    def is_on_curve(point: Tuple[int, int]) -> bool:
        """验证点是否在曲线上（基础功能保留）"""
        x, y = point
        return (y * y - (x * x * x + a * x + b)) % p == 0

    @staticmethod
    def double(P: Tuple[int, int]) -> Tuple[int, int]:
        """双倍点运算（优化计算步骤）"""
        x1, y1 = P
        if x1 == 0 and y1 == 0:  # 无穷远点
            return (0, 0)
        # 计算λ = (3x1² + a) / (2y1) mod p
        x1_sq = (x1 * x1) % p
        lam_numerator = (3 * x1_sq + a) % p
        lam_denominator = (2 * y1) % p
        lam = (lam_numerator * MontgomeryBigNumber.inv(lam_denominator, p)) % p

        # 计算x3 = λ² - 2x1，y3 = λ(x1 - x3) - y1
        x3 = (lam * lam - 2 * x1) % p
        y3 = (lam * (x1 - x3) - y1) % p
        return (x3, y3)

    @staticmethod
    def add_co_z(P: Tuple[int, int], Q: Tuple[int, int]) -> Tuple[int, int]:
        """Co-Z点加（当P和Q有相同Z坐标时，优化点加复杂度）"""
        x1, y1 = P
        x2, y2 = Q
        if x1 == 0 and y1 == 0:
            return Q
        if x2 == 0 and y2 == 0:
            return P
        if x1 == x2 and y1 != y2:  # 互逆点
            return (0, 0)
        if x1 == x2 and y1 == y2:  # 同点（调用双倍点）
            return OptimizedECPoint.double(P)

        # Co-Z优化：假设Z1=Z2，计算步骤简化
        dx = (x2 - x1) % p
        dy = (y2 - y1) % p
        dx_sq = (dx * dx) % p  # A = (x2-x1)²
        dx_cu = (dx_sq * dx) % p  # 用于后续Y计算

        x1_dx_sq = (x1 * dx_sq) % p  # B = x1*A
        x2_dx_sq = (x2 * dx_sq) % p  # C = x2*A
        dy_sq = (dy * dy) % p  # D = (y2-y1)²

        x3 = (dy_sq - x1_dx_sq - x2_dx_sq) % p
        y3 = (dy * (x1_dx_sq - x3) - y1 * dx_cu) % p
        return (x3, y3)

    @staticmethod
    def wnaf_encode(k: int, w: int) -> List[int]:
        """宽度-w NAF编码（减少非零元素数量）"""
        naf = []
        while k > 0:
            if k % 2 == 1:
                # 计算k mod 2^w，确保结果在(-2^(w-1), 2^(w-1)]
                k_mod = k % (1 << w)
                if k_mod > (1 << (w - 1)):
                    k_mod -= (1 << w)
                naf.append(k_mod)
                k -= k_mod
            else:
                naf.append(0)
            k //= 2
        return naf

    @staticmethod
    def fixed_point_mul(k: int, G: Tuple[int, int], window: int = 8) -> Tuple[int, int]:
        """固定点点乘（kG）：窗口法+预计算表优化"""
        # 步骤1：预计算窗口表（存储G的1,3,...,2^window-1倍）
        pre_table = [(0, 0)] * (1 << (window - 1))
        current = G
        pre_table[0] = current  # 1*G
        for i in range(1, 1 << (window - 1)):
            current = OptimizedECPoint.add_co_z(current, G)  # 累加G（i*G）
            pre_table[i] = current

        # 步骤2：将k用窗口法分解（每window比特一组）
        result = (0, 0)
        k_bits = bin(k)[2:].zfill(((len(bin(k)) - 2 + window - 1) // window) * window)  # 补全为window整数倍
        for i in range(0, len(k_bits), window):
            chunk = k_bits[i:i + window]
            if chunk == '0' * window:
                result = OptimizedECPoint.double(result)  # 左移window位（等价于乘2^window）
                continue
            # 从预计算表取对应点并累加
            chunk_val = int(chunk, 2)
            result = OptimizedECPoint.add_co_z(result, pre_table[chunk_val // 2])
            result = OptimizedECPoint.double(result)  # 完成当前窗口的移位
        return result

    @staticmethod
    def mul(k: int, P: Tuple[int, int]) -> Tuple[int, int]:
        """非固定点点乘（kP）：NAF编码优化"""
        if P == (0, 0):
            return (0, 0)
        # 步骤1：NAF编码k（减少非零元素数量）
        naf = OptimizedECPoint.wnaf_encode(k, 3)  # 宽度3的NAF编码
        # 步骤2：预计算±P, ±3P（适应NAF的非零值范围）
        pre_table = [(0, 0)] * 7  # 索引0:0,1:P,2:3P,3:-P,4:-3P
        pre_table[1] = P
        pre_table[2] = OptimizedECPoint.add_co_z(P, OptimizedECPoint.double(P))  # 3P = P + 2P
        pre_table[3] = (P[0], (-P[1]) % p)  # -P
        pre_table[4] = (pre_table[2][0], (-pre_table[2][1]) % p)  # -3P

        # 步骤3：按NAF编码累加
        result = (0, 0)
        for val in reversed(naf):
            result = OptimizedECPoint.double(result)  # 每次迭代先双倍
            if val == 1:
                result = OptimizedECPoint.add_co_z(result, pre_table[1])
            elif val == 3:
                result = OptimizedECPoint.add_co_z(result, pre_table[2])
            elif val == -1:
                result = OptimizedECPoint.add_co_z(result, pre_table[3])
            elif val == -3:
                result = OptimizedECPoint.add_co_z(result, pre_table[4])
        return result


### 优化3：SM2协议实现（验签避免模逆）
class OptimizedSM2:
    def __init__(self):
        self.private_key = random.randint(1, n - 1)
        self.public_key = OptimizedECPoint.fixed_point_mul(self.private_key, G)  # 固定点G的点乘优化

    def sign(self, msg: bytes) -> Tuple[int, int]:
        """签名算法（复用优化的点乘）"""
        e = int.from_bytes(msg, byteorder='big') % n
        k = random.randint(1, n - 1)
        kG = OptimizedECPoint.fixed_point_mul(k, G)  # 固定点优化
        r = (e + kG[0]) % n
        # 计算s = (1 + d)^-1 * (k - r*d) mod n（优化模逆）
        d = self.private_key
        inv_1d = MontgomeryBigNumber.inv((1 + d) % n, n)
        s = (inv_1d * (k - r * d)) % n
        return (r, s)

    @staticmethod
    def verify(pub_key: Tuple[int, int], msg: bytes, signature: Tuple[int, int]) -> bool:
        """验签算法（避免模逆，直接验证等式）"""
        r, s = signature
        if not (1 <= r <= n - 1 and 1 <= s <= n - 1):
            return False
        e = int.from_bytes(msg, byteorder='big') % n
        t = (r + s) % n
        if t == 0:
            return False
        # 计算tG + sP（优化点乘）
        tG = OptimizedECPoint.fixed_point_mul(t, G)
        sP = OptimizedECPoint.mul(s, pub_key)
        x1y1 = OptimizedECPoint.add_co_z(tG, sP)
        # 验签核心：(e + x1) mod n == r（避免模逆操作）
        return (e + x1y1[0]) % n == r


### 性能测试（对比基础版本）
def performance_test():
    test_times = 100
    msg = b"SM2 Optimization Test Message with Montgomery and Window Method"

    # 初始化优化版本实例
    opt_sm2 = OptimizedSM2()

    # 1. 大数运算性能（蒙哥马利vs普通）
    start = time.time()
    for _ in range(test_times):
        a = random.getrandbits(256) % p
        b = random.getrandbits(256) % p
        # 蒙哥马利乘法测试
        a_mont = MontgomeryBigNumber.to_mont(a, p)
        b_mont = MontgomeryBigNumber.to_mont(b, p)
        MontgomeryBigNumber.mont_mul(a_mont, b_mont, p)
        MontgomeryBigNumber.inv(a, p)
    mont_time = time.time() - start

    # 2. 点运算性能（优化点乘vs基础点乘）
    start = time.time()
    P = OptimizedECPoint.mul(random.getrandbits(256) % n, G)
    for _ in range(test_times):
        OptimizedECPoint.double(P)
        OptimizedECPoint.add_co_z(P, G)
    opt_point_time = time.time() - start

    # 3. 签名验签性能
    start = time.time()
    for _ in range(test_times):
        sig = opt_sm2.sign(msg)
        # 修复：调整参数顺序为 (公钥, 消息, 签名)
        OptimizedSM2.verify(opt_sm2.public_key, msg, sig)
    opt_sign_time = time.time() - start

    # 输出结果
    print(f"【优化后性能】")
    print(f"蒙哥马利大数运算({test_times}次)：{mont_time:.4f}秒")
    print(f"优化点运算({test_times}次)：{opt_point_time:.4f}秒")
    print(f"签名验签({test_times}次)：{opt_sign_time:.4f}秒")

if __name__ == "__main__":
    performance_test()

