import asyncio
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.account.account import Account
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.client_models import Call
import requests
import math
import os
import json


PRIVATE_KEY = "0x1800000000300000180000000000030000000000003006001800006600"
PUBLIC_KEY = "0x2b191c2f3ecf685a91af7cf72a43e7b90e2e41220175de5c4f7498981b10053"
ACCOUNT_ADDRESS = "0x6162896d1d7ab204c7ccac6dd5f8e9e7c25ecd5ae4fcb4ad32e57786bb46e03"
CONTRACT_ADDRESS = int("0x29d7c04fba830a9af1ce47b8fac1cb1790c7f3cfc201378adaf3aed60cc45d0", 16)
FUNCTION_NAME = "random"
NODE_URL = "http://localhost:5050"
TORII_URL = 'http://localhost:8080/graphql'

DISCORD_CHANNEL_WEBHOOK = 'https://discord.com/api/webhooks/1218511459714207784/xqsESHV8WNeU_l4gm2wevj3h1kclNUWxpU1jPIBSZIn47f-bTUURoCwypzrtLw0FHSGh'

BLOCK_CHECK_INTERVAL = 1
LOOP_SECONDS_INTERVAL = 20




# this will crash if the game is over
async def call_create_event_func(account, gameid):
    try:
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

def make_graphql_request(query):
    response = requests.post(url=TORII_URL, json={"query": query})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

# call to fetch the latests event
def fetch_current_world_events(game_id):
    # GraphQL query for CurrentWorldEvent entities
    query = f"""
        query {{
            currentWorldEventModels(where: {{game_id: "{game_id}"}}) {{
                edges {{
                    node {{
                        entity {{
                            keys
                            models {{
                                __typename
                                ... on CurrentWorldEvent {{
                                    game_id
                                    event_id
                                    position {{
                                        x
                                        y
                                    }}
                                    radius
                                    number
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
    """

    response = requests.post(url=TORII_URL, json={"query": query})
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        
        # Initialize a list to hold the current world events
        current_world_events = []
        
        # Navigate through the response to extract CurrentWorldEvent entities
        edges = data.get("data", {}).get("currentWorldEventModels", {}).get("edges", [])
        
        if not edges:  # Check if edges list is empty
            print(f"No current world events found for game_id: {game_id}")
            return current_world_events  # Return an empty list if no events found        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "CurrentWorldEvent":
                    event_details = {
                        "game_id": model.get("game_id"),
                        "event_id": model.get("event_id"),
                        "position": model.get("position"),
                        "radius": model.get("radius"),
                        "number": model.get("number")
                    }
                    current_world_events.append(event_details)
        
        # Return the extracted events
        return current_world_events
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

# this gets all the outposts and saves them
def fetch_outposts(game_id):
    # GraphQL query for Outpost entities
    query = f"""
    query {{
        outpostModels(where: {{game_id: "{game_id}"}}) {{
            edges {{
                node {{
                    entity {{
                        keys
                        models {{
                            __typename
                            ... on Outpost {{
                                game_id
                                position {{
                                    x
                                    y
                                }}
                                life
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    """
    
    # Make the POST request
    response = requests.post(url=TORII_URL, json={"query": query})
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        
        # Initialize a list to hold the outposts
        outposts = []
        # Navigate through the response to extract Outpost entities
        edges = data.get("data", {}).get("outpostModels", {}).get("edges", [])
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "Outpost":
                    outpost_details = {
                        "game_id": model.get("game_id"),
                        "position": model.get("position"),
                        "life": model.get("life")
                    }
                    outposts.append(outpost_details)
        
        # Return the extracted outposts
        return outposts
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

# for the current given event get the outpotverifeid object and then return all that have not been hit
def fetch_unverified_outposts(event_id, hit_outposts, game_id):
    query = f"""
    query {{
        outpostVerifiedModels(where: {{game_id: "{game_id}", event_id: "{event_id}"}}) {{
            edges {{
                node {{
                    entity {{
                        keys
                        models {{
                            __typename
                            ... on OutpostVerified {{
                                game_id
                                event_id
                                outpost_id {{
                                    x
                                    y
                                }}
                                verified
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    """
    response = requests.post(url=TORII_URL, json={"query": query})
    if response.status_code == 200:
        data = response.json()
        verified_outposts = []
        edges = data.get("data", {}).get("outpostVerifiedModels", {}).get("edges", [])
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "OutpostVerified" and model.get("verified"):
                    verified_outposts.append(model["outpost_id"])
                    
        # Check which hit outposts are not verified
        unverified_outposts = [outpost for outpost in hit_outposts if outpost["position"] not in verified_outposts]
        
        return unverified_outposts
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

# get all the ouposts that are currnetly being hit by the event via maths
def fetch_all_outpost_hit_by_current_event(event, outposts) -> []:

    print(f"Fetching outposts hit by event {event}...")

    if not event or not outposts:
        return [False]

    hit_outposts = [] 
    print(f"Event: {event}")
    print(event["position"]["x"])
    event_x = event["position"]["x"]
    event_y = event["position"]["y"]
    event_radius = event["radius"]
    
    for outpost in outposts:

        if (outpost["life"] == 0):
            continue

        outpost_x = outpost["position"]["x"]
        outpost_y = outpost["position"]["y"]
        
        distance = math.sqrt((outpost_x - event_x) ** 2 + (outpost_y - event_y) ** 2)
        
        if distance <= event_radius:
            hit_outposts.append(outpost)  # Add hit outpost to the list
            
    return hit_outposts  # Return the list of hit outposts instead of True/False

def fetch_latest_game_phase_info(game_id):
    
    query = f"""
    query {{
        gamePhasesModels(where: {{game_id: "{game_id}"}}) {{
            edges {{
                node {{
                    entity {{
                        keys
                        models {{
                            __typename
                             ... on GamePhases {{
                                status
                                preparation_block_number
                                game_id
                                play_block_number
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    """
    
    # Assuming TORII_URL is defined elsewhere in your code
    response = requests.post(url=TORII_URL, json={"query": query})
    
    if response.status_code == 200:
        data = response.json()
        
        # Corrected path to access 'edges' based on the provided JSON structure
        edges = data.get("data", {}).get("gamePhasesModels", {}).get("edges", [])
        
        if edges:
            for edge in edges:
                models = edge.get("node", {}).get("entity", {}).get("models", [])
                for model in models:
                    if model.get("__typename") == "GamePhases":
                        start_prep_phase = model.get("preparation_block_number")
                        start_play_phase = model.get("play_block_number")
                        print(f"Preparation Block Number: {start_prep_phase}")
                        print(f"Play Block Number: {start_play_phase}")
                        return (start_prep_phase, start_play_phase)
        
        return False  # Return False if no relevant data was found
    else:
        print(f"Error fetching data: {response.status_code}")
        return False

def fetch_latest_game_number() -> int:
    
    # GraphQL query for CurrentGame models
    query = """
    query {
        currentGameModels {
            edges {
                node {
                    entity {
                        keys
                        models {
                            __typename
                            ... on CurrentGame {
                                game_id
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    # Make the POST request
    response = requests.post(url=TORII_URL, json={"query": query})
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        
        # Navigate through the response to extract the game_id
        edges = data.get("data", {}).get("currentGameModels", {}).get("edges", [])
        
        if edges:
            for edge in edges:
                models = edge.get("node", {}).get("entity", {}).get("models", [])
                for model in models:
                    if model.get("__typename") == "CurrentGame":
                        game_id_hex = model.get("game_id")
                        # Convert hex game_id to int and return
                        return int(game_id_hex, 16)
                        
        # Return False if no game_id is found
        return -1
    else:
        print(f"Error fetching data: {response.status_code}")
        return -1

def send_discord_message(webhook_url, message):
    
    data = {'content': message}
    response = requests.post(webhook_url, json=data)
    return response.text

def clear_console():
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For macOS and Linux (os.name is 'posix' in these cases)
    else:
        os.system('clear')


def send_webhook(webhook_url, content, title=None, description=None, color=None, fields=None, footer=None, thumbnail=None, image=None):
    """
    Sends a webhook to the specified URL with an embedded message.

    Args:
        webhook_url (str): The URL of the webhook.
        content (str): The content of the message.
        title (str, optional): The title of the embed. Defaults to None.
        description (str, optional): The description of the embed. Defaults to None.
        color (int, optional): The color of the embed. Defaults to None.
        fields (list, optional): A list of fields to include in the embed. Defaults to None.
        footer (dict, optional): A dictionary containing the footer text and icon URL. Defaults to None.
        thumbnail (dict, optional): A dictionary containing the thumbnail URL and height and width. Defaults to None.
        image (dict, optional): A dictionary containing the image URL and height and width. Defaults to None.
    """
    # Create the embed object
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "fields": fields,
        "footer": footer,
        "thumbnail": thumbnail,
        "image": image
    }

    # Remove any None values from the embed
    embed = {k: v for k, v in embed.items() if v is not None}

    # Create the JSON payload
    payload = {
        "content": content,
        "embeds": [embed]
    }

    # Send the webhook
    requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})



# ok so we need to do the following
        

# 1. get the latest game number
        
#check if the latest game id is the same as the one all the data is saved from if it not the same then we restart all data

# 2. get the latest game info
# based on the phase we are in we do different things
#preparation phase we do nothing
# start of play phase we gfetch all the outpost
#then we continusoly fetch the current world event
# if there is no current world event then we create one
        
# 3. get the outposts that are currently being hit by the event
# 4. get the outposts that have not been verified
        
# 5. if all outposts have been verified then we create a new event


async def main():
    client = FullNodeClient(node_url=NODE_URL)

    # Initialize the account
    private_key_int = int(PRIVATE_KEY, 16)
    public_key_int = int(PUBLIC_KEY, 16)
    account = Account(
        client=client,
        address=ACCOUNT_ADDRESS, 
        key_pair=KeyPair(private_key=private_key_int, public_key=public_key_int),
        chain=0x4b4154414e41,      #katana chain id
    )

    last_block_number_checked = 0
    current_saved_game_id = -1 
    saved_outposts_for_this_game = []

    start_of_prep_phase = -1
    start_of_play_phase = -1

    send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"Rising revenant bot starting...")

    while True:
        send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"\n\n\n-------------------------------------------------")
        clear_console()  
        current_block_number = await client.get_block_number()   # get the current block number

        if current_block_number >= last_block_number_checked + BLOCK_CHECK_INTERVAL:  ##we want to run a check on the game every 5 blocks
            print("running check on the block number")
            last_block_number_checked = current_block_number # update the last block number checked

            # here we get the most current game number
            latest_game_id = fetch_latest_game_number() ##get the current game number
            if latest_game_id != current_saved_game_id:  # the current game number is different from the one we have saved therefore we load everything in
                print(f"New game detected. Game ID: {latest_game_id}")
                send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"New game detected. Game ID: {latest_game_id}")

                current_saved_game_id = latest_game_id
                saved_outposts_for_this_game = []  # we reset everything ready for the new game

                game_phase_data = fetch_latest_game_phase_info(current_saved_game_id)  # get the latest game phase info
                print(f"new Game Phase Data: {game_phase_data}")
                if (game_phase_data == False): # there has been an issue with the fetching of data we retry next time
                    print("there was an issue on the game phase data retrieve")
                    await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                    continue

                start_of_prep_phase = game_phase_data[0]
                start_of_play_phase = game_phase_data[1]
                send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"Game ID: {latest_game_id} has started. Waiting for the next check interval. Game phase starts at {start_of_prep_phase}, Play phase starts at {start_of_play_phase}...")
            else:
                print(f"Game ID: {latest_game_id} is the same as the one saved. No need to update.")
                send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"Game ID: {latest_game_id} is the same as the one saved. No need to update.")

            # now that we have all the data we need we check if we are in the play phase
            
            if (current_saved_game_id == -1):
                send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"No game found. Waiting for the next check interval...")
                
                await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                continue

            if (current_block_number >= start_of_play_phase):
                print("we are in the play phase")

                # if (len(saved_outposts_for_this_game) == 0):
                # print("Fetching outposts as the arr was empty")
                send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"Fetching outposts for game_id: {current_saved_game_id}...")
                saved_outposts_for_this_game = fetch_outposts(current_saved_game_id)
                print(f"Outposts fetched successfully. Total of {len(saved_outposts_for_this_game)} outposts found.")
                
                current_world_event = fetch_current_world_events(current_saved_game_id)

                print("Current World Event: ", current_world_event)

                if (len(current_world_event) > 0):
                      print("there is a world event")
                      send_discord_message(DISCORD_CHANNEL_WEBHOOK, "World event found. Checking outposts...")
                      allHitOutposts = fetch_all_outpost_hit_by_current_event(current_world_event[0], saved_outposts_for_this_game)
                      print(f"Outposts hit by the event: {allHitOutposts}")
                      unverifiedOutposts = fetch_unverified_outposts(current_world_event[0]["event_id"], allHitOutposts, current_saved_game_id)
                      print(f"Unverified outposts: {unverifiedOutposts}")

                      if len(unverifiedOutposts) == 0:
                            print("all outposts verified") 
                            send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"All outposts have been verified. Creating a new event...")
                            send_webhook(webhook_url=DISCORD_CHANNEL_WEBHOOK, content="All outposts have been verified. Creating a new event...", title="All outposts verified", color=0x00FF00)
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

                            send_webhook(webhook_url=DISCORD_CHANNEL_WEBHOOK, content="All outposts have not been verified. Missing outposts:", title="Not all outposts verified", description=missing_outposts_message, color=0xFF0000)

                            send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"Not all outposts have been verified yet. Waiting for the next check interval...")
                            await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                            continue
                      
                      
                else: # no event so we make a new one 
                    print("No current world event found. Creating a new one...")
                    send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"No current world event found. Creating a new one...")
                    await call_create_event_func(account, current_saved_game_id)
                    await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                    continue

            else:
                print("not in the play phase yet or no game found")
                send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"Not in the play phase...")
                await asyncio.sleep(LOOP_SECONDS_INTERVAL)
                continue    
        else:
            print("current block number is less than the last block number checked so we wait for the next check interval, block number is ", current_block_number)
            send_discord_message(DISCORD_CHANNEL_WEBHOOK, f"Current block number is {current_block_number}. Waiting for the next check interval which is at block {last_block_number_checked + BLOCK_CHECK_INTERVAL} ...")

        await asyncio.sleep(LOOP_SECONDS_INTERVAL)

asyncio.run(main())
