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
from utils.index import get_sn_price, extract_stake_events_from_data

def fetch_extrinsic_data(self, block_number):
    """Extract ColdkeySwapScheduled events from the data"""
    coldkey_swaps = []
    identity_changes = []
    print(f"Fetching events from chain")
    block_hash = self.subtensor.substrate.get_block_hash(block_id=block_number)
    extrinsics = self.subtensor.substrate.get_extrinsics(block_hash=block_hash)
    subnet_infos = self.subtensor.all_subnets()
    owner_coldkeys = [subnet_info.owner_coldkey for subnet_info in subnet_infos]
    subnet_names = [subnet_info.subnet_name for subnet_info in subnet_infos]
    print(f"Fetched {len(extrinsics)} events from chain and {len(subnet_infos)} subnets")

    for ex in extrinsics:
        call = ex.value.get('call', {})
        if (
            call.get('call_module') == 'SubtensorModule' and
            call.get('call_function') == 'schedule_swap_coldkey'
        ):
            # Get the new coldkey from call_args
            args = call.get('call_args', [])
            new_coldkey = next((a['value'] for a in args if a['name'] == 'new_coldkey'), None)
            from_coldkey = ex.value.get('address', None)
            print(f"Swap scheduled: from {from_coldkey} to {new_coldkey}")
            
            try:
                subnet_id = owner_coldkeys.index(from_coldkey)
                swap_info = {
                    'old_coldkey': from_coldkey,
                    'new_coldkey': new_coldkey,
                    'subnet': subnet_id,
                }
                
                coldkey_swaps.append(swap_info)
            except ValueError:
                print(f"From coldkey {from_coldkey} not found in owner coldkeys")
            
    subnet_count = len(self.subnet_names)
    for i in range(subnet_count):
        if subnet_names[i] != self.subnet_names[i]:
            identity_change_info = {
                'subnet': i,
                'old_identity': self.subnet_names[i],
                'new_identity': subnet_names[i],
            }
            identity_changes.append(identity_change_info)

    self.subnet_names = subnet_names
    return coldkey_swaps, identity_changes

if __name__ == '__main__':
    
    wallet_name = 'leo' # input("Enter the wallet name: ")
    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()
    
    subtensor = bt.Subtensor(network=NETWORK)
    
    user_stake_amount = float(input("Enter the stake amount: "))
    dest_hotkey = ROUND_TABLE_HOTKEY
    threshold = float(input("Enter the threshold: "))
    tolerance = float(input("Enter the tolerance: "))

    while True:
        try:
            block_number = subtensor.get_current_block()
            block_hash = subtensor.substrate.get_block_hash(block_id=block_number)
            events = subtensor.substrate.get_events(block_hash=block_hash)

            stake_events = extract_stake_events_from_data(subtensor, events)
            
            if staked and sn_price > user_unstake_price:
                result = subtensor.unstake(
                    netuid=netuid, 
                    wallet=wallet, 
                    amount=None,
                    hotkey_ss58=dest_hotkey,
                    safe_staking=True,
                    rate_tolerance=tolerance,
                    period=True
                )
                if not result:
                    raise Exception("Unstake failed")
                print("Unstaked successfully")
                staked = False
                sn_price = get_sn_price(subtensor, netuid)
                user_stake_price = sn_price - threshold    
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

                print("Staked successfully")
                staked = True
                sn_price = get_sn_price(subtensor, netuid)
                user_unstake_price = sn_price + threshold
            subtensor.wait_for_block()
            sn_price = get_sn_price(subtensor, netuid)
            print(f"SN{netuid} price: {sn_price}, stake_price: {user_stake_price}, unstake_price: {user_unstake_price}, stake_amount: {user_stake_amount}, staked: {staked}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            continue
