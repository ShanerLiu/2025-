# project1--SM4的软件实现及优化
# 摘要
本项目聚焦于SM4分组密码算法的高效软件实现、对比不同优化技术的原理与性能，包括循环展开、并行化、指令集优化（如AES-NI、SIMD）、T-Table方法等    
# 1.基础优化思路
循环展开：通过宏定义（如SM4_CORE_4R）将多轮运算合并，减少循环控制开销。  
并行化处理：利用64/128位寄存器并行处理2/4个数据块。
# 2.T-Table优化方法  
原理：将线性变化折叠到S盒中，预计算4个8x32的T表（共4KB），消除每轮4次循环位移操作。  
![T-Table](https://github.com/ShanerLiu/2025-/blob/main/png/SM4_T-Table.png)  
# 3. SIMD指令集优化  
SSE/AVX系列：利用128位（SSE）、256位（AVX）、512位（AVX512）寄存器并行处理多字节数据。  
例如：AVX2可同时处理4个SM4块，通过_mm256_loadu_si256等指令批量加载/存储数据。  
AVX512的VPROLD和VPTERNLOGD指令优化线形层运算。



