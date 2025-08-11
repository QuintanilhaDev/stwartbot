import discord
from discord.ext import commands

class LogsSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        embed = discord.Embed(
            title="🗑️ Mensagem apagada",
            description=f"**Autor:** {message.author.mention}\n**Canal:** {message.channel.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="Conteúdo", value=message.content or "Mensagem sem texto")
        embed.set_footer(text=f"ID do autor: {message.author.id}")
        embed.timestamp = message.created_at

        log_channel = discord.utils.get(message.guild.text_channels, name="logs")
        if log_channel:
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        embed = discord.Embed(
            title="📨 Convite criado",
            description=f"**Criador:** {invite.inviter.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Link", value=invite.url)
        embed.set_footer(text=f"ID: {invite.inviter.id}")
        embed.timestamp = invite.created_at

        log_channel = discord.utils.get(invite.guild.text_channels, name="logs")
        if log_channel:
            await log_channel.send(embed=embed)

# ESTA FUNÇÃO É ESSENCIAL
async def setup(bot):
    await bot.add_cog(LogsSystem(bot))
