import bittensor as bt
from substrateinterface import SubstrateInterface
from substrateinterface.exceptions import SubstrateRequestException
from typing import Optional, cast
from bittensor.utils.balance import Balance, FixedPoint, fixed_to_float
import threading
import time

RPC_ENDPOINTS = {
    'test': 'wss://test.finney.opentensor.ai:443',
    'finney': 'wss://entrypoint-finney.opentensor.ai:443',
}

class RonProxy:
    def __init__(self, proxy_wallet: str, network: str, delegator: str):
        """
        Initialize the RonProxy object.
        
        Args:
            proxy_wallet: Proxy wallet address
            network: Network name
            delegator: Delegator address
        """
        if network not in RPC_ENDPOINTS:
            raise ValueError(f"Invalid network: {network}")
        
        self.network = network
        self.delegator = delegator
        self.proxy_wallet = bt.Wallet(name=proxy_wallet)
        self.subtensor = bt.Subtensor(network=network)
        self.substrate = SubstrateInterface(
            url=RPC_ENDPOINTS[self.network],
            ss58_format=42,
            type_registry_preset='substrate-node-template',
        )


    def add_stake(self, netuid: int, hotkey: str, amount: Balance, tolerance: float = 0.01) -> None:
        """
        Add stake to a subnet.
        
        Args:
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to stake
            tolerance: Tolerance for stake amount
        """
        free_balance = self.subtensor.get_balance(
            address=self.delegator,
        )
        print("--------------------------------")
        print(f"Adding stake...")
        print(f"Tolerance set to: {tolerance}")
        print(f"Current free balance: {free_balance}")
        
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            print(f"Subnet with netuid {netuid} does not exist")
            return
        
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
        is_success, error_message = self._do_proxy_call(call, 'Staking')
        if is_success:
            new_free_balance = self.subtensor.get_balance(
                address=self.delegator,
            )
            print(f"New free balance: {new_free_balance}")
            print(f"Free balance: {free_balance}")
            if new_free_balance.rao < free_balance.rao:
                print(f"Stake added successfully, free balance changed from {free_balance.rao} to {new_free_balance.rao}")
                return
            else:
                print(f"Stake added failed")
        else:
            print(f"Error: {error_message}")


    def remove_stake(self, netuid: int, hotkey: str, amount: Balance,
                    all: bool = False, tolerance: float = 0.05) -> None:
        """
        Remove stake from a subnet.
        
        Args:
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to unstake (if not using --all)
            all: Whether to unstake all available balance
        """
        balance = self.subtensor.get_stake(
            coldkey_ss58=self.delegator,
            hotkey_ss58=hotkey,
            netuid=netuid,
        )
        print("--------------------------------")
        print(f"Removing stake...")
        print(f"Tolerance set to: {tolerance}")
        print(f"Current alpha balance: {balance}")

        if all:
            amount = balance
            
        if amount.rao > balance.rao:
            print(f"Error: Amount to unstake is greater than current balance")
            return
        
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            print(f"Subnet with netuid {netuid} does not exist")
            return
        
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

        free_balance = self.subtensor.get_balance(
            address=self.delegator,
        )
        
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            print(f"Subnet with netuid {netuid} does not exist")
            return
        
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
        is_success, error_message = self._do_proxy_call(call, 'Staking')
        if is_success:
            free_new_balance = self.subtensor.get_balance(
                address=self.delegator,
            )
            if free_new_balance.rao > free_balance.rao:
                print(f"Stake removed successfully, free balance changed from {free_balance.rao} to {free_new_balance.rao}")
                return
            else:
                print(f"Stake removal failed")
        else:
            print(f"Error: {error_message}")


    def swap_stake(self, hotkey: str, origin_netuid: int, dest_netuid: int,
                amount: Balance, all: bool = False) -> None:
        """
        Swap stake between subnets.
        
        Args:
            hotkey: Hotkey address
            origin_netuid: Source subnet ID
            dest_netuid: Destination subnet ID
            amount: Amount to swap (if not using --all)
            all: Whether to swap all available balance
        """
        balance = self.subtensor.get_stake(
            coldkey_ss58=self.delegator,
            hotkey_ss58=hotkey,
            netuid=origin_netuid,
        )
        print(f"Current alpha balance on netuid {origin_netuid}: {balance}")
        
        if all:
            confirm = input("Do you really want to swap all available balance? (y/n)")
            if confirm == "y":
                amount = balance
            else:
                return
        else:
            confirm = input(f"Do you really want to swap {amount}? (y/n)")
            if confirm == "y":
                pass
            else:
                return
            
        if amount.rao > balance.rao:
            print(f"Error: Amount to swap is greater than current balance")
            return
        
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='swap_stake',
            call_params={
                'hotkey': hotkey,
                'origin_netuid': origin_netuid,
                'destination_netuid': dest_netuid,
                'alpha_amount': amount.rao,
            }
        )
        is_success, error_message = self._do_proxy_call(call, 'Staking')
        if is_success:
            print(f"Stake swapped successfully")
        else:
            print(f"Error: {error_message}")
            
            
    def burned_register(self, hotkey: str, netuid: int) -> None:
        """
        Do burned register.
        
        Args:
            hotkey: Hotkey address
            netuid: Subnet ID
        """
        balance = self.subtensor.get_balance(
            address=self.delegator,
        )
        print(f"Current balance: {balance}")
        
        confirm = input(f"Do you really want to register? (y/n)")
        if confirm == "y":
            pass
        else:
            return
        
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='burned_register',
            call_params={
                'netuid': netuid,
                'hotkey': hotkey,
            }
        )
        is_success, error_message = self._do_proxy_call(call, 'Registration')
        if is_success:
            print(f"Register successfully")
        else:
            print(f"Error: {error_message}")

    def transfer(self, destination: str, amount: Balance) -> None:
        """
        Transfer balance between hotkeys.
        
        Args:
            destination: Destination coldkey address
            amount: Amount to transfer
        """
        balance = self.subtensor.get_balance(
            address=self.delegator,
        )
        print(f"Current balance: {balance}")
        
        confirm = input(f"Do you really want to transfer {amount}? (y/n)")
        if confirm == "y":
            pass
        else:
            return
        
        call = self.substrate.compose_call(
            call_module='Balances',
            call_function='transfer_keep_alive',
            call_params={
                'dest': destination,
                'value': amount.rao,
            }
        )

        is_success, error_message = self._do_proxy_call(call, 'Transfer')
        if is_success:
            print(f"Transfer successfully")
        else:
            print(f"Error: {error_message}")

    def transfer_stake(self, netuid: int, hotkey: str, destination: str, amount: Balance, all: bool = False) -> None:
        """
        Transfer stake between hotkeys.
        
        Args:
            netuid: Subnet ID
            destination: Destination coldkey address
            amount: Amount to transfer
        """
        balance = self.subtensor.get_stake(
            coldkey_ss58=self.delegator,
            hotkey_ss58=hotkey,
            netuid=netuid,
        )
        print(f"Current stake: {balance}")

        if all:
            confirm = input("Do you really want to transfer all available stake? (y/n)")
            if confirm == "y":
                amount = balance
            else:
                return
        else:
            confirm = input(f"Do you really want to transfer {amount}? (y/n)")
            if confirm == "y":
                pass
            else:
                return

        if amount.rao > balance.rao:
            print(f"Error: Amount to transfer is greater than current stake")
            return

        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='transfer_stake',
            call_params={
                'destination_coldkey': destination,
                'hotkey': hotkey,
                'origin_netuid': netuid,
                'destination_netuid': netuid,
                'alpha_amount': amount.rao,
            }
        )
        is_success, error_message = self._do_proxy_call(call, 'Transfer')
        if is_success:
            print(f"Stake transferred successfully")
        else:
            print(f"Error: {error_message}")

    def _do_proxy_call(self, call, proxy_type) -> tuple[bool, str]:
        proxy_call = self.substrate.compose_call(
            call_module='Proxy',
            call_function='proxy',
            call_params={
                'real': self.delegator,
                'force_proxy_type': proxy_type,
                'call': call,
            }
        )
        extrinsic = self.substrate.create_signed_extrinsic(
            call=proxy_call,
            keypair=self.proxy_wallet.coldkey,
            era={"period": 1},
        )
        try:
            receipt = self.substrate.submit_extrinsic(
                extrinsic,
                wait_for_inclusion=True,
                wait_for_finalization=False,
            )
        except SubstrateRequestException as e:
            error_message = f"SubstrateRequestException: {e}"
            print(error_message)
            if "Custom error: 8" in str(e):
                error_message = f"""
                    \nPrice exceeded tolerance limit.
                    Transaction rejected because partial unstaking is disabled.
                    Either increase price tolerance or enable partial unstaking.
                """
            return False, error_message
        
        print(f"Extrinsic: {receipt.get_extrinsic_identifier()}")
        
        is_success = receipt.is_success
        error_message = receipt.error_message
        return is_success, error_message
    
class LeoProxy:
    def __init__(self, proxy_wallet: bt.Wallet, network: str, delegator: str):
        """
        Initialize the LeoProxy object.
        
        Args:
            proxy_wallet: Proxy wallet address
            network: Network name
            delegator: Delegator address
        """
        if network not in RPC_ENDPOINTS:
            raise ValueError(f"Invalid network: {network}")
        
        self.network = network
        self.delegator = delegator
        self.proxy_wallet = proxy_wallet
        self.subtensor = bt.Subtensor(network=network)
        self.substrate = SubstrateInterface(
            url=RPC_ENDPOINTS[self.network],
            ss58_format=42,
            type_registry_preset='substrate-node-template',
        )


    def add_stake(self, netuid: int, hotkey: str, amount: Balance, tolerance: float = 0.01) -> None:
        """
        Add stake to a subnet.
        
        Args:
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to stake
            tolerance: Tolerance for stake amount
        """
        free_balance = self.subtensor.get_balance(
            address=self.delegator,
        )
        print("--------------------------------")
        print(f"Adding stake...")
        print(f"Tolerance set to: {tolerance}")
        print(f"Current free balance: {free_balance}")
        
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            print(f"Subnet with netuid {netuid} does not exist")
            return
        print("stake step 1")
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
        print("stake step 2")
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
        print("stake step 3")
        is_success, error_message = self._do_proxy_call(call, 'Staking')
        print("stake step 4")
        if is_success:
            new_free_balance = self.subtensor.get_balance(
                address=self.delegator,
            )
            print(f"New free balance: {new_free_balance}")
            print(f"Free balance: {free_balance}")
            if new_free_balance.rao < free_balance.rao:
                print(f"Stake added successfully, free balance changed from {free_balance.rao} to {new_free_balance.rao}")
                return
            else:
                print(f"Stake added failed")
        else:
            print(f"Error: {error_message}")


    def remove_stake(self, netuid: int, hotkey: str, amount: Balance,
                    all: bool = False, tolerance: float = 0.05) -> None:
        """
        Remove stake from a subnet.
        
        Args:
            netuid: Network/subnet ID
            hotkey: Hotkey address
            amount: Amount to unstake (if not using --all)
            all: Whether to unstake all available balance
        """
        balance = self.subtensor.get_stake(
            coldkey_ss58=self.delegator,
            hotkey_ss58=hotkey,
            netuid=netuid,
        )
        print("--------------------------------")
        print(f"Removing stake...")
        print(f"Tolerance set to: {tolerance}")
        print(f"Current alpha balance: {balance}")

        amount = balance
        if amount.rao > balance.rao:
            print(f"Error: Amount to unstake is greater than current balance")
            return
        print("step1")
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            print(f"Subnet with netuid {netuid} does not exist")
            return
        print("step2")
        
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
        print("step3")

        free_balance = self.subtensor.get_balance(
            address=self.delegator,
        )
        print("step4")
        
        subnet_info = self.subtensor.subnet(netuid)
        if not subnet_info:
            print(f"Subnet with netuid {netuid} does not exist")
            return
        print("step5")
        
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
        print("step6")
            
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
        print("step7")
        is_success, error_message = self._do_proxy_call(call, 'Staking')
        if is_success:
            free_new_balance = self.subtensor.get_balance(
                address=self.delegator,
            )
            if free_new_balance.rao > free_balance.rao:
                print(f"Stake removed successfully, free balance changed from {free_balance.rao} to {free_new_balance.rao}")
                return
            else:
                print(f"Stake removal failed")
        else:
            print(f"Error: {error_message}")


    def swap_stake(self, hotkey: str, origin_netuid: int, dest_netuid: int,
                amount: Balance, all: bool = False) -> None:
        """
        Swap stake between subnets.
        
        Args:
            hotkey: Hotkey address
            origin_netuid: Source subnet ID
            dest_netuid: Destination subnet ID
            amount: Amount to swap (if not using --all)
            all: Whether to swap all available balance
        """
        balance = self.subtensor.get_stake(
            coldkey_ss58=self.delegator,
            hotkey_ss58=hotkey,
            netuid=origin_netuid,
        )
        print(f"Current alpha balance on netuid {origin_netuid}: {balance}")
            
        if amount.rao > balance.rao:
            print(f"Error: Amount to swap is greater than current balance")
            return
        
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='swap_stake',
            call_params={
                'hotkey': hotkey,
                'origin_netuid': origin_netuid,
                'destination_netuid': dest_netuid,
                'alpha_amount': amount.rao,
            }
        )
        is_success, error_message = self._do_proxy_call(call, 'Staking')
        if is_success:
            print(f"Stake swapped successfully")
        else:
            print(f"Error: {error_message}")
            
            
    def burned_register(self, hotkey: str, netuid: int) -> None:
        """
        Do burned register.
        
        Args:
            hotkey: Hotkey address
            netuid: Subnet ID
        """
        balance = self.subtensor.get_balance(
            address=self.delegator,
        )
        print(f"Current balance: {balance}")
        
        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='burned_register',
            call_params={
                'netuid': netuid,
                'hotkey': hotkey,
            }
        )
        is_success, error_message = self._do_proxy_call(call, 'Registration')
        if is_success:
            print(f"Register successfully")
        else:
            print(f"Error: {error_message}")

    def transfer(self, destination: str, amount: Balance) -> None:
        """
        Transfer balance between hotkeys.
        
        Args:
            destination: Destination coldkey address
            amount: Amount to transfer
        """
        balance = self.subtensor.get_balance(
            address=self.delegator,
        )
        print(f"Current balance: {balance}")
        
        call = self.substrate.compose_call(
            call_module='Balances',
            call_function='transfer_keep_alive',
            call_params={
                'dest': destination,
                'value': amount.rao,
            }
        )

        is_success, error_message = self._do_proxy_call(call, 'Transfer')
        if is_success:
            print(f"Transfer successfully")
        else:
            print(f"Error: {error_message}")

    def transfer_stake(self, netuid: int, hotkey: str, destination: str, amount: Balance, all: bool = False) -> None:
        """
        Transfer stake between hotkeys.
        
        Args:
            netuid: Subnet ID
            destination: Destination coldkey address
            amount: Amount to transfer
        """
        balance = self.subtensor.get_stake(
            coldkey_ss58=self.delegator,
            hotkey_ss58=hotkey,
            netuid=netuid,
        )
        print(f"Current stake: {balance}")

        if amount.rao > balance.rao:
            print(f"Error: Amount to transfer is greater than current stake")
            return

        call = self.substrate.compose_call(
            call_module='SubtensorModule',
            call_function='transfer_stake',
            call_params={
                'destination_coldkey': destination,
                'hotkey': hotkey,
                'origin_netuid': netuid,
                'destination_netuid': netuid,
                'alpha_amount': amount.rao,
            }
        )
        is_success, error_message = self._do_proxy_call(call, 'Transfer')
        if is_success:
            print(f"Stake transferred successfully")
        else:
            print(f"Error: {error_message}")

    def _do_proxy_call(self, call, proxy_type, timeout: int = 12) -> tuple[bool, str]:
        proxy_call = self.substrate.compose_call(
            call_module='Proxy',
            call_function='proxy',
            call_params={
                'real': self.delegator,
                'force_proxy_type': proxy_type,
                'call': call,
            }
        )
        print("proxy_call_step1")
        extrinsic = self.substrate.create_signed_extrinsic(
            call=proxy_call,
            keypair=self.proxy_wallet.coldkey,
            era={"period": 1},
        )
        print("proxy_call_step2")
        
        receipt = [None]
        exception = [None]
        
        def submit_with_timeout():
            try:
                receipt[0] = self.substrate.submit_extrinsic(
                    extrinsic,
                    wait_for_inclusion=True,
                    wait_for_finalization=False,
                )
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=submit_with_timeout, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            print(f"Timeout: submit_extrinsic exceeded {timeout} seconds")
            return False, f"Timeout: Transaction submission took longer than {timeout} seconds"
        
        if exception[0] is not None:
            e = exception[0]
            print(f"SubstrateRequestException: {e}")
            if isinstance(e, SubstrateRequestException) and "Custom error: 8" in str(e):
                error_message = f"""
                    Price exceeded tolerance limit.
                    Transaction rejected because partial unstaking is disabled.
                    Either increase price tolerance or enable partial unstaking.
                """
            return False, "SubstrateRequestException Error occurred"
        
        if receipt[0] is None:
            return False, "No receipt received from transaction"
        
        print(f"Extrinsic: {receipt[0].get_extrinsic_identifier()}")
        
        is_success = receipt[0].is_success
        error_message = receipt[0].error_message
        return is_success, error_message
    
    