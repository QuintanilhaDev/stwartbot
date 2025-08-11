import discord
import time
from discord import app_commands
from discord.ext import commands
from modules.utils import create_embed

class Info(commands.Cog):
    """Comandos para obter informações do servidor e de usuários."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="ping", description="Verifica a latência e o tempo de atividade do bot.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        uptime_seconds = time.time() - self.start_time
        
        days, rem = divmod(uptime_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        
        uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

        embed = create_embed("🏓 Pong!", color=discord.Color.green())
        embed.add_field(name="Latência da API", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="Tempo de Atividade", value=f"`{uptime_str}`", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="userinfo", description="Mostra informações detalhadas sobre um membro.")
    @app_commands.describe(member="O membro sobre o qual você quer informações (padrão: você mesmo).")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user

        embed = create_embed(f"Informações de {target.display_name}", color=target.color)
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)

        embed.add_field(name="📝 Nome de Usuário", value=f"`{target.name}`", inline=True)
        embed.add_field(name="🆔 ID", value=f"`{target.id}`", inline=True)
        
        created_at_str = f"<t:{int(target.created_at.timestamp())}:f>"
        joined_at_str = f"<t:{int(target.joined_at.timestamp())}:f>"
        embed.add_field(name="📅 Conta Criada em", value=created_at_str, inline=False)
        embed.add_field(name="➡️ Entrou no Servidor em", value=joined_at_str, inline=False)
        
        roles = [role.mention for role in reversed(target.roles) if role.name != "@everyone"]
        
        roles_str = ", ".join(roles) if roles else "Nenhum cargo específico."
        embed.add_field(name=f"🎭 Cargos [{len(roles)}]", value=roles_str, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Mostra informações detalhadas sobre o servidor.")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild

        embed = create_embed(f"Informações do Servidor: {guild.name}")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="👑 Dono(a)", value=guild.owner.mention, inline=True)
        embed.add_field(name="🆔 ID do Servidor", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="📅 Criado em", value=f"<t:{int(guild.created_at.timestamp())}:f>", inline=False)
        
        member_count = guild.member_count
        bot_count = sum(1 for member in guild.members if member.bot)
        human_count = member_count - bot_count
        embed.add_field(name="👥 Membros", value=f"**Total:** {member_count}\n**Humanos:** {human_count}\n**Bots:** {bot_count}", inline=True)
        
        channel_count = len(guild.channels)
        text_count = len(guild.text_channels)
        voice_count = len(guild.voice_channels)
        embed.add_field(name="💬 Canais", value=f"**Total:** {channel_count}\n**Texto:** {text_count}\n**Voz:** {voice_count}", inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Info(bot))