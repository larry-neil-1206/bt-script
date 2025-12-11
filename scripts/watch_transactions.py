import bittensor as bt
import threading
import requests
import re


REFRESH_INTERVAL = 20 # minutes
NETWORK = "finney"
#NETWORK = "ws://161.97.128.68:9944"
subtensor = bt.Subtensor(NETWORK)
subtensor_owner_coldkeys = bt.Subtensor(NETWORK)

bots = []
wallet_owners = {}
owner_coldkeys = []


def load_bots_from_gdoc():
    url = "https://docs.google.com/document/d/1Vdm20cXVAK-kjgjBw9XcbVYaAvvCWyY8IuPLAE2aRBI/export?format=txt"
    try:
        global bots
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        text = response.text
        bots = re.findall(r'5[1-9A-HJ-NP-Za-km-z]{47}', text)
    except Exception as e:
        print(f"Failed to load bots from Google Doc: {e}")

def load_wallet_owners_from_gdoc():
    url = "https://docs.google.com/document/d/1VUDA8mzHd_iUQEqiDWMORys6--2ab8nDSThGb--_PaQ/export?format=txt"
    try:
        global wallet_owners
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        text = response.text
        # Each pair is like: <wallet_address> <owner_name>
        # build a dict mapping wallet address to owner name
        wallet_owners = {}
        pattern = r'(5[1-9A-HJ-NP-Za-km-z]{47})\s+([^\s]+)'
        for match in re.findall(pattern, text):
            address, owner = match
            wallet_owners[address] = owner
    except Exception as e:
        print(f"Failed to load wallet owners from Google Doc: {e}")

def refresh_bots_periodically(interval_minutes=REFRESH_INTERVAL):
    def refresh_bots():
        load_wallet_owners_from_gdoc()  
        load_bots_from_gdoc()
        # Reschedule the timer to run again
        threading.Timer(interval_minutes * 60, refresh_bots, []).start()
    refresh_bots()

refresh_bots_periodically()


def refresh_owner_coldkeys_periodically(interval_minutes=REFRESH_INTERVAL):
    def refresh_owner_coldkeys():
        subnet_infos = subtensor_owner_coldkeys.all_subnets()
        global owner_coldkeys
        owner_coldkeys = [subnet_info.owner_coldkey for subnet_info in subnet_infos]
        # Reschedule the timer to run again
        threading.Timer(interval_minutes * 60, refresh_owner_coldkeys, []).start()
    refresh_owner_coldkeys()

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
    
    return coldkey

def get_color(event_type, coldkey):
    if event_type == 'StakeAdded':
        return "\033[92m"
    elif event_type == 'StakeRemoved':
        return "\033[91m"
    else:
        return "\033[0m"


def extract_stake_events_from_data(events_data):
    """
    Extract stake and unstake events from blockchain event data.
    
    Args:
        events_data: List of event dictionaries from blockchain
    
    Returns:
        List of dictionaries containing stake/unstake event information
    """
    stake_events = []
    
    for event in events_data:
        phase = event.get('phase', {})
        event_info = event.get('event', {})
        
        # Check if this is a SubtensorModule event
        if event_info.get('module_id') == 'SubtensorModule':
            event_id = event_info.get('event_id')
            attributes = event_info.get('attributes', {})
            
            # Convert coldkey and hotkey to ss58 addresses if possible
            def to_ss58(addr_bytes, ss58_format = 42):
                if addr_bytes is None:
                    return None
                pubkey_bytes = bytes(addr_bytes).hex()
                if not pubkey_bytes.startswith("0x"):
                    pubkey_bytes = "0x" + pubkey_bytes
                return subtensor.substrate.ss58_encode(pubkey_bytes, ss58_format=ss58_format)
                
            if event_id == 'StakeAdded':
                # The attributes for StakeAdded are a tuple, not a dict.
                # Example: (
                #   ((coldkey_bytes,), (hotkey_bytes,), amount, stake, netuid, block_number)
                # )
                # So we need to unpack the tuple accordingly.
                if isinstance(attributes, tuple) and len(attributes) >= 6:
                    coldkey_tuple = to_ss58(attributes[0][0]) if isinstance(attributes[0], tuple) and len(attributes[0]) > 0 else attributes[0]
                    hotkey_tuple = to_ss58(attributes[1][0]) if isinstance(attributes[1], tuple) and len(attributes[1]) > 0 else attributes[1]
                    amount = attributes[2]
                    # attributes[3] is stake, but we use amount for TAO
                    netuid = attributes[4]
                else:
                    coldkey_tuple = None
                    hotkey_tuple = None
                    amount = None
                    netuid = None
                stake_events.append({
                    'type': 'StakeAdded',
                    'coldkey': coldkey_tuple,
                    'hotkey': hotkey_tuple,
                    'netuid': netuid,
                    'amount': amount,
                    'amount_tao': amount / 1e9 if amount else 0,
                })
                
            elif event_id == 'StakeRemoved':
                # Extract unstake information - also a tuple
                if isinstance(attributes, tuple) and len(attributes) >= 6:
                    coldkey_tuple = to_ss58(attributes[0][0]) if isinstance(attributes[0], tuple) and len(attributes[0]) > 0 else attributes[0]
                    hotkey_tuple = to_ss58(attributes[1][0]) if isinstance(attributes[1], tuple) and len(attributes[1]) > 0 else attributes[1]
                    amount = attributes[2]
                    netuid = attributes[4]
                else:
                    coldkey_tuple = None
                    hotkey_tuple = None
                    amount = None
                    netuid = None
                    block_number = None

                stake_events.append({
                    'type': 'StakeRemoved',
                    'coldkey': coldkey_tuple,
                    'hotkey': hotkey_tuple,
                    'netuid': netuid,
                    'amount': amount,
                    'amount_tao': amount / 1e9 if amount else 0,
                })
                
            elif event_id == 'StakeMoved':
                # Extract stake move information - also a tuple
                if isinstance(attributes, tuple) and len(attributes) >= 6:
                    coldkey_tuple = to_ss58(attributes[0][0]) if isinstance(attributes[0], tuple) and len(attributes[0]) > 0 else attributes[0]
                    from_hotkey_tuple = to_ss58(attributes[1][0]) if isinstance(attributes[1], tuple) and len(attributes[1]) > 0 else attributes[1]
                    to_hotkey_tuple = to_ss58(attributes[3][0]) if isinstance(attributes[3], tuple) and len(attributes[3]) > 0 else attributes[3]
                    netuid = attributes[4]
                    amount = attributes[5]
                else:
                    coldkey_tuple = None
                    from_hotkey_tuple = None
                    to_hotkey_tuple = None
                    netuid = None
                    amount = None
                
                stake_events.append({
                    'type': 'StakeMoved',
                    'coldkey': coldkey_tuple,
                    'from_hotkey': from_hotkey_tuple,
                    'to_hotkey': to_hotkey_tuple,
                    'netuid': netuid,
                    'amount': amount,
                    'amount_tao': amount / 1e9 if amount else 0,
                })
    
    return stake_events
def print_stake_events(stake_events, netuid):
    now_subnet_infos = subtensor.all_subnets()
    prices = [float(subnet_info.price) for subnet_info in now_subnet_infos]
    for event in stake_events:
        netuid_val = int(event['netuid'])
        tao_amount = float(event['amount_tao'])
        coldkey = event['coldkey']
        coldkey = get_coldkey_display_name(coldkey)

        color = get_color(event['type'], coldkey)    

        # Green for stake added, red for stake removed (bright)
        if event['type'] == 'StakeAdded':
            sign = "+"
        elif event['type'] == 'StakeRemoved':
            sign = "-"
        else:
            continue

        reset = "\033[0m"
        if (netuid == netuid or netuid == -1) and (abs(tao_amount) > threshold or threshold == -1):
            print(f"{color}SN {netuid_val:3d} => {prices[netuid_val]:8.5f}  {sign}{tao_amount:5.1f}  {coldkey}{reset}")

                  
if __name__ == "__main__":    

    #netuid = int(input("Enter the netuid: "))
    #threshold = float(input("Enter the threshold: "))
    netuid = -1
    threshold = 0.5
    while True:
        block_number = subtensor.get_current_block()
        block_hash = subtensor.substrate.get_block_hash(block_id=block_number)
        events = subtensor.substrate.get_events(block_hash=block_hash)

        
        # Extract stake events from live data
        stake_events = extract_stake_events_from_data(events)
        if stake_events:
            print(f"*{'*'*40}")
            print_stake_events(stake_events, netuid)
        
        subtensor.wait_for_block()