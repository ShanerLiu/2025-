#include <iostream>
#include <cstdint>
#include <vector>
#include <chrono>
#include <cstring> 

using namespace std;
using namespace chrono;

// 初始哈希值
const uint32_t IV[8] = {
    0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
    0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E
};

// Tj常量
const uint32_t T[64] = {
    0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519,
    0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519, 0x79CC4519,
    0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A,
    0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A,
    0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A,
    0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A,
    0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A,
    0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A, 0x7A879D8A
};

// 循环左移
uint32_t ROTL32(uint32_t x, int n) {
    return (x << n) | (x >> (32 - n));
}

// P1函数
uint32_t P1(uint32_t x) {
    return x ^ ROTL32(x, 15) ^ ROTL32(x, 23);
}

// FF函数
uint32_t FF(uint32_t X, uint32_t Y, uint32_t Z, int j) {
    if (0 <= j && j <= 15) {
        return X ^ Y ^ Z;
    }
    else {
        return (X & Y) | (X & Z) | (Y & Z);
    }
}

// GG函数
uint32_t GG(uint32_t X, uint32_t Y, uint32_t Z, int j) {
    if (0 <= j && j <= 15) {
        return X ^ Y ^ Z;
    }
    else {
        return (X & Y) | (~X & Z);
    }
}

// 填充函数
vector<uint8_t> pad(const vector<uint8_t>& msg) {
    size_t l = msg.size() * 8;
    size_t k = (448 - l - 1) % 512;
    if (k < 0) k += 512;
    vector<uint8_t> padded = msg;
    padded.push_back(0x80);
    padded.insert(padded.end(), (k + 7) / 8, 0x00);
    for (int i = 7; i >= 0; --i) {
        padded.push_back((l >> (i * 8)) & 0xFF);
    }
    return padded;
}

// SM3哈希函数
vector<uint8_t> sm3(const vector<uint8_t>& msg) {
    vector<uint8_t> padded = pad(msg);
    size_t n = padded.size() / 64;
    uint32_t V[8];
    memcpy(V, IV, 8 * sizeof(uint32_t));

    for (size_t i = 0; i < n; ++i) {
        uint8_t* block = &padded[i * 64]; 
        uint32_t W[68], W1[64];

        // 消息扩展
        for (int j = 0; j < 16; ++j) {
            W[j] = (block[j * 4] << 24) | (block[j * 4 + 1] << 16) | (block[j * 4 + 2] << 8) | block[j * 4 + 3];
        }
        for (int j = 16; j < 68; ++j) {
            W[j] = P1(W[j - 16] ^ W[j - 9] ^ ROTL32(W[j - 3], 15)) ^ ROTL32(W[j - 13], 7) ^ W[j - 6];
        }
        for (int j = 0; j < 64; ++j) {
            W1[j] = W[j] ^ W[j + 4];
        }

        // 迭代压缩
        uint32_t A = V[0], B = V[1], C = V[2], D = V[3];
        uint32_t E = V[4], F = V[5], G = V[6], H = V[7];
        for (int j = 0; j < 64; ++j) {
            uint32_t SS1 = ROTL32(ROTL32(A, 12) + E + ROTL32(T[j], j), 7);
            uint32_t SS2 = SS1 ^ ROTL32(A, 12);
            uint32_t TT1 = FF(A, B, C, j) + D + SS2 + W1[j];
            uint32_t TT2 = GG(E, F, G, j) + H + SS1 + W[j];
            D = C;
            C = ROTL32(B, 9);
            B = A;
            A = TT1;
            H = G;
            G = ROTL32(F, 19);
            F = E;
            E = P1(TT2);
        }
        V[0] ^= A;
        V[1] ^= B;
        V[2] ^= C;
        V[3] ^= D;
        V[4] ^= E;
        V[5] ^= F;
        V[6] ^= G;
        V[7] ^= H;
    }

    // 输出哈希值
    vector<uint8_t> hash(32);
    for (int i = 0; i < 8; ++i) {
        hash[i * 4] = (V[i] >> 24) & 0xFF;
        hash[i * 4 + 1] = (V[i] >> 16) & 0xFF;
        hash[i * 4 + 2] = (V[i] >> 8) & 0xFF;
        hash[i * 4 + 3] = V[i] & 0xFF;
    }
    return hash;
}

int main() {
    // 测试数据大小：100MB
    const size_t data_size = 100 * 1024 * 1024;
    vector<uint8_t> data(data_size, 0xAA);

    auto start = high_resolution_clock::now();
    vector<uint8_t> hash = sm3(data);
    auto end = high_resolution_clock::now();

    duration<double> elapsed = end - start;
    double throughput = data_size / (1024.0 * 1024.0) / elapsed.count();
    cout << "基础实现吞吐量: " << throughput << " MB/s" << endl;

    return 0;
}
