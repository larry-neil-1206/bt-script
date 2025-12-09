import re

def get_sn_price(subtensor, netuid):
    subnet = subtensor.subnet(netuid=netuid)
    if subnet is None:
        raise Exception(f"Subnet is None for netuid: {netuid}")
    sn_price_raw = subnet.alpha_to_tao(1)
    sn_price = float(str(sn_price_raw).replace('τ', '').strip())
    return sn_price

def convert_alpha_to_float(raw_amount):
    if isinstance(raw_amount, (int, float)):
        amount = float(raw_amount)
    else:
        s = str(raw_amount).strip()
        # If last char isn't digit or dot, drop it
        if s and not (s[-1].isdigit() or s[-1] == '.'):
            s = s[:-1]
        # Remove common grouping separators
        s = s.replace(',', '')
        try:
            amount = float(s)
        except ValueError:
            m = re.search(r'[-+]?[0-9]*\.?[0-9]+', s)
            if m:
                amount = float(m.group(0))
            else:
                raise ValueError(f"Could not parse stake amount: {raw_amount}")

    return amount

# Convert coldkey and hotkey to ss58 addresses if possible
def to_ss58(subtensor, addr_bytes, ss58_format = 42):
    if addr_bytes is None:
        return None
    pubkey_bytes = bytes(addr_bytes).hex()
    if not pubkey_bytes.startswith("0x"):
        pubkey_bytes = "0x" + pubkey_bytes
    return subtensor.substrate.ss58_encode(pubkey_bytes, ss58_format=ss58_format)
    
def extract_stake_events_from_data(subtensor, events_data):
    """
    Extract stake and unstake events from blockchain event data.
    
    Args:
        events_data: List of event dictionaries from blockchain
    
    Returns:
        List of dictionaries containing stake/unstake event information
    """
    stake_events = []
    
    for event in events_data:
        event_info = event.get('event', {})
        
        # Check if this is a SubtensorModule event
        if not event_info.get('module_id') == 'SubtensorModule':
            continue

        event_id = event_info.get('event_id')
        attributes = event_info.get('attributes', {})
        
           
        if event_id == 'StakeAdded':
            # The attributes for StakeAdded are a tuple, not a dict.
            # Example: (
            #   ((coldkey_bytes,), (hotkey_bytes,), amount, stake, netuid, block_number)
            # )
            # So we need to unpack the tuple accordingly.
            if isinstance(attributes, tuple) and len(attributes) >= 6:
                coldkey_tuple = to_ss58(subtensor, attributes[0][0]) if isinstance(attributes[0], tuple) and len(attributes[0]) > 0 else attributes[0]
                hotkey_tuple = to_ss58(subtensor, attributes[1][0]) if isinstance(attributes[1], tuple) and len(attributes[1]) > 0 else attributes[1]
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
                coldkey_tuple = to_ss58(subtensor, attributes[0][0]) if isinstance(attributes[0], tuple) and len(attributes[0]) > 0 else attributes[0]
                hotkey_tuple = to_ss58(subtensor, attributes[1][0]) if isinstance(attributes[1], tuple) and len(attributes[1]) > 0 else attributes[1]
                amount = attributes[2]
                netuid = attributes[4]
            else:
                coldkey_tuple = None
                hotkey_tuple = None
                amount = None
                netuid = None

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
                coldkey_tuple = to_ss58(subtensor, attributes[0][0]) if isinstance(attributes[0], tuple) and len(attributes[0]) > 0 else attributes[0]
                from_hotkey_tuple = to_ss58(subtensor, attributes[1][0]) if isinstance(attributes[1], tuple) and len(attributes[1]) > 0 else attributes[1]
                to_hotkey_tuple = to_ss58(subtensor, attributes[3][0]) if isinstance(attributes[3], tuple) and len(attributes[3]) > 0 else attributes[3]
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

# def print_stake_events(subtensor, stake_events):
#     now_subnet_infos = subtensor.all_subnets()
#     prices = [float(subnet_info.price) for subnet_info in now_subnet_infos]
#     for event in stake_events:
#         netuid_val = int(event['netuid'])
#         tao_amount = float(event['amount_tao'])
#         coldkey = event['coldkey']
#         coldkey = get_coldkey_display_name(coldkey)

#         color = get_color(event['type'], coldkey)    

#         # Green for stake added, red for stake removed (bright)
#         if event['type'] == 'StakeAdded':
#             sign = "+"
#         elif event['type'] == 'StakeRemoved':
#             sign = "-"
#         else:
#             continue

#         reset = "\033[0m"
#         print(f"{color}SN {netuid_val:3d} => {prices[netuid_val]:8.5f}  {sign}{tao_amount:5.1f}  {coldkey}{reset}")