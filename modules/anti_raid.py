import discord
import logging
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from collections import defaultdict
from modules.utils import create_embed
from config.settings import (
    RAID_JOIN_THRESHOLD,
    RAID_TIME_WINDOW,
    MIN_ACCOUNT_AGE_DAYS,
    WHITELIST
)

class AntiRaid(commands.Cog):
    """Sistema de proteção contra raids de contas novas e entradas em massa."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.join_times = defaultdict(list)
        self.lockdown_active = defaultdict(bool)
        # Dicionário para guardar as permissões originais do canal durante o lockdown
        self.original_permissions = defaultdict(dict)
        self.raid_monitor.start()

    def cog_unload(self):
        self.raid_monitor.cancel()

    @tasks.loop(seconds=RAID_TIME_WINDOW)
    async def raid_monitor(self):
        now = datetime.utcnow()
        for guild in self.bot.guilds:
            if not self.bot.get_guild(guild.id): continue # Ignora se o bot não está mais no servidor
            
            # Limpa os timestamps de entrada antigos
            self.join_times[guild.id] = [
                t for t in self.join_times[guild.id]
                if (now - t) < timedelta(seconds=RAID_TIME_WINDOW)
            ]
            
            # Verifica se um raid está acontecendo e ativa o lockdown se necessário
            if len(self.join_times[guild.id]) >= RAID_JOIN_THRESHOLD and not self.lockdown_active[guild.id]:
                await self.activate_lockdown(guild)

    @raid_monitor.before_loop
    async def before_raid_monitor(self):
        await self.bot.wait_until_ready()

    async def activate_lockdown(self, guild: discord.Guild, manual_author: discord.User = None):
        """Ativa o modo de lockdown no servidor."""
        self.lockdown_active[guild.id] = True
        log_reason = f"RAID DETECTADO AUTOMATICAMENTE" if not manual_author else f"Lockdown ativado manualmente por {manual_author}"
        logging.critical(f"🚨 {log_reason} NO SERVIDOR '{guild.name}'!")

        for channel in guild.text_channels:
            try:
                # Salva as permissões atuais antes de alterá-las
                self.original_permissions[guild.id][channel.id] = channel.overwrites_for(guild.default_role)
                overwrite = discord.PermissionOverwrite(send_messages=False)
                await channel.set_permissions(guild.default_role, overwrite=overwrite, reason=log_reason)
            except discord.Forbidden:
                logging.error(f"Anti-Raid: Sem permissão para alterar permissões no canal #{channel.name} em '{guild.name}'.")
            except Exception as e:
                logging.error(f"Anti-Raid: Erro ao bloquear o canal #{channel.name}:", exc_info=e)

    async def deactivate_lockdown(self, guild: discord.Guild, manual_author: discord.User = None):
        """Desativa o modo de lockdown no servidor."""
        if not self.lockdown_active[guild.id]: return

        self.lockdown_active[guild.id] = False
        log_reason = f"Lockdown desativado manualmente por {manual_author}" if manual_author else "Lockdown desativado"
        logging.info(f"🔓 {log_reason} no servidor '{guild.name}'.")

        for channel_id, original_overwrite in self.original_permissions[guild.id].items():
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.set_permissions(guild.default_role, overwrite=original_overwrite, reason=log_reason)
                except discord.Forbidden:
                     logging.error(f"Anti-Raid: Sem permissão para restaurar permissões no canal #{channel.name} em '{guild.name}'.")
                except Exception as e:
                    logging.error(f"Anti-Raid: Erro ao restaurar o canal #{channel.name}:", exc_info=e)
        
        self.original_permissions[guild.id].clear()


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot or member.id in WHITELIST:
            return

        account_age = discord.utils.utcnow() - member.created_at
        if account_age < timedelta(days=MIN_ACCOUNT_AGE_DAYS):
            try:
                await member.ban(reason=f"Conta muito nova (criada há menos de {MIN_ACCOUNT_AGE_DAYS} dias)")
                logging.warning(f"🚫 Anti-Raid: Membro {member} banido automaticamente por conta nova em '{member.guild.name}'.")
            except discord.Forbidden:
                logging.error(f"Anti-Raid: Sem permissão para banir {member} por conta nova em '{member.guild.name}'.")

        self.join_times[member.guild.id].append(discord.utils.utcnow())
    
    # --- Grupo de Comandos para Lockdown ---
    lockdown = app_commands.Group(name="lockdown", description="Gerencia o modo de lockdown do servidor.", default_permissions=discord.Permissions(manage_guild=True))

    @lockdown.command(name="on", description="Ativa o lockdown manualmente, bloqueando o envio de mensagens.")
    async def lockdown_on(self, interaction: discord.Interaction):
        if self.lockdown_active[interaction.guild.id]:
            return await interaction.response.send_message(embed=create_embed("⚠️ Atenção", "O lockdown já está ativo.", discord.Color.orange()), ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        await self.activate_lockdown(interaction.guild, manual_author=interaction.user)
        await interaction.followup.send(embed=create_embed("🔒 Lockdown Ativado", "O envio de mensagens foi bloqueado para membros comuns em todos os canais de texto.", discord.Color.red()))

    @lockdown.command(name="off", description="Desativa o lockdown manualmente, restaurando as permissões.")
    async def lockdown_off(self, interaction: discord.Interaction):
        if not self.lockdown_active[interaction.guild.id]:
            return await interaction.response.send_message(embed=create_embed("⚠️ Atenção", "O lockdown não está ativo.", discord.Color.orange()), ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        await self.deactivate_lockdown(interaction.guild, manual_author=interaction.user)
        await interaction.followup.send(embed=create_embed("🔓 Lockdown Desativado", "As permissões dos canais foram restauradas.", discord.Color.green()))

    @app_commands.command(name="raidstatus", description="Mostra o status do sistema anti-raid.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def raidstatus(self, interaction: discord.Interaction):
        guild = interaction.guild
        recent_joins = len([t for t in self.join_times[guild.id] if (discord.utils.utcnow() - t) < timedelta(seconds=RAID_TIME_WINDOW)])
        is_lockdown = self.lockdown_active[guild.id]

        embed = create_embed("🛡️ Status do Sistema Anti-Raid", color=discord.Color.blue())
        embed.add_field(name="Lockdown Ativo?", value=f"`{'Sim' if is_lockdown else 'Não'}`", inline=True)
        embed.add_field(name="Entradas Recentes", value=f"`{recent_joins} / {RAID_JOIN_THRESHOLD}`", inline=True)
        embed.set_footer(text=f"Janela de tempo: {RAID_TIME_WINDOW} segundos")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AntiRaid(bot))