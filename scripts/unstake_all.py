import bittensor as bt

        
if __name__ == '__main__':
    
    wallet_name = input("Enter the wallet name: ")            

    subtensor = bt.Subtensor('finney')

    wallet = bt.Wallet(name=wallet_name)
    wallet.unlock_coldkey()
    
    subtensor.unstake(
        hotkey_ss58='5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21',
        netuid=0,
        amount=bt.Balance.from_tao(1),
        wallet=wallet
    )
    print(f"Unstaked from 5Gq2gs4ft5dhhjbHabvVbAhjMCV2RgKmVJKAFCUWiirbRT21 on netuid {0}")
