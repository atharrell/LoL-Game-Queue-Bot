# bot.py
import os
import random
import json

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Server list, used to make queues and settings independent between servers.
servers = {}

# Loads in environment variables for the whole bot, mostly just used to obscure the bot token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Generates a new bot/client for the bot, setting the command prefix
client = commands.Bot(command_prefix='!!')

# Server object used to store per server queue and settings
class Server:
    def __init__(self, autofill=True):
        self.top_queue = []
        self.jungle_queue = []
        self.mid_queue = []
        self.bot_queue = []
        self.support_queue = []
        self.total_queue = []
        self.autofill = autofill
        self.total_queue = []

# Dumps the json (data) into the file
def write_json(data, filename):
    with open(filename,'w') as f:
        json.dump(data, f, indent=4)

# Sorts the subset of objects based on the order of the full list of objects
def sort_subset(subset, full):
    dct = {x: i for i, x in enumerate(full)}
    return sorted(subset, key=dct.get)

# Picks players from a queue based on who was queued first and how many people are in the queue, players are then randomly assigned to teams
def pick_players(team_a, team_b, idx, queue, leftovers):
    # If there are 2 players in the queue, take these two players and assign them to random teams
    if len(queue) == 2:
        players = random.sample(queue, 2)
        team_a[idx] = players[0]
        team_b[idx] = players[1]

    # If there are more than 2 players take the first two and assign them to random teams, assign remaining players to a list of leftover players
    elif len(queue) > 2:
        leftovers.extend(queue[2:])
        players = random.sample(queue[0:2], 2)
        team_a[idx] = players[0]
        team_b[idx] = players[1]

    # If there is only 1 player in the queue assign them to a random team
    elif len(queue) == 1:
        team = random.randint(0,1)
        if team:
            team_a[idx] = queue[0]
        else:
            team_b[idx] = queue[0]

    # Return the 2 teams and leftover players (returns the original teams if none of the above conditions are met)
    return team_a, team_b, leftovers

# Generates randomized teams based on the current queue and server autofill setting
def get_suggested_teams(server):
    team_a = [None] * 5
    team_b = [None] * 5
    leftovers = []
    random.seed()

    team_a, team_b, leftovers = pick_players(team_a, team_b, 0, server.top_queue, leftovers)
    team_a, team_b, leftovers = pick_players(team_a, team_b, 1, server.jungle_queue, leftovers)
    team_a, team_b, leftovers = pick_players(team_a, team_b, 2, server.mid_queue, leftovers)
    team_a, team_b, leftovers = pick_players(team_a, team_b, 3, server.bot_queue, leftovers)
    team_a, team_b, leftovers = pick_players(team_a, team_b, 4, server.support_queue, leftovers)

    a_empty = [i for i, val in enumerate(team_a) if val == None]
    b_empty = [i for i, val in enumerate(team_b) if val == None]
    leftovers = sort_subset(leftovers, server.total_queue)
    empty_count = len(a_empty) + len(b_empty)

    # Manages the autofill for any empty spots if autofill is enabled or ends the queue if not
    if server.autofill:
        if empty_count == 0:
            return team_a, team_b, leftovers
        else:
            players = leftovers[0:(empty_count)]
            leftovers = leftovers[(empty_count - 2):len(leftovers)]
            if a_empty != []:
                for a in a_empty:
                    player = random.choice(players)
                    players.remove(player)
                    team_a[a] = player
            if b_empty != []:
                for b in b_empty:
                    player = random.choice(players)
                    players.remove(player)
                    team_b[b] = player

            return team_a, team_b, leftovers
    else:
        if empty_count > 0:
            return None, None, None
        else:
            return team_a, team_b, leftovers

# Whenever the bot is started, set up the required roles and load/generate default settings for each server
@client.event
async def on_ready():
    # Checks the available roles for each guild and then adds any roles that are missing
    for guild in client.guilds:
        roles = ['Top', 'Jungle', 'Mid', 'Bot', 'Support']
        new_roles = ['Top', 'Jungle', 'Mid', 'Bot', 'Support']
        for role in roles:
            for guild_role in guild.roles:
                if str(guild_role) == role:
                    new_roles.remove(role)
                    break
        for role in new_roles:
            await guild.create_role(name=role, color=discord.Color(0x13c262), mentionable=True)

        # Loads the settings from the json file of persisted settings if available, otherwise uses the default settings and writes a new
        # entry into the persisted settings file for that server.
        if guild.id not in servers:
            with open('persistent_settings.json') as json_file:
                settings = json.load(json_file)['servers']
                loaded = False
                for server in settings:
                    if server['guild_id'] == guild.id:
                        servers[guild.id] = Server(server['autofill'])
                        loaded = True
            if not loaded:
                servers[guild.id] = Server()
                with open('persistent_settings.json') as json_file:
                    settings = json.load(json_file)
                    temp = settings['servers']
                    server = {"guild_id": guild.id, "autofill": 1}
                    temp.append(server)
                write_json(settings, 'persistent_settings.json')
        print(f'{client.user.name} has connected to {guild.name}!')

# Lets a user add themselves to a role and removes them from any other
@client.command(name='role', help='!role {Top/Jungle/Mid/Bot/Support}')
async def role(ctx, role):
    if role.capitalize() not in ['Top', 'Jungle', 'Mid', 'Bot', 'Support']:
        await ctx.send(f'{str(role)} role not supported please choose a valid role (Top/Jungle/Mid/Bot/Support).')
    else:
        role = discord.utils.get(ctx.guild.roles, name=role.capitalize())
        user = ctx.message.author
        roles = [str(role) for role in user.roles]
        removed_from = None
        if 'Top' in roles:
            await user.remove_roles(user.roles[roles.index('Top')])
            removed_from = 'Top'
        elif 'Jungle' in roles:
            await user.remove_roles(user.roles[roles.index('Jungle')])
            removed_from = 'Jungle'
        elif 'Mid' in roles:
            await user.remove_roles(user.roles[roles.index('Mid')])
            removed_from = 'Mid'
        elif 'Bot' in roles:
            await user.remove_roles(user.roles[roles.index('Bot')])
            removed_from = 'Bot'
        elif 'Support' in roles:
            await user.remove_roles(user.roles[roles.index('Support')])
            removed_from = 'Support'
        try:
            await user.add_roles(role)
            if removed_from is None:
                await ctx.send(f'Successfully Joined {str(role)} role.')
            else:
                await ctx.send(f'Removed from {removed_from} role and joined {str(role)} role.')
        except:
            await ctx.send("Failed to join role, please check that the spelling is correct for the role name and that the role exists in this server.")

# Joins the queue, and resolves the queue/creates teams if there are enough people in the queue
@client.command(name='join', help='!join  (places you in the queue for a game based on your primary role)')
async def join(ctx):
    user = ctx.message.author
    server = servers[ctx.guild.id]
    if user in server.total_queue:
        await ctx.send(f'User is already in queue, can not be in the queue twice.')
    else:
        roles = [str(role) for role in user.roles]
        if 'Top' in roles:
            server.top_queue.append(user)
            server.total_queue.append(user)
            await ctx.send(f'Successfully Queued, position {len(server.top_queue)} of Top players.')
        elif 'Jungle' in roles:
            server.jungle_queue.append(user)
            server.total_queue.append(user)
            await ctx.send(f'Successfully Queued, position {len(server.jungle_queue)} of Jungle players.')
        elif 'Mid' in roles:
            server.mid_queue.append(user)
            server.total_queue.append(user)
            await ctx.send(f'Successfully Queued, position {len(server.mid_queue)} of Mid players.')
        elif 'Bot' in roles:
            server.bot_queue.append(user)
            server.total_queue.append(user)
            await ctx.send(f'Successfully Queued, position {len(server.bot_queue)} of Bot players.')
        elif 'Support' in roles:
            server.support_queue.append(user)
            server.total_queue.append(user)
            await ctx.send(f'Successfully Queued, position {len(server.support_queue)} of Support players.')
        else:
            await ctx.send("Failed to queue please check that you have joined a role. (!role {Top/Jungle/Mid/Bot/Support} to join a role)")
        queue_length = len(server.total_queue)
        if queue_length >= 10:
            a, b, c = get_suggested_teams(server)
            if c is None:
                pass
            else:
                copy = server.total_queue.copy()
                for p in copy:
                    if (p in a) or (p in b):
                        server.total_queue.remove(p)
                        if p in server.top_queue:
                            server.top_queue.remove(p)
                        elif p in server.jungle_queue:
                            server.jungle_queue.remove(p)
                        elif p in server.mid_queue:
                            server.mid_queue.remove(p)
                        elif p in server.bot_queue:
                            server.bot_queue.remove(p)
                        elif p in server.support_queue:
                            server.support_queue.remove(p)

                await ctx.send(f'Queue is filled and teams have been created, see below:')
                await ctx.send(f'Team A: Top-{a[0].mention} , Jungle-{a[1].mention} , Mid-{a[2].mention} , Bot-{a[3].mention} , Support-{a[4].mention}')
                await ctx.send(f'Team B: Top-{b[0].mention} , Jungle-{b[1].mention} , Mid-{b[2].mention} , Bot-{b[3].mention} , Support-{b[4].mention}')

# Prints the current queue of players with an optional argument to print based on role
@client.command(name='queue', help='!queue (option argument role Top/Jungle/Mid/Bot/Support) prints the current queue for all players or for that individual role.')
async def queue(ctx, role=None):
    server = servers[ctx.guild.id]
    if len(server.total_queue) == 0:
        await ctx.send('Queue is empty.')
    elif role is None:
        players = ', '.join([player.name for player in server.total_queue])
        await ctx.send(f'Currently {len(server.total_queue)} in queue: {players}')
    elif role.capitalize() == 'Top':
        players = ', '.join([player.name for player in server.top_queue])
        await ctx.send(f'Currently {len(server.top_queue)} in the top queue: {players}')
    elif role.capitalize() == 'Jungle':
        players = ', '.join([player.name for player in server.jungle_queue])
        await ctx.send(f'Currently {len(server.jungle_queue)} in the jungle queue: {players}')
    elif role.capitalize() == 'Mid':
        players = ', '.join([player.name for player in server.mid_queue])
        await ctx.send(f'Currently {len(server.mid_queue)} in the mid queue: {players}')
    elif role.capitalize() == 'Bot':
        players = ', '.join([player.name for player in server.bot_queue])
        await ctx.send(f'Currently {len(server.bot_queue)} in the bot queue: {players}')
    elif role.capitalize() == 'Support':
        players = ', '.join([player.name for player in server.support_queue])
        await ctx.send(f'Currently {len(server.support_queue)} in the support queue: {players}')
    else:
        await ctx.send(f'{str(role)} role not supported please choose a valid role (Top/Jungle/Mid/Bot/Support) or no role to get the whole queue.')

# Removes the player from the queue
@client.command(name='leave', help='!leave removes the user from the queue')
async def leave(ctx):
    server = servers[ctx.guild.id]
    user = ctx.message.author
    if user in server.total_queue:
        roles = [str(role) for role in user.roles]
        if 'Top' in roles:
            server.top_queue.remove(user)
            server.total_queue.remove(user)
        elif 'Jungle' in roles:
            server.jungle_queue.remove(user)
            server.total_queue.remove(user)
        elif 'Mid' in roles:
            server.mid_queue.remove(user)
            server.total_queue.remove(user)
        elif 'Bot' in roles:
            server.bot_queue.remove(user)
            server.total_queue.remove(user)
        elif 'Support' in roles:
            server.support_queue.remove(user)
            server.total_queue.remove(user)
        await ctx.send(f'Successfully removed from the queue.')
    else:
        await ctx.send("User not in queue.")

# Clears the entire queue (Note that players that are put into a game are automatically removed)
@client.command(name='clear', help='!clear clears the entire queue')
async def clear(ctx):
    server = servers[ctx.guild.id]
    server.top_queue = []
    server.jungle_queue = []
    server.mid_queue = []
    server.bot_queue = []
    server.support_queue = []
    server.total_queue = []
    await ctx.send("Queue successfully cleared.")

# Toggles whether or not autofill is on for the queue, setting persists per server.
@client.command(name='autofill', help='!autofill toggles autofill for game creation on or off for this server')
async def autofill(ctx):
    servers[ctx.guild.id].autofill = not servers[ctx.guild.id].autofill

    with open('persistent_settings.json') as json_file:
        settings_file = json.load(json_file)
        settings = settings_file['servers']
        for server in settings:
            if server['guild_id'] == ctx.guild.id:
                server['autofill'] = int(not server['autofill'])
    write_json(settings_file, 'persistent_settings.json')

    if servers[ctx.guild.id].autofill:
        await ctx.send(f'Autofill updated to true.')
    else:
        await ctx.send(f'Autofill updated to false.')

client.run(TOKEN)