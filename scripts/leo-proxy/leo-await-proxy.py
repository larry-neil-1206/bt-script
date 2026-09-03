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
  block_ids = [104, 67, 76, 96, 91, 107, 99, 78]
  use_mev = True
  while True:
    try:
      action_type = int(input("What kind of action do you want? ( stake = 0 / unstake = 1 / swapstake = 2 ): "))
      is_remove_stake = False
      user_stake_amount = float(input("Enter the amount: "))
      dest_netuid = 0
      if action_type == 1 or action_type == 2:
        unstake_all = input("Do you want to unstake/swap all? (y/n)")
        if unstake_all == "y":
          user_stake_amount = 0
          is_remove_stake = True
          print(f"Unstaking all({user_stake_amount})...")
        if action_type == 2:
          dest_netuid = int(input("Enter the destination netuid: "))
      netuid = int(input("Enter the netuid: "))
      # if netuid in block_ids:
      #   print("Poor sn detection. Please use another netuid.")
      #   continue
      sn_price = get_sn_price(subtensor, netuid)
      print(f"SN{netuid} price: {sn_price}")
      # tolerance = input("Enter tolerance (default 0.005): ")
      # if tolerance == "":
      #   tolerance = 0.005
      # else:
      #   tolerance = float(tolerance)
      
      is_using_mev = input("Do you want to use MEV? (y/n): ")
      use_mev = True if is_using_mev.lower() == 'y' else False
      
      tolerance = calculate_stake_limit_price(
        tao_amount = user_stake_amount,
        netuid=netuid,
        min_tolerance_staking=True,
        default_rate_tolerance=0.01,
        subtensor=subtensor,
      )

      # dest_hotkey = NETUID_TO_ADDRESS.get(netuid, "5E2LP6EnZ54m3wS8s1yPvD5c3xo71kQroBw7aUVK32TKeZ5u")
      dest_hotkey = "5E2LP6EnZ54m3wS8s1yPvD5c3xo71kQroBw7aUVK32TKeZ5u"
      
      while True:
        try:
          leo_proxy = LeoProxy(
            proxy_wallet=wallet,
            network=NETWORK,
            delegator=delegator,
          )
          if action_type == 0:
            leo_proxy.add_stake(
              netuid=netuid,
              hotkey=dest_hotkey,
              amount=Balance.from_tao(user_stake_amount),
              tolerance=tolerance,
              use_mev=use_mev,
            )
            print("Staked successfully")
          elif action_type == 1:
            print(f"Unstaking amount: {user_stake_amount}...")
            print(f"Is remove all: {is_remove_stake}...")
            print(f"netuid: {netuid}...")
            leo_proxy.remove_stake(
              netuid=netuid,
              hotkey=dest_hotkey,
              amount=Balance.from_tao(user_stake_amount, netuid=netuid),
              tolerance=1,
              all=is_remove_stake,
              use_mev=use_mev,
            )
            print("Unstaked successfully")
          else:
            print(f"Swaping {user_stake_amount}alpha from sn{netuid} to sn{dest_netuid}")
            leo_proxy.swap_stake_limit(
              hotkey=dest_hotkey,
              origin_netuid=netuid,
              dest_netuid=dest_netuid,
              amount=Balance.from_tao(user_stake_amount, netuid=netuid),
              all=is_remove_stake,
              use_mev=use_mev,
              tolerance=tolerance
            )
          break
        except Exception as e:
          print(f"Action Error: {e}")
          break
      
    except Exception as e:
      print(f"Error: {e}")