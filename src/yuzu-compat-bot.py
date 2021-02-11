import json
from typing import Optional
from discord.enums import Status
from discord.ext import commands
import discord
from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands.errors import BadArgument, MissingRequiredArgument
from rich import traceback, inspect
from rich.console import Console
from inspect import cleandoc as multiline

console = Console()
# traceback.install(console=console, extra_lines=5, word_wrap=True, show_locals=True)
database_location = "games.json"

bot = commands.Bot(command_prefix=">")
list_channels: list[discord.TextChannel] = []
log_channels: list[discord.TextChannel] = []
db_lock: bool = False  # To prevent async race conditions from ocurring.


def convert_game_dict_to_message(game: dict, number: int):
    functional = ""
    found = False
    for i, x in enumerate(game["functional"]):
        functional += f"{i+1}. {x}\n"
        found = True
    if not found:
        functional += "* None\n"

    broken = ""
    found = False
    for i, x in enumerate(game["broken"]):
        broken += f"{i+1}. {x}\n"
        found = True
    if not found:
        broken += "* None\n"

    crashes = ""
    found = False
    for i, x in enumerate(game["crashes"]):
        crashes += f"{i+1}. {x}\n"
        found = True
    if not found:
        crashes += "* None\n"

    settings = ""
    found = False
    for i, x in enumerate(game["recommendedsettings"]):
        settings += f"{i+1}. {x}\n"
        found = True
    if not found:
        settings += "* None\n"

    notes = ""
    found = False
    for i, x in enumerate(game["notes"]):
        notes += f"{i+1}. {x}\n"
        found = True
    if not found:
        notes += "* None\n"

    message = f"""```markdown
[{number:03}]: {game['name']}

# Functional
{functional}
# Broken
{broken}
# Crashes
{crashes}
# Recommended Settings
{settings}
# Notes
{notes}```"""
    return message

# Custom context manager to open a json file for writing


class JsonFile:
    def __init__(self, file_name, mode="r+", encoding="utf8"):
        self.file = open(file_name, mode=mode, encoding=encoding)
        self.obj = json.load(self.file, )

    def __enter__(self):
        db_lock = True
        return self.obj

    def __exit__(self, type, value, traceback):
        if self.file.writable():
            self.file.seek(0)
            json.dump(self.obj, self.file, indent=4)
            self.file.truncate()
        self.file.close()
        db_lock = False


def db_access(ctx):
    return not db_lock


@bot.event
async def on_ready():
    for c_guild in bot.guilds:
        for c_channel in c_guild.text_channels:
            c_channel: discord.TextChannel
            # Short circuit topic existance check, 2nd half fails if channel has no topic
            if c_channel.topic and "<yuzu-compat: list>" in c_channel.topic:
                list_channels.append(c_channel)
                console.log(f"Got list channel: {c_channel.name} in {c_channel.guild.name}")
            # list channels take priority
            if c_channel.topic and "<yuzu-compat: log>" in c_channel.topic and c_channel not in list_channels:
                log_channels.append(c_channel)
                console.log(f"Got log channel: {c_channel.name} in {c_channel.guild.name}")
    console.log("--- We're ready to go. ---", style="green")


@bot.event
async def on_error(error, *args, **kwargs):
    console.log(traceback.Traceback())


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if type(error) == MissingRequiredArgument:
        error: MissingRequiredArgument
        message = "You're missing a required parameter.\n"
        message += f"Run `>help {ctx.command.name}` for more details on command usage.\n\n"
        message += "More information:\n"
        message += f"Parameter: `{error.param}`\n"
        message += f"Raw error: `{error}`"
        await ctx.send(message)
    else:
        message = "An error occurred.\n"
        message += f"Run `>help` for instructions.\n\n"
        message += "More information:\n"
        message += f"Error type: `{type(error)}`\n"
        message += f"Raw error: `{error}`"
        await ctx.send(message)


@bot.check(db_access)
@bot.command()
async def kill(ctx: commands.Context):
    await ctx.send(":pensive::gun:")
    await bot.change_presence(status=Status.offline)
    await bot.logout()


@bot.check(db_access)
@bot.command()
async def edit(ctx: commands.Context, game_number: int, category: str, attribute_num: int, *, text: str):
    with JsonFile(database_location) as games:
        if not 1 <= game_number <= len(games):  # If 2 games, be between 1 and 2 incl.
            raise BadArgument(f"game_number must be between 1 and {len(games)} inclusive.")
        if category not in ["functional", "broken", "crashes", "recommendedsettings", "notes"]:
            raise BadArgument('category must be one of ["functional","broken","crashes","recommendedsettings","notes"]')
        if not 1 <= attribute_num <= len(games[game_number-1][category])+1:  # if 3 attributes, must be between 1 and 4
            raise BadArgument(f"attribute_num must be between 1 and {len(games[game_number-1][category])+1} inclusive.")
            # TODO Show present attributes and a +1 for add new one.
        if not text:
            raise BadArgument("text is a required parameter. If you intended to delete the attribute, use \"delete\".")
        if attribute_num == len(games[game_number-1][category])+1 and text == "delete":
            raise BadArgument("You cannot simultaneously create and delete an attribute.")
        # Add attrib
        if attribute_num == len(games[game_number-1][category])+1:
            games[game_number-1][category].append(text)
            log(f"```diff\nAttribute added in {games[game_number-1]['name']}:\n+ {text}")
        # Remove attrib
        elif text.lower() == "delete":
            oldtext = games[game_number-1][category][attribute_num-1]
            games[game_number-1][category].pop(attribute_num-1)
            log(f"```diff\nAttribute removed in {games[game_number-1]['name']}:\n- {oldtext}")
        # Update attrib
        else:
            oldtext = games[game_number-1][category][attribute_num-1]
            games[game_number-1][category][attribute_num-1] = text
            log(f"```diff\nAttribute updated in {games[game_number-1]['name']}:\n- {oldtext}\n+ {text}")


async def log(message: str):
    for x in log_channels:
        await x.send(message)


@bot.check(db_access)
@bot.command()
async def add_game(ctx: commands.Context, gamename: str):
    with JsonFile(database_location) as games:
        games.append({
            "name": gamename,
            "functional": [],
            "broken": [],
            "crashes": [],
            "recommendedsettings": [],
            "notes": [],
        })
    console.log(f"Added game {gamename}", style="blue")
    log(f"```diff\nAdded game:\n+{gamename}")
    await sync(ctx)

# Checks the channels and makes any needed adjustments.


@commands.max_concurrency(1, per=BucketType.default)
@commands.check(db_access)
@bot.command(brief="Updates all compatibility lists, trying to do the least work.",
             help=multiline("""
    Validates the list of games in every server, and updates them accordingly.
    If non-bot messages are present, deletes them and reprimands the author via DM.
    (reprimands can be disabled by adding <yuzu-compat: noreprimand> to the channel topic.)
    If more messages then games are present, deletes the extras.
    If less are present, sends placeholders.
    Then, it goes through the list and edits the messages so they match up with game order. 
    
    If somebody messages while a sync is taking place, things will break.
    In that case, the bot will do a fallback hardsync. Don't do it. It sucks. It's slow.
    """))
async def sync(ctx: commands.Context):
    with JsonFile(database_location) as games:
        # Sort the list of games
        games: list
        games.sort(key=lambda game: game["name"])
        # console.log(games)
    with JsonFile(database_location, "r") as games:
        for channel in list_channels:
            with channel.typing() as _:
                console.log(f"Syncing <{channel.name}> in <{channel.guild.name}>.", style="green")
                # Get a list of all messages in chron. order.
                messages = await channel.history(oldest_first=True, limit=None).flatten()
                # Check through the messages and make sure that they are mine, delete otherwise
                # <
                authors_reprimanded = []
                messages_to_delete = []
                for message in messages:
                    message: discord.Message
                    if message.author != bot.user:
                        # If message is someone else's, reprimand them.
                        if "<yuzu-compat: noreprimand>" not in message.channel.topic and message.author not in authors_reprimanded:
                            await message.author.send(
                                f"Please don't send messages in `#{message.channel.name}` in `{message.channel.guild.name}`. It'll break things.")
                            # Don't spam the user, add them to the exempt list temporarily.
                            authors_reprimanded.append(message.author)
                        # Don't delete the message now, as it'll mess up ordering.
                        messages_to_delete.append(message)
                del(authors_reprimanded)  # We don't need this anymore, and it'll be in scope for a while. idk
                # >
                # Delete the above found messages, and re-get a new list. Assume no messages in this time, and then check if len(messages) = len(games)
                # <
                for message in messages_to_delete:
                    await message.delete()
                messages = await channel.history(oldest_first=True, limit=None).flatten()
                messages = [x for x in messages if x.author == bot.user]
                # If there are more messages than games, delete the last X messages, evening them out.
                if len(messages) > len(games):
                    for _ in range(len(messages) - len(games)):
                        await messages.pop().delete()
                # If there are more, send placeholder messages.
                if len(messages) < len(games):
                    for _ in range(len(games) - len(messages)):
                        messages.append(await channel.send(
                            "```diff\n- Placeholder. Please hold. If this persists for 2 minutes, ping typecasto#0517.\n```"))
                # Just to be sure, let's make sure the lengths are equal.
                if len(messages) != len(games):
                    repair(ctx, channel)

                for num, message in enumerate(messages):
                    game_message = convert_game_dict_to_message(games[num], num+1)
                    if message.content != game_message:
                        await message.edit(content=game_message)

                print(len(messages))


@bot.command()
async def test(ctx: commands.Context):
    with JsonFile(database_location, "r") as games:
        for i, x in enumerate(games):
            await ctx.send(convert_game_dict_to_message(x, i))


@commands.check(db_access)
@bot.command()
async def repair(ctx: commands.Context, channel: discord.TextChannel):
    if "<yuzu-compat: list>" not in channel.topic:
        ctx.send("Failed. Channel is not a valid list channel.")
        return
    console.log(f"Repairing <{channel.name}> in <{channel.guild.name}>.", style="red bold")
    messages = await channel.history(oldest_first=True, limit=None).flatten()
    with channel.typing() as _:
        while messages:
            await messages.pop().delete()
        with JsonFile(database_location, "r") as games:
            for num, game in enumerate(games):
                game_message = convert_game_dict_to_message(game, num+1)
                await channel.send(game_message)


@bot.check
def only_run_author(ctx: commands.Context):
    return ctx.author.id == 134509976956829697


# Extract the token from the file, trim a trailing newline, and start the bot.
token = ""
with open("token", "r") as file:
    token = file.read()
token.removesuffix("\n")
bot.run(token)