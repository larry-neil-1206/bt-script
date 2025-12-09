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
    USE_ERA: bool = os.getenv("USE_ERA", "true").lower() == "true"
    
    # WALLET_NAMES: List[str] = os.getenv("WALLET_NAMES", "").split(",")
    # DELEGATORS: List[str] = os.getenv("DELEGATORS", "").split(",")
    WALLET_NAMES: List[str] = ["leo"]
    DELEGATORS: List[str] = ["5CsiGTsNBAn1bNiGNEd5LYpo6bm3PXT5ogPrQmvpZaUb2XzZ"]
    
    ADMIN_HASH: str = "$2b$12$nJCB59aSOjndYY665l/zN.SMIB5OSIv6TagvBcUUyhBKD2wi/WTUC"

settings = Settings()

print(f"USE_ERA: {settings.USE_ERA}")