import bittensor as bt
from substrateinterface import SubstrateInterface
from substrateinterface.exceptions import SubstrateRequestException
from typing import Optional, cast
from bittensor.utils.balance import Balance, FixedPoint, fixed_to_float

class Proxy:
    def __init__(self, network: str, use_era: bool = True):
        """
        Initialize the RonProxy object.
        
        Args:
            network: Network name
            use_era: Whether to use era parameter in extrinsic creation
        """
        self.network = network
        self.use_era = use_era
        self.subtensor = bt.subtensor(network=network)
        

    def init_runtime(self):
        self.substrate = SubstrateInterface(
            url=self.network,
            ss58_format=42,
            type_registry_preset='substrate-node-template',
            auto_reconnect=True,
        )

    def add_stake(
        self, 
        proxy_wallet: bt.wallet,
        delegator: str,
        netuid: int, 
        hotkey: str, 
        amount: Balance, 
        tolerance: float = 0.005,
    ) -> tuple[bool, str]:
        """
        Add stake to a subnet.
        
        Args:
            proxy_wallet: Proxy wallet
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to stake
            tolerance: Tolerance for stake amount
        """
        free_balance = self.subtensor.get_balance(
            address=delegator,
        )
        print(f"free_balance: {free_balance}")
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            return False, f"Subnet with netuid {netuid} does not exist"
        
        if subnet_info.is_dynamic:
            rate = 1 / subnet_info.price.tao or 1
            _rate_with_tolerance = rate * (
                1 + tolerance
            )  # Rate only for display
            rate_with_tolerance = f"{_rate_with_tolerance:.4f}"
            price_with_tolerance = subnet_info.price.rao * (
                1 + tolerance
            )
        else:
            rate_with_tolerance = "1"
            price_with_tolerance = Balance.from_rao(1)

        print(f"price_with_tolerance: {price_with_tolerance}")
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='add_stake_limit',
            call_params={
                "hotkey": hotkey,
                "netuid": netuid,
                "amount_staked": amount.rao,
                "limit_price": price_with_tolerance,
                "allow_partial": False,
            }
        )
        print(f"call: {call}")
        is_success, error_message = self._do_proxy_call(proxy_wallet, delegator, call)
        new_free_balance = self.subtensor.get_balance(
            address=delegator,
        )
        if new_free_balance.rao < free_balance.rao:
            return True, f"Stake added successfully"
        else:
            return False, f"Error: {error_message}"


    def remove_stake(
        self, 
        proxy_wallet: bt.wallet,
        delegator: str,
        netuid: int,
        hotkey: str,
        amount: Balance,
        tolerance: float = 0.005,
    ) -> tuple[bool, str]:
        """
        Remove stake from a subnet.
        
        Args:
            proxy_wallet: Proxy wallet
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to unstake (if not using --all)
            all: Whether to unstake all available balance
        """
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            return False, f"Subnet with netuid {netuid} does not exist"
        
        if subnet_info.is_dynamic:
            rate = subnet_info.price.tao or 1
            rate_with_tolerance = rate * (
                1 - tolerance
            )  # Rate only for display
            price_with_tolerance = subnet_info.price.rao * (
                1 - tolerance
            )  # Actual price to pass to extrinsic
        else:
            rate_with_tolerance = 1
            price_with_tolerance = 1
        print(f"amount: {amount.rao}")
        self.init_runtime()
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='remove_stake_limit',
            call_params={
                "hotkey": hotkey,
                "netuid": netuid,
                "amount_unstaked": amount.rao - 1,
                "limit_price": price_with_tolerance,
                "allow_partial": False,
            }
        )
        free_balance = self.subtensor.get_balance(
            address=delegator,
        )
        
        is_success, error_message = self._do_proxy_call(proxy_wallet, delegator, call)
        new_free_balance = self.subtensor.get_balance(
            address=delegator,
        )
        if new_free_balance.rao > free_balance.rao:
            return True, f"Stake removed successfully"
        else:
            return False, f"Error: {error_message}"

    def move_stake(
        self, 
        proxy_wallet: bt.wallet,
        delegator: str,
        origin_hotkey: str, 
        destination_hotkey: str, 
        origin_netuid: int, 
        destination_netuid: int, 
        amount: Balance, 
    ) -> tuple[bool, str]:
        """
        Move stake between validators
        
        Args:
            hotkey: Hotkey address
            origin_netuid: Source subnet ID
            dest_netuid: Destination subnet ID
            amount: Amount to swap (if not using --all)
            all: Whether to swap all available balance
        """
        balance = self.subtensor.get_stake(
            coldkey_ss58=delegator,
            hotkey_ss58=origin_hotkey,
            netuid=origin_netuid,
        )
        print(f"Current alpha balance on netuid {origin_netuid}: {balance}")
        
        if amount.rao > balance.rao:
            return False, f"Error: Amount to swap is greater than current balance"

        self.init_runtime()
        
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='move_stake',
            call_params={
                'origin_hotkey': origin_hotkey,
                'destination_hotkey': destination_hotkey,
                'origin_netuid': origin_netuid,
                'destination_netuid': destination_netuid,
                'alpha_amount': amount.rao - 1,
            }
        )
        is_success, error_message = self._do_proxy_call(proxy_wallet, delegator, call)
        new_balance = self.subtensor.get_stake(
            coldkey_ss58=delegator,
            hotkey_ss58=origin_hotkey,
            netuid=origin_netuid,
        )
        print(f"New alpha balance on netuid {origin_netuid}: {new_balance}")
        if new_balance.rao < balance.rao:
            return True, f"Stake swapped successfully"
        else:
            return False, f"Error: {error_message}"

    def _do_proxy_call(
        self,
        proxy_wallet: bt.wallet,
        delegator: str,
        call,
    ) -> tuple[bool, str]:
        proxy_call = self.substrate.compose_call(
            call_module='Proxy',
            call_function='proxy',
            call_params={
                'real': delegator,
                'force_proxy_type': 'Staking',
                'call': call,
            }
        )
        if self.use_era:
            extrinsic = self.substrate.create_signed_extrinsic(
                call=proxy_call,
                keypair=proxy_wallet.coldkey,
                era={"period": 1},
            )
        else:
            extrinsic = self.substrate.create_signed_extrinsic(
                call=proxy_call,
                keypair=proxy_wallet.coldkey,
            )
        print(f"extrinsic: {extrinsic}")
        try:
            receipt = self.substrate.submit_extrinsic(
                extrinsic,
                wait_for_inclusion=True,
                wait_for_finalization=False,
            )
        except Exception as e:
            error_message = str(e)
            return False, error_message
        
        is_success = receipt.is_success
        error_message = receipt.error_message
        return is_success, str(error_message)


if __name__ == "__main__":
    proxy_wallet = bt.wallet(name="black")
    delegator = "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2"
    amount = input("Enter amount to stake: ")
    netuid = input("Enter netuid: ")
    proxy_wallet.unlock_coldkey()
    proxy = Proxy("finney")
    is_success, error_message = proxy.add_stake(proxy_wallet, delegator, int(netuid), "5F5WLLEzDBXQDdTzDYgbQ3d3JKbM15HhPdFuLMmuzcUW5xG2", Balance.from_tao(int(amount)))
    print(is_success, error_message)