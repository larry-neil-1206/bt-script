import time
import bittensor as bt

from app.constants import ROUND_TABLE_HOTKEY

        
if __name__ == '__main__':
    
    netuid = int(input("Enter the netuid: "))
    threshold = float(input("Enter the threshold price (in TAO): "))

    subtensor = bt.Subtensor(network="finney")
    subnet = subtensor.subnet(netuid=netuid)
    alpha_price = subnet.alpha_to_tao(1)
    print(f"Current alpha token price: {alpha_price} TAO")

    wallet_name = input("Enter the wallet name: ")            
    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()
    dest_hotkey = input("Enter the destination hotkey (default is Round table): ") or ROUND_TABLE_HOTKEY
    
    print("Press Ctrl+C to stop the script")
    while True:
        try:
            subnet = subtensor.subnet(netuid=netuid)
            alpha_price = subnet.alpha_to_tao(1)
            print(f"Current alpha token price: {alpha_price} TAO")
            
            if threshold != -1 and alpha_price < bt.Balance.from_tao(threshold):
                print(f"Current price {alpha_price} TAO is below threshold {threshold} TAO. Skipping...")
                continue
            
            subtensor.unstake(
                netuid=netuid,
                wallet=wallet,
                hotkey_ss58=dest_hotkey,
            )
            break
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
        
