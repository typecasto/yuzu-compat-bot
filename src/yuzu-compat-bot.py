import json
# from typing import Optional
from discord.enums import Status
from discord.ext import commands
import discord
from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands.errors import BadArgument, CheckFailure, CommandNotFound
from discord.ext.commands.errors import MissingRequiredArgument, NotOwner, TooManyArguments
from rich import traceback
from rich.console import Console
from inspect import cleandoc as multiline
from binascii import Error as BinAsciiError
import base64

console = Console()
# traceback.install(console=console, extra_lines=5, word_wrap=True, show_locals=True)
database_location = "games.json"

bot = commands.Bot(command_prefix=">")
list_channels: list[discord.TextChannel] = []
log_channels: list[discord.TextChannel] = []
db_lock: bool = False  # To prevent the funny race conditions from ocurring.


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

    message = "```markdown\n"
    message += f"[{number:03}]: {game['name']}\n"
    message += f"\n"
    message += f"# Functional\n"
    message += f"{functional}\n"
    message += f"# Broken\n"
    message += f"{broken}\n"
    message += f"# Crashes\n"
    message += f"{crashes}\n"
    message += f"# Recommended Settings\n"
    message += f"{settings}\n"
    message += f"# Notes\n"
    message += f"{notes}"
    message += f"```"
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


def valid_user_check(ctx: commands.Context):
    return ctx.author.id == 134509976956829697 or 809853472316981279 in [x.id for x in ctx.author.roles]  # Shoot me a DM, why not?


async def log(message: str):
    # TODO GLOBAL: Fix logging so that it logs who made what change.
    for x in log_channels:
        await x.send(message)


@bot.event
async def on_ready():
    # Empty the channels here, so that on dropped connection we don't dupe logs and do extra work on sync events
    list_channels.clear()
    log_channels.clear()
    # Add each channel to the list of list/log channels
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
    elif type(error) == TooManyArguments:
        error: TooManyArguments
        message = "You've got too many arguments.\n"
        message += f"Run `>help {ctx.command.name}` for more details on command usage.\n\n"
        message += "More information:\n"
        message += f"Raw error: `{error}`"
        await ctx.send(message)
    elif type(error) == NotOwner:
        error: NotOwner
        message = "That command is only available for @typecasto#0517.\n"
        message += f"Run `>help {ctx.command.name}` for more details on command usage.\n\n"
        message += "More information:\n"
        message += f"Raw error: `{error}`"
        await ctx.send(message)
    elif type(error) == CommandNotFound:
        await ctx.message.add_reaction("❓")
    elif type(error) == BadArgument:
        error: BadArgument
        message = "One of your arguments was incorrect.\n"
        message += f"Run `>help {ctx.command.name}` for more details on command usage.\n\n"
        message += "More information:\n"
        message += f"Raw error: `{error}`"
        await ctx.send(message)
    elif type(error) == CheckFailure:
        error: CheckFailure
        message = "Either the database is in use, or you don't have access to this command.\n"
        message += f"Run `>help` to see which commands you can use.\n\n"
        message += "More information:\n"
        message += f"Raw error: `{error}`"
        await ctx.send(message)
    else:
        message = "An error occurred.\n"
        message += f"Run `>help` for instructions.\n\n"
        message += "More information:\n"
        message += f"Error type: `{type(error)}`\n"
        message += f"Raw error: `{error}`"
        await ctx.send(message)
        message += f"\nhttp://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}\n"
        message += f"Original message by {ctx.author}:\n"
        message += ctx.message.content
        owner = await bot.fetch_user(bot.owner_id)
        await owner.send(message)
        # console.log(user)


############################
#         COMMANDS         #
############################

@bot.command(brief="Decodes base64",
             aliases=["d"],
             help=multiline("""
    Decodes a base64 encoded string.
    Fairly simple, may be improved in the future with new features.
    """))
async def decode(ctx: commands.Context, *, code: str):
    try:
        while len(code) % 4 != 0:  # Fine, I'll do it myself.
            code += "="
        await ctx.author.send(f"Decoded text: {str(base64.b64decode(code, validate=True), encoding='utf8')}")  # the slice is to remove the b''
        await ctx.send("Done, check your dms.")
    except BinAsciiError:
        await ctx.send("Not a valid base64 encoded string.")


@bot.command(brief="Encodes base64",
             aliases=["e"],
             help=multiline("""
    Encodes a string into base64.
    This command deletes the message that invoked it.

    Fairly simple, may be improved in the future with new features.
    """))
async def encode(ctx: commands.Context, *, text: str):
    try:
        await ctx.send(f"<@{ctx.author.id}>: {str(base64.b64encode(bytes(text, encoding='utf8')))[2:-1]}")  # again, slice to remove b''
    finally:  # not sure if this is the right place to use a finally, but it seems right?
        await ctx.message.delete()


@commands.check(db_access)
@commands.is_owner()
@bot.command(brief="what a shame",
             help=multiline("""
    what a shame, he was a good man

    what a rotten way to die
    """))
async def kill(ctx: commands.Context):
    await ctx.send(":pensive::gun:")
    await bot.change_presence(status=Status.offline)
    console.log("Goodbye, world", style="red")
    await bot.logout()


@commands.is_owner()
@bot.command(name="eval",
             brief="oh god",
             help=multiline("""
    oh fuck,
    oh jeez,
    oh god oh fuck,
    oh no oh fuck oh godf ohg od o h fuck
    """))
async def eval_stuff(ctx: commands.Context, *, code: str):
    try:
        return_message = str(eval(code))
    except Exception as e:
        return_message = str(e)
    ctx.send(return_message)


@commands.check(valid_user_check)
@commands.check(db_access)
@bot.command(brief="Adds, edits, or deletes attributes",
             help=multiline("""
    Edits the attributes of a game.

    <game_number> is the number of the game, as shown in the list channel.
    <category> must be "functional", "broken", "crashes", "recommendedsettings", or "notes".
    <attribute_num> is the number next to the attribute you want to edit.
        To add an attribute, use the number one higher than the highest one.
        If there are no attributes, use 1.
    <text> is the text you want the attribute to be set to, or "delete" to remove the attribute.

    This action is logged.
    """))
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
            await log(f"```diff\nAttribute in \"{category}\" added for {games[game_number-1]['name']}:\n+ {text}\n@{ctx.author}\n```")
        # Remove attrib
        elif text.lower() == "delete":
            oldtext = games[game_number-1][category][attribute_num-1]
            games[game_number-1][category].pop(attribute_num-1)
            await log(f"```diff\nAttribute in \"{category}\" removed for {games[game_number-1]['name']}:\n- {oldtext}\n@{ctx.author}\n```")
        # Update attrib
        else:
            oldtext = games[game_number-1][category][attribute_num-1]
            games[game_number-1][category][attribute_num-1] = text
            await log(f"```diff\nAttribute in \"{category}\" updated for {games[game_number-1]['name']}:\n- {oldtext}\n+ {text}\n@{ctx.author}\n```")
    console.log(f"Attribute modified: [green]{category}:{attribute_num}[/green] for [green]{games[game_number-1]['name']}[/green].", style="blue")
    await sync(ctx)
    await ctx.message.add_reaction("👍")


@commands.check(valid_user_check)
@commands.check(db_access)
@bot.command(brief="Renames a game",
             help=multiline("""
    Renames a game, pretty simple. Use the ID number in the compatability list.

    This action is logged.
    """))
async def rename(ctx: commands.Context, game_number: int, *, new_name: str):
    with JsonFile(database_location) as games:
        if not 1 <= game_number <= len(games):  # If 2 games, be between 1 and 2 incl.
            raise BadArgument(f"game_number must be between 1 and {len(games)} inclusive.")
        if not new_name:
            raise BadArgument("new_name is a required parameter.")
        else:
            oldtext = games[game_number-1]["name"]
            games[game_number-1]["name"] = new_name
            await log(f"```diff\nRenamed game:\n- {oldtext}\n+ {new_name}\n@{ctx.author}\n```")
    await sync(ctx)
    await ctx.message.add_reaction("👍")


@commands.check(valid_user_check)
@commands.check(db_access)
@bot.command(brief="Adds a blank game to the list",
             help=multiline("""
    Creates a game named <gamename> and adds it to the list (and then syncs the list).
    To add attributes, use >edit. 
    
    This action is logged.
    """))
async def add_game(ctx: commands.Context, *, gamename: str):
    new_game = {
        "name": gamename,
        "functional": [],
        "broken": [],
        "crashes": [],
        "recommendedsettings": [],
        "notes": [],
    }
    with JsonFile(database_location) as games:
        games.append(new_game)
    console.log(f"Added game [green]{gamename}[/green]", style="blue")
    await log(f"```diff\nAdded game:\n+{gamename}\n@{ctx.author}\n```")
    await sync(ctx)
    with JsonFile(database_location) as games:
        await ctx.send(f"Added game {games.index(new_game)+1}.")


@bot.command(brief="Removes bot DMs",
             help=multiline("""
    This will delete any DMs from the bot to you.
    This is mostly here for testing, but there's no reason not to keep it around. 
    You shouldn't get any DMs from the bot, unless you're posting in the wrong channels, but either way.
    """))
async def clear_dm(ctx: commands.Context):
    messages = await ctx.author.create_dm()
    messages = await messages.history(limit=None).flatten()
    for x in messages:
        x: discord.Message
        if x.author == bot.user:
            await x.delete()
    await ctx.message.add_reaction("👍")


@commands.max_concurrency(1, per=BucketType.default)
@commands.check(valid_user_check)
@commands.check(db_access)
@bot.command(brief="Updates all compatibility lists, trying to do the least work",
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
        games.sort(key=lambda game: game["name"].casefold())
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
                    return

                for num, message in enumerate(messages):
                    game_message = convert_game_dict_to_message(games[num], num+1)
                    if message.content != game_message:
                        await message.edit(content=game_message)
    console.log("Done.", style="green")


@commands.check(valid_user_check)
@commands.check(db_access)
@bot.command(brief="Fully destroys the list in a given channel and remakes it",
             help=multiline(f"""
    Deletes every message in <channel> and recreates the list completely.
    Depending on the number of games, this can be time consuming.
    Avoid using this command unless the list of games is completely borked.
    Use >sync instead.

    Can also be used to add a new list channel, since we don't check for those after the bot is started.
    """))
async def repair(ctx: commands.Context, channel: discord.TextChannel):
    if "<yuzu-compat: list>" not in channel.topic:
        raise BadArgument(f"{channel} is not a valid list channel.")
    elif channel not in list_channels:
        list_channels.append(channel)
    console.log(f"Repairing <{channel.name}> in <{channel.guild.name}>.", style="red bold")
    messages = await channel.history(oldest_first=True, limit=None).flatten()
    with channel.typing() as _:
        while messages:
            await messages.pop().delete()
        with JsonFile(database_location, "r") as games:
            for num, game in enumerate(games):
                game_message = convert_game_dict_to_message(game, num+1)
                await channel.send(game_message)


@commands.check(db_access)
@commands.is_owner()
@bot.command(brief="Sends a copy of games.json to the current channel")
async def backup(ctx: commands.Context):
    jsonfile = discord.File("games.json", "games.json")
    await ctx.send(file=jsonfile)


# @bot.check
# def bot_commands_channel_only(ctx: commands.Context):
#     return (type(ctx.channel) == discord.DMChannel) or (len(ctx.channel.topic) > 1 and "<yuzu-compat: commands>" in ctx.channel.topic)


# Extract the token from the file, trim a trailing newline, and get this shit rolling.
token = ""
with open("token", "r") as file:
    token = file.read()
token.removesuffix("\n")
bot.owner_id = 134509976956829697
bot.run(token)
