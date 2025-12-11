import bittensor as bt

        
if __name__ == '__main__':
    
    netuid = int(input("Enter the netuid or -1 for all: "))
    wallet_name = input("Enter the wallet name: ")            

    subtensor = bt.Subtensor('finney')

    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()
    
    stake_infos = subtensor.get_stake_for_coldkey(
        coldkey_ss58=wallet.coldkey.ss58_address
    )

    for info in stake_infos:
        if netuid != -1 and info.netuid != netuid:
            continue

        subtensor.unstake(
            hotkey_ss58=info.hotkey_ss58,
            netuid=info.netuid,
            amount=None,
            wallet=wallet
        )
        print(f"Unstaked from {info.hotkey_ss58} on netuid {info.netuid}")
