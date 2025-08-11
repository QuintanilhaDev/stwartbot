import discord
from discord import app_commands, ui
from discord.ext import commands
from modules.utils import create_embed

# Modal para coletar o motivo da punição
class PunishmentModal(ui.Modal, title="Formulário de Punição"):
    reason = ui.TextInput(label="Motivo", style=discord.TextStyle.paragraph, placeholder="Descreva o motivo da punição.", required=True, max_length=500)

    def __init__(self, target: discord.Member, action: str):
        super().__init__()
        self.target = target
        self.action = action.lower()

    async def on_submit(self, interaction: discord.Interaction):
        try:
            action_text = ""
            if self.action == "ban":
                await self.target.ban(reason=self.reason.value)
                action_text = "banido(a)"
            elif self.action == "kick":
                await self.target.kick(reason=self.reason.value)
                action_text = "expulso(a)"
            
            embed = create_embed(
                f"✅ Ação Concluída: {self.target.display_name} foi {action_text}",
                f"**Moderador:** {interaction.user.mention}\n**Motivo:** {self.reason.value}",
                discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message(embed=create_embed("❌ Erro de Permissão", f"Eu não tenho permissão para punir {self.target.mention}.", discord.Color.red()), ephemeral=True)
        except Exception as e:
            # Erros inesperados são capturados pelo tratador global em main.py
            raise e

class Moderation(commands.Cog):
    """Comandos para ajudar na moderação do servidor."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def can_moderate(self, interaction: discord.Interaction, member: discord.Member) -> tuple[bool, str]:
        """Verifica se o moderador pode punir o membro."""
        if member.id == interaction.user.id:
            return False, "Você não pode punir a si mesmo."
        if member.id == self.bot.user.id:
            return False, "Eu não posso me punir."
        if member.guild.owner == member:
            return False, "Você não pode punir o dono do servidor."
        if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
             return False, "Você não pode punir um membro com cargo igual ou superior ao seu."
        return True, ""

    @app_commands.command(name="ban", description="Bane um membro do servidor.")
    @app_commands.describe(member="O membro a ser banido.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member):
        can_act, reason = self.can_moderate(interaction, member)
        if not can_act:
            return await interaction.response.send_message(embed=create_embed("🚫 Ação Inválida", reason, discord.Color.orange()), ephemeral=True)

        modal = PunishmentModal(target=member, action="ban")
        await interaction.response.send_modal(modal)

    @app_commands.command(name="kick", description="Expulsa um membro do servidor.")
    @app_commands.describe(member="O membro a ser expulso.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member):
        can_act, reason = self.can_moderate(interaction, member)
        if not can_act:
            return await interaction.response.send_message(embed=create_embed("🚫 Ação Inválida", reason, discord.Color.orange()), ephemeral=True)
        
        modal = PunishmentModal(target=member, action="kick")
        await interaction.response.send_modal(modal)

    @app_commands.command(name="clear", description="Apaga uma quantidade de mensagens de um canal.")
    @app_commands.describe(quantidade="O número de mensagens a serem apagadas (entre 1 e 100).")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        deleted = await interaction.channel.purge(limit=quantidade)
        
        embed = create_embed(
            "🧹 Mensagens Apagadas",
            f"**{len(deleted)}** mensagens foram apagadas com sucesso neste canal.",
            discord.Color.green(),
            author=interaction.user
        )
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))