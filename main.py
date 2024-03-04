import asyncio
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.account.account import Account
from starknet_py.net.models.chains import StarknetChainId
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.net.client_models import Call
from starknet_py.contract import Contract

from starknet_py.net.account.base_account import BaseAccount

# Provided details
PRIVATE_KEY = "0x1800000000300000180000000000030000000000003006001800006600"
PUBLIC_KEY = "0x2b191c2f3ecf685a91af7cf72a43e7b90e2e41220175de5c4f7498981b10053"
ACCOUNT_ADDRESS = "0x6162896d1d7ab204c7ccac6dd5f8e9e7c25ecd5ae4fcb4ad32e57786bb46e03"
CONTRACT_ADDRESS = int("0x29d7c04fba830a9af1ce47b8fac1cb1790c7f3cfc201378adaf3aed60cc45d0",16)
FUNCTION_NAME = "create"
NODE_URL = "http://localhost:5050"

async def main():
    client = FullNodeClient(node_url=NODE_URL)

    private_key_int = int(PRIVATE_KEY, 16)
    public_key_int = int(PUBLIC_KEY, 16)

    # Initialize the key pair with integers
    account = Account(
        client=client,
        address=ACCOUNT_ADDRESS,
        key_pair=KeyPair(private_key=private_key_int, public_key=public_key_int),
        chain=0x4b4154414e41,
    )

    call = Call(
    to_addr=CONTRACT_ADDRESS, selector=get_selector_from_name(FUNCTION_NAME), calldata=[0]
    )

    resp = await account.execute(calls=call, max_fee=int(1e16))

    await account.client.wait_for_tx(resp.transaction_hash)

# Run the asynchronous main function
asyncio.run(main())




# import requests
# import math

# def fetch_current_world_events():
#     # GraphQL endpoint URL
#     url = 'http://localhost:8080/graphql'
    
#     # GraphQL query for CurrentWorldEvent entities
#     query = """
#     query {
#         currentWorldEventModels(where: {game_id: "0"}) {
#             edges {
#                 node {
#                     entity {
#                         keys
#                         models {
#                             __typename
#                             ... on CurrentWorldEvent {
#                                 game_id
#                                 event_id
#                                 position {
#                                     x
#                                     y
#                                 }
#                                 radius
#                                 number
#                             }
#                         }
#                     }
#                 }
#             }
#         }
#     }
#     """
    
#     # Make the POST request
#     response = requests.post(url=url, json={"query": query})
    
#     # Check if the request was successful
#     if response.status_code == 200:
#         # Parse the JSON response
#         data = response.json()
        
#         # Initialize a list to hold the current world events
#         current_world_events = []
        
#         # Navigate through the response to extract CurrentWorldEvent entities
#         edges = data.get("data", {}).get("currentWorldEventModels", {}).get("edges", [])
        
#         for edge in edges:
#             models = edge.get("node", {}).get("entity", {}).get("models", [])
#             for model in models:
#                 if model.get("__typename") == "CurrentWorldEvent":
#                     event_details = {
#                         "game_id": model.get("game_id"),
#                         "event_id": model.get("event_id"),
#                         "position": model.get("position"),
#                         "radius": model.get("radius"),
#                         "number": model.get("number")
#                     }
#                     current_world_events.append(event_details)
        
#         # Return the extracted events
#         return current_world_events
#     else:
#         print(f"Error fetching data: {response.status_code}")
#         return []

# def fetch_outposts():
#     # GraphQL endpoint URL
#     url = 'http://localhost:8080/graphql'
    
#     # GraphQL query for Outpost entities
#     query = """
#     query {
#         outpostModels(where: {game_id: "0"}) {
#             edges {
#                 node {
#                     entity {
#                         keys
#                         models {
#                             __typename
#                             ... on Outpost {
#                                 game_id
#                                 position {
#                                     x
#                                     y
#                                 }
#                                 life
#                             }
#                         }
#                     }
#                 }
#             }
#         }
#     }
#     """
    
#     # Make the POST request
#     response = requests.post(url=url, json={"query": query})
    
#     # Check if the request was successful
#     if response.status_code == 200:
#         # Parse the JSON response
#         data = response.json()
        
#         # Initialize a list to hold the outposts
#         outposts = []
        
#         # Navigate through the response to extract Outpost entities
#         edges = data.get("data", {}).get("outpostModels", {}).get("edges", [])
        
#         for edge in edges:
#             models = edge.get("node", {}).get("entity", {}).get("models", [])
#             for model in models:
#                 if model.get("__typename") == "Outpost":
#                     outpost_details = {
#                         "game_id": model.get("game_id"),
#                         "position": model.get("position"),
#                         "life": model.get("life")
#                     }
#                     outposts.append(outpost_details)
        
#         # Return the extracted outposts
#         return outposts
#     else:
#         print(f"Error fetching data: {response.status_code}")
#         return []

# def fetch_unverified_outposts(event_id, hit_outposts):
#     url = 'http://localhost:8080/graphql'
#     query = f"""
#     query {{
#         outpostVerifiedModels(where: {{game_id: "0", event_id: "{event_id}"}}) {{
#             edges {{
#                 node {{
#                     entity {{
#                         keys
#                         models {{
#                             __typename
#                             ... on OutpostVerified {{
#                                 game_id
#                                 event_id
#                                 outpost_id {{
#                                     x
#                                     y
#                                 }}
#                                 verified
#                             }}
#                         }}
#                     }}
#                 }}
#             }}
#         }}
#     }}
#     """
#     response = requests.post(url=url, json={"query": query})
#     if response.status_code == 200:
#         data = response.json()
#         verified_outposts = []
#         edges = data.get("data", {}).get("outpostVerifiedModels", {}).get("edges", [])
        
#         for edge in edges:
#             models = edge.get("node", {}).get("entity", {}).get("models", [])
#             for model in models:
#                 if model.get("__typename") == "OutpostVerified" and model.get("verified"):
#                     verified_outposts.append(model["outpost_id"])
                    
#         # Check which hit outposts are not verified
#         unverified_outposts = [outpost for outpost in hit_outposts if outpost["position"] not in verified_outposts]
        
#         return unverified_outposts
#     else:
#         print(f"Error fetching data: {response.status_code}")
#         return []

# def is_outpost_inside_event(event, outposts):
#     hit_outposts = []  # To track outposts hit by the event
#     event_x = event["position"]["x"]
#     event_y = event["position"]["y"]
#     event_radius = event["radius"]
    
#     for outpost in outposts:
#         outpost_x = outpost["position"]["x"]
#         outpost_y = outpost["position"]["y"]
        
#         distance = math.sqrt((outpost_x - event_x) ** 2 + (outpost_y - event_y) ** 2)
        
#         if distance <= event_radius:
#             print("INSIDE")
#             hit_outposts.append(outpost)  # Add hit outpost to the list
            
#     return hit_outposts  # Return the list of hit outposts instead of True/False

# def fethc_latest_game_number():
#     # GraphQL endpoint URL
#     url = 'http://localhost:8080/graphql'
    
#     # GraphQL query for CurrentGame models
#     query = """
#     query {
#         currentGameModels {
#             edges {
#                 node {
#                     entity {
#                         keys
#                         models {
#                             __typename
#                             ... on CurrentGame {
#                                 game_id
#                             }
#                         }
#                     }
#                 }
#             }
#         }
#     }
#     """
    
#     # Make the POST request
#     response = requests.post(url=url, json={"query": query})
    
#     # Check if the request was successful
#     if response.status_code == 200:
#         # Parse the JSON response
#         data = response.json()
        
#         # Navigate through the response to extract the game_id
#         edges = data.get("data", {}).get("currentGameModels", {}).get("edges", [])
        
#         if edges:
#             for edge in edges:
#                 models = edge.get("node", {}).get("entity", {}).get("models", [])
#                 for model in models:
#                     if model.get("__typename") == "CurrentGame":
#                         game_id_hex = model.get("game_id")
#                         # Convert hex game_id to int and return
#                         return int(game_id_hex, 16)
                        
#         # Return False if no game_id is found
#         return False
#     else:
#         print(f"Error fetching data: {response.status_code}")
#         return False


# current_world_events = fetch_current_world_events()
# outposts = fetch_outposts()
# for event in current_world_events:
#     hit_outposts = is_outpost_inside_event(event, outposts)
    
#     if hit_outposts:
#         unverified_outposts = fetch_unverified_outposts(event["event_id"], hit_outposts)
#         if unverified_outposts:
#             print(f"Unverified Outposts for Event ID {event['event_id']}:")
#             for outpost in unverified_outposts:
#                 print(outpost)
#         else:
#             print(f"All outposts verified for Event ID {event['event_id']}.")
#     else:
#         print(f"No outposts hit by Event ID {event['event_id']}.")

