import sys
import os
import time

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bittensor as bt
from typing import List

from app.constants import ROUND_TABLE_HOTKEY, NETWORK
from app.core.config import settings
from app.services.proxy import Proxy
from utils.logger import logger
from utils.index import get_sn_price, convert_alpha_to_float
from modules import LeoProxy
from bittensor.utils.balance import Balance

if __name__ == '__main__':
    
    dest_hotkey = ROUND_TABLE_HOTKEY
    wallet_name = 'leo' # input("Enter the wallet name: ")
    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()
    
    subtensor = bt.Subtensor(network=NETWORK)
    netuid = int(input("Enter the netuid: "))
    sn_price = get_sn_price(subtensor, netuid)
    logger.info(f"Subnet price for netuid {netuid}: {sn_price} TAO per alpha")

    user_stake_amount = float(input("Enter the stake amount: "))
    threshold = float(input("Enter the threshold: "))
    tolerance = float(input("Enter the tolerance: "))
    repeat_cnt = int(input("Enter the number of repeats: "))
    
    delegator = '5ESwpyuGxBmkXuQ1J8DqtmhFZQEDzLWKVup9xai567JRhvDN'

    try:
        sn_price = get_sn_price(subtensor, netuid)
        user_unstake_price = sn_price + threshold
        user_stake_price = sn_price - threshold

        confirm = input(f"Already staked? If so this script will starts with unstaking functionality. (y/n): ")
        if confirm.lower() == 'y':
            staked = True
            user_unstake_price = float(input("Enter the unstake price: "))
        else:
            user_stake_price = sn_price - threshold
            staked = False

        while repeat_cnt != 0:
            try:
                leo_proxy = LeoProxy(
                    proxy_wallet=wallet,
                    network=NETWORK,
                    delegator=delegator,
                )
                sn_price = get_sn_price(subtensor, netuid)
                print(f"SN{netuid} price: {sn_price}, stake_price: {user_stake_price}, unstake_price: {user_unstake_price}, stake_amount: {user_stake_amount}, staked: {staked}")
                
                if staked and sn_price > user_unstake_price:
                    leo_proxy.remove_stake(
                        netuid=netuid,
                        hotkey=dest_hotkey,
                        amount=Balance.from_tao(0, netuid=netuid),
                        tolerance=tolerance,
                        all=True,
                    )
                    print("Unstaked successfully")
                    staked = False
                    repeat_cnt -= 1
                    sn_price = get_sn_price(subtensor, netuid)
                    user_stake_price = sn_price - threshold    
                elif not staked and sn_price < user_stake_price:
                    leo_proxy.add_stake(
                        netuid=netuid,
                        hotkey=dest_hotkey,
                        amount=Balance.from_tao(user_stake_amount),
                        tolerance=tolerance,
                    )
                    print("Staked successfully")
                    staked = True
                    sn_price = get_sn_price(subtensor, netuid)
                    user_unstake_price = sn_price + threshold
                subtensor.wait_for_block()
                
            except Exception as e:
                logger.error(f"Error: {e}")
                subtensor.wait_for_block()
                continue
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Error: {e}")
        
        