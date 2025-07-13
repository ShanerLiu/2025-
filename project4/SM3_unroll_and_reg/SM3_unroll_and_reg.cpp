#include <iostream>
#include <cstdint>
#include <vector>
#include <chrono>
#include <immintrin.h>
#include <cstring>  // 添加缺少的头文件

using namespace std;
using namespace chrono;

const uint32_t IV[8] = {
    0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
    0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E
};

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

uint32_t ROTL32(uint32_t x, int n) {
    return (x << n) | (x >> (32 - n));
}

uint32_t P1(uint32_t x) {
    return x ^ ROTL32(x, 15) ^ ROTL32(x, 23);
}

uint32_t FF0(uint32_t X, uint32_t Y, uint32_t Z) { return X ^ Y ^ Z; }
uint32_t FF1(uint32_t X, uint32_t Y, uint32_t Z) { return (X & Y) | (X & Z) | (Y & Z); }
uint32_t GG0(uint32_t X, uint32_t Y, uint32_t Z) { return X ^ Y ^ Z; }
uint32_t GG1(uint32_t X, uint32_t Y, uint32_t Z) { return (X & Y) | (~X & Z); }

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

// 将ROUND宏改为内联函数，避免变量重复定义
inline void round_function(uint32_t& A, uint32_t& B, uint32_t& C, uint32_t& D,
    uint32_t& E, uint32_t& F, uint32_t& G, uint32_t& H,
    uint32_t W[], uint32_t W1[], int j,
    uint32_t(*FF)(uint32_t, uint32_t, uint32_t),
    uint32_t(*GG)(uint32_t, uint32_t, uint32_t)) {
    uint32_t SS1 = ROTL32(ROTL32(A, 12) + E + ROTL32(T[j], 7), 7); // 修正为ROTL32(T[j], 7)
    uint32_t SS2 = SS1 ^ ROTL32(A, 12);
    uint32_t TT1 = FF(A, B, C) + D + SS2 + W1[j];
    uint32_t TT2 = GG(E, F, G) + H + SS1 + W[j];
    D = C;
    C = ROTL32(B, 9);
    B = A;
    A = TT1;
    H = G;
    G = ROTL32(F, 19);
    F = E;
    E = P1(TT2);
}

vector<uint8_t> sm3_optimized1(const vector<uint8_t>& msg) {
    vector<uint8_t> padded = pad(msg);
    size_t n = padded.size() / 64;
    uint32_t V[8];
    memcpy(V, IV, 8 * sizeof(uint32_t));

    for (size_t i = 0; i < n; ++i) {
        uint8_t* block = &padded[i * 64];  // 重命名为block避免冲突
        uint32_t W[68], W1[64];

        // 消息扩展（循环展开）
        W[0] = (block[0] << 24) | (block[1] << 16) | (block[2] << 8) | block[3];
        W[1] = (block[4] << 24) | (block[5] << 16) | (block[6] << 8) | block[7];
        W[2] = (block[8] << 24) | (block[9] << 16) | (block[10] << 8) | block[11];
        W[3] = (block[12] << 24) | (block[13] << 16) | (block[14] << 8) | block[15];
        W[4] = (block[16] << 24) | (block[17] << 16) | (block[18] << 8) | block[19];
        W[5] = (block[20] << 24) | (block[21] << 16) | (block[22] << 8) | block[23];
        W[6] = (block[24] << 24) | (block[25] << 16) | (block[26] << 8) | block[27];
        W[7] = (block[28] << 24) | (block[29] << 16) | (block[30] << 8) | block[31];
        W[8] = (block[32] << 24) | (block[33] << 16) | (block[34] << 8) | block[35];
        W[9] = (block[36] << 24) | (block[37] << 16) | (block[38] << 8) | block[39];
        W[10] = (block[40] << 24) | (block[41] << 16) | (block[42] << 8) | block[43];
        W[11] = (block[44] << 24) | (block[45] << 16) | (block[46] << 8) | block[47];
        W[12] = (block[48] << 24) | (block[49] << 16) | (block[50] << 8) | block[51];
        W[13] = (block[52] << 24) | (block[53] << 16) | (block[54] << 8) | block[55];
        W[14] = (block[56] << 24) | (block[57] << 16) | (block[58] << 8) | block[59];
        W[15] = (block[60] << 24) | (block[61] << 16) | (block[62] << 8) | block[63];

        for (int j = 16; j < 68; ++j) {
            W[j] = P1(W[j - 16] ^ W[j - 9] ^ ROTL32(W[j - 3], 15)) ^ ROTL32(W[j - 13], 7) ^ W[j - 6];
        }
        for (int j = 0; j < 64; ++j) {
            W1[j] = W[j] ^ W[j + 4];
        }

        // 迭代压缩（循环展开4轮）
        uint32_t A = V[0], b = V[1], C = V[2], D = V[3];  // 将B改为b避免冲突
        uint32_t E = V[4], F = V[5], G = V[6], H = V[7];

        // 前16轮
        for (int j = 0; j < 16; j += 4) {
            round_function(A, b, C, D, E, F, G, H, W, W1, j, FF0, GG0);
            round_function(A, b, C, D, E, F, G, H, W, W1, j + 1, FF0, GG0);
            round_function(A, b, C, D, E, F, G, H, W, W1, j + 2, FF0, GG0);
            round_function(A, b, C, D, E, F, G, H, W, W1, j + 3, FF0, GG0);
        }
        for (int j = 16; j < 64; j += 4) {
            round_function(A, b, C, D, E, F, G, H, W, W1, j, FF1, GG1);
            round_function(A, b, C, D, E, F, G, H, W, W1, j + 1, FF1, GG1);
            round_function(A, b, C, D, E, F, G, H, W, W1, j + 2, FF1, GG1);
            round_function(A, b, C, D, E, F, G, H, W, W1, j + 3, FF1, GG1);
        }

        V[0] ^= A;
        V[1] ^= b;  // 使用小写b
        V[2] ^= C;
        V[3] ^= D;
        V[4] ^= E;
        V[5] ^= F;
        V[6] ^= G;
        V[7] ^= H;
    }

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
    const size_t data_size = 100 * 1024 * 1024;
    vector<uint8_t> data(data_size, 0xAA);

    auto start = high_resolution_clock::now();
    vector<uint8_t> hash = sm3_optimized1(data);
    auto end = high_resolution_clock::now();

    duration<double> elapsed = end - start;
    double throughput = data_size / (1024.0 * 1024.0) / elapsed.count();
    cout << "循环展开+寄存器优化吞吐量: " << throughput << " MB/s" << endl;

    return 0;
}