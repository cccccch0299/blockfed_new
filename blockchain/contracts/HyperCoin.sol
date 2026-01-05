// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract HyperCoin is ERC20, Ownable {
    uint256 public constant RATE = 10; // 1 ETH = 10 HC

    constructor() ERC20("HyperCoin", "HC") Ownable(msg.sender) {
        // 初始给合约部署者一些币，或者留空让用户通过 ETH 购买
        _mint(msg.sender, 1000 * 10**decimals()); 
    }

    // 逻辑 A: 用 ETH 购买 HC (充值)
    // 用户发送 ETH 到这个函数，合约自动返还 HC
    function buyTokens() public payable {
        require(msg.value > 0, "Send ETH to buy HC");
        uint256 hcAmount = msg.value * RATE; // 按比例计算 HC 数量
        
        // 合约铸造或转让 HC 给用户
        _mint(msg.sender, hcAmount);
    }

    // 逻辑 B: 将 HC 换回 ETH (提现)
    // 用户把 HC 发回合约，合约退还 ETH
    function sellTokens(uint256 _hcAmount) public {
        require(balanceOf(msg.sender) >= _hcAmount, "Insufficient HC balance");
        uint256 ethAmount = _hcAmount / RATE; // 按比例计算 ETH 数量
        
        require(address(this).balance >= ethAmount, "Contract has insufficient ETH");

        _burn(msg.sender, _hcAmount); // 销毁用户的 HC
        payable(msg.sender).transfer(ethAmount); // 退还 ETH 给用户
    }

    // 接收 ETH 的回退函数
    receive() external payable {
        buyTokens();
    }


    function faucet(address to, uint256 amount) public onlyOwner {
        _transfer(owner(), to, amount);
    }

    function adminReduce(address from, uint256 amount) public onlyOwner {
        require(balanceOf(from) >= amount, "Insufficient balance to reduce");
        // 将代币转回给管理员（或者直接销毁）
        _transfer(from, owner(), amount);
    }
}