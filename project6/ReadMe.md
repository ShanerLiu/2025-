# Project6--Google Password Checkup验证    
# 摘要  
&emsp;&emsp;本实验基于 Google Password Checkup 功能的核心需求，实现了一种隐私保护的密码泄露检测方案。 
该方案参考论文《On Deploying Secure Computing: Private Intersection-Sum-with-Cardinality》中 Section 3.1 的 DDH（Decisional Diffie-Hellman）协议，
通过椭圆曲线加密、Paillier 同态加密和随机化技术，在不泄露用户密码哈希和服务端泄露密码哈希的前提下，完成 “用户密码是否在泄露集合中” 的检测。实验结果表明，
该方案能准确识别交集（泄露密码），且双方均无法从交互中获取额外隐私信息，符合隐私保护与功能正确性要求。      
# 一、实验目的   
&emsp;&emsp;Google Password Checkup验证，来自刘巍然老师的报告google password checkup，
参考论文 https://eprint.iacr.org/2019/723.pdf 的 section 3.1 ，
也即 Figure 2 中展示的协议，尝试实现该协议，（编程语言不限）。        
# 二、实验原理     
## 2.1 核心需求与问题抽象    
&emsp;&emsp;Google Password Checkup的核心需求是：用户P1持有自己的密码哈希集合，服务端P2持有已知泄露的密码哈希集合，
双方需检测“用户密码哈希是否在泄露集合中”，即计算交集大小，但不得泄露任何一方原始哈希数据。       
&emsp;&emsp;该问题可抽象为“私有交集-基数与和”问题：        
**P1输入**：用户密码哈希集合V={v<sub>1</sub>,v<sub>2</sub>,···,V<sub>m1</sub>}       
**P2输入**：泄露密码哈希集合及标记W={（w<sub>1</sub>,t<sub>1</sub>),(w<sub>2</sub>,t<sub>2</sub>),···,w<sub>m2</sub>,t<sub>m2</sub>)}（其中t<sub>j</sub>=1表示“该哈希已泄漏”）     
**目标**：双方获取交集大小c（共同哈希数量）和交集和S（∑t<sub>j</sub>，即泄露密码数量），不泄露其他信息。     
## 2.2 关键密码学技术   
### 2.2.1 DDH假设与椭圆曲线加密    
&emsp;&emsp;DDH（判定性Diffie-Hellman）假设是协议安全性的基础：在椭圆曲线群中，给定g,g<sup>a</sup>,g<sup>b</sup>,
无法区分g<sup>ab</sup>与随机群元素。本实验使用NIST-P256椭圆曲线，通过“二次加密”隐藏哈希值：    
**P1用私钥k<sub>1</sub>加密哈希**：H(v<sub>i</sub>)<sup>k<sub>1</sub></sup>。      
**P2用私钥k<sub>2</sub>二次加密**：H(v<sub>i</sub>)<sup>k<sub>1</sub>k<sub>2</sub></sup>。  
### 2.2.2 Paillier同态加密    
&emsp;&emsp;Paillier加密支持“密文加法对应明文加法”的同态特性，用于安全计算交集和：      
1.P2加密t<sub>j</sub>得到AEnc(t<sub>j</sub>)      
2.P1对交集对应的密文求和：ASum({AEnc(t<sub>j</sub>)})=AEnc(∑t<sub>j</sub>)     
3.P2解密得到交集和S，无需暴露单个t<sub>j</sub>。     
### 2.2.3 随机化与打乱     
&emsp;&emsp;通过“打乱加密后数据的顺序”，隐藏元素对应关系：P1和P2在交互中均对加密后的哈希列表随机排序，
避免对方通过顺序推断原始数据。       
## 2.3 协议流程    
**1.初始化**：P2生成Paillier密钥对并发送公钥给P1；双方生成DDH私钥k<sub>1</sub>,k<sub>2</sub>。    
**2.第一轮（P1->P2）**：P1将用户哈希v<sub>i</sub>映射到椭圆曲线->用k<sub>1</sub>加密->打乱后发送给P2。    
**3.第二轮（P2->P1)**： P2用k<sub>2</sub>加密P1的消息->打乱后回发（用于交集比对）;    
&ensp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;P2将泄露哈希w<sub>j</sub>映射到曲线->用k<sub>2</sub>加密->结合AEnc(t<sub>j</sub>)->打乱后发送给P1。      
**4.第三轮（P1->P2)**:P1用k<sub>1</sub>加密P2的泄露哈希->与P2回发的消息比对，找到交集；    
&ensp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;P1对交集对应的AEnc(t<sub>j</sub>)求和->发送加密结果给P2。     
**5.结果**：P2解密得到交集和S，若S>0则表示存在泄露密码。  
# 三、实验步骤    
## 3.1 代码结构    
**password_checkup_protocol.py**：协议核心（DDH、哈希映射、加密运算）     
**password_client.py**：用户端（P1）实现，处理用户密码并参与协议    
**password_server.py**：服务端（P2）实现，存储泄露密码并参与协议      
**password_util.py**：密码哈希工具（生成/加载哈希、验证密码）     
## 3.2 实验步骤  




