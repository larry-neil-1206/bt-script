import os
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from app.constants import ROUND_TABLE_HOTKEY

# Load environment variables from .env file
load_dotenv(".env")


class Settings(BaseModel):
    VERSION: str = "0.1.0"
    NETWORK: str = "wss://entrypoint-finney.opentensor.ai:443"
    #NETWORK: str = "ws://161.97.128.68:9944"

    # WALLET_NAMES: List[str] = []
    # DELEGATORS: List[str] = []
    DEFAULT_RATE_TOLERANCE: float = 0.005
    DEFAULT_MIN_TOLERANCE: bool = False
    DEFAULT_RETRIES: int = 1
    DEFAULT_DEST_HOTKEY: str = ROUND_TABLE_HOTKEY
    
    # WALLET_NAMES: List[str] = os.getenv("WALLET_NAMES", "").split(",")
    # DELEGATORS: List[str] = os.getenv("DELEGATORS", "").split(",")
    WALLET_NAMES: List[str] = ["black", "green", "webgenie"]
    DELEGATORS: List[str] = ["5DZhYqgHhRPYUHqjaU2gS2LNL7VS8Fb5utxZ7QEkVGqTnmh5","5FWhdv8o7fGo6yn54qXCn1xTxXsMaNLaotKYzUSG2iZp4tVZ", "5GhDziWFX56mTrG8Qgytr5bcPNDKVxnVeWCZt3PC4n59pCCP"]
    
    ADMIN_HASH: str = "$2b$12$rFj2f8j0jphOUMy3ZMjfdO9wQedLq7zSHmsjYDOU9zZkULYkdfMj2"

settings = Settings()
