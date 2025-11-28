import bittensor as bt
from typing import Dict, Tuple, Optional, Any

from app.core.config import settings
from app.services.proxy import Proxy
from app.services.wallets import wallets


class StakeService:
    """
    Service class for handling stake-related business logic.
    Encapsulates all staking operations including min tolerance calculations,
    stake/unstake operations with retry mechanisms, and error handling.
    """
    
    def __init__(self, wallets: Dict[str, Tuple[bt.wallet, str]]):
        """
        Initialize the StakeService with wallets and proxy instance.
        
        Args:
            wallets: Dictionary mapping wallet names to (wallet, delegator) tuples
            proxy: Proxy instance for handling stake operations
        """
        self.wallets = wallets
        self.proxy = Proxy(settings.NETWORK, use_era=settings.USE_ERA)
        self.subtensor = bt.subtensor(network=settings.NETWORK)
    
    def get_stake_min_tolerance(self, tao_amount: float, netuid: int) -> float:
        """
        Calculate the minimum tolerance for staking operations.
        
        Args:
            tao_amount: Amount in TAO
            netuid: Network/subnet ID
            
        Returns:
            float: Minimum tolerance value
        """
        subnet = self.subtensor.subnet(netuid=netuid)
        if subnet is None:
            raise ValueError(f"Subnet with netuid {netuid} does not exist")
        min_tolerance = tao_amount / subnet.tao_in.tao
        return min_tolerance


    def get_unstake_min_tolerance(self, tao_amount: float, netuid: int) -> float:
        """
        Calculate the minimum tolerance for unstaking operations.
        """
        subnet = self.subtensor.subnet(netuid=netuid)
        if subnet is None:
            raise ValueError(f"Subnet with netuid {netuid} does not exist")
        min_tolerance = tao_amount / (tao_amount + subnet.alpha_in.tao)
        return min_tolerance

    
    def stake(
        self,
        tao_amount: float,
        netuid: int,
        wallet_name: str,
        dest_hotkey: str = settings.DEFAULT_DEST_HOTKEY,
        rate_tolerance: float = settings.DEFAULT_RATE_TOLERANCE,
        min_tolerance_staking: bool = settings.DEFAULT_MIN_TOLERANCE,
        retries: int = settings.DEFAULT_RETRIES
    ) -> Dict[str, Any]:
        """
        Execute staking operation with retry mechanism and error handling.
        
        Args:
            tao_amount: Amount to stake in TAO
            netuid: Network/subnet ID
            wallet_name: Name of the wallet to use
            dest_hotkey: Destination hotkey address
            rate_tolerance: Tolerance for rate calculations
            min_tolerance_staking: Whether to use minimum tolerance
            retries: Number of retry attempts
            
        Returns:
            Dict containing success status, result, and min_tolerance
        """ 
        wallet, delegator = self.wallets[wallet_name]
        
        # Adjust rate tolerance if using minimum tolerance staking
        if min_tolerance_staking:
            # Calculate minimum tolerance
            subnet = self.subtensor.subnet(netuid=netuid)
            if subnet is None:
                return {
                    "success": False,
                    "error": f"Subnet with netuid {netuid} does not exist"
                }
            min_tolerance = tao_amount / subnet.tao_in.tao
    
            rate_tolerance = min_tolerance + 0.001
        
        # Execute staking with retry mechanism
        success = False
        msg = None

        for _ in range(retries):
            try:
                result, msg = self.proxy.add_stake(
                    amount=bt.Balance.from_tao(tao_amount),
                    proxy_wallet=wallet,
                    delegator=delegator,
                    netuid=netuid,
                    hotkey=dest_hotkey,
                    tolerance=rate_tolerance,
                )
                
                if result:
                    success = True
                    break
            except Exception as e:
                msg = str(e)
                continue
        
        # This should never be reached, but required for type checking
        return {
            "success": success,
            "error": msg
        }
    
    def unstake(
        self,
        netuid: int,
        wallet_name: str,
        amount: Optional[float] = None,
        dest_hotkey: str = settings.DEFAULT_DEST_HOTKEY,
        rate_tolerance: float = settings.DEFAULT_RATE_TOLERANCE,
        min_tolerance_unstaking: bool = settings.DEFAULT_MIN_TOLERANCE,
        retries: int = settings.DEFAULT_RETRIES
    ) -> Dict[str, Any]:
        """
        Execute unstaking operation with retry mechanism and error handling.
        
        Args:
            netuid: Network/subnet ID
            wallet_name: Name of the wallet to use
            amount: Amount to unstake (if None, unstakes all available)
            dest_hotkey: Destination hotkey address
            rate_tolerance: Tolerance for rate calculations
            min_tolerance_unstaking: Whether to use minimum tolerance
            retries: Number of retry attempts
            
        Returns:
            Dict containing success status, result, and min_tolerance
        """ 
        wallet, delegator = self.wallets[wallet_name]
        
        # Determine amount to unstake
        if amount is None:
            # Unstake all available balance
            amount_balance = self.subtensor.get_stake(
                coldkey_ss58=delegator,
                hotkey_ss58=dest_hotkey,
                netuid=netuid
            )
        else:
            # Convert TAO amount to Balance object
            amount_balance = bt.Balance.from_tao(amount, netuid)

        if amount_balance.rao <= 0:
            return {
                "success": False,
                "error": "No balance to unstake"
            }
        
        # Adjust rate tolerance if using minimum tolerance unstaking
        if min_tolerance_unstaking:
            subnet = self.subtensor.subnet(netuid=netuid)
            if subnet is None:
                return {
                    "success": False,
                    "error": f"Subnet with netuid {netuid} does not exist"
                }
            # Calculate minimum tolerance for unstaking
            min_tolerance = amount_balance.tao / (amount_balance.tao + subnet.alpha_in.tao)
            rate_tolerance = min_tolerance + 0.001
        
        # Execute unstaking with retry mechanism
        success = False
        msg = None

        for _ in range(retries):
            try:
                result, msg = self.proxy.remove_stake(
                    netuid=netuid,
                    proxy_wallet=wallet,
                    delegator=delegator,
                    amount=amount_balance,
                    hotkey=dest_hotkey,
                    tolerance=rate_tolerance,
                )
                if result:
                    success = True
                    break     
            except Exception as e:
                msg = str(e)                
                continue
        
        # This should never be reached, but required for type checking
        return {
            "success": success,
            "error": msg
        }


    def move_stake(
        self,
        wallet_name: str,
        origin_netuid: int, 
        destination_netuid: int, 
        amount: Optional[float] = None, 
        origin_hotkey: str = settings.DEFAULT_DEST_HOTKEY, 
        destination_hotkey: str = settings.DEFAULT_DEST_HOTKEY, 
        retries: int = settings.DEFAULT_RETRIES
    ) -> Dict[str, Any]:
        """
        Execute move stake operation with retry mechanism and error handling.
        """
        wallet, delegator = self.wallets[wallet_name]

        if amount is None:
            amount_balance = self.subtensor.get_stake(
                coldkey_ss58=delegator,
                hotkey_ss58=origin_hotkey,
                netuid=origin_netuid
            )
        else:
            amount_balance = bt.Balance.from_tao(amount, origin_netuid)   
        
        
        # Execute move stake with retry mechanism
        success = False
        msg = None

        for _ in range(retries):
            try:
                result, msg = self.proxy.move_stake(
                    amount=amount_balance,
                    proxy_wallet=wallet,
                    delegator=delegator,
                    origin_hotkey=origin_hotkey,
                    destination_hotkey=destination_hotkey,
                    origin_netuid=origin_netuid,
                    destination_netuid=destination_netuid,
                )
                if result:
                    success = True
                    break
            except Exception as e:
                msg = str(e)
                continue
        
        # This should never be reached, but required for type checking
        return {
            "success": success,
            "error": msg
        }

stake_service = StakeService(wallets)