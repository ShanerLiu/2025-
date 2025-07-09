#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <thread>
#include <vector>

// 常量定义
#define m_bits 10000000
#define THREAD_NUM 4  // 线程数量
const uint32_t fk[4] = {0xa3b1bac6, 0x56aa3350, 0x677d9197, 0xb27022dc};
const uint32_t ck[32] = {/* 同基础实现 */};
const uint8_t s_box[256] = {/* 同基础实现 */};

// 辅助函数
static uint32_t rol(uint32_t data, int length) {
    return (data << length) | (data >> (32 - length));
}

static uint32_t t_transform(uint32_t input) {
    uint8_t b[4];
    b[0] = (input>>24)&0xFF;
    b[1] = (input>>16)&0xFF;
    b[2] = (input>>8)&0xFF;
    b[3] = input&0xFF;
    for (int i = 0; i < 4; i++) b[i] = s_box[b[i]];
    uint32_t c = (b[0]<<24)|(b[1]<<16)|(b[2]<<8)|b[3];
    return c ^ rol(c,2) ^ rol(c,10) ^ rol(c,18) ^ rol(c,24);
}

static void generate_round_keys(const uint32_t* key, uint32_t* rk) {
    uint32_t k[36];
    for (int i = 0; i < 4; i++) k[i] = key[i] ^ fk[i];
    for (int i = 0; i < 32; i++) {
        uint32_t t = k[i+1] ^ k[i+2] ^ k[i+3] ^ ck[i];
        uint8_t b[4];
        b[0] = (t>>24)&0xFF;
        b[1] = (t>>16)&0xFF;
        b[2] = (t>>8)&0xFF;
        b[3] = t&0xFF;
        for (int j = 0; j < 4; j++) b[j] = s_box[b[j]];
        t = (b[0]<<24)|(b[1]<<16)|(b[2]<<8)|b[3];
        t ^= rol(t,13) ^ rol(t,23);
        rk[i] = k[i] ^ t;
        k[i+4] = rk[i];
    }
}

// 单线程加密函数（处理部分数据）
static void thread_encrypt(const uint32_t* rk, uint32_t* plain, int start_idx, int end_idx) {
    uint32_t state[4], temp[4];
    for (int i = start_idx; i < end_idx; i += 4) {
        state[0] = plain[i];
        state[1] = plain[i+1];
        state[2] = plain[i+2];
        state[3] = plain[i+3];
        
        for (int round = 0; round < 32; round++) {
            temp[0] = state[1];
            temp[1] = state[2];
            temp[2] = state[3];
            temp[3] = state[0] ^ t_transform(state[1]^state[2]^state[3]^rk[round]);
            memcpy(state, temp, sizeof(state));
        }
        
        plain[i] = state[3];
        plain[i+1] = state[2];
        plain[i+2] = state[1];
        plain[i+3] = state[0];
    }
}

// 多线程加密
void sm4_encrypt_multithread(const uint32_t* rk, uint32_t* plain, int size) {
    clock_t start_time = clock();  // 重命名避免冲突
    std::vector<std::thread> threads;
    int block_per_thread = (size + THREAD_NUM - 1) / THREAD_NUM;
    
    // 启动线程
    for (int t = 0; t < THREAD_NUM; t++) {
        int start_idx = t * block_per_thread;  // 重命名避免冲突
        int end_idx = (t + 1) * block_per_thread;
        if (end_idx > size) end_idx = size;
        threads.emplace_back(thread_encrypt, rk, plain, start_idx, end_idx);
    }
    
    // 等待所有线程完成
    for (auto& th : threads) {
        th.join();
    }
    
    clock_t end_time = clock();  // 重命名避免冲突
    double time = (double)(end_time - start_time) / CLOCKS_PER_SEC;
    printf("多线程SM4用时: %f 秒\n", time);
}

int main() {
    uint32_t key[4] = {0x01234567, 0x89abcdef, 0xfedcba98, 0x76543210};
    uint32_t* plain = (uint32_t*)malloc(sizeof(uint32_t) * m_bits);
    for (int i = 0; i < m_bits; i++) plain[i] = rand();
    
    uint32_t rk[32];
    generate_round_keys(key, rk);
    
    sm4_encrypt_multithread(rk, plain, m_bits);
    
    free(plain);
    return 0;
}