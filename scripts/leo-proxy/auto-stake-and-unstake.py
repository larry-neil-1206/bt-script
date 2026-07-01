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
  delegator = '5ESwpyuGxBmkXuQ1J8DqtmhFZQEDzLWKVup9xai567JRhvDN'
  is_stake = True
  netuid = int(input("Enter the netuid: "))
  threshold = float(input("Enter the threshold: "))
  while True:
    try:
      sn_price = get_sn_price(subtensor, netuid)
      print(f"SN{netuid} price: {sn_price}")

      # dest_hotkey = NETUID_TO_ADDRESS.get(netuid, ROUND_TABLE_HOTKEY)
      dest_hotkey = "5E2LP6EnZ54m3wS8s1yPvD5c3xo71kQroBw7aUVK32TKeZ5u"
      
      leo_proxy = LeoProxy(
        proxy_wallet=wallet,
        network=NETWORK,
        delegator=delegator,
      )
      if is_stake :
        leo_proxy.add_stake(
          netuid=netuid,
          hotkey=dest_hotkey,
          amount=Balance.from_tao(3),
          tolerance=1,
        )
        print("Staked successfully")
        is_stake = False
      elif not is_stake and sn_price > threshold:
        print("Unstaking...")
        leo_proxy.remove_stake(
          netuid=netuid,
          hotkey=dest_hotkey,
          amount=Balance.from_tao(0, netuid=netuid),
          tolerance=1,
          all=True,
        )
        print("Unstaked successfully")
        is_stake = True
        
      subtensor.wait_for_block()
        
      
    except Exception as e:
      print(f"Error: {e}")
    
        