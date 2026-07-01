import bittensor as bt

        
if __name__ == '__main__':
    
    wallet_name = input("Enter the wallet name: ")            

    subtensor = bt.Subtensor('finney')

    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()
    
    subtensor.unstake(
        hotkey_ss58='5GW2HAdmcbSR6p2QECmcVa7Rccyjm7WeAxN7EsWYvNN7kvv4',
        netuid=0,
        amount=bt.Balance.from_tao(0.5),
        wallet=wallet
    )
    print(f"Unstaked from 5GW2HAdmcbSR6p2QECmcVa7Rccyjm7WeAxN7EsWYvNN7kvv4 on netuid {0}")
