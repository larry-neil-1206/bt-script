import sys
import os

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
import bittensor as bt
from app.constants import NETWORK
from utils.logger import logger

if __name__ == '__main__':
    netuid_input = input("Enter the netuids (comma-separated): ")
    netuids = [int(uid.strip()) for uid in netuid_input.split(',')]
    
    subtensor = bt.Subtensor(network=NETWORK)
    prev_tao_in = {uid: 0 for uid in netuids}
    prev_price = {uid: 0 for uid in netuids}
    
    # Color codes
    green = "\033[38;5;46m"
    red = "\033[38;5;196m"
    reset = "\033[0m"
    
    while True:
        try:
            for netuid in netuids:
                subnet = subtensor.subnet(netuid=netuid)
                if subnet is None:
                    logger.error(f"Subnet is None for netuid: {netuid}")
                    continue
                
                price = float(subnet.alpha_to_tao(1).tao)
                now_tao_in = subnet.tao_in
                if now_tao_in is None:
                    logger.error(f"Now tao in is None for netuid: {netuid}")
                    continue
                
                tao_flow = now_tao_in - prev_tao_in[netuid]
                price_change = price - prev_price[netuid]
                
                # Determine color based on price change
                if price_change > 0:
                    price_color = green
                    change_str = f"+{price_change:.6f}"
                elif price_change < 0:
                    price_color = red
                    change_str = f"{price_change:.6f}"
                else:
                    price_color = reset
                    change_str = "0.000000"
                
                print(f"Netuid: {netuid} ===> price: {price_color}{price:.6f}{reset} [{change_str}], tao_flow: {tao_flow}")
                prev_tao_in[netuid] = now_tao_in
                prev_price[netuid] = price
            
            subtensor.wait_for_block()
            print(f"*{'*'*40}")
            
        except Exception as e:
            logger.error(f"Error in watching_price: {e}")
            continue