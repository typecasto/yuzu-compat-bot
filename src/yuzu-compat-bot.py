import json
from discord.ext import commands
import discord
from rich import traceback
from rich.console import Console
console = Console()
# traceback.install(console=console, extra_lines=5, word_wrap=True, show_locals=True)
list_json_filename = "games.json"

bot = commands.Bot(command_prefix=">")
list_channels: list[discord.TextChannel] = []

def convert_game_dict_to_message(game: dict, number: int):
    message = "⠀\n"
    message += f"`{number}. {game['name']}`\n"
    message += "\n**__Functional__**: \n"
    for line in game["functional"]:
        message += line + "\n"
    else:
        message += "None\n"
    message += "\n**__Broken__**: \n"
    for line in game["broken"]:
        message += line + "\n"
    else:
        message += "None\n"
    message += "\n**__Crashes__**: \n"
    for line in game["crashes"]:
        message += line + "\n"
    else:
        message += "None\n"
    message += "\n**__Recommended Settings__**: \n"
    for line in game["recommendedsettings"]:
        message += line + "\n"
    else:
        message += "None\n"
    message += "\n**__Notes__**: \n"
    for line in game["notes"]:
        message += line + "\n"
    else:
        message += "None\n"
    return message

# Custom context manager to open a json file for writing
class JsonFile(object):
    def __init__(self, file_name, method):
        self.file = open(file_name, method)
        self.obj = json.load(self.file)
    def __enter__(self):
        return self.obj
    def __exit__(self, type, value, traceback):
        if self.file.writable():
            json.dump(self.obj, self.file)
        self.file.close()

@bot.event
async def on_ready():
    for c_guild in bot.guilds:
        for c_channel in c_guild.text_channels:
            c_channel: discord.TextChannel
            # Short circuit topic existance check, 2nd half fails if channel has no topic
            if c_channel.topic and "<yuzu-compat: list>" in c_channel.topic:
                list_channels.append(c_channel)
                console.log(f"Got channel: {c_channel.name} in {c_channel.guild.name}")
    console.log("--- We're ready to go. ---", style="green")


@bot.event
async def on_error(error, *args, **kwargs):
    console.log(traceback.Traceback())


@bot.command()
async def add_game(ctx: commands.Context, *game: str):
    with open(list_json_filename) as file:
        games = json.load(file)

        json.dump(games, file)
    pass

# Checks the channels and makes any needed adjustments.


@bot.command()
async def sync(ctx: commands.Context):
    for channel in list_channels:
        console.log(f"Syncing channel in <{channel.guild}>.", style="green")

    pass

# Clear the channels and re-do the messages. Restrict to administrators.


@bot.command()
async def repair(ctx: commands.Context):
    console.log(f"Repairing channel in <{ctx.guild}>.", style="red bold underline")

    pass

# Extract the token from the file, trim a trailing newline, and start the bot.
token = ""
with open("token", "r") as file:
    token = file.read()
token.removesuffix("\n")
bot.run(token)
