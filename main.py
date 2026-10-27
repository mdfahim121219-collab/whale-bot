import requests
import time

# ১. আপনার সঠিক টেলিগ্রাম ক্রেডেনশিয়ালস
USER_ID = "5451132819"
TELEGRAM_URL = "https://telegram.org"

# 🚫 ২. বড় মেইন কয়েন ও স্টেবলকয়েন ব্ল্যাকলিস্ট (এগুলো সরাসরি ব্লক করা হবে)
EXCLUDED_TOKENS = ["BTC", "WBTC", "ETH", "WETH", "BNB", "WBNB", "SOL", "WSOL", "USDT", "USDC", "DAI", "BUSD", "XRP"]

# ৩. আপনার এপিআই কী দিয়ে প্রতিটি চেইনের সম্পূর্ণ সঠিক ও ফিক্সড লিঙ্ক (কোনো টাইপো এরর হবে না)
CHANNELS = {
    "ETHEREUM MAINNET": "https://alchemy.com",
    "BASE CHAIN": "https://alchemy.com",
    "ARBITRUM": "https://alchemy.com",
    "POLYGON": "https://alchemy.com"
}

def send_telegram_alert(text):
    try:
        # ব্লকিং এড়াতে একদম ফ্রেশ প্লেইন টেক্সট পাঠানো হচ্ছে
        response = requests.post(TELEGRAM_URL, json={"chat_id": USER_ID, "text": text}, timeout=10)
        if response.status_code != 200:
            print("❌ Telegram Bot Error Response:", response.text)
        else:
            print("✅ Alert message pushed to Telegram successfully!")
    except Exception as e:
        print("❌ Connection Error (Telegram Network Trace):", e)

print("🚀 Alchemy মাল্টি-চেইন ডেডিকেটেড নোড সচল হচ্ছে...")
print("🔄 Attempting to send initial Telegram activation message...")

# অ্যাক্টিভেশন মেসেজ ফায়ার করা
send_telegram_alert("Whale Tracker Bot has been successfully activated via Multi-Chain Dedicated Node!")

print("✅ Setup bypassed successfully! Entering main blockchain data loop now...")

last_seen_blocks = {chain: None for chain in CHANNELS.keys()}
processed_txs = {}

while True:
    for chain_name, rpc_url in CHANNELS.items():
        try:
            # সরাসরি চেইনের নোড থেকে সর্বশেষ ব্লক নাম্বার তুলে আনা
            block_payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}
            block_res = requests.post(rpc_url, json=block_payload, timeout=15).json()
            current_block = int(block_res["result"], 16)
            
            if last_seen_blocks[chain_name] is None:
                last_seen_blocks[chain_name] = current_block - 1
                
            # নতুন ব্লক তৈরি হওয়া মাত্রই নগদ তার ভেতরের ট্রানজেকশন স্ক্যান হবে
            if current_block > last_seen_blocks[chain_name]:
                for block_num in range(last_seen_blocks[chain_name] + 1, current_block + 1):
                    hex_block = hex(block_num)
                    
                    # কাস্টম টোকেন (ERC20) ট্রান্সফার ডাটা সরাসরি নোড সার্ভার থেকে রিড করা
                    tx_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "alchemy_getAssetTransfers",
                        "params": [{
                            "fromBlock": hex_block,
                            "toBlock": hex_block,
                            "category": ["erc20"],
                            "maxCount": "0x32"
                        }]
                    }
                    
                    tx_res = requests.post(rpc_url, json=tx_payload, timeout=20).json()
                    transfers = tx_res.get("result", {}).get("transfers", [])
                    
                    for tx in transfers:
                        asset_symbol = tx.get("asset", "UNKNOWN").upper()
                        contract_addr = tx.get("contractAddress", "").lower()
                        
                        # 🚫 ফিল্টার ১: মেইন কয়েন বা স্টেবলকয়েন হলে সাথে সাথে স্কিপ
                        if asset_symbol in EXCLUDED_TOKENS or "USD" in asset_symbol:
                            continue
                        
                        token_amount = float(tx.get("value", 0) or 0)
                        
                        # 💰 ফিল্টার ২: তিমির অ্যاکیউমুলেশন মনস্তত্ত্ব অনুযায়ী সর্বনিম্ন ৫০,০০০ (৫০ কে) টোকেন
                        if token_amount >= 50000:
                            tx_hash = tx.get("transactionHash", "")
                            
                            # ডুপ্লিকেট মেসেজ আটকানোর লজিক
                            current_time = time.time()
                            if tx_hash in processed_txs and (current_time - processed_txs[tx_hash] < 1800):
                                continue
                                
                            from_addr = tx.get("fromAddress", "")
                            to_addr = tx.get("toAddress", "")
                            from_short = from_addr[:6] + "..." + from_addr[-4:]
                            to_short = to_addr[:6] + "..." + to_addr[-4:]
                            
                            # একদম ক্লিন এবং প্লেইন টেক্সট মেসেজ ফরম্যাট
                            msg = (
                                "🚨 Crypto Whale Transaction Alert 🚨\n\n"
                                "Network: " + str(chain_name) + "\n"
                                "Token: " + str(asset_symbol) + "\n"
                                "Contract: " + str(contract_addr[:10]) + "...\n"
                                "Amount: " + str("{:,.2f}".format(token_amount)) + " " + str(asset_symbol) + "\n\n"
                                "From Wallet: " + str(from_short) + "\n"
                                "To Wallet: " + str(to_short) + "\n"
                                "Status: Large custom token transfer detected directly on-chain!"
                            )
                            send_telegram_alert(msg)
                            processed_txs[tx_hash] = current_time
                            print("🔥 Live On-Chain Data Found for " + str(asset_symbol) + " on " + str(chain_name))
                            
                last_seen_blocks[chain_name] = current_block
                
        except Exception as chain_error:
            # সাময়িক কোনো নেটওয়ার্ক ডিলে হলে স্ক্রিনে প্রিন্ট করবে, কিন্তু কোড ক্র্যাশ করবে না
            print("⚠️ Sync Update on " + str(chain_name) + ": Waiting for new block...")
            
    # ব্লকচেইনের নতুন ব্লক ডাটা নগদ প্রসেস করতে প্রতি ১০ সেকেন্ড পর পর লুপ ঘুরবে
    time.sleep(10)
