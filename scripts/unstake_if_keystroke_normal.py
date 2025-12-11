import time
import bittensor as bt

from app.constants import ROUND_TABLE_HOTKEY

if __name__ == '__main__':
    
    netuid = int(input("Enter the netuid: "))

    subtensor = bt.Subtensor(network="finney")
    subnet = subtensor.subnet(netuid=netuid)
    alpha_price = subnet.alpha_to_tao(1)
    print(f"Current alpha token price: {alpha_price} TAO")

    wallet_name = input("Enter the wallet name: ")            
    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()
    dest_hotkey = input("Enter the destination hotkey (default is Round table): ") or ROUND_TABLE_HOTKEY
    
    print("Press 'y' to unstake, or Ctrl+C to exit")
    try:
        if input().lower() == 'y':
            while True:
                try:
                    result = subtensor.unstake(
                        netuid=netuid,
                        wallet=wallet,
                        hotkey_ss58=dest_hotkey,
                    )
                    if result:
                        break
                except Exception as e:
                    print(f"Error: {e}")
                    continue
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        
