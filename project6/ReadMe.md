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
**P1输入**：用户密码哈希集合V={v~1~,v~2~,···,V~m1~}
