pragma circom 2.0.0;

include "node_modules/circomlib/circuits/poseidon.circom";

template Poseidon2Hash() {
    signal input in;         // 隐私输入 (哈希原象)
    signal output out;       // 公开输出 (哈希值)
    
    // 使用 circomlib 的标准 Poseidon 实现
    // 只接受一个参数：输入元素数量
    component poseidon = Poseidon(1);
    
    // 输入连接
    poseidon.inputs[0] <== in;
    
    // 输出连接
    out <== poseidon.out;
}

// 主组件: 公开输出哈希值，隐私输入原象
// 注意：public [] 中只能放输入信号，但这里没有需要公开的输入
component main = Poseidon2Hash();