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
    netuid = int(input("Enter the netuid: "))
    subtensor = bt.Subtensor(network=NETWORK)
    prev_tao_in = 0
    while True:
        try:
            subnet = subtensor.subnet(netuid=netuid)
            if subnet is None:
                logger.error(f"Subnet is None for netuid: {netuid}")
                continue
            
            price = subnet.alpha_to_tao(1)
            now_tao_in = subnet.tao_in
            if now_tao_in is None:
                logger.error(f"Now tao in is None for netuid: {netuid}")
                continue
            tao_flow = now_tao_in - prev_tao_in
            logger.info(f"Netuid: {netuid} ===> price: {price}, tao_flow: {tao_flow}")
            prev_tao_in = now_tao_in
            subtensor.wait_for_block()
        except Exception as e:
            logger.error(f"Error in watching_price: {e}")
            continue