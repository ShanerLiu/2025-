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
<dr/>     

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
**create_leaked_hashes.py**：用于生成包含泄露密码哈希的文件     
**create_user_hashes.py**：用于生成包含用户密码哈希的文件        

## 3.2 实验步骤  
### 3.2.1 生成密码哈希文件     
&emsp;&emsp;Step1：运行 create_leaked_hashes.py 生成包含泄露密码哈希的文件 leaked_hashes.txt。       
&emsp;&emsp;Step2：运行 create_user_hashes.py 生成包含用户密码哈希的文件 user_hashes.txt。       
### 3.2.2 启动服务器     
运行 password_server.py 启动密码检查服务器，服务器监听指定的地址和端口，等待客户端的连接请求。       
### 3.2.3 客户端执行密码检查     
运行 password_client.py 启动密码检查客户端，客户端连接到服务器，执行以下步骤：     
&emsp;&emsp;Step1：向服务器请求 Paillier 公钥。        
&emsp;&emsp;Step2：将用户密码哈希映射到椭圆曲线上的点，并使用私钥加密。     
&emsp;&emsp;Step3：将加密后的点发送给服务器。        
&emsp;&emsp;Step4：接收服务器返回的第二轮消息。     
&emsp;&emsp;Step5：计算交集并同态求和，将加密的交集和发送给服务器。      
&emsp;&emsp;Step6：接收服务器返回的最终结果，判断是否有密码泄露。         

# 四、实验结果分析     
## 4.1 功能正确性    
&emsp;&emsp;在实验中，我设置了包含泄露密码的用户密码列表和泄露密码列表。运行客户端和服务端程序后，程序能够正确识别出用户密码中存在的泄露密码，返回的交集和S大于0，表明方案能够准确检测出 “用户密码是否在泄露集合中”，满足功能正确性要求。       
## 4.2 隐私保护    
&emsp;&emsp;由于采用了椭圆曲线加密、Paillier同态加密和随机化技术，在整个协议交互过程中，双方均无法从交互中获取额外隐私信息。椭圆曲线加密通过二次加密隐藏了哈希值，Paillier同态加密在计算交集和时无需暴露单个标记值，随机化技术打乱了加密数据的顺序，避免了通过顺序推断原始数据，符合隐私保护要求。      




