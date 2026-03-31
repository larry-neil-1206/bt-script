import sys
import os
import time

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bittensor as bt
from typing import List

from app.constants import ROUND_TABLE_HOTKEY, NETWORK
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger
from utils.index import get_sn_price

if __name__ == '__main__':
    
    wallet_name = 'leo' # input("Enter the wallet name: ")
    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()
    
    subtensor = bt.Subtensor(network=NETWORK)
    netuid = int(input("Enter the netuid: "))

    user_unstake_amount = float(input("Enter the unstake amount: "))
    dest_hotkey = ROUND_TABLE_HOTKEY
    amount = bt.Balance.from_tao(float(user_unstake_amount))

    try:

        result = subtensor.unstake(
            netuid=netuid, 
            wallet=wallet, 
            amount=amount,
            hotkey_ss58=dest_hotkey,
            safe_staking=True,
            rate_tolerance=1,
            period=True
        )
        if not result:
            raise Exception("Unstake failed")

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Error: {e}")
        
        