# Project5--SM2的软件实现以及优化
# 摘要  
&emsp;&emsp;本实验旨在实现 SM2 椭圆曲线密码算法的核心功能，并通过算法优化提升其运行性能。实验首先基于 SM2 算法标准实现了基础版本的大数运算、
椭圆曲线点运算及签名、验签等协议功能，随后结合蒙哥马利模约、NAF 编码、Co-Z 点加等优化技术对关键模块进行改进。
# 一、实验目标   
## 1.1 SM2基础实现
&emsp;&emsp;实现 SM2 算法的基础功能，包括大数运算（加、减、乘、模逆）、椭圆曲线点运算（点加、双倍点、点乘）及签名、验签协议。       
## 1.2 SM2优化实现   
&emsp;&emsp;基于算法原理设计优化方案，降低关键运算的计算复杂度。       
## 1.3 性能测试与对比    
&emsp;&emsp;通过性能测试对比基础版本与优化版本的效率，验证优化效果。       
# 二、实验原理    
## 2.1 SM2核心结构   
&emsp;&emsp;SM2是我国自主设计的椭圆曲线密码算法，基于椭圆曲线离散对数问题（ECDLP），核心结构包括三部分：       
**1.大数运算**：256 比特多精度运算（加、减、乘、模逆等），是所有密码操作的基础。     
**2.椭圆曲线点运算**：基于椭圆曲线方程y^2=x^3+ax+b的点运算，包括双倍点（2P）、点加（P+Q）、点乘（kP、即k次点加）。        
**3.协议实现**：基于点运算的密码协议，如签名、验签、加解密，密钥协商等。        
## 2.2 关键优化技术    
### 2.2.1 蒙哥马利大数运算
&emsp;&emsp;蒙哥马利大数运算由三个核心算法构成，相互协作实现高效计算：       
**a.蒙哥马利模乘**：    
功能：计算c=a*R mod N、b'=b*R mod N。       
步骤：（1）域转换：预计算a'=a*R mod N 、b'=b*Rmod N。      
&emsp;&emsp;&ensp;（2）中间计算：计算t=a'*b'。       
&emsp;&emsp;&ensp;（3）蒙哥马利约减：通过调整t使其能被R整除，再右移k位得到结果c=t*R^(-1) mod N。       
**b.蒙哥马利约减**：    
步骤：（1）计算m=t*R^(-1) mod R，调整t使其能被R整除。        
&emsp;&emsp;&ensp;（2）通过t=(t+m*N)消除余数，再右移k位得到结果。       
**c.蒙哥马利幂约**：      
功能：高效计算c=a^e mod N，减少模乘次数。      
步骤：（1）将指数e转换为二进制形式。      
&emsp;&emsp;&ensp;（2）通过平方和乘法操作逐位处理二进制位，例如：       
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;c=1，for i∈二进制高位到低位       
&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;c=c^2 * R^(-1) mod N，若当前位为1则额外乘以a'      
<dr/>     
### 2.2.2 点运算运算
**1.Co-Z点加**：当两点Z坐标相同时，点加复杂度从12M+4s降至5M+2S。      
**2.NAF编码点乘**：将k编码为非相邻形式（NAF），减少非零比特数（从128降至85左右），降低点加次数。     
<dr/>    
### 2.2.3 协议优化   
**验签阶段避免模拟操作**：通过直接验证X=(r-e)*Z^2 mod p，减少一次模逆计算。      
# 三、核心代码实现   
## 3.1 蒙哥马利大数运算模块    
实现蒙哥马利约简与模乘，将256比特模乘从“乘法+模约”转化为“乘法+加法”，减少模操作开销。      
![1_1](https://github.com/ShanerLiu/2025-/blob/main/png/mgml_1.png)      
基于二进制扩展欧几里得算法实现模逆，支持常量时间运算，适配SM2素域运算需求。      
## 3.2 椭圆曲线点运算核心优化     
**add_co_z**:实现Co-Z点加，利用两点Z坐标相同的特性，将点加计算复杂度从12M+4S降至5M+2S。      
![co-z](https://github.com/ShanerLiu/2025-/blob/main/png/co_z.png)      
**fixed_point_mul**：基于预计算表与窗口优化固定点（如G）点乘，通过预存G的倍数点减少在线计算量。     
![fixed](https://github.com/ShanerLiu/2025-/blob/main/png/2_2.png)        
**mul**:结合NAF编码（减少非零比特数）与预计算表优化非固定点点乘。        
![mul](https://github.com/ShanerLiu/2025-/blob/main/png/2_3.png)        
## 3.3 签名与验签协议    
**sign**：结合优化的固定点点乘与蒙哥马利模逆，提升签名效率，符合SM2签名流程。    
![sign](https://github.com/ShanerLiu/2025-/blob/main/png/3_1.png)       
**verify**：通过fixed_point_mul和add_co_z优化点运算，之间验证(e+x1) mod n==r，避免模逆操作，提升验签效率。      
![verify](https://github.com/ShanerLiu/2025-/blob/main/png/3_2.png)        
<dr/>       
# 四、实验结果    
|        |  大数运算（100次） |  点运算（100次）| 签名验签（100次） |
| :----: | :-------------:  |  :----------: |  :---------: | 
|SM2基础软件实现| 0.0086s | 0.0571s | 10.8487s |  
|SM2优化后| 0.0084s | 0.0294s | 2.8733s |  
![base_result](https://github.com/ShanerLiu/2025-/blob/main/png/SM2_base.png)        
![op](https://github.com/ShanerLiu/2025-/blob/main/png/SM2_optimized.png)     







