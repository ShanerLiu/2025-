# project1--SM4的软件实现及优化
# 摘要
本项目聚焦于SM4分组密码算法的高效软件实现、对比不同优化技术的原理与性能，包括循环展开、并行化、指令集优化（如AES-NI、SIMD）、T-Table方法等。    
# 1.基础优化思路
**循环展开**：通过宏定义（如SM4_CORE_4R）将多轮运算合并，减少循环控制开销。  
**并行化处理**：利用64/128位寄存器并行处理2/4个数据块。
# 2.T-Table优化方法  
**原理**：将线性变化折叠到S盒中，预计算4个8x32的T表（共4KB），消除每轮4次循环位移操作。  
![T-Table](https://github.com/ShanerLiu/2025-/blob/main/png/SM4_T-Table.png)  
# 3. SIMD指令集优化  
**SSE/AVX系列**：利用128位（SSE）、256位（AVX）、512位（AVX512）寄存器并行处理多字节数据。  
**例如**：AVX2可同时处理4个SM4块，通过_mm256_loadu_si256等指令批量加载/存储数据。  
AVX512的VPROLD和VPTERNLOGD指令优化线形层运算。
![SIMD](https://github.com/ShanerLiu/2025-/blob/main/png/SIMD.png)
# 4.利用AES-NI加速SM4
**域同构原理**：SM4与AES的S盒均基于有限域GF(2^8)逆运算，通过同构映射SBox_SM4(x)=(x·A₁+C₁)⁻¹·A₂+C₂，可将SM4的S盒运算转换为AES-NI支持的操作。  
![isomorphic](https://github.com/ShanerLiu/2025-/blob/main/png/%E5%90%8C%E6%9E%84.png)  
# 5.性能数据对比
将五种加密方案分别运行20次后的时间进行对比： 
| 优化方案 | 基础 | 循环展开 | 并行 | T-Table | AES-NI同构 |
| :----: | :---: | :----: | :----: | :----: | :----: |
| 二十次加密均值|1.25s|1.03s| 0.62s | 0.47s | 0.03s | 
| 优化程度 | - | 17.6% | 50.4% | 62.4% | 97.6% |



