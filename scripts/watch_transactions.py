import bittensor as bt
import threading
import requests
import re

# Constants (inlined from modules.constants)
NETWORK = "finney"

CEXS = {
    "5FqBL928choLPmeFz5UVAvonBD5k7K2mZSXVC9RkFzLxoy2s": "MEXC",
    "5GBnPzvPghS8AuCoo6bfnK7JUFHuyUhWSFD4woBNsKnPiEUi": "Binance",
    "5HiveMEoWPmQmBAb8v63bKPcFhgTGCmST1TVZNvPHSTKFLCv": "Taobridge",
    "5FqqXKb9zonSNKbZhEuHYjCXnmPbX9tdzMCU2gx8gir8Z8a5": "Cex",
}

GOOGLE_DOC_ID_OWNER_WALLETS = "1_d4mGniJfOuNuY1mPwrNjwNBAZaxrq_FKEGOo7eGXbU"
GOOGLE_DOC_ID_BOTS = "1Vdm20cXVAK-kjgjBw9XcbVYaAvvCWyY8IuPLAE2aRBI"
GOOGLE_DOC_ID_CHANNELS = "1c-KDhGKINbJRKlXBtsLahyuNIZg3ptRic1ZwM1PpWo4"
GOOGLE_DOC_ID_OWNER_WALLETS_SS = "13N5_ITB7YTJwD0iOCE2ImgD-Im4w8Umf9wXWO5XwVbU"
GOOGLE_DOC_ID_OWNER_WALLETS_PS = "1zD1YWtmHIt9cs-6naMUHOyunJCvEMXL2sVnWMXQ-g5w"

REFRESH_INTERVAL = 20 # minutes
subtensor = bt.Subtensor(NETWORK)
subtensor_owner_coldkeys = bt.Subtensor(NETWORK)

bots = []
wallet_owners = {}
owner_coldkeys = []


def load_bots_from_gdoc():
    url = f"https://docs.google.com/document/d/{GOOGLE_DOC_ID_BOTS}/export?format=txt"
    try:
        global bots
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        text = response.text
        bots = re.findall(r'5[1-9A-HJ-NP-Za-km-z]{47}', text)
    except Exception as e:
        print(f"Failed to load bots from Google Doc: {e}")
         
def load_wallet_owners_from_gdoc():
    global wallet_owners
    urls = [
        f"https://docs.google.com/document/d/{GOOGLE_DOC_ID_OWNER_WALLETS}/export?format=txt",
        f"https://docs.google.com/document/d/{GOOGLE_DOC_ID_OWNER_WALLETS_SS}/export?format=txt",
        f"https://docs.google.com/document/d/{GOOGLE_DOC_ID_OWNER_WALLETS_PS}/export?format=txt"
    ]
    for url in urls:    
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            text = response.text
            # Each pair is like: <wallet_address> <owner_name>
            # build a dict mapping wallet address to owner name
            pattern = r'(5[1-9A-HJ-NP-Za-km-z]{47})\s+([^\s]+)'
            for match in re.findall(pattern, text):
                address, owner = match
                wallet_owners[address] = owner

        except Exception as e:
            print(f"Failed to load wallet owners from Google Doc: {e}")

        
def refresh_bots_periodically(interval_minutes=REFRESH_INTERVAL):
    load_wallet_owners_from_gdoc()
    load_bots_from_gdoc()
    threading.Timer(interval_minutes * 60, refresh_bots_periodically, [interval_minutes]).start()

refresh_bots_periodically()


def refresh_owner_coldkeys_periodically(interval_minutes=REFRESH_INTERVAL):
    global owner_coldkeys
    subnet_infos = subtensor_owner_coldkeys.all_subnets()
    owner_coldkeys = [subnet_info.owner_coldkey for subnet_info in subnet_infos]
    threading.Timer(interval_minutes * 60, refresh_owner_coldkeys_periodically, [interval_minutes]).start()

refresh_owner_coldkeys_periodically()

def get_coldkey_display_name(coldkey):
    if coldkey is None:
        return "Unknown"
    owner_color = "\033[93m"
    color = "\033[94m"
    reset = "\033[0m" 

    if coldkey in owner_coldkeys:
        return coldkey + f"{owner_color} (owner{owner_coldkeys.index(coldkey)}){reset}"

    if coldkey in bots:
        return coldkey + f"{color} (bot{bots.index(coldkey)+1}){reset}"
    

    if coldkey in wallet_owners:
        return coldkey + f"{owner_color} ({wallet_owners[coldkey]}){reset}"
    
    if coldkey in CEXS:
        return coldkey + f"{owner_color} ({CEXS[coldkey]}){reset}"
    
    return coldkey

def get_color(event_type, coldkey):
    if event_type == 'StakeAdded':
        return "\033[92m"
    elif event_type == 'StakeRemoved':
        return "\033[91m"
    else:
        return "\033[0m"



def extract_transfer_events_from_data(events_data):
    # Extract events which transfer TAO, like StakeAdded, StakeRemoved, StakeMoved, and direct TAO transfers
    transfer_events = []
    for event in events_data:
        event_info = event.get('event', {})
        module_id = event_info.get('module_id')
        event_id = event_info.get('event_id')
        attributes = event_info.get('attributes', {})

        # SubtensorMo

        # Balances pallet (native TAO transfers)
        if module_id == 'Balances' and event_id in ('Transfer', 'Deposit'):
            # Transfer between accounts
            if event_id == 'Transfer':
                from_addr = attributes.get('from')
                to_addr = attributes.get('to')
                amount = attributes.get('amount')
                transfer_events.append({
                    'type': 'Transfer',
                    'from': from_addr,
                    'to': to_addr,
                    'amount': amount,
                    'amount_tao': amount / 1e9 if amount else 0,
                })
            # # Deposit event - typically corresponds to fee refund or reward
            # elif event_id == 'Deposit':
            #     to_addr = attributes.get('who')
            #     amount = attributes.get('amount')
            #     transfer_events.append({
            #         'type': 'Deposit',
            #         'to': to_addr,
            #         'amount': amount,
            #         'amount_tao': amount / 1e9 if amount else 0,
            #     })

    return transfer_events

def print_transfer_events(transfer_events, threshold):
     for event in transfer_events:
        from_addr = event['from']
        to_addr = event['to']
        amount_tao = event['amount_tao']
        from_owner_name = get_coldkey_display_name(from_addr)
        to_owner_name = get_coldkey_display_name(to_addr)

        if amount_tao > threshold:
            print(f"\033[91m{from_owner_name}\033[0m => \033[92m{to_owner_name}\033[0m: \033[94m{round(amount_tao, 1)} TAO\033[0m")

                  
if __name__ == "__main__":    
    
    #threshold = float(input("Enter the threshold: "))
    threshold = 0.5
    while True:
        block_number = subtensor.get_current_block()
        block_hash = subtensor.substrate.get_block_hash(block_id=block_number)
        events = subtensor.substrate.get_events(block_hash=block_hash)

        
        # Extract stake events from live data
        transfer_events = extract_transfer_events_from_data(events)
        print(f"{'*'*40}")
        
        if transfer_events:
            print_transfer_events(transfer_events, threshold)
        
        subtensor.wait_for_block()