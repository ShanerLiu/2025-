from password_util import generate_password_hash_file

# 泄露密码列表
leaked_passwords = [
    "leaked_password_abc",  # 与用户密码重复，模拟泄露
    "common_password_123",
    "p@ssw0rd"
]

generate_password_hash_file(leaked_passwords, "leaked_hashes.txt")
print("泄露密码哈希文件已生成: leaked_hashes.txt")
