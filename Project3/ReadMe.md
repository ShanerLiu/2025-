# Project3--用circom实现poseidon2哈希算法的电路
# 摘要  

# 一、实验要求  
1) poseidon2哈希算法参数参考参考文档1的Table1，用(n,t,d)=(256,3,5)或(256,2,5)。
2) 电路的公开输入用poseidon2哈希值，隐私输入为哈希原象，哈希算法的输入只考虑一个block即可。
3) 用Groth16算法生成证明
<dr/>

**参考文档**     
1. poseidon2哈希算法https://eprint.iacr.org/2023/323.pdf     
2. circom说明文档https://docs.circom.io/      
3. circom电路样例 https://github.com/iden3/circomlib          
<dr/>

# 二、实验环境   
&emsp;&emsp;本次实验在Windows11环境下配置Circom及相关实验依赖的步骤如下，严格基于参考文档中涉及的工具链。
## 2.1 安装Rust环境（Circom依赖） 
**1.下载并运行Rust安装工具**：    
访问Rust官方网站下载适用于Windows的安装程序：https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe   
运行程序后，选择默认安装选项（按1并回车），自动完成rustup、cargo（Rust包管理器）和Rust编译器的安装。    
**2.验证Rust安装**：    
打开PowerShell或命令提示符，执行以下命令：    
rustc --version  # 应显示Rust版本信息      
cargo --version   # 应显示Cargo版本信息     
<br/>      

## 2.2 安装Git   
**1.下载Git for Windows**：       
访问Git官网下载安装程序：https://git-scm.com/download/win，安装时勾选"Add Git to PATH"（默认选项），确保Git可在命令行中直接调用。     
**2.验证GIt安装**：      
在PoweShell中执行：git --version，应显示Git版本信息。      
<br/>   
## 2.3 安装Circom编译器  
**1.克隆Circom仓库**：     
在PowerShell中执行以下命令，克隆官方仓库：git clone https://github.com/iden3/circom.git     
**2.编译并安装Circom**：    
进入仓库目录，使用Cargo编译并安装：     
cd circom      
cargo build --release      
cd circom      
cargo install --path .      
**3.验证Circom安装**：      
关闭当前PowerShell窗口并重新打开，执行：circom --version       
<dr/>    
## 2.4 安装snarkjs（生成Groth16证明）      
**1.安装Node.js(包含npm）**：    
访问Node.js官网下载LTS版本安装程序：https://nodejs.org/en/download/，安装时勾选"Add to PATH"，确保node和npm可在命令行中调用。     
**2.验证Node.js和npm**：    
在PowerShell中执行：     
node --version       
npm --version        
**3.安装snarkjs**：      
执行以下命令安装全局snarkjs：npm install -g snarkjs       
**4。验证snarkjs安装**：      
运行以下命令查看snarkjs的版本：snarkjs --version       
<dr/>   
## 2.5 配置环境变量     
Rust/Cargo的二进制目录和Node.js的目录已默认添加到PATH，若工具无法识别，可手动检查       
## 2.6 验证环境完整性    
**1.创建测试目录并进入**：     
mkdir zk-test && cd zk-test       
**2.生成一个简单的circom电路（如test.circom)**：      
template Test() {        
    signal input a;      
    signal input b;      
    signal output c;      
    c <== a * b;     
}      
component main = Test();     
**3.编译电路**：     
circom test.circom --r1cs --wasm ，会生成test.r1cs和test.wasm，则说明环境配置正确     
<dr/>  
# 三、实验原理    
## 3.1 Poseidon2哈希算法原理    
&emsp;&emsp;Poseidon2 是一种高效的密码学哈希算法，属于 ARX（Add-Rotate-XOR）类设计，
核心是通过置换函数实现输入的混淆与扩散，其参数遵循(n,t,d)=(256,3,5)规范：      
**n=256**：基于256位有限域运算      
**t=3**：状态尺寸为3个域元素，即输入为1个包含3个元素的"block"     
**d=5**：采用5次幂S-box（非线性变换），满足gcd(d,p-1)=1（p为有限域素数），确保非线性扩散能力      
<dr/>    

其核心流程为置换函数，包含以下步骤：     
**1.初始线性层**：输入状态先经过MDS矩阵乘法，实现初步扩散     
**2.轮运算**：   
**外部轮（8轮）**：每轮对所有3个状态元素添加轮常量（公开随机数），再应用S-box（5次幂），最后通过线性层扩散    
**内部轮（56轮）**：仅对第一个状态元素添加轮常量、应用S-box，再通过线性层扩散，平衡效率与安全性     
<dr/>   
## 3.2 零知识证明（Groth16算法）原理    
&emsp;&emsp;Groth16 是一种高效的非交互式零知识证明（ZK-SNARK）算法，允许证明者在不泄露隐私输入的情况下，
向验证者证明 “某个陈述为真”。其核心原理是将计算问题转化为代数约束系统，并通过预计算的可信设置生成证明与验证密钥。      
本实验中Groth16的应用逻辑：     
**1.问题转化**：将“证明者知道一个哈希原象，其Poseidon2哈希值等于公开值”转化为R1CS约束    
**2.可信设置**：预计算PTAU文件，完成“Phase 1”公共参考字符串生成；
基于电路约束生成“Phase 2”密钥(Zkey)，用于后续证明生成与验证。    
**3.证明生成**：证明者输入隐私原象和公开hash值，计算满足约束的“见证”，并利用Zkey生成零知识证明；     
**4.验证**：验证者通过公开哈希值、证明和验证密钥，高效验证正面的正确性，且无需知晓隐私原象。     
# 四、实验步骤      
## 4.1 准备工作目录     
mkdir poseidon2-circuit      
cd poseidon2-circuit      
将完整的Circom电路代码poseidon2.circom放入该目录中，注意node_modules文件夹应该放在该文件夹中      
## 4.2 编译电路，生成R1CS约束     
circom poseidon2.circom --r1cs --wasm --sym -l node_modules      
## 4.3 生成见证文件      
cd poseidon2_js   进入生成的JS目录       
notepad input.json    创建输入文件input.json
node generate_witness.js poseidon2.wasm input.json witness.wtns      生成见证文件        
## 4.4 Groth16可信设置      
cd ..   返回项目根目录       
snarkjs powersoftau new bn128 12 pot12_0000.ptau -v   创建新的初始ptau文件      
snarkjs powersoftau contribute pot12_0000.ptau pot12_0001.ptau --name="First Contribution" -v   进行第一次贡献     
snarkjs powersoftau prepare phase2 pot12_0001.ptau pot12_final.ptau -v     准备phase2      
snarkjs groth16 setup poseidon2.r1cs pot12_final.ptau poseidon2_0000.zkey     Groth16 设置（创建初始zKey)    
snarkjs zkey contribute poseidon2_0000.zkey poseidon2_0001.zkey --name="Second Contribution" -v    第二阶段贡献，增强安全性        
snarkjs zkey export verificationkey poseidon2_0001.zkey verification_key.json    导出验证密钥     
snarkjs groth16 prove poseidon2_0001.zkey poseidon2_js/witness.wtns proof.json public.json    生成证明    
snarkjs groth16 verify verification_key.json public.json proof.json   验证证明     






