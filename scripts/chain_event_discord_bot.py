import bittensor as bt
import os
import requests
import json
import time
import threading
import requests


WEBHOOK_URL = "https://discord.com/api/webhooks/1396875737952292936/Bggfi9QEHVljmOxaqzJniLwQ70oCjnlj0lb7nIBq4avsVya_dkGNfjOKaGlOt_urwdul"
WEBHOOK_URL_OWN = "https://canary.discord.com/api/webhooks/1410255303689375856/Rkt1TkqmxV3tV_82xFNz_SRP7O0RVBVPaOuZM4JXveyLYypFKqi05EeSCKc4m1a9gJh0"
NETWORK = "finney"
#NETWORK = "ws://34.30.248.57:9944"

class DiscordBot:
    def __init__(self):
        self.webhook_url = WEBHOOK_URL

    def send_message(self, content):
        data = {
            "content": content,
            "username": "Coldkey Swap Bot",  # Optional: Custom username for the webhook
            "avatar_url": "https://vidaio-justin.s3.us-east-2.amazonaws.com/favicon.ico"  # Optional: Custom avatar for the webhook
        }
        response = requests.post(self.webhook_url, data=json.dumps(data), headers={"Content-Type": "application/json"})
        
        if response.status_code == 204:
            print("Message sent successfully!")
            return True
        else:
            print(f"Failed to send message: {response.status_code}, {response.text}")
        return False

    def send_message_to_my_own(self, content):
        data = {
            "content": content,
            "username": "Coldkey Swap Bot",  # Optional: Custom username for the webhook
            "avatar_url": "https://vidaio-justin.s3.us-east-2.amazonaws.com/favicon.ico"  # Optional: Custom avatar for the webhook
        }
        response = requests.post(WEBHOOK_URL_OWN, data=json.dumps(data), headers={"Content-Type": "application/json"})
        
        if response.status_code == 204:
            print("Message sent successfully!")
            return True
        else:
            print(f"Failed to send message: {response.status_code}, {response.text}")
        return False


class ColdkeySwapFetcher:
    def __init__(self):
        self.subtensor = bt.Subtensor(NETWORK)
        self.subtensor_finney = bt.Subtensor("finney")

        self.last_checked_block = self.subtensor.get_current_block()
        self.discord_bot = DiscordBot()
        self.subnet_names = []
  
    def fetch_extrinsic_data(self, block_number):
        """Extract ColdkeySwapScheduled events from the data"""
        coldkey_swaps = []
        identity_changes = []
        print(f"Fetching events from chain")
        block_hash = self.subtensor.substrate.get_block_hash(block_id=block_number)
        extrinsics = self.subtensor.substrate.get_extrinsics(block_hash=block_hash)
        subnet_infos = self.subtensor.all_subnets()
        owner_coldkeys = [subnet_info.owner_coldkey for subnet_info in subnet_infos]
        subnet_names = [subnet_info.subnet_name for subnet_info in subnet_infos]
        print(f"Fetched {len(extrinsics)} events from chain and {len(subnet_infos)} subnets")

        for ex in extrinsics:
            call = ex.value.get('call', {})
            if (
                call.get('call_module') == 'SubtensorModule' and
                call.get('call_function') == 'schedule_swap_coldkey'
            ):
                # Get the new coldkey from call_args
                args = call.get('call_args', [])
                new_coldkey = next((a['value'] for a in args if a['name'] == 'new_coldkey'), None)
                from_coldkey = ex.value.get('address', None)
                print(f"Swap scheduled: from {from_coldkey} to {new_coldkey}")
                
                try:
                    subnet_id = owner_coldkeys.index(from_coldkey)
                    swap_info = {
                        'old_coldkey': from_coldkey,
                        'new_coldkey': new_coldkey,
                        'subnet': subnet_id,
                    }
                    
                    coldkey_swaps.append(swap_info)
                except ValueError:
                    print(f"From coldkey {from_coldkey} not found in owner coldkeys")
                
        subnet_count = len(self.subnet_names)
        for i in range(subnet_count):
            if subnet_names[i] != self.subnet_names[i]:
                identity_change_info = {
                    'subnet': i,
                    'old_identity': self.subnet_names[i],
                    'new_identity': subnet_names[i],
                }
                identity_changes.append(identity_change_info)

        self.subnet_names = subnet_names
        return coldkey_swaps, identity_changes
 
    def run(self):
        while True:
            current_block = self.subtensor.get_current_block()
            print(f"Current block: {current_block}")
            if current_block < self.last_checked_block:
                time.sleep(2)
                continue

            print(f"Fetching coldkey swaps for block {self.last_checked_block}")
            while True:
                try:
                    coldkey_swaps, identity_changes = self.fetch_extrinsic_data(self.last_checked_block)
                    if len(coldkey_swaps) > 0 or len(identity_changes) > 0:
                        try:
                            with open("coldkey_swaps.log", "a") as f:
                                for swap in coldkey_swaps:
                                    f.write(f"{swap}\n")
                        except Exception as e:
                            print(f"Error writing to file: {e}")
        
                        try:
                            with open("identity_changes.log", "a") as f:
                                for change in identity_changes:
                                    f.write(f"{change}\n")
                        except Exception as e:
                            print(f"Error writing to file: {e}")

                        try:
                            message = self.format_message(coldkey_swaps, identity_changes)
                            self.discord_bot.send_message_to_my_own(message)
                            threading.Timer(60.0, lambda: self.discord_bot.send_message(message)).start()
                        except Exception as e:
                            print(f"Error sending message: {e}")
                    else:
                        print("No coldkey swaps found")
                    
                    self.last_checked_block += 1
                    break

                except Exception as e:
                    print(f"Error fetching coldkey swaps: {e}")
                    time.sleep(1)


    def format_message(self, coldkey_swaps, identity_changes):
        message = "Hey @everyone! \n"
        for swap in coldkey_swaps:
            message += f"Subnet {swap['subnet']} is swapping coldkey from {swap['old_coldkey']} to {swap['new_coldkey']}\n"

        for change in identity_changes:
            message += f"Subnet {change['subnet']} has changed identity from {change['old_identity']} to {change['new_identity']}\n"
        return message


if __name__ == "__main__":
    fetcher = ColdkeySwapFetcher()
    fetcher.run()