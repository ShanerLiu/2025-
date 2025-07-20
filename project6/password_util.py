import hashlib
import os
from typing import List, Tuple, Dict

def hash_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """
    使用PBKDF2-HMAC-SHA256哈希密码

    参数:
        password: 明文密码
        salt: 可选盐值，如果未提供则生成一个新的

    返回:
        (哈希值, 盐值) 元组
    """
    if salt is None:
        salt = os.urandom(16)  # 生成16字节的随机盐

    # 使用PBKDF2-HMAC-SHA256进行100,000次迭代
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)

    return hash_obj, salt


def generate_password_hash_file(passwords: List[str], output_file: str):
    """
    生成包含密码哈希的文件

    参数:
        passwords: 明文密码列表
        output_file: 输出文件名
    """
    with open(output_file, 'wb') as f:
        for password in passwords:
            hash_val, salt = hash_password(password)
            # 格式: 盐值(16字节) + 哈希值(32字节)
            f.write(salt + hash_val + b'\n')


def load_password_hashes(file_path: str) -> List[bytes]:
    """
    从文件加载密码哈希

    参数:
        file_path: 文件路径

    返回:
        密码哈希列表
    """
    hashes = []
    with open(file_path, 'rb') as f:
        for line in f:
            line = line.strip()
            if len(line) >= 48:  # 至少包含盐值和哈希值
                salt = line[:16]
                stored_hash = line[16:48]
                hashes.append(stored_hash)
    return hashes


def check_password(password: str, stored_hash: bytes, stored_salt: bytes) -> bool:
    """
    验证密码是否匹配存储的哈希值

    参数:
        password: 明文密码
        stored_hash: 存储的哈希值
        stored_salt: 存储的盐值

    返回:
        如果匹配返回True，否则返回False
    """
    computed_hash, _ = hash_password(password, stored_salt)
    return computed_hash == stored_hash