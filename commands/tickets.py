from discord.ext import commands
import discord
import asyncio

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ticket(self, ctx):
        guild = ctx.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")
        ticket_channel = await guild.create_text_channel(f"ticket-{ctx.author.name}", overwrites=overwrites, category=category)
        await ticket_channel.send(f"Hello {ctx.author.mention}, staff will be with you shortly. Type `!close` to close this ticket.")
        await ctx.send("🎟️ Ticket created! Check the channel in Tickets category.")

    @commands.command()
    async def close(self, ctx):
        if "ticket" in ctx.channel.name:
            await ctx.send("🔒 Ticket will be closed in 5 seconds...")
            await asyncio.sleep(5)
            await ctx.channel.delete()

def setup(bot):
    bot.add_cog(Tickets(bot))
