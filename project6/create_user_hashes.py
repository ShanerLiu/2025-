from password_util import generate_password_hash_file

# 用户密码列表
user_passwords = [
    "my_secure_password1",
    "leaked_password_abc",  # 假设这个密码已泄露
    "another_secure_password"
]

# 生成哈希文件
generate_password_hash_file(user_passwords, "user_hashes.txt")
print("用户密码哈希文件已生成: user_hashes.txt")
