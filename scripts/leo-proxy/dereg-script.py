import sys
import os

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bittensor as bt

from app.constants import NETWORK
from utils.index import get_sn_price
from modules import LeoProxy
from bittensor.utils.balance import Balance

if __name__ == '__main__':
    
  wallet_name = 'leo' # input("Enter the wallet name: ")
  wallet = bt.Wallet(name=wallet_name)
  wallet.unlock_coldkey()
  subtensor = bt.Subtensor(network=NETWORK)
  tolerance = 0.1
  delegator = '5ESwpyuGxBmkXuQ1J8DqtmhFZQEDzLWKVup9xai567JRhvDN'
  dest_hotkey = "5E2LP6EnZ54m3wS8s1yPvD5c3xo71kQroBw7aUVK32TKeZ5u"
  user_stake_amount = float(input("Enter the amount: "))
  netuid = int(input("Enter the netuid: "))
  action = 'stake'
  staked_price = 0
  while True:
    try:
      sn_price = get_sn_price(subtensor, netuid)
      print(f"SN{netuid} price: {sn_price}")
      if sn_price > 0.005 and action == 'stake':
        print(f"trying to stake, SN_price: {sn_price}")
        leo_proxy = LeoProxy(
          proxy_wallet=wallet,
          network=NETWORK,
          delegator=delegator,
        )
        leo_proxy.add_stake(
          netuid=netuid,
          hotkey=dest_hotkey,
          amount=Balance.from_tao(user_stake_amount),
          use_mev=False,
          tolerance=tolerance,
        )
        action = 'unstake'
        print("Staked successfully")
        subtensor.wait_for_block()
        subtensor.wait_for_block()
        staked_price = get_sn_price(subtensor, netuid)
        subtensor.wait_for_block()
        continue
        
      if action == 'unstake' and sn_price > staked_price:
        print(f"trying to unstake, staked_price: {staked_price}, SN_price: {sn_price}")
        leo_proxy = LeoProxy(
          proxy_wallet=wallet,
          network=NETWORK,
          delegator=delegator,
        )
        leo_proxy.remove_stake(
          netuid=netuid,
          hotkey=dest_hotkey,
          amount=Balance.from_tao(user_stake_amount, netuid=netuid),
          tolerance=1,
          all=True,
        )
        print("Unstaked successfully")
        break
      subtensor.wait_for_block()
    except Exception as e:
      print(f"Error: {e}")