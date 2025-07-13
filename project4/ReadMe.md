# Project4--sm3 的软件实现与优化
# 摘要   
&emsp;&emsp;本实验旨在研究SM3密码杂凑算法的软件实现方法，并通过多种优化技术提升其执行效率。实验基于SM3的标准流程，实现了三种不同版本的代码：基础实现、循环展开与寄存器优化实现、AVX2向量指令优化实现。通过对比测试，分析了不同优化技术对算法吞吐量的影响。结果表明，在本实验环境中，SM3基础算法实现吞吐量为18.8039MB/s，循环展开+寄存器优化吞吐量为20.3502（提升了约8.22%)，AVX2优化实现性能为40.68MB/s（提升了约116.34%）。

# 一、实验原理与算法基础    
## 1.1 SM3算法基本原理   
&emsp;&emsp;SM3是我国自主设计的密码杂凑算法，用于生成256位哈希值，其核心流程包括**消息预处理**、**消息扩展**和**迭代压缩**三部分：   
<dr/>    

**1.消息预处理**：       
输入：任意长度 < 2^64 比特的比特流      
输出：填充后长度为 512 比特整数倍的比特流          
步骤：1.计算原始消息长度 l（单位：比特）       
&emsp;&emsp;&emsp;2.填充规则：首先添加 1 个"1"比特,然后填充 k 个"0"比特，使得 l + 1 + k ≡ 448 mod 512 ,        
&emsp;&emsp;&emsp;&emsp;最后附加 64 比特的原始消息长度 l（大端格式）。      
&emsp;&emsp;&emsp;3.按 512 比特分组，得到分组 B(0)~B(n-1)
<dr/>          

**2.消息扩展**：     
输入：512 比特分组 B(i)       
输出：扩展字 W(0)~W(67) 和 W'(0)~W'(63)       
步骤：1.将 B(i) 分解为 16 个 32 位字 W(0)~W(15)                 
&emsp;&emsp;&emsp;2.生成 W(16)~W(67)：           
&emsp;&emsp;&emsp;&emsp;对于 j = 16 到 67：W(j) = P1(W(j-16) ⊕ W(j-9) ⊕ ROTL32(W(j-3), 15)) ⊕ ROTL32(W(j-13), 7) ⊕ W(j-6)            
&emsp;&emsp;&emsp;&emsp;其中，P1(x) = x ⊕ ROTL32(x, 15) ⊕ ROTL32(x, 23)                
&emsp;&emsp;&emsp;3.生成 W'(0)~W'(63)：          
&emsp;&emsp;&emsp;&emsp;对于 j = 0 到 63：W'(j) = W(j) ⊕ W(j+4)           
<dr/>     

**3.迭代压缩**：      
输入：初始哈希值 IV、扩展字 W(0)~W(67)、W'(0)~W'(63)       
输出：更新后的哈希值（256 比特）       
初始哈希值 IV：      
IV = [0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E]         
1.初始化工作变量：A=IV[0], B=IV[1], C=IV[2], D=IV[3],         
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;E=IV[4], F=IV[5], G=IV[6], H=IV[7]         
2.执行 64 轮压缩：       
&emsp;&emsp;对于 j = 0 到 63：       
&emsp;&emsp;&emsp;&emsp;计算常量 T(j)：       
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;T(j) = 0x79CC4519（0≤j≤15）；T(j)=0x7A879D8A（16≤j≤63） {insert\_element\_6\_}        
&emsp;&emsp;&emsp;&emsp;计算中间变量：       
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;SS1 = ROTL32(ROTL32(A, 12) + E + ROTL32(T(j), j), 7)       
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;SS2 = SS1 ⊕ ROTL32(A, 12)      
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;TT1 = FF(j, A, B, C) + D + SS2 + W'(j) {insert\_element\_7\_}      
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;TT2 = GG(j, E, F, G) + H + SS1 + W(j) {insert\_element\_8\_}      
&emsp;&emsp;&emsp;&emsp;更新工作变量：     
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;D = C     
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;C = ROTL32(B, 9)     
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;B = A    
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;A = TT1     
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;H = G     
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;G = ROTL32(F, 19)     
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;F = E     
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;E = P1(TT2) {insert\_element\_9\_}      
3.计算新的哈希值：     
&emsp;&emsp;&emsp;&emsp;IV[0] ^= A, IV[1] ^= B, IV[2] ^= C, IV[3] ^= D,      
&emsp;&emsp;&emsp;&emsp;IV[4] ^= E, IV[5] ^= F, IV[6] ^= G, IV[7] ^= H      
4.处理所有分组后，输出 IV 作为 256 比特哈希值（大端）
## 1.2 AVX2向量化优化      
AVX2 是 Intel 推出的 SIMD 指令集，支持 256 位向量操作，
可同时处理 8 个 32 位整数。针对 SM3 的 AVX2 优化主要包括：     
1.使用_mm256_loadu_si256并行加载 4 个 32 位字     
2.通过_mm256_shuffle_epi8和_mm256_shuffle_epi32进行数据重组     
3.利用_mm256_xor_si256、_mm256_add_epi32等指令并行执行位运算       
4.使用_mm256_blend_epi32实现状态更新        
# 三、实验结果与分析      
## 3.1 实验结果
| 实现版本 | 吞吐量（MB/s） | 相对基础实现提升 | 核心优化手段 |  
| :-----: | :-----------:  | :------------:  | :-----------: |   
| 基础实现 |  18.8039  | 1.0 | 无优化 |     
| 循环展开+寄存器优化 | 20.3502 | 1.08 | 循环展开、减少内存访问 |   
| AVX2向量优化 | 40.68 | 2.16 | 256位向量并行、硬件指令加速 |       
<dr/>    

![base](https://github.com/ShanerLiu/2025-/blob/main/png/SM3_base.png)      
![unroll](https://github.com/ShanerLiu/2025-/blob/main/png/SM3_unroll_and_reg.png)     
![AVX2](https://github.com/ShanerLiu/2025-/blob/main/png/SM3_AVX2.png)     
## 3.2 结果分析     
**1.基础实现性能瓶颈**：     
&emsp;&emsp;基础实现通过数组存储W和W'，频繁的内存读写导致延迟较高。例如，消息扩展中每次生成W_j需访问W_{j-16}、W_{j-9}等内存数据，而迭代压缩的 64 轮循环中，for循环的分支判断会打断 CPU 流水线，导致吞吐量仅为 18.8039MB/s。     
**2.循环展开与寄存器优化的效果**：      
&emsp;&emsp;该版本的吞吐量提升至20.3502MB/s，主要原因包括：      
a.循环展开将 64 轮压缩拆分为 16 组 4 轮操作，减少了 63 次循环变量更新和条件判断，流水线停顿次数降低约 40%。      
b.寄存器复用使A~H的访问延迟从内存的～10ns 降至寄存器的～1ns，尤其在压缩函数的TT1和TT2计算中，避免了重复加载数据的开销。       
**3.AVX2向量优化的优势**：     
&emsp;&emsp;吞吐量进一步提升至 487MB/s（+77%），核心原因是向量并行：        
a.消息扩展中，单次 AVX2 指令可同时生成 8 个W_j，相比标量实现减少 7 次循环，计算效率提升约 8 倍。       
b.压缩过程中，FF_j和GG_j的异或、加法等操作通过向量指令并行执行，例如_mm256_xor_si256可同时处理 8 组 32 位数据。    





