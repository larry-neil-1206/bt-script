import sys
import os
import time

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bittensor as bt
from typing import List

from app.constants import ROUND_TABLE_HOTKEY
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger

WALLET_NAMES: List[str] = ["black", "green"]
DELEGATORS: List[str] = ["5DZhYqgHhRPYUHqjaU2gS2LNL7VS8Fb5utxZ7QEkVGqTnmh5","5FWhdv8o7fGo6yn54qXCn1xTxXsMaNLaotKYzUSG2iZp4tVZ"]

 
if __name__ == '__main__':
    
    netuid = int(input("Enter the netuid: "))
    wallet_name = input("Enter the wallet name: ")
    dest_hotkey = input("Enter the destination hotkey: ") or ROUND_TABLE_HOTKEY
    tolerance = float(input("Enter the tolerance: "))

    subtensor = bt.Subtensor(network=settings.NETWORK)
    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()
    delegator = DELEGATORS[WALLET_NAMES.index(wallet_name)]
    
    proxy = Proxy(network=settings.NETWORK)
    proxy.init_runtime()
    amount_balance = subtensor.get_stake(
        coldkey_ss58=delegator,
        hotkey_ss58=dest_hotkey,
        netuid=netuid
    )

    print(f"Wallet: {wallet_name}, Delegator: {delegator}, Dest Hotkey: {dest_hotkey}, Amount: {amount_balance.tao}")

    print("Press 'y' to unstake, or Ctrl+C to exit")
    try:
        if input().lower() == 'y':
            while True:
                try:
                    success, msg = proxy.remove_stake(
                        proxy_wallet=wallet,
                        delegator=delegator,
                        netuid=netuid,
                        hotkey=dest_hotkey,
                        amount=amount_balance,
                        tolerance=tolerance,
                    )
                    if success:
                        break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Error: {e}")
        
        