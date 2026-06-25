import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import json
import time
import asyncio

DATA_FILE = 'data.json'

load_dotenv()  # processes the .env file
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


def load_data():
    if not os.path.exists(DATA_FILE):
        return {'values': {'ticket_count': 0}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)
    
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

async def sendMakoAuditLogMessage(interaction: discord.Interaction, message: str = "..."):
    data = load_data()
    log_channel = interaction.guild.get_channel(data['IDS']['makoAuditLogChannelID'])
    if log_channel is not None:
        return await log_channel.send(message)
    return None

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

@bot.tree.command(name='makokick', description="ADMIN ONLY - Kicks the given user.")
async def makokick(interaction: discord.Interaction, target: discord.Member, reasoninfo: str = "No info provided."):
    try:
        await target.send(f'You have been kicked from {interaction.guild} for the following reason: \n{reasoninfo}')
        await target.kick()
        await interaction.response.send_message(f'Kicked `{target}` for reason: `{reasoninfo}`', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to kick this member.", ephemeral=True)

@bot.tree.command(name='makoban', description="ADMIN ONLY - Bans the given user.")
@app_commands.checks.has_permissions(ban_members=True)
async def makoban(interaction: discord.Interaction, target: discord.Member, reasoninfo: str = "No info provided."):
    try:
        await target.send(f'You have been banned from {interaction.guild} for the following:\n{reasoninfo}')
    except discord.Forbidden:
        pass
    try:
        await target.ban(reason=reasoninfo)
        await interaction.response.send_message(f'Banned `{target}` for reason: `{reasoninfo}`.', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to ban users.", ephemeral=True)

@bot.tree.command(name='createticket', description='Creates a ticket channel.')
@app_commands.checks.has_permissions(manage_channels=True)
async def createticket(interaction: discord.Interaction, target: discord.Member):
    try:
        data = load_data()
        data['values']['ticket_count'] += 1
        save_data(data)

        wantedCategory = discord.utils.get(interaction.guild.categories, id=data["IDS"]["ticketCategoryID"])
        if wantedCategory is None:
            await interaction.response.send_message("Couldn't find the 'Tickets' category.", ephemeral=True)
            return
        
        channelName = f"ticket-{data["values"]["ticket_count"]}"

        channel = await interaction.guild.create_text_channel(name=channelName, category=wantedCategory)

        log_channel = interaction.guild.get_channel(data['IDS']['makoAuditLogChannelID'])
        if log_channel is not None:
            await log_channel.send(
                f"`{channelName}` has been made by {interaction.user}."
            )

        try:
            await channel.set_permissions(target, view_channel=True, send_messages=True)
        except:
            await interaction.response.send_message("I don't have permissions to edit channels.")
            return

        await interaction.response.send_message(f'Created `ticket-{data["values"]["ticket_count"]}` with user `{target}`.', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permissions to make channels.")

@bot.tree.command(name='closeticket', description='Closes the ticket the command is ran in.')
@app_commands.checks.has_permissions(manage_channels=True)
async def closeticket(interaction: discord.Interaction, reasoninfo: str = "No info provided"):
    try:
        futureTime = int(time.time()) + 10
        countdownString = f"<t:{futureTime}:R>"

        channelName = interaction.channel.name

        deletemessage = await sendMakoAuditLogMessage(
            interaction,
            f"`{channelName}` will be deleted {countdownString} for `{reasoninfo}` by `{interaction.user}`"
            )

        await interaction.response.send_message(f"Ticket will be removed {countdownString} for the following reason: {reasoninfo}.")
        await asyncio.sleep(10)
        try:
            await interaction.channel.delete(reason=reasoninfo)
        except:
            await interaction.response.send_message("I don't have permissions to delete channels.", ephemeral=True)

        if deletemessage is not None:
            await deletemessage.edit(
                content=f"`{channelName}` has been deleted by `{interaction.user}` for `{reasoninfo}`."
            )
    except:
        await interaction.response.send_message("I don't have permissions to remove channels.", ephemeral=True)

@bot.tree.command(name='purge', description="Remove a number of messages from the channel.")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, messagenumber: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=messagenumber)
    await interaction.followup.send(f"Purged {len(deleted)} message(s).", ephemeral=True)

@bot.tree.command(name='help', description='Shows what mako can do.')
async def help(interaction: discord.Interaction):
    message = (
        "## hey! welcome to using mako :)\n"
        "mako is a lightweight bot designed to help with general server functionality.\n\n"
        "heres a few things mako can help you with at the moment:\n"
        "# tickets\n"
        "- `/createticket` : creates a ticket with support for adding a user\n"
        "- `/closeticket` : closes the ticket the command is ran in\n"
        "# moderation\n"
        "- `/makokick` : kicks user with a sent dm (if able)\n"
        "- `/makoban` : bans user with a sent dm (if able)\n"
        "- `/purge` : deletes a set amount of messages from chat\n"
        "# misc\n"
        "- `/testcommand` : test to see if mako is alive! also checks my permissions in the given channel ;)\n\n"
        "make sure permissions are correctly set and have fun :)"
    )
    await interaction.response.send_message(message)

@bot.tree.command(name='testcommand', description="Checks mako's permissions in this channel.")
async def testcommand(interaction: discord.Interaction):
    me = interaction.guild.me  # the bot's member object
    perms = interaction.channel.permissions_for(me)

    # the permissions most relevant to what mako does
    relevant = [
        "view_channel",
        "send_messages",
        "manage_messages",
        "manage_channels",
        "read_message_history",
        "kick_members",
        "ban_members",
        "embed_links",
    ]

    lines = []
    for name in relevant:
        allowed = getattr(perms, name)
        status = "yes" if allowed else "no"
        lines.append(f"`{name}`: {status}")

    permreport = "\n".join(lines)

    message = (
        f"**mako status check :3**\n"
        f"alive and responding: yes\n"
        f"guild: `{interaction.guild}`\n"
        f"channel: {interaction.channel.mention}\n\n"
        f"**what can i do?:**\n"
        f"{permreport}"
    )

    await interaction.response.send_message(message, ephemeral=True)

bot.run(os.getenv('DISCORD_TOKEN'))