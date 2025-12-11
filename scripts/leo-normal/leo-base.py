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
    sn_price = get_sn_price(subtensor, netuid)
    logger.info(f"Subnet price for netuid {netuid}: {sn_price} TAO per alpha")

    user_stake_amount = float(input("Enter the stake amount: "))
    user_stake_price = float(input("Enter the stake price: "))
    user_unstake_price = float(input("Enter the unstake price: "))
    dest_hotkey = ROUND_TABLE_HOTKEY
    tolerance = float(input("Enter the tolerance: "))

    staked = False
    try:
        while True:
            try:
                sn_price = get_sn_price(subtensor, netuid)
                print(f"Current subnet price: {sn_price}, stake_price: {user_stake_price}, unstake_price: {user_unstake_price}, stake_amount: {user_stake_amount}")
                if staked and sn_price > user_unstake_price:
                    amount = subtensor.get_stake(
                        coldkey_ss58=wallet.coldkeypub.ss58_address,
                        hotkey_ss58=dest_hotkey,
                        netuid=netuid
                    )
                    result = subtensor.unstake(
                        netuid=netuid, 
                        wallet=wallet, 
                        amount=amount,
                        hotkey_ss58=dest_hotkey,
                        safe_staking=True,
                        rate_tolerance=tolerance,
                        period=True
                    )
                    if not result:
                        raise Exception("Unstake failed")

                    staked = False
                    logger.info(f"Unstaked from netuid {netuid} at price {sn_price}")
                elif not staked and sn_price < user_stake_price:
                    result = subtensor.add_stake(
                        netuid=netuid,
                        amount= bt.Balance.from_tao(user_stake_amount, netuid),
                        wallet=wallet,
                        hotkey_ss58=dest_hotkey,
                        safe_staking=True,
                        rate_tolerance=tolerance,
                        period=True
                    )
                    if not result:
                        raise Exception("Stake failed")

                    staked = True
                    logger.info(f"Staked to netuid {netuid} at price {sn_price}")
                subtensor.wait_for_block()
            except Exception as e:
                logger.error(f"Error: {e}")
                continue
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.error(f"Error: {e}")
        
        