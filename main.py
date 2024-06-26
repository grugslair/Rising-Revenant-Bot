import asyncio
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.account.account import Account
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.client_models import Call
import math
import os
import requests

from queries import fetch_latest_game_number, fetch_game_phase_info, fetch_outposts, fetch_current_world_event, fetch_unverified_outposts, fetch_all_outpost_hit_by_current_event
from queries import Vec2, Outpost, GamePhaseInfo, EventDetails

PRIVATE_KEY = "0x1800000000300000180000000000030000000000003006001800006600"
PUBLIC_KEY = "0x2b191c2f3ecf685a91af7cf72a43e7b90e2e41220175de5c4f7498981b10053"
ACCOUNT_ADDRESS = "0x6162896d1d7ab204c7ccac6dd5f8e9e7c25ecd5ae4fcb4ad32e57786bb46e03"
CONTRACT_ADDRESS = int("0x29d7c04fba830a9af1ce47b8fac1cb1790c7f3cfc201378adaf3aed60cc45d0", 16)


FUNCTION_NAME = "random"

NODE_URL = "https://starknet-sepolia.public.blastapi.io/rpc/v0_6"

DISCORD_CHANNEL_WEBHOOK = 'https://discord.com/api/webhooks/1120776777388789810/UR3JQ6nOUoEvpEAX6OvKr8HHStd5ymGJrpzzziO5larh_n5A3W80YJWNA72t50VO4wVZ'

BLOCK_CHECK_INTERVAL = 1
LOOP_SECONDS_INTERVAL = 30

# this will crash if the game is over
async def call_create_event_func(account, gameid):
    try:

        # The payload for the embedded message
        data = {
            "embeds": [{
                "title": "New World Event Created for game",
                "description": "A new world event has been created. Please verify the outposts.",
                "color": 16711680  # Red
            }]
        }
        headers = {"Content-Type": "application/json"}
        
        # Sending the POST request to the webhook URL with the embedded message
        requests.post(DISCORD_CHANNEL_WEBHOOK, json=data, headers=headers)

        print("Calling the create event function...")
        call = Call(
            to_addr=CONTRACT_ADDRESS, 
            selector=get_selector_from_name(FUNCTION_NAME), 
            calldata=[gameid]
        )
        resp = await account.execute(calls=[call], max_fee=int(1e16))
        await account.client.wait_for_tx(resp.transaction_hash)

  
        print("Function called successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

def clear_console():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')


async def main():
    client = FullNodeClient(node_url=NODE_URL)

    # Initialize the account
    private_key_int = int(PRIVATE_KEY, 16)
    public_key_int = int(PUBLIC_KEY, 16)
    account = Account(
        client=client,
        address=ACCOUNT_ADDRESS, 
        key_pair=KeyPair(private_key=private_key_int, public_key=public_key_int),
        # chain=0x4b4154414e41,      #katana chain id
        chain=0x534e5f5345504f4c4941, #sepolia chain id
    )

    last_block_number_checked = 0
    current_saved_game_id = -1 
    saved_outposts_for_this_game: list[Outpost] = []

    start_of_prep_phase = -1
    start_of_play_phase = -1

    while True:
        clear_console()  
        current_block_number = await client.get_block_number()   # get the current block number

        if current_block_number >= last_block_number_checked + BLOCK_CHECK_INTERVAL:  # check if the current block number is greater than the last block number checked
            print("running check on the block number")
            last_block_number_checked = current_block_number # update the last block number checked

            # here we get the most current game number
            latest_game_id = await fetch_latest_game_number() ##get the current game number
            if latest_game_id != current_saved_game_id:  # the current game number is different from the one we have saved therefore we load everything in
                print(f"New game detected. Game ID: {latest_game_id}")

                current_saved_game_id = latest_game_id
                saved_outposts_for_this_game = []  # we reset everything ready for the new game

                game_phase_data: GamePhaseInfo = await fetch_game_phase_info(current_saved_game_id)  # get the latest game phase info
                print(f"new Game Phase Data: {game_phase_data}")
                if (game_phase_data == None): # there has been an issue with the fetching of data we retry next time
                    print("there was an issue on the game phase data retrieve")
                    await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                    continue

                start_of_prep_phase = game_phase_data.preparation_block_number
                start_of_play_phase = game_phase_data.play_block_number
            else:
                print(f"Game ID: {latest_game_id} is the same as the one saved. No need to update.")

            # now that we have all the data we need we check if we are in the play phase
            
            if (current_saved_game_id == -1):
                await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                continue

            if (current_block_number >= start_of_play_phase):
                print("we are in the play phase")
                saved_outposts_for_this_game = await fetch_outposts(current_saved_game_id)

                if (saved_outposts_for_this_game[1] == 0):
                    print("No outposts found for the current game. Retrying...")
                    await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                    continue

                print(f"Outposts fetched successfully. Total of {len(saved_outposts_for_this_game[1])} outposts found.")
                
                current_world_event: EventDetails = await fetch_current_world_event(current_saved_game_id)

                print("Current World Event: ", current_world_event)

                if (current_world_event is not None):
                      print("there is a world event")
                      allHitOutposts = await fetch_all_outpost_hit_by_current_event(current_world_event, saved_outposts_for_this_game[0])
                      print(f"Outposts hit by the event: {allHitOutposts}")
                      unverifiedOutposts = await fetch_unverified_outposts(current_world_event.event_id  , allHitOutposts, current_saved_game_id)
                      print(f"Unverified outposts: {unverifiedOutposts}")

                      if len(unverifiedOutposts) == 0:
                            print("all outposts verified") 
                            await call_create_event_func(account, current_saved_game_id)
                            await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                            continue
                      else:
                            print("Not all outposts have been verified yet.")

                            missing_outposts_message = "All outposts have not been verified. Missing outposts:\n"
                            for outpost in unverifiedOutposts:
                                outpost_id = 1
                                outpost_position = outpost["position"]
                                missing_outposts_message += f"Outpost ID: {outpost_id}, Position: {outpost_position}\n"
                            await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                            continue
                      
                      
                else: # no event so we make a new one 
                    print("No current world event found. Creating a new one...")
                    await call_create_event_func(account, current_saved_game_id)
                    await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                    continue

            else:
                print("not in the play phase yet or no game found")
                await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                continue    
        else:
            print("current block number is less than the last block number checked so we wait for the next check interval, block number is ", current_block_number)

        await asyncio.sleep(LOOP_SECONDS_INTERVAL)

asyncio.run(main())
