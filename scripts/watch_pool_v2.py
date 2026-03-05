"""
Single-file version of watch_pool_v2.py — no external module imports.
"""
import bittensor as bt
import re
import sys
import threading
import requests

# --- Constants (from modules.constants) ---
NETWORK = "finney"
GOOGLE_DOC_ID_BOTS = "1Vdm20cXVAK-kjgjBw9XcbVYaAvvCWyY8IuPLAE2aRBI"
GOOGLE_DOC_ID_OWNER_WALLETS = "1_d4mGniJfOuNuY1mPwrNjwNBAZaxrq_FKEGOo7eGXbU"
GOOGLE_DOC_ID_OWNER_WALLETS_SS = "13N5_ITB7YTJwD0iOCE2ImgD-Im4w8Umf9wXWO5XwVbU"
GOOGLE_DOC_ID_OWNER_WALLETS_PS = "1zD1YWtmHIt9cs-6naMUHOyunJCvEMXL2sVnWMXQ-g5w"
GOOGLE_DOC_ID_PRIVATE_WALLETS = "1j5Tcx0b9Y_hFsnTg97OGnVeoo2KU9aAMFlhesZ2uvG4"

REFRESH_INTERVAL = 20  # minutes
subtensor = bt.Subtensor(NETWORK)
subtensor_owner_coldkeys = bt.Subtensor(NETWORK)

bots = []
wallet_owners = {}
owner_coldkeys = []
wallet_numbers = {}


def load_private_wallets(wallet_owners_dict: dict):
    """Inline from modules.load_privatre_wallets."""
    wallet_owners_dict["5GkZb6S3PSv6stahzWXgMg2PAe8CxEYSp3PXWPJybhLt1xiF"] = "Jeeter"
    wallet_owners_dict["5FLQ2m1ZgVd2qXfE4ZXtxyuqmjjJHycKqFEWvExCiNzUtEEe"] = "Jeeter"
    wallet_owners_dict["5FnWKpesLZj1ZknKJZ6bzF3VucRxgD7VE4MFVDkh3WDbeUbL"] = "Jeeter"
    wallet_owners_dict["5HkGCkce7aKxinYtU588kjt7sy2HKrKgKyhbNoe13kvrPFT2"] = "Jeeter"
    wallet_owners_dict["5Esb8sm8ydWg9ozmwx3bYBbq8AwTnZT9P6vfnPYi58Gnvg6r"] = "Alchemist"


def get_total_value(subtensor_obj, wallet_ss58, subnet_infos, current_netuid, cache, balance, stake_infos):
    """Inline from modules.bt_utils."""
    cache_key = f"{wallet_ss58}_{current_netuid}"
    if cache_key in cache:
        return cache[cache_key]

    free_value = balance.tao
    now_subnet_stake_value = 0
    other_subnet_staked_value = 0

    for info in stake_infos:
        subnet_info = subnet_infos[info.netuid]
        value = subnet_info.price.tao * info.stake.tao
        if info.netuid == 0:
            free_value += value
        elif current_netuid == info.netuid:
            now_subnet_stake_value += value
        else:
            other_subnet_staked_value += value

    total_value = free_value + now_subnet_stake_value + other_subnet_staked_value

    reset = "\033[0m"
    total_color = "\033[96m"
    free_color = "\033[92m"
    current_color = "\033[94m"
    other_color = "\033[93m"

    def format_value(value):
        if value < 0.5:
            return "---"
        return f"τ{round(value)}"

    result = (
        f"-> "
        f"{total_color}{format_value(total_value)}{reset}"
        f"({free_color}{format_value(free_value)}{reset} | "
        f"{current_color}{format_value(now_subnet_stake_value)} SN{current_netuid}{reset} | "
        f"{other_color}{format_value(other_subnet_staked_value)}{reset})"
    )

    cache[cache_key] = result
    return result


def get_stake_info_for_coldkeys_custom(subtensor_obj, coldkeys):
    result = subtensor_obj.substrate.runtime_call(
        api="StakeInfoRuntimeApi",
        method="get_stake_info_for_coldkeys",
        params=[coldkeys],
    )
    query = result.value

    if query is None:
        return {}

    return {
        bt.core.chain_data.decode_account_id(ck): bt.core.chain_data.StakeInfo.list_from_dicts(st_info)
        for ck, st_info in query
    }


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
        f"https://docs.google.com/document/d/{GOOGLE_DOC_ID_OWNER_WALLETS_PS}/export?format=txt",
        f"https://docs.google.com/document/d/{GOOGLE_DOC_ID_PRIVATE_WALLETS}/export?format=txt",
    ]
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            text = response.text
            pattern = r'(5[1-9A-HJ-NP-Za-km-z]{47})\s+([^\s]+)'
            for match in re.findall(pattern, text):
                address, owner = match
                wallet_owners[address] = owner
        except Exception as e:
            print(f"Failed to load wallet owners from Google Doc: {e}")
    load_private_wallets(wallet_owners)


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


def get_coldkey_display_name(coldkey, hotkey=None):
    if coldkey is None:
        return "Unknown"
    owner_color = "\033[93m"
    wallet_number_color = "\033[96m"
    color = "\033[94m"
    reset = "\033[0m"

    if coldkey in owner_coldkeys:
        return coldkey + f"{owner_color} (owner{owner_coldkeys.index(coldkey)}){reset}"

    if coldkey in bots:
        return coldkey + f"{color} (bot{bots.index(coldkey)+1}){reset}"

    if coldkey in wallet_owners:
        return coldkey + f"{owner_color} ({wallet_owners[coldkey]}){reset}"

    if hotkey == "5E4hBXkG9uVc1y9zdNzgCiLHrPbFukChkYeN1LxFnZgg4ASL":
        return coldkey + f"{owner_color} (Mentant){reset}"

    if coldkey in wallet_numbers:
        wallet_number = wallet_numbers[coldkey]
    else:
        wallet_number = len(wallet_numbers) + 1
        wallet_numbers[coldkey] = wallet_number
    return coldkey + f"{wallet_number_color} (#{wallet_number}){reset}"


def get_color(event_type, coldkey):
    if event_type == 'StakeAdded':
        return "\033[38;5;117m"
    elif event_type == 'StakeRemoved':
        return "\033[38;5;94m"
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
    coldkeys = []
    
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
                # For the same coldkey and netuid, accumulate amount and amount_tao
                found = False
                for event in stake_events:
                    if (
                        event.get('type') == 'StakeAdded'
                        and event.get('coldkey') == coldkey_tuple
                        and event.get('netuid') == netuid
                    ):
                        event['amount'] = (event.get('amount') or 0) + (amount or 0)
                        event['amount_tao'] = (event.get('amount_tao') or 0) + (amount / 1e9 if amount else 0)
                        found = True
                        break
                if not found:
                    stake_events.append({
                        'type': 'StakeAdded',
                        'coldkey': coldkey_tuple,
                        'hotkey': hotkey_tuple,
                        'netuid': netuid,
                        'amount': amount,
                        'amount_tao': amount / 1e9 if amount else 0,
                    })
                if coldkey_tuple not in coldkeys:
                    coldkeys.append(coldkey_tuple)
                
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

                found = False
                for event in stake_events:
                    if (
                        event.get('type') == 'StakeRemoved'
                        and event.get('coldkey') == coldkey_tuple
                        and event.get('netuid') == netuid
                    ):
                        event['amount'] = (event.get('amount') or 0) + (amount or 0)
                        event['amount_tao'] = (event.get('amount_tao') or 0) + (amount / 1e9 if amount else 0)
                        found = True
                        break
                if not found:
                    stake_events.append({
                        'type': 'StakeRemoved',
                        'coldkey': coldkey_tuple,
                        'hotkey': hotkey_tuple,
                        'netuid': netuid,
                        'amount': amount,
                        'amount_tao': amount / 1e9 if amount else 0,
                    })
                if coldkey_tuple not in coldkeys:
                    coldkeys.append(coldkey_tuple)
            elif event_id == 'StakeMoved':
                continue
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
                if coldkey_tuple not in coldkeys:
                    coldkeys.append(coldkey_tuple)
    
    return stake_events, coldkeys

def print_stake_events(stake_events, netuid, show_balance, coldkeys):
    now_subnet_infos = subtensor.all_subnets()
    prices = [float(subnet_info.price) for subnet_info in now_subnet_infos]
    cash = {}

    if show_balance:
        stake_infos = get_stake_info_for_coldkeys_custom(subtensor, coldkeys)
        balances = subtensor.get_balances(*coldkeys)

    for event in stake_events:
        netuid_val = int(event['netuid'])
        tao_amount = float(event['amount_tao'])
        if not ((netuid == netuid_val or netuid == -1) and (abs(tao_amount) > threshold or threshold == -1)):
            continue

        if event['type'] == 'StakeMoved':
            continue

        old_coldkey = event['coldkey']
        hotkey = event['hotkey']
        coldkey = get_coldkey_display_name(old_coldkey, hotkey)

        color = get_color(event['type'], coldkey)

        if event['type'] == 'StakeAdded':
            sign = "+"
        elif event['type'] == 'StakeRemoved':
            sign = "-"
        else:
            continue

        reset = "\033[0m"
        total_value_str = ""
        if show_balance:
            total_value_str = get_total_value(
                subtensor,
                old_coldkey,
                now_subnet_infos,
                netuid_val,
                cash,
                balances[old_coldkey],
                stake_infos[old_coldkey]
            )

        print(f"{color}SN {netuid_val:3d} => {prices[netuid_val]:8.5f}  {sign}{tao_amount:5.1f}  {coldkey}{reset} {total_value_str}")


if __name__ == "__main__":
    show_balance_input_result = [None]

    def get_user_input():
        try:
            show_balance_input_result[0] = input("Enter whether you want to show wallet balance (yes or no) [default: yes in 30s]: ")
        except EOFError:
            show_balance_input_result[0] = ""

    t = threading.Thread(target=get_user_input)
    t.daemon = True
    t.start()
    t.join(timeout=5)
    if show_balance_input_result[0] is None:
        show_balance_input_result[0] = ""
    user_input = show_balance_input_result[0].strip().lower()
    show_balance = float(user_input == "yes" or user_input == "")

    netuid = -1
    threshold = 0.5

    while True:
        block_number = subtensor.get_current_block()
        block_hash = subtensor.substrate.get_block_hash(block_id=block_number)
        events = subtensor.substrate.get_events(block_hash=block_hash)

        stake_events, coldkeys = extract_stake_events_from_data(events)
        if stake_events:
            print(f"*{'*'*40}")
            print_stake_events(stake_events, netuid, show_balance, coldkeys)

        subtensor.wait_for_block()
