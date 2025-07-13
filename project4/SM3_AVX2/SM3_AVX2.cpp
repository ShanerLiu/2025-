#include <iostream>
#include <vector>
#include <cstdint>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <immintrin.h>

using namespace std;
using namespace chrono;

// 常量定义（AVX2向量形式）
const __m256i T0 = _mm256_set1_epi32(0x79cc4519);
const __m256i T1 = _mm256_set1_epi32(0x7a879d8a);
const __m256i IV_vec = _mm256_set_epi32(
    0xb0fb0e4e, 0xe38dee4d, 0x163138aa, 0xa96f30bc,
    0xda8a0600, 0x172442d7, 0x4914b2b9, 0x7380166f
);

// 循环左移（32位）
inline __m256i rotl32_epi32(__m256i x, int n) {
    return _mm256_or_si256(
        _mm256_slli_epi32(x, n),
        _mm256_srli_epi32(x, 32 - n)
    );
}

// P1置换（向量化）
inline __m256i P1_vec(__m256i x) {
    return _mm256_xor_si256(
        _mm256_xor_si256(x, rotl32_epi32(x, 15)),
        rotl32_epi32(x, 23)
    );
}

// 消息扩展优化（向量化处理）
inline void msg_extend_avx2(__m256i* W, const __m256i* block) {
    // 加载初始16个字（分4个256位向量）
    W[0] = block[0];  // W0-W7
    W[1] = block[1];  // W8-W15

    // 生成W16-W67（向量化批量计算）
    for (int j = 16; j < 68; j += 8) {
        __m256i w16 = _mm256_xor_si256(
            _mm256_xor_si256(W[(j - 16) / 8], W[(j - 9) / 8]),
            rotl32_epi32(W[(j - 3) / 8], 15)
        );
        w16 = P1_vec(w16);
        w16 = _mm256_xor_si256(
            _mm256_xor_si256(w16, rotl32_epi32(W[(j - 13) / 8], 7)),
            W[(j - 6) / 8]
        );
        W[j / 8] = w16;
    }
}

// 压缩函数优化（AVX2向量并行）
inline void compress_avx2(__m256i& state, const __m256i* W, const __m256i* W1) {
    // 修正工作变量初始化
    __m256i A = _mm256_inserti128_si256(_mm256_castsi128_si256(_mm256_extracti128_si256(state, 1)), _mm256_extracti128_si256(state, 1), 1);
    __m256i B = _mm256_inserti128_si256(_mm256_castsi128_si256(_mm256_extracti128_si256(state, 1)), _mm256_extracti128_si256(state, 1), 1);
    __m256i C = state;
    __m256i D = _mm256_castsi128_si256(_mm256_extracti128_si256(state, 0));
    __m256i E = _mm256_shuffle_epi32(state, _MM_SHUFFLE(3, 2, 1, 0));
    __m256i F = _mm256_shuffle_epi32(state, _MM_SHUFFLE(2, 3, 0, 1));
    __m256i G = _mm256_shuffle_epi32(state, _MM_SHUFFLE(1, 0, 3, 2));
    __m256i H = _mm256_shuffle_epi32(state, _MM_SHUFFLE(0, 1, 2, 3));

    // 前16轮（并行处理4组）
    for (int j = 0; j < 16; j += 4) {
        __m256i T = T0;
        __m256i ss1 = rotl32_epi32(
            _mm256_add_epi32(
                _mm256_add_epi32(rotl32_epi32(A, 12), E),
                rotl32_epi32(T, j)
            ), 7
        );
        __m256i ss2 = _mm256_xor_si256(ss1, rotl32_epi32(A, 12));
        __m256i tt1 = _mm256_add_epi32(
            _mm256_add_epi32(_mm256_xor_si256(_mm256_xor_si256(A, B), C), D),
            _mm256_add_epi32(ss2, W1[j / 4])
        );
        __m256i tt2 = _mm256_add_epi32(
            _mm256_add_epi32(_mm256_xor_si256(_mm256_xor_si256(E, F), G), H),
            _mm256_add_epi32(ss1, W[j / 4])
        );

        // 更新工作变量（循环展开）
        D = C;
        C = rotl32_epi32(B, 9);
        B = A;
        A = tt1;
        H = G;
        G = rotl32_epi32(F, 19);
        F = E;
        E = P1_vec(tt2);
    }

    // 后48轮（并行处理4组）
    for (int j = 16; j < 64; j += 4) {
        __m256i T = T1;
        __m256i ss1 = rotl32_epi32(
            _mm256_add_epi32(
                _mm256_add_epi32(rotl32_epi32(A, 12), E),
                rotl32_epi32(T, j)
            ), 7
        );
        __m256i ss2 = _mm256_xor_si256(ss1, rotl32_epi32(A, 12));
        __m256i ff = _mm256_or_si256(
            _mm256_and_si256(A, B),
            _mm256_or_si256(_mm256_and_si256(A, C), _mm256_and_si256(B, C))
        );
        __m256i gg = _mm256_or_si256(
            _mm256_and_si256(E, F),
            _mm256_andnot_si256(E, G)
        );
        __m256i tt1 = _mm256_add_epi32(
            _mm256_add_epi32(ff, D),
            _mm256_add_epi32(ss2, W1[j / 4])
        );
        __m256i tt2 = _mm256_add_epi32(
            _mm256_add_epi32(gg, H),
            _mm256_add_epi32(ss1, W[j / 4])
        );

        // 更新工作变量（循环展开）
        D = C;
        C = rotl32_epi32(B, 9);
        B = A;
        A = tt1;
        H = G;
        G = rotl32_epi32(F, 19);
        F = E;
        E = P1_vec(tt2);
    }

    // 修正状态更新
    __m128i a_low = _mm256_extracti128_si256(A, 0);
    __m128i a_high = _mm256_extracti128_si256(A, 1);
    __m256i new_state = _mm256_inserti128_si256(_mm256_castsi128_si256(a_low), a_high, 1);
    state = _mm256_xor_si256(state, new_state);
}

// 优化版SM3哈希函数
vector<uint8_t> sm3_optimized(const vector<uint8_t>& msg) {
    vector<uint8_t> data = msg;
    size_t len = data.size() * 8;

    // 填充（与标准实现相同）
    data.push_back(0x80);
    while ((data.size() * 8) % 512 != 448) {
        data.push_back(0x00);
    }
    for (int i = 7; i >= 0; i--) {
        data.push_back((len >> (i * 8)) & 0xff);
    }

    // 初始化状态（AVX2向量）
    __m256i state = IV_vec;

    // 按512比特分组处理（使用AVX2批量处理）
    __m256i block[2];  // 每个block包含16个32位字（2个256位向量）
    __m256i W[9], W1[8];  // 消息扩展数组（向量化）

    for (size_t i = 0; i < data.size(); i += 64) {
        // 加载数据到AVX2寄存器
        block[0] = _mm256_loadu_si256((const __m256i*)(data.data() + i));
        block[1] = _mm256_loadu_si256((const __m256i*)(data.data() + i + 32));

        // 消息扩展
        msg_extend_avx2(W, block);

        // 生成W1
        for (int j = 0; j < 8; j++) {
            W1[j] = _mm256_xor_si256(W[j], W[j + 1]);
        }

        // 压缩
        compress_avx2(state, W, W1);
    }

    // 提取结果
    uint32_t state_arr[8];
    _mm256_storeu_si256((__m256i*)state_arr, state);

    vector<uint8_t> result(32);
    for (int i = 0; i < 8; i++) {
        result[i * 4] = (state_arr[7 - i] >> 24) & 0xff;
        result[i * 4 + 1] = (state_arr[7 - i] >> 16) & 0xff;
        result[i * 4 + 2] = (state_arr[7 - i] >> 8) & 0xff;
        result[i * 4 + 3] = state_arr[7 - i] & 0xff;
    }
    return result;
}

// 优化版性能测试
double testSM3OptimizedPerformance(size_t dataSize) {
    vector<uint8_t> data(dataSize, 0x5a);
    const int iterations = 20;  // 更多迭代次数提高精度

    auto start = high_resolution_clock::now();
    for (int i = 0; i < iterations; i++) {
        sm3_optimized(data);
    }
    auto end = high_resolution_clock::now();

    duration<double> elapsed = end - start;
    double totalBytes = dataSize * iterations;
    double mbPerSec = (totalBytes / (1024 * 1024)) / elapsed.count();
    return mbPerSec;
}

int main() {
    // 测试优化版性能
    size_t testSize = 1024 * 1024;  // 1MB测试数据
    double speed = testSM3OptimizedPerformance(testSize);
    cout << "AVX2优化实现性能: " << fixed << setprecision(2) << speed << " MB/s" << endl;

    // 验证正确性
    vector<uint8_t> emptyMsg;
    vector<uint8_t> hash = sm3_optimized(emptyMsg);
    stringstream ss;
    for (uint8_t b : hash) {
        ss << hex << setw(2) << setfill('0') << (int)b;
    }
    cout << "空消息哈希值: " << ss.str() << endl;

    return 0;
}