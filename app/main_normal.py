import os
import fastapi
import bittensor as bt
import uvicorn
import subprocess
from typing import Dict
from fastapi import Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv


from app.core.config import settings
from app.services.auth import get_current_username
from app.constants import ROUND_TABLE_HOTKEY, NETWORK

app = fastapi.FastAPI()

# Set up templates
templates = Jinja2Templates(directory="app/templates")

wallet_names = ["green"]
wallets: Dict[str, bt.Wallet] = {}

def unlock_wallets():
    for wallet_name in wallet_names:
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
        wallets[wallet_name] = wallet


unlock_wallets()

@app.get("/")
def read_root(request: fastapi.Request, username: str = Depends(get_current_username)):
    try:
        subtensor = bt.Subtensor(network=NETWORK)
        def get_balance_html():
            balance_html = ""
            for wallet_name in wallet_names:
                wallet = wallets[wallet_name]
                balance = subtensor.get_balance(wallet.coldkey.ss58_address)
                balance_html += f"""
                    <div class="balance-container">
                        <div class="balance-title"><a target="_blank" href="/stake_list?wallet_name={wallet_name}" style="text-decoration: none; color: inherit; cursor: pointer; text-decoration: underline;">{wallet_name}</a></div>
                        <div class="balance-amount">{balance} TAO</div>
                    </div>
                """
            return balance_html

        return templates.TemplateResponse(
            "index_normal.html",
            {"request": request, "balance_html": get_balance_html(), "wallet_names": wallet_names}
        )
    except Exception as e:
        print(e)



@app.get("/stake")
def stake(
    tao_amount: float, 
    netuid: int, 
    wallet_name: str, 
    dest_hotkey: str = ROUND_TABLE_HOTKEY, 
    rate_tolerance: float = 0.005,
    min_tolerance_staking: bool = True,
    retries: int = 1,
    username: str = Depends(get_current_username)
):
    if retries < 1:
        retries = 1
    result = None
    wallet = wallets[wallet_name]
    subtensor = bt.Subtensor(network=NETWORK)

    while retries > 0:
        try:

            result = subtensor.add_stake(
                netuid=netuid,
                amount= bt.Balance.from_tao(tao_amount, netuid),
                wallet=wallet,
                hotkey_ss58=dest_hotkey,
                safe_staking=True,
                rate_tolerance=rate_tolerance
            )
            if not result:
                raise Exception("Stake failed")
            
            return {
                "success": True,
                "result": result,
            }
        except Exception as e:
            retries -= 1
            if retries == 0:
                return {
                    "success": False,
                    "result": result,
                }


@app.get("/unstake")
def unstake(
    netuid: int,
    wallet_name: str,
    amount: float = None,
    dest_hotkey: str = ROUND_TABLE_HOTKEY,
    rate_tolerance: float = 0.005,
    min_tolerance_unstaking: bool = True,
    retries: int = 1,
    username: str = Depends(get_current_username)
):
    if retries < 1:
        retries = 1
    result = None
    wallet = wallets[wallet_name]
    subtensor = bt.Subtensor(network=NETWORK)
    subnet = subtensor.subnet(netuid=netuid)

    if amount is None:
        amount = subtensor.get_stake(
            coldkey_ss58=wallet.coldkeypub.ss58_address,
            hotkey_ss58=dest_hotkey,
            netuid=netuid
        )
    else:
        amount = bt.Balance.from_tao(amount / subnet.price.tao, netuid)
                    
    while retries > 0:
        try:
            result = subtensor.unstake(
                netuid=netuid, 
                wallet=wallet, 
                amount=amount,
                hotkey_ss58=dest_hotkey,
                safe_staking=True,
                rate_tolerance=rate_tolerance,
            )
            if not result:
                raise Exception("Unstake failed")
            
            return {
                "success": True,
                "result": result,
            }
        
        except Exception as e:
            retries -= 1
            if retries == 0:
                return {
                    "success": False,
                    "result": result,
                }