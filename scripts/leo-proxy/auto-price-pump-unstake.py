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
from utils.index import get_sn_price, calculate_stake_limit_price
from modules import LeoProxy
from bittensor.utils.balance import Balance
from utils.const import NETUID_TO_ADDRESS

if __name__ == '__main__':
    
  wallet_name = 'leo' # input("Enter the wallet name: ")
  wallet = bt.Wallet(name=wallet_name)
  wallet.unlock_coldkey()
  subtensor = bt.Subtensor(network=NETWORK)
  tolerance = 0.01
  delegator = '5ESwpyuGxBmkXuQ1J8DqtmhFZQEDzLWKVup9xai567JRhvDN'
  block_ids = [104, 126, 67, 107, 99, 15, 47, 38, 114]
  
  try:
    action = 'unstake'
    user_stake_amount = 0
    is_remove_stake = True
    
    netuid = 76

    dest_hotkey = NETUID_TO_ADDRESS.get(netuid, ROUND_TABLE_HOTKEY)
    
    leo_proxy = LeoProxy(
      proxy_wallet=wallet,
      network=NETWORK,
      delegator=delegator,
    )
    while True:
      try:
        sn_price = get_sn_price(subtensor, netuid)
        print(f"Current SN Price: {sn_price}")
        if sn_price > 5000:
          leo_proxy.remove_stake(
            netuid=netuid,
            hotkey=dest_hotkey,
            amount=Balance.from_tao(user_stake_amount, netuid=netuid),
            tolerance=1,
            all=is_remove_stake,
          )
          print("Unstaked successfully")
          
        subtensor.wait_for_block()
      except Exception as e:
        print(f"Action Error: {e}")
    
  except Exception as e:
    print(f"Error: {e}")
    
        