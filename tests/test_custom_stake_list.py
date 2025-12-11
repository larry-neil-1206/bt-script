import sys
import os
import time

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


import bittensor as bt

from rich.console import Console
from rich.table import Table
from io import StringIO
from utils.stake_list import get_stake_list

if __name__ == "__main__":
    subtensor = bt.Subtensor("finney")
    wallet_ss58 = "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2"
    stake_list = get_stake_list(subtensor, wallet_ss58)    
    print(stake_list)
    

