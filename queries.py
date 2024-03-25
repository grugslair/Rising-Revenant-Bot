# this is the query script all the queries should be saved here instead of randomly putting them in the main script
import requests
from typing import List, Optional
import requests
from dataclasses import dataclass
import asyncio
import math

# TORII_URL = 'http://localhost:8080/graphql'
TORII_URL = 'https://api.cartridge.gg/x/rr/torii/graphql'

NODE_URL = "http://localhost:5050"

@dataclass
class Vec2:
    x: int
    y: int

@dataclass
class Outpost:
    game_id: int
    position: Vec2
    life: int

@dataclass
class GamePhaseInfo:
    status: str
    preparation_block_number: int
    game_id: int
    play_block_number: int

@dataclass
class GamePotInfo:
    game_id: int
    dev_pot: int
    claimed: bool
    confirmation_pot: int
    winners_pot: int
    ltr_pot: int
    total_pot: int

@dataclass
class EventDetails:
    game_id: int
    event_id: str
    position: Vec2
    radius: int
    number: int
    event_type: str
    block_number: int

@dataclass
class OutpostTrade:
    game_id: int
    status: int
    offer: Vec2  

@dataclass
class ReinforcementTrade:
    game_id: int
    status: int
    offer: str  

@dataclass
class Contribution:
    player_id: str
    score: int

@dataclass
class GameState:
    reinforcement_count: int
    remain_life_count: int
    outpost_created_count: int
    still_available_revs: int
    contribution_score_total: int


def hex_to_number(hex_str: str, add_decimals: bool = False) -> float:
    number = int(hex_str, 16)
    if add_decimals:
        return number / 10**18  # Adjust the divisor based on your needs (18 decimal places here)
    else:
        return number

async def fetch_unverified_outposts(event_id: EventDetails, hit_outposts: List[Vec2], game_id: str) -> List[Vec2]:

    if event_id is None or hit_outposts is None:
        return []

    query = f"""
    query {{
        outpostVerifiedModels(where: {{game_id: "{game_id}", event_id: "{event_id.event_id}"}}) {{
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

    response = requests.post(url=TORII_URL, json={"query": query})  # Make sure TORII_URL is defined
    if response.status_code == 200:
        data = response.json()
        verified_outposts_positions = []  # This will hold positions of verified outposts
        
        edges = data.get("data", {}).get("outpostVerifiedModels", {}).get("edges", [])
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "OutpostVerified" and model.get("verified"):
                    outpost_position = Vec2(x=model["outpost_id"]["x"], y=model["outpost_id"]["y"])
                    verified_outposts_positions.append(outpost_position)
                    
        # Filter to find unverified outposts
        unverified_outposts = [outpost for outpost in hit_outposts if outpost not in verified_outposts_positions]
        
        return unverified_outposts
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

async def fetch_outposts(game_id: str, address: str = "", type: str = "") -> (list, int):
    where_clause = f'game_id: "{game_id}"' + (f', owner: "{address}"' if address else "") + (f', reinforcement_type: "{type}"' if type else "")
    
    query = f"""
    query {{
        outpostModels(where: {{{where_clause}}}) {{
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
                                { 'owner' if address else '' }
                                { 'reinforcement_type' if type else '' }
                            }}
                        }}
                    }}
                }}
            }}
            totalCount
        }}
    }}
    """
    response = requests.post(url=TORII_URL, json={"query": query})
    if response.status_code == 200:
        data = response.json()
        outposts = []

        edges = data.get("data", {}).get("outpostModels", {}).get("edges", [])

        totalCount = data.get("data", {}).get("outpostModels", {}).get("totalCount", 0)
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "Outpost":
                    outpost_details = Outpost(
                        game_id=hex_to_number(model.get("game_id"), add_decimals=False),
                        position= Vec2(x= int(model.get("position").get("x")), y= int(model.get("position").get("y"))),
                        life=model.get("life")
                    )
                    outposts.append(outpost_details)
        
        return outposts, totalCount
    else:
        print(f"Error fetching data: {response.status_code}")
        return [], 0

async def fetch_game_phase_info(game_id: str) -> Optional[GamePhaseInfo]:
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

    response = requests.post(url=TORII_URL, json={"query": query})
    
    if response.status_code == 200:
        data = response.json()
        edges = data.get("data", {}).get("gamePhasesModels", {}).get("edges", [])
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "GamePhases":
                    game_phase_info = GamePhaseInfo(
                        model.get("status"),
                        model.get("preparation_block_number"),
                        hex_to_number(model.get("game_id"), add_decimals=False),
                        model.get("play_block_number")
                    )
                    return game_phase_info
        
        return None  
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

async def fetch_game_pot_info(game_id: str) -> Optional[GamePotInfo]:
    query = f"""
    query {{
        gamePotModels(where: {{game_id: "{game_id}"}}) {{
            edges {{
                node {{
                    entity {{
                        keys
                        models {{
                            __typename
                            ... on GamePot {{
                                game_id
                                dev_pot
                                claimed
                                confirmation_pot
                                winners_pot
                                ltr_pot
                                total_pot
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
        edges = data.get("data", {}).get("gamePotModels", {}).get("edges", [])
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "GamePot":
                    game_pot_info = GamePotInfo(
                        hex_to_number(model.get("game_id"), add_decimals=False),
                        hex_to_number(model.get("dev_pot"), add_decimals=True),
                        model.get("claimed"),
                        hex_to_number(model.get("confirmation_pot"), add_decimals=True),
                        hex_to_number(model.get("winners_pot"), add_decimals=True),
                        hex_to_number(model.get("ltr_pot"), add_decimals=True),
                        hex_to_number(model.get("total_pot"), add_decimals=True)
                    )
                    return game_pot_info
        
        return None  
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

async def fetch_current_world_event(game_id: str) -> Optional[EventDetails]:
    # GraphQL query for CurrentWorldEvent entities
    print(f"Fetching current world event for game_id: {game_id}")

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
                                    event_type
                                    block_number
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
        edges = data.get("data", {}).get("currentWorldEventModels", {}).get("edges", [])
        
        if not edges: 
            print(f"No current world events found for game_id: {game_id}")
            return None 
            
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "CurrentWorldEvent":
                    event_details = EventDetails(
                        game_id=hex_to_number(model.get("game_id"), add_decimals=False),
                        event_id=model.get("event_id"),
                        position = Vec2(x=int(model.get("position").get("x")), y=int(model.get("position").get("y"))),
                        radius=model.get("radius"),
                        number=model.get("number"),
                        event_type=model.get("event_type"),
                        block_number=model.get("block_number")
                    )
                    return event_details
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

async def fetch_latest_game_number() -> int:
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

    response = requests.post(url=TORII_URL, json={"query": query})
    
    if response.status_code == 200:
        data = response.json()

        edges = data.get("data", {}).get("currentGameModels", {}).get("edges", [])
        
        if edges:
            for edge in edges:
                models = edge.get("node", {}).get("entity", {}).get("models", [])
                for model in models:
                    if model.get("__typename") == "CurrentGame":
                        game_id_hex = model.get("game_id")

                        return int(game_id_hex, 16)
                        
        return -1
    else:
        print(f"Error fetching data: {response.status_code}")
        return -1

async def fetch_game_state(game_id: str) -> GameState:
    query = f"""
    query {{
        gameStateModels(where: {{game_id: "{game_id}"}}) {{
            edges {{
                node {{
                    entity {{
                        keys
                        models {{
                            ... on GameState {{
                                __typename
                                game_id
                                reinforcement_count
                                remain_life_count
                                outpost_created_count
                                outpost_remaining_count
                                contribution_score_total
                            }}
                            ... on OutpostMarket {{
                                __typename
                                game_id
                              	available
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

        edges = data.get("data", {}).get("gameStateModels", {}).get("edges", [])
        
        game_state_info:GameState = GameState(reinforcement_count=0, remain_life_count=0, outpost_created_count=0, still_available_revs=0, contribution_score_total=0)

        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                print(model)
                if model.get("__typename") == "OutpostMarket":
                    game_state_info.still_available_revs = model.get("available")

                if model.get("__typename") == "GameState":
                    game_state_info.reinforcement_count=model.get("reinforcement_count")
                    game_state_info.remain_life_count=model.get("remain_life_count")
                    game_state_info.outpost_created_count=model.get("outpost_created_count")
                    game_state_info.contribution_score_total=int(model.get("contribution_score_total"), 16)
                    
        return game_state_info  
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

async def fetch_outpost_trades(game_id: str, status: int = "", seller: str = "") -> (list, int):
    where_clause = f'game_id: "{game_id}"' + (f', seller: "{seller}"' if seller else "") + (f', status: {status}' if status else "")

    query = f"""
    query {{
        outpostTradeModels(where: {{{where_clause}}}) {{
            edges {{
                node {{
                    entity {{
                        keys
                        models {{
                            __typename
                            ... on OutpostTrade {{
                                game_id
                                offer {{
                                    x
                                    y
                                }}
                                { 'status' if status else '' }
                                { 'seller' if seller else '' }
                            }}
                        }}
                    }}
                }}
            }}
            totalCount
        }}
    }}
    """

    response = requests.post(url=TORII_URL, json={"query": query})
    
    if response.status_code == 200:
        data = response.json()
        trades = []
        edges = data.get("data", {}).get("outpostTradeModels", {}).get("edges", [])
        totalCount = data.get("data", {}).get("outpostTradeModels", {}).get("totalCount", 0)
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "OutpostTrade":
                    trade_details = OutpostTrade(
                        game_id= hex_to_number(model.get("game_id"), add_decimals=False),
                        status=model.get("status"),
                        offer=Vec2(x= int(model.get("offer").get("x")), y= int(model.get("offer").get("y"))) ,
                    )
                    trades.append(trade_details)
        
        return trades, totalCount
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

async def fetch_reinforcement_trades(game_id: str, status: int = "", seller:str = "") -> (list, int):
    where_clause = f'game_id: "{game_id}"' + (f', seller: "{seller}"' if seller else "") + (f', status: {status}' if status else "")

    query = f"""
    query {{
        reinforcementTradeModels(where: {{{where_clause}}}) {{
            edges {{
                node {{
                    entity {{
                        keys
                        models {{
                            __typename
                            ... on ReinforcementTrade {{
                                game_id
                                offer
                                { 'status' if status else '' }
                                { 'seller' if seller else '' }
                            }}
                        }}
                    }}
                }}
            }}
            totalCount
        }}
    }}
    """

    response = requests.post(url=TORII_URL, json={"query": query})

    if response.status_code == 200:
        data = response.json()  
        trades = []

        edges = data.get("data", {}).get("reinforcementTradeModels", {}).get("edges", [])
        totalCount = data.get("data", {}).get("reinforcementTradeModels", {}).get("totalCount", 0)
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "ReinforcementTrade":
                    trade_details = ReinforcementTrade(
                        game_id= hex_to_number(model.get("game_id"), add_decimals=False),
                        status=model.get("status"),
                        offer=model.get("offer"),
                    )
                    trades.append(trade_details)
        
        return trades, totalCount
    else:
        print(f"Error fetching data: {response.status_code}")
        return [], 0

async def fetch_contribution_sorted(game_id: str,  address:str = "") -> (list, int):
    where_clause = f'game_id: "{game_id}"' + (f', player_id: "{address}"' if address else "") 

    query = f"""
    query {{
        playerContributionModels(
            where: {{{where_clause}}}  
            order: {{direction: DESC, field: SCORE}}
            ) {{
            edges {{
                node {{
                    entity {{
                        keys
                        models {{
                            __typename
                            ... on PlayerContribution {{
                                game_id
                              	player_id
                                score
                                { 'player_id' if address else '' }
                            }}
                        }}
                    }}
                }}
            }}
            totalCount
        }}
    }}
    """

    response = requests.post(url=TORII_URL, json={"query": query})
    
    if response.status_code == 200:
        data = response.json()  # Removed await since requests does not support async
        contributions: Contribution = []

        edges = data.get("data", {}).get("playerContributionModels", {}).get("edges", [])
        totalCount = data.get("data", {}).get("playerContributionModels", {}).get("totalCount", 0)
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "PlayerContribution":
                    contrib_details = Contribution(
                        player_id=model.get("player_id"),
                        score=int(model.get("score"), 16)
                    )
                    contributions.append(contrib_details)
        
        return contributions, totalCount
    else:
        print(f"Error fetching data: {response.status_code}")
        return [], 0

async def fetch_world_event_info(game_id: str, number: int) -> Optional[EventDetails]:
    query = f"""
    query {{
        worldEventModels(where: {{game_id: "{game_id}", number: {number}}}) {{
            edges {{
                node {{
                    entity {{
                        keys
                        models {{
                            __typename
                            ... on WorldEvent {{
                                game_id
                                event_id
                                position {{
                                    x
                                    y
                                }}
                                radius
                                number
                                event_type
                                block_number
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    """

    print(query)

    response = requests.post(url=TORII_URL, json={"query": query})
    
    if response.status_code == 200:
        data = response.json()
        edges = data.get("data", {}).get("worldEventModels", {}).get("edges", [])
        
        for edge in edges:
            models = edge.get("node", {}).get("entity", {}).get("models", [])
            for model in models:
                if model.get("__typename") == "WorldEvent":
                    world_event_info = EventDetails(
                        game_id=hex_to_number(model.get("game_id"), add_decimals=False),
                        event_id=model.get("event_id"),
                        position = Vec2(x=int(model.get("position").get("x")), y=int(model.get("position").get("y"))),
                        radius=model.get("radius"),
                        number=model.get("number"),
                        event_type=model.get("event_type"),
                        block_number=model.get("block_number")
                    )
                    return world_event_info
        
        return None  
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

async def check_if_game_exists(game_id: str) -> int:
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
                                game_id
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
        edges = data.get("data", {}).get("gamePhasesModels", {}).get("edges", [])
        if len(edges) > 0:
            return game_id

        return -1  
    else:
        print(f"Error fetching data: {response.status_code}")
        return -1

def fetch_all_outpost_hit_by_current_event(event: EventDetails, outposts: list[Outpost]) -> list[Outpost]:

    print(f"Fetching outposts hit by event {event}...")

    if event is None or outposts is None:
        return []

    hit_outposts : list[Outpost] = [] 

    for outpost in outposts:
        if (outpost.life == 0):
            continue

        distance = math.sqrt((outpost.position.x - event.position.x ) ** 2 + (outpost.position.y  - event.position.y ) ** 2)
        
        if distance <= event.radius:
            hit_outposts.append(outpost) 
            
    return hit_outposts  



async def test_each_query():

    game_id = "0"
    data = await fetch_game_state(game_id)
    print("\n\nGame State: ")
    print(data)
    



    outposts = await fetch_outposts(game_id)
    print("Outposts: ")
    print(outposts[0])
    print(f"Total Count: {outposts[1]}")

    # Test fetch_outposts_of
    address = "0x00d31ff85db0d9e46f1f14551b501ef3c2e689763befedae94d69dd0f83b7e57"
    outposts = await fetch_outposts(game_id, address)
    print(f"\n\nOutposts of {address}: ")
    print(outposts[0])
    print(f"Total Count: {outposts[1]}")

    # test fetch_contribution_sorted
    contributions, total_count = await fetch_contribution_sorted(game_id, address)
    print(f"\n\nContributions of {address}: ")
    print(contributions)

    # test full contribution
    contributions, total_count = await fetch_contribution_sorted(game_id)
    print(f"\n\nfull Contributions of: ")
    print(contributions)

    # # Test fetch_outposts_of_type
    # type = "None"
    # outposts = await fetch_outposts(game_id, type=type)
    # print("\n\nOutposts of type None: ")
    # print(outposts[0])
    # print(f"Total Count: {outposts[1]}")

    # type = "Wall"
    # outposts = await fetch_outposts(game_id, type=type)
    # print("\n\nOutposts of type Wall: ")
    # print(outposts[0])
    # print(f"Total Count: {outposts[1]}")

    # type = "Trench"
    # outposts = await fetch_outposts(game_id, type=type)
    # print("\n\nOutposts of type trench: ")
    # print(outposts[0])
    # print(f"Total Count: {outposts[1]}")

    # # Test fetch_outposts_of_type
    # type = "Bunker"
    # outposts = await fetch_outposts(game_id, type=type)
    # print("\n\nOutposts of type Bunker: ")
    # print(outposts[0])
    # print(f"Total Count: {outposts[1]}")

    # Test fetch_latest_game_phase_info
    game_phase_info = await fetch_game_phase_info(game_id)
    print("\n\nGame Phase Info: ")
    print(game_phase_info)

    # Test fetch_latest_game_pot_info
    game_pot_info = await fetch_game_pot_info(game_id)
    print("\n\nGame Pot Info: ")
    print(game_pot_info)

    # Test fetch_current_world_event
    event_details = await fetch_current_world_event(game_id)
    print("\n\nEvent Details: ")
    print(event_details)

    # Test fetch_latest_game_number
    latest_game_number = await fetch_latest_game_number()
    print("\n\nLatest Game Number: ")
    print(latest_game_number)

    # Test fetch_unverified_outposts
    hit_outposts = fetch_all_outpost_hit_by_current_event(event_details, outposts[0])
    print(f"\n\nHit Outposts: ")
    print(hit_outposts)
    unverified_outposts = await fetch_unverified_outposts(event_details, hit_outposts, game_id)
    print("\n\nUnverified Outposts: ")
    print(unverified_outposts)

    # Test fetch_latest_world_event_info
    number = 0
    world_event_info = await fetch_world_event_info(game_id, number)
    print(f"\n\nWorld Event Info {number}: ")
    print(world_event_info)

    # Test fetch_outpost_trades
    status = 1
    trades, total_count = await fetch_outpost_trades(game_id,status= status)
    print("\n\nOutpost Trades selling: ")
    print(trades)
    print(f"Total Count: {total_count}")

    status = 2
    trades, total_count = await fetch_outpost_trades(game_id,status= status)
    print("\n\nOutpost Trades sold: ")
    print(trades)
    print(f"Total Count: {total_count}")

    status = 3
    trades, total_count = await fetch_outpost_trades(game_id,status= status)
    print("\n\nOutpost Trades revoked: ")
    print(trades)
    print(f"Total Count: {total_count}")

    # Test fetch_reinforcement_trades
    status = 1
    trades, total_count = await fetch_reinforcement_trades(game_id, status=status)
    print("\n\nReinforcement Trades selling: ")
    print(trades)
    print(f"Total Count: {total_count}")

    status = 2
    trades, total_count = await fetch_reinforcement_trades(game_id, status=status)
    print("\n\nReinforcement Trades sold: ")
    print(trades)
    print(f"Total Count: {total_count}")

    status = 3
    trades, total_count = await fetch_reinforcement_trades(game_id, status= status)
    print("\n\nReinforcement Trades revoked: ")
    print(trades)
    print(f"Total Count: {total_count}")

    # Test fetch_reinforcement_trades_specific_seller
    status = 1
    trades, total_count = await fetch_reinforcement_trades(game_id,seller= address,status= status)
    print(f"\n\nReinforcement Trades from {address} status active: ")
    print(trades)
    print(f"Total Count: {total_count}")





# Run the test_each_query function
asyncio.run(test_each_query())
