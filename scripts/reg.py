import sys
import os

# Add the parent directory to the Python search path (sys.path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import bittensor as bt
from app.constants import NETWORK

from bittensor_wallet import Wallet
from bittensor.core.subtensor import Subtensor
from scalecodec import (
    GenericCall,
    GenericExtrinsic,
    GenericRuntimeCallDefinition,
    ss58_encode,
)
import json
from typing import Optional
import random
def sign_extrinsic(
    subtensor:"Subtensor",
    call: "GenericCall",
    wallet: "Wallet",
    sign_with: str = "coldkey",
    use_nonce: bool = False,
    period: Optional[int] = None,
    nonce_key: str = "hotkey",
) -> GenericExtrinsic:
    """
    Helper method to sign and submit an extrinsic call to chain.

    Arguments:
        call (scalecodec.types.GenericCall): a prepared Call object
        wallet (bittensor_wallet.Wallet): the wallet whose coldkey will be used to sign the extrinsic
        wait_for_inclusion (bool): whether to wait until the extrinsic call is included on the chain
        wait_for_finalization (bool): whether to wait until the extrinsic call is finalized on the chain
        sign_with: the wallet's keypair to use for the signing. Options are "coldkey", "hotkey", "coldkeypub"

    Returns:
        (success, error message)
    """
    possible_keys = ("coldkey", "hotkey", "coldkeypub")
    if sign_with not in possible_keys:
        raise AttributeError(
            f"'sign_with' must be either 'coldkey', 'hotkey' or 'coldkeypub', not '{sign_with}'"
        )

    signing_keypair = getattr(wallet, sign_with)
    extrinsic_data = {"call": call, "keypair": signing_keypair}
    if use_nonce:
        if nonce_key not in possible_keys:
            raise AttributeError(
                f"'nonce_key' must be either 'coldkey', 'hotkey' or 'coldkeypub', not '{nonce_key}'"
            )
        next_nonce = subtensor.substrate.get_account_next_index(
            getattr(wallet, nonce_key).ss58_address
        )
        extrinsic_data["nonce"] = next_nonce
    if period is not None:
        extrinsic_data["era"] = {"period": period}

    extrinsic = subtensor.substrate.create_signed_extrinsic(**extrinsic_data)

    return extrinsic


def send_extrinsic(subtensor:"Subtensor", 
    extrinsic: GenericExtrinsic,
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
):
    try:
        # response = subtensor.substrate.submit_extrinsic(
        #     extrinsic,
        #     wait_for_inclusion=wait_for_inclusion,
        #     wait_for_finalization=wait_for_finalization,
        # )
        # # We only wait here if we expect finalization.
        # if not wait_for_finalization and not wait_for_inclusion:
        #     return True, ""

        # if response.is_success:
        #     return True, ""

        # return False, str(response.error_message)

        response = subtensor.substrate.rpc_request("author_submitExtrinsic", [str(extrinsic.data)])
        if "result" not in response:
            raise "Error"
        return True, ""
    
    except Exception as e:
        return False, str(e)


def dtao_register(netuid, subtensor: "Subtensor", wallet: "Wallet", block = 0):
    call = subtensor.substrate.compose_call(
        call_module="SubtensorModule",
        call_function="burned_register",
        call_params={
            "netuid": netuid,
            "hotkey": wallet.hotkey.ss58_address,
        },
    )
    extrinsic = sign_extrinsic(
        subtensor=subtensor,
        call=call,
        wallet=wallet,
    )

    ws = subtensor.substrate.ws
    payload = {
        "jsonrpc": "2.0", "method": "chain_getHeader", "params": [None], "id": 0
    }
    get_block_ws_data = json.dumps(payload)
    method = "author_submitExtrinsic"
    params = [str(extrinsic.data)]
    payload_id = f"{method}{random.randint(0, 7000)}"
    payload = {
        "id": payload_id,
        "payload": {"jsonrpc": "2.0", "method": method, "params": params},
    }
    
    item_id = f"{method}{random.randint(0, 7000)}"
    burned_register_ws_data = json.dumps({**payload["payload"], **{"id": item_id}})

    while True:
        try:
            ws.send(get_block_ws_data)
            response = json.loads(ws.recv())
            b = int(response["result"]["number"],0)
            if block != 0 and b < block: 
                print(f"Waiting for the {block}: current Block {b}")
            if b > block + 20:
                print(f"Block {b} is too far from the expected block {block}")
                break
            ws.send(burned_register_ws_data)
            response = json.loads(ws.recv())
        except Exception as e:
            print(e)
            continue

def reg_in_the_next_avaialbale_block(subtensor: "Subtensor", wallet: "Wallet", netuid: int, delta_block: int):
    prev_adjustment_block = subtensor.query_map_subtensor(name='LastAdjustmentBlock',params=(),block=subtensor.block)[netuid][1].value
    block = prev_adjustment_block + 360
    
    if delta_block == -100:
        block = 0
    else:
        block = block + delta_block

    print(f"Registering to the subnet {netuid} at block {block}")
    dtao_register(netuid, subtensor, wallet, block)    

if __name__ == '__main__':
    netuid = int(input("Enter the netuid: "))
    wallet_name = input("Enter the wallet name: ")
    hotkey = input("Enter the hotkey: ")
    delta_block = int(input("Enter the delta block: "))

    # Create a wallet instance
    wallet = bt.Wallet(name=wallet_name, hotkey=hotkey)
    wallet.unlock_coldkey()
    
    subtensor = bt.Subtensor(network=NETWORK)
    while True:
        try:
            reg_in_the_next_avaialbale_block(subtensor, wallet, netuid, delta_block)
        except Exception as e:
            print(f"Error in reg_in_the_next_avaialbale_block: {e}")
            continue