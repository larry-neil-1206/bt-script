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
from utils.index import get_sn_price, convert_alpha_to_float
from modules import LeoProxy
from bittensor.utils.balance import Balance

if __name__ == '__main__':
    
  dest_hotkey = ROUND_TABLE_HOTKEY
  wallet_name = 'leo' # input("Enter the wallet name: ")
  wallet = bt.Wallet(name=wallet_name)
  wallet.unlock_coldkey()
  subtensor = bt.Subtensor(network=NETWORK)
  tolerance = 1
  delegator = '5ESwpyuGxBmkXuQ1J8DqtmhFZQEDzLWKVup9xai567JRhvDN'
  
  while True:
    try:
      is_stake = input("Do you want to stake or unstake? (y/n): ")
      action = 'unstake'
      user_stake_amount = 0
      user_stake_amount = float(input("Enter the amount: "))
      if is_stake.lower() == 'y':
        action = 'stake'
      else:
        unstake_all = input("Do you want to unstake all? (y/n)")
        if unstake_all == "y":
            user_stake_amount = 0
      
      netuid = int(input("Enter the netuid: "))
      sn_price = get_sn_price(subtensor, netuid)
      print(f"SN{netuid} price: {sn_price}")
      
      while True:
        try:
          leo_proxy = LeoProxy(
            proxy_wallet=wallet,
            network=NETWORK,
            delegator=delegator,
          )
          if action == 'stake':
            leo_proxy.add_stake(
              netuid=netuid,
              hotkey=dest_hotkey,
              amount=Balance.from_tao(user_stake_amount),
              tolerance=tolerance,
            )
            print("Staked successfully")
          else:
            leo_proxy.remove_stake(
              netuid=netuid,
              hotkey=dest_hotkey,
              amount=Balance.from_tao(user_stake_amount),
              tolerance=tolerance,
              all=True,
            )
            print("Unstaked successfully")
          break
        except Exception as e:
          print(f"Action Error: {e}")
      
    except Exception as e:
      print(f"Error: {e}")
    
        