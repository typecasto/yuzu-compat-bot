from discord.ext import commands
import base64
from inspect import cleandoc as multiline


class Base64(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(brief="Decodes base64",
             aliases=["d"],
             help="Decodes a base64 string and sends it to the author")
    async def decode(ctx: commands.Context, *, code: str):
        try:
            # If the string isn't a multiple of 4, pad it with '='
            while len(code) % 4 != 0: 
                code += "="
            
            # Decode the base64 string
            await ctx.author.send(f"Decoded text: {str(base64.b64decode(code, validate=True), encoding='utf8')}")

            # Send a conformation message
            await ctx.send("Done, check your dms.")
        except Exception:
            await ctx.send("Not a valid base64 encoded string.")

    @commands.command(brief="Encodes base64",
                aliases=["e"],
                help=multiline("""
        Encodes a string into base64.
        This command deletes the message that invoked it.
        """))
    async def encode(ctx: commands.Context, *, text: str):
        try:
            # Encode the string, add the author's name, and send it, removing the b'' enfix.
            await ctx.send(f"<@{ctx.author.id}>: {str(base64.b64encode(bytes(text, encoding='utf8')))[2:-1]}")  # again, slice to remove b''
        finally:
            # Delete the message that invoked the command, no matter if failure or success.
            await ctx.message.delete()


def setup(bot):
    bot.add_cog(Base64(bot))