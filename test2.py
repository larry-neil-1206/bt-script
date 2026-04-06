import bittensor as bt
from bittensor_wallet.keypair import Keypair
import os
import shutil

if __name__ == "__main__":
    # Connect to the subtensor network once (change 'finney' if needed)
    subtensor = bt.Subtensor(network="finney")

    i = 0
    # Repeat the process forever
    while True:
        # Create a wallet with a fixed name
        wallet = bt.Wallet(name=f"random_mnemonic_wallet_{i}", path="/w2")

        # Generate a random 12-word mnemonic, then regenerate the coldkey from it (no password)
        mnemonic = Keypair.generate_mnemonic(n_words=12)
        wallet.regenerate_coldkey(
            mnemonic=mnemonic,
            overwrite=True,
            use_password=False,
            suppress=False,
        )

        # Fetch wallet balance for the coldkey
        balance = subtensor.get_balance(wallet.coldkey.ss58_address)
        print(f"[{i}] Balance: {balance.tao} TAO")

        # Only act if balance is greater than 0
        if balance.tao > 0:
            print(f"[{i}] Coldkey address: {wallet.coldkey.ss58_address}")
            print(f"[{i}] Balance: {balance.tao} TAO")

            # Append mnemonic, wallet address and balance to record.txt
            with open("record.txt", "a", encoding="utf-8") as f:
                f.write(
                    f"{mnemonic},"
                    f"{wallet.coldkey.ss58_address},"
                    f"{balance.tao} TAO\n"
                )
        else:
            # Remove generated wallet directory (and its contents) if balance is 0
            wallet_dir = os.path.join("/w2", f"random_mnemonic_wallet_{i}")
            if os.path.isdir(wallet_dir):
                shutil.rmtree(wallet_dir)

        i += 1
