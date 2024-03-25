
# TORII_URL = 'https://api.cartridge.gg/x/rr/torii/graphql'


import discord
from discord import app_commands
from typing import Optional
#import everything from queries
from queries import fetch_outposts, fetch_unverified_outposts, fetch_latest_game_number, fetch_game_phase_info,check_if_game_exists, fetch_current_world_event, fetch_game_state , fetch_all_outpost_hit_by_current_event, fetch_outpost_trades, fetch_reinforcement_trades, fetch_game_pot_info, fetch_contribution_sorted, fetch_world_event_info
from queries import Vec2, Outpost, GamePhaseInfo, EventDetails, Contribution, OutpostTrade, ReinforcementTrade, GamePotInfo, GameState, NODE_URL, TORII_URL
from starknet_py.net.full_node_client import FullNodeClient


def format_string(s, n):
    # If the string is short enough, just return it as is
    if len(s) <= 2*n:
        return s
    
    # Otherwise, construct the formatted string
    start = s[:n]
    end = s[-n:]
    return f"{start}...{end}"


def remove_third_character(s: str) -> str:
    return s[:2] + s[3:]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return
#     if message.content.startswith('$hello'):
#         await message.channel.send('Hello!')

# work
@tree.command()
@app_commands.describe(address='Address', game_id='Optional: Game Number')
async def player_info(interaction: discord.Interaction, address: str, game_id: Optional[str] = None):

    query_game_id = await get_query_game_id(game_id)

    if query_game_id == -1:
        await interaction.response.send_message("No game found")
        return

    outposts = await fetch_outposts(game_id=query_game_id, address=address)
    trades_outposts = await fetch_outpost_trades(game_id=query_game_id, seller=address)
    trades_reinforcement  = await fetch_reinforcement_trades(game_id=query_game_id, seller=address)

    title = f"Data about {format_string(address,4)} for game {query_game_id}"
    embed = discord.Embed(title=title, color=discord.Color.blue())

    # Outposts
    outpost_details = '\n'.join([f"Position: X{outpost.position.x}, Y{outpost.position.y} | Life: {outpost.life}" for outpost in outposts[0]])
    embed.add_field(name="Outposts", value=outpost_details if outpost_details else "No outposts available", inline=False)

    # Outpost Trades
    outpost_trades_details = '\n'.join([f"Status: {trade.status} | Offer: X{trade.offer.x}, Y{trade.offer.y}" for trade in trades_outposts[0]])
    embed.add_field(name="Outpost Trades", value=outpost_trades_details if outpost_trades_details else "No outpost trades available", inline=False)

    # Reinforcement Trades
    reinforcement_trades_details = '\n'.join([f" Status: {trade.status} | Offer: {trade.offer}" for trade in trades_reinforcement[0]])
    embed.add_field(name="Reinforcement Trades", value=reinforcement_trades_details if reinforcement_trades_details else "No reinforcement trades available", inline=False)

    await interaction.response.send_message(embed=embed)


# test
@tree.command()
@app_commands.describe(game_id='Optional: Game number')
async def game_info(interaction: discord.Interaction, game_id: Optional[str] = None):

    query_game_id = await get_query_game_id(game_id)

    if query_game_id == -1:
        await interaction.response.send_message("No game found")
        return


    game_phase_data: GamePhaseInfo = await fetch_game_phase_info(query_game_id)
    game_state: GameState = await fetch_game_state(query_game_id)

    trade_reinforcement_selling_data = await fetch_reinforcement_trades(query_game_id, status=1)
    total_reinforcement_volume_in_active_trades = sum(trade.offer for trade in trade_reinforcement_selling_data[0])

    trade_reinforcement_sold_data = await fetch_reinforcement_trades(query_game_id, status=2)
    trade_reinforcement_revoked_data = await fetch_reinforcement_trades(query_game_id, status= 3)

    trade_outpost_selling_data = await fetch_outpost_trades(query_game_id, status=1)
    trade_outpost_sold_data = await fetch_outpost_trades(query_game_id, status=2)
    trade_outpost_revoked_data = await fetch_outpost_trades(query_game_id, status=3)

    main_game_info_embed = discord.Embed(title= f"Phase Info for Game {query_game_id}", color=discord.Color.blue())

    client = FullNodeClient(node_url=NODE_URL)
    current_block_number = await client.get_block_number()

    if current_block_number > game_phase_data.play_block_number:
        current_phase = "Play Phase"
    elif current_block_number < game_phase_data.preparation_block_number:
        current_phase = "Game Waiting to Start"
    else:
        current_phase = "Preparation Phase"

    main_game_info_embed.add_field(name="Game Phase Info", value=f"Game ID: {game_phase_data.game_id}\nStart of Game Block: {game_phase_data.preparation_block_number}\nGame Phase Block: {game_phase_data.play_block_number}\nLength of Preparation Phase: {game_phase_data.play_block_number - game_phase_data.preparation_block_number}\nCurrent Phase: {current_phase}", inline=False)

    main_game_info_embed.add_field(name=f"Entities Info for Game {query_game_id}", value=f"Summoned revenants {game_state.outpost_created_count}/{game_state.still_available_revs + game_state.outpost_created_count}\nReinforcements in Outposts: {game_state.remain_life_count}\nReinforcements in Wallets: {game_state.reinforcement_count}", inline=False)

    main_game_info_embed.add_field(name=f"Market Info for Game {query_game_id}", value=f"Active Trades: {trade_reinforcement_selling_data[1]}\nSold Trades: {trade_reinforcement_sold_data[1]}\nRevoked Trades: {trade_reinforcement_revoked_data[1]}\n\nTotal Volume In Trades: {total_reinforcement_volume_in_active_trades}", inline=False)
    main_game_info_embed.add_field(name=f"Market Info for Game {query_game_id}", value=f"Active Trades: {trade_outpost_selling_data[1]}\nSold Trades: {trade_outpost_sold_data[1]}\nRevoked Trades: {trade_outpost_revoked_data[1]}", inline=False)
    await interaction.response.send_message(embed=main_game_info_embed)


# event id doenst wokr
@tree.command()
@app_commands.describe(event_id='Optional: Event number', game_id='Optional: Game number')
async def event_data(interaction: discord.Interaction, event_id: Optional[str] = None, game_id: Optional[str] = None):

    query_game_id = await get_query_game_id(game_id)

    if query_game_id == -1:
        await interaction.response.send_message("No game found")
        return

    print(f"Event ID: {event_id}")
    if event_id is 0:
        await interaction.response.send_message("Event ID cannot be 0")
        return

    event_data = ""
    
    title = f"Event Data for Game {query_game_id}"

    if event_id is not None:
        event_data = await fetch_world_event_info(game_id=query_game_id, number=event_id)

        if (event_data is None):
            await interaction.response.send_message("No event found")
            return
        title = f"Event Number {event_data.number} Data for Game {query_game_id}"
    else:
        event_data: EventDetails = await fetch_current_world_event(query_game_id)
        title = f"Current Event Data for Game {query_game_id}"

    if not event_data:
        await interaction.response.send_message("No event found")
        return
    
    # get all outposts
    all_outposts = await fetch_outposts(game_id=query_game_id)

    print(event_data)
    outpost_hit = fetch_all_outpost_hit_by_current_event(event_data, all_outposts[0])

    embed = discord.Embed(title=title, color=discord.Color.blue())
    #event detail embed
    embed.add_field(name="Event Details", value=f"Event ID: {event_data.event_id}\nEvent Number: {event_data.number}\nEvent Type: {event_data.event_type}\nEvent Start Block: {event_data.block_number}", inline=False)
    
    outpost_hit_details = '\n'.join([f"Position: X{outpost.position.x}, Y{outpost.position.y} | Life: {outpost.life}" for outpost in outpost_hit])
    embed.add_field(name="Outposts Hit", value=outpost_hit_details if outpost_hit_details else "No outposts hit", inline=False)

    if (len(outpost_hit) == 0):
        unverified_outposts = await fetch_unverified_outposts(event_data, outpost_hit, query_game_id)
        unverified_outposts_details = '\n'.join([f"Position: X{outpost.position.x}, Y{outpost.position.y} | Life: {outpost.life}" for outpost in unverified_outposts])
        embed.add_field(name="Unverified Outposts", value=unverified_outposts_details if unverified_outposts_details else "All outposts verified", inline=False)

    image_url = "https://picsum.photos/id/237/200/300"
    embed.set_image(url=image_url)

    await interaction.response.send_message(embed=embed)
    

# works
@tree.command()
@app_commands.describe( game_id='Optional: Game number', address='Optional: Address')
async def contribution_leaderboard(interaction: discord.Interaction, game_id: Optional[str] = None, address: Optional[str] = None):

    query_game_id = await get_query_game_id(game_id)

    if query_game_id == -1:
        await interaction.response.send_message("No game found")
        return
    
    contributions = await fetch_contribution_sorted(game_id=query_game_id)
    game_full_score = await fetch_game_state(game_id=query_game_id)

    request_index = -1
    if address is not None:
        address = remove_third_character(address)
        request_index = next((i for i, contribution in enumerate(contributions[0]) if contribution.player_id == address), -1)

    title = f"Contribution Leaderboard for Game {query_game_id}"
    embed = discord.Embed(title=title, color=discord.Color.blue())
    
    if game_full_score is not None:
        embed.add_field(name="Game Total Score", value=game_full_score.contribution_score_total, inline=False)
   
    if address is not None:
        if request_index != -1:
            player_contribution = contributions[0][request_index]
            embed.add_field(name="Your Position", value=f"#{request_index+1} - {format_string(player_contribution.player_id,6)} - {player_contribution.score}", inline=False)
        else:
            embed.add_field(name="Your Address Doesn's exist", value="\n", inline=False)
    
    leaderboard_details = '\n'.join([f"#{i+1} - {format_string( contribution.player_id,6)} - Score: {contribution.score}" for i, contribution in enumerate(contributions[0][:20])])
    embed.add_field(name="Leaderboard", value=leaderboard_details if leaderboard_details else "No contributions available", inline=False)

    await interaction.response.send_message(embed=embed)


# works
@tree.command()
@app_commands.describe(game_id='Optional: Game number')
async def jackpot_info(interaction: discord.Interaction, game_id: Optional[str] = None):

    query_game_id = await get_query_game_id(game_id)

    if query_game_id == -1:
        await interaction.response.send_message("No game found")
        return
    
    game_pot_info: GamePotInfo = await fetch_game_pot_info(game_id=query_game_id)
    title = f"Jackpot for Game {query_game_id}"

    embed = discord.Embed(title=title, color=discord.Color.blue())
    embed.add_field(name="Game Pot Info", value=f"Game ID: {game_pot_info.game_id}\nGame Total Pot: {round(game_pot_info.total_pot, 3)} $LORDS\nLast Standing Revenant Pot: {round(game_pot_info.winners_pot, 3)} $LORDS\nContribution Pot: {round(game_pot_info.confirmation_pot, 3)} $LORDS \nDevs pot: {round(game_pot_info.dev_pot, 3)} $LORDS", inline=False)

    await interaction.response.send_message(embed=embed)    

async def get_query_game_id(game_id):
    if game_id is None:
        return await fetch_latest_game_number()
    else:
        return await check_if_game_exists(game_id)

@client.event
async def on_ready():
    await tree.sync()
    print("Ready!")

client.run(BOT_TOKEN)