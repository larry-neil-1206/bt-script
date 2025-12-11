import time
import datetime
import asyncio
import argparse
import traceback
import bittensor as bt

from bittensor import AsyncSubtensor
from bittensor.utils.networking import get_external_ip


async def boot():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coldkey', type=str, default="miners")
    parser.add_argument('--hotkey', type=str, default="miner_1")
    parser.add_argument('--netuid', type=int, default=15)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--external_ip', type=str, default=None)
    parser.add_argument('--subtensor_address', type=str, default="finney")
    parser.add_argument('--wallet_path', type=str, default="~/.bittensor/wallets/")

    args = parser.parse_args()

    wallet = bt.Wallet(args.coldkey, args.hotkey, path=args.wallet_path)
    axon = bt.axon(wallet=wallet, port=args.port, external_ip=args.external_ip)
    subtensor = bt.Subtensor(network=args.subtensor_address)
    try:
        subtensor.serve_axon(
            netuid=args.netuid,
            axon=axon
        )
        metagraph = subtensor.metagraph(args.netuid)

        if wallet.hotkey.ss58_address not in metagraph.hotkeys:
            print(f"\nYour miner: {wallet} is not registered. Run 'btcli register'.")
            exit()
        my_subnet_uid = metagraph.hotkeys.index(wallet.hotkey.ss58_address)
        print(f"coldkey: {args.coldkey}, hotkey: {args.hotkey}, UID: {my_subnet_uid}")
        print(f"Axon served on {args.external_ip}:{args.port}")
    except Exception as e:
        print(f"Error serving axon: {e}")
        traceback.print_exc()
    
if __name__ == "__main__":
    asyncio.run(boot())