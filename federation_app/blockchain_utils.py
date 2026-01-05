# federation_app/blockchain_utils.py
from web3 import Web3
import json
import os
from django.conf import settings
from decimal import Decimal
# 连接到 Ganache (确保 Ganache 已启动)
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))

def get_contract(contract_name):
    # 根据你的目录结构定位 Truffle 编译后的 JSON
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_path, 'blockchain/build/contracts', f'{contract_name}.json')
    
    with open(json_path, 'r') as f:
        contract_data = json.load(f)
    
    # 自动获取当前网络 ID (Ganache 通常是 5777)
    network_id = list(contract_data['networks'].keys())[0]
    contract_address = contract_data['networks'][network_id]['address']
    abi = contract_data['abi']
    
    return w3.eth.contract(address=contract_address, abi=abi)

def sync_contribution_to_chain(task_id, contribution_data, model_hash):
    """将贡献度比例上链"""
    try:
        manager_contract = get_contract('FederationManager')
        # 使用 Ganache 的第一个账号作为管理员执行交易
        admin_account = w3.eth.accounts[0]
        
        # 准备数据：地址列表和放大后的比例（Solidity 不支持浮点数，需转为整数）
        addresses = []
        ratios = []
        for user_id, contribution in contribution_data.items():
            # 这里建议在 User 模型中增加一个 wallet_address 字段，
            # 暂时用映射或测试地址代替
            from .models import User
            user = User.objects.get(id=user_id)
            # 假设你给用户分配了 Ganache 的地址，或者先模拟一个
            test_address = w3.eth.accounts[int(user_id) % 10] 
            addresses.append(test_address)
            ratios.append(int(float(contribution) * 10000)) # 放大一万倍

        tx_hash = manager_contract.functions.setContributionRatios(
            task_id, addresses, ratios, model_hash
        ).transact({'from': admin_account})
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    except Exception as e:
        print(f"区块链同步失败: {e}")
        return False
    
# federation_app/blockchain_utils.py
from .blockchain_utils import get_contract, w3
from web3 import Web3

def get_balance_by_address(address):
    """
    1. 通过钱包地址直接读取 HyperCoin 余额
    """
    try:
        hc_contract = get_contract('HyperCoin')
        
        # 验证地址格式是否正确
        if not Web3.is_address(address):
            print(f"无效的地址格式: {address}")
            return 0.0
            
        # 转换为校验和地址（Checksum Address）
        checksum_address = Web3.to_checksum_address(address)
        
        # 获取余额
        balance_wei = hc_contract.functions.balanceOf(checksum_address).call()
        balance_hc = w3.from_wei(balance_wei, 'ether')
        
        return float(balance_hc)
    except Exception as e:
        print(f"通过地址读取余额失败: {e}")
        return 0.0

def adjust_balance_by_address(target_address, amount_hc, mode='increase'):
    """
    2. 通过钱包地址手动增加或减少余额
    """
    try:
        hc_contract = get_contract('HyperCoin')
        admin_address = w3.eth.accounts[0] # 管理员（通常是部署合约的账号）
        
        checksum_address = Web3.to_checksum_address(target_address)
        amount_wei = w3.to_wei(amount_hc, 'ether')
        
        if mode == 'increase':
            # 管理员调用 faucet 发币
            tx_hash = hc_contract.functions.faucet(checksum_address, amount_wei).transact({'from': admin_address})
        elif mode == 'decrease':
            # 管理员调用之前新增的 adminReduce 扣币
            tx_hash = hc_contract.functions.adminReduce(checksum_address, amount_wei).transact({'from': admin_address})
        else:
            raise ValueError("仅支持 'increase' 或 'decrease'")
            
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    except Exception as e:
        print(f"通过地址调节余额失败: {e}")
        return False
    
# federation_app/blockchain_utils.py

def exchange_eth_to_hc(user_id, eth_amount):
    """
    用户通过发送 ETH 换取 HC (1 ETH = 10 HC)
    """
    try:
        hc_contract = get_contract('HyperCoin')
        user_address = w3.eth.accounts[int(user_id) % 10]
        
        # 将 ETH 转换为 wei
        value_in_wei = w3.to_wei(eth_amount, 'ether')
        
        # 调用 payable 函数并发送 ETH
        tx_hash = hc_contract.functions.buyTokens().transact({
            'from': user_address,
            'value': value_in_wei
        })
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    except Exception as e:
        print(f"兑换失败: {e}")
        return False
    

# federation_app/blockchain_utils.py

def exchange_hc_to_eth(user_id, hc_amount):
    """
    用户通过销毁 HC 换回 ETH (10 HC = 1 ETH)
    """
    try:
        from .blockchain_utils import get_contract, w3
        hc_contract = get_contract('HyperCoin')
        
        # 依然使用你之前的映射逻辑，或者直接传入地址
        user_address = w3.eth.accounts[int(user_id) % 10]
        
        # 将要卖出的 HC 数量转换为最小单位 (wei)
        hc_amount_wei = w3.to_wei(hc_amount, 'ether')
        
        print(f"正在发起兑换请求：{hc_amount} HC -> {hc_amount / 10} ETH...")
        
        # 调用合约的 sellTokens 函数
        # 注意：这个操作会减少用户的 HC 余额，增加用户的 ETH 余额
        tx_hash = hc_contract.functions.sellTokens(hc_amount_wei).transact({
            'from': user_address,
            'gas': 200000  # 手动指定 gas 限制以防万一
        })
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"✅ 兑换成功！交易哈希: {receipt.transactionHash.hex()}")
            return True
        else:
            print("❌ 交易被区块链拒绝。")
            return False
            
    except Exception as e:
        print(f"❌ 兑换失败: {e}")
        return False