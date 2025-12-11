import bittensor as bt
from typing import Dict, Tuple
from app.core.config import settings

wallets: Dict[str, Tuple[bt.Wallet, str]] = {}


def unlock_wallets():
    print(settings.WALLET_NAMES)
    for wallet_name in settings.WALLET_NAMES:
        wallet = bt.Wallet(name=wallet_name)
        print(f"Unlocking wallet {wallet_name}")
        retries = 3
        for _ in range(retries):
            try:
                wallet.unlock_coldkey()
                break
            except Exception as e:
                print(f"Error unlocking wallet {wallet_name}: {e}")
                continue
        wallets[wallet_name] = (wallet, settings.DELEGATORS[settings.WALLET_NAMES.index(wallet_name)])

unlock_wallets()