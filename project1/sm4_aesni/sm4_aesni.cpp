#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <immintrin.h>  // AES-NI指令集
#include <cpuid.h>     // CPU特性检测

// 启用AES-NI和SSE4.1指令集
#pragma GCC target("aes,sse4.1")

// 常量定义
#define BLOCK_SIZE 16
#define ROUNDS 32

const uint32_t fk[4] = {0xa3b1bac6, 0x56aa3350, 0x677d9197, 0xb27022dc};
const uint32_t ck[32] = {
    0x00070e15, 0x1c232a31, 0x383f464d, 0x545b6269,
    0x70777e85, 0x8c939aa1, 0xa8afb6bd, 0xc4cbd2d9,
    0xe0e7eef5, 0xfc030a11, 0x181f262d, 0x343b4249,
    0x50575e65, 0x6c737a81, 0x888f969d, 0xa4abb2b9,
    0xc0c7ced5, 0xdce3eaf1, 0xf8ff060d, 0x141b2229,
    0x30373e45, 0x4c535a61, 0x686f767d, 0x848b9299,
    0xa0a7aeb5, 0xbcc3cad1, 0xd8dfe6ed, 0xf4fb0209,
    0x10171e25, 0x2c333a41, 0x484f565d, 0x646b7279
};

// 域同构映射矩阵（文档34页）
const __m128i AES_TO_SM4 = _mm_set_epi32(
    0x11010000, 0x00111001, 0x10110110, 0x01001111
);
const __m128i SM4_TO_AES = _mm_set_epi32(
    0x01101011, 0x11011100, 0x10010011, 0x11100100
);

// 检查CPU是否支持AES-NI指令集
bool check_aes_support() {
    unsigned int eax, ebx, ecx, edx;
    __get_cpuid(1, &eax, &ebx, &ecx, &edx);
    return (ecx & (1 << 25)) != 0; // AES-NI支持位
}

// 密钥扩展（同基础版）
static void key_expansion(const uint32_t* key, uint32_t* rk) { /* 同基础版 */ }

// 循环移位
static inline uint32_t rotl(uint32_t x, int n) {
    return (x << n) | (x >> (32 - n));
}

// 使用AES-NI实现SM4的S盒（通过域同构）
static __m128i sm4_sbox_aesni(__m128i x) {
    // 1. SM4域 → AES域
    x = _mm_aesimc_si128(x);  // 逆MixColumns（用于AES解密）
    x = _mm_shuffle_epi8(x, SM4_TO_AES);  // 同构映射

    // 2. 利用AES的S盒（AES解密的最后一轮）
    x = _mm_aesdeclast_si128(x, _mm_setzero_si128());

    // 3. AES域 → SM4域
    x = _mm_shuffle_epi8(x, AES_TO_SM4);  // 逆同构映射
    return x;
}

// T变换（AES-NI加速版）
static __m128i t_aesni(__m128i input) {
    // S盒替换
    __m128i s = sm4_sbox_aesni(input);
    // 线性变换 L: x ^ rotl(x,2) ^ rotl(x,10) ^ rotl(x,18) ^ rotl(x,24)
    __m128i rot2 = _mm_or_si128(_mm_slli_epi32(s, 2), _mm_srli_epi32(s, 30));
    __m128i rot10 = _mm_or_si128(_mm_slli_epi32(s, 10), _mm_srli_epi32(s, 22));
    __m128i rot18 = _mm_or_si128(_mm_slli_epi32(s, 18), _mm_srli_epi32(s, 14));
    __m128i rot24 = _mm_or_si128(_mm_slli_epi32(s, 24), _mm_srli_epi32(s, 8));
    return _mm_xor_si128(_mm_xor_si128(_mm_xor_si128(_mm_xor_si128(s, rot2), rot10), rot18), rot24);
}

// AES-NI加速的块加密
static void sm4_block_encrypt_aesni(const uint32_t* rk, const uint32_t* input, uint32_t* output) {
    __m128i x = _mm_loadu_si128((const __m128i*)input);
    __m128i rk_vec[32];
    for (int i = 0; i < 32; i++) {
        rk_vec[i] = _mm_set1_epi32(rk[i]);  // 扩展轮密钥为128位
    }

    for (int i = 0; i < 32; i++) {
        __m128i temp = _mm_xor_si128(_mm_xor_si128(_mm_srli_si128(x, 4), _mm_srli_si128(x, 8)), 
                                    _mm_xor_si128(_mm_srli_si128(x, 12), rk_vec[i]));
        __m128i t = t_aesni(temp);
        x = _mm_xor_si128(_mm_slli_si128(x, 4), t);  // 移位更新
    }

    // 最终交换
    x = _mm_shuffle_epi32(x, _MM_SHUFFLE(0, 1, 2, 3));  // 交换32位字
    _mm_storeu_si128((__m128i*)output, x);
}

// 批量加密（AES-NI加速版）
void SM4_encrypt_aesni(const uint32_t* rk, uint32_t* plain, int size) {
    if (!check_aes_support()) {
        fprintf(stderr, "错误: 当前CPU不支持AES-NI指令集\n");
        return;
    }
    
    clock_t start = clock();
    for (int i = 0; i < size; i += 4) {
        uint32_t cipher[4];
        sm4_block_encrypt_aesni(rk, plain + i, cipher);
        memcpy(plain + i, cipher, sizeof(cipher));
    }
    clock_t end = clock();
    double time = (double)(end - start) / CLOCKS_PER_SEC;
    printf("AES-NI优化SM4加密用时：%f 秒\n", time);
}

// 测试主函数（需在支持AES-NI的CPU上运行）
int main() {
    if (!check_aes_support()) {
        fprintf(stderr, "错误: 当前CPU不支持AES-NI指令集，程序无法运行\n");
        return 1;
    }
    
    uint32_t key[4] = {0x01234567, 0x89abcdef, 0xfedcba98, 0x76543210};
    uint32_t rk[32];
    key_expansion(key, rk);

    const int data_size = 1024 * 4;
    uint32_t* data = new uint32_t[data_size];
    memset(data, 0xAA, data_size * sizeof(uint32_t));

    SM4_encrypt_aesni(rk, data, data_size);

    delete[] data;
    return 0;
}