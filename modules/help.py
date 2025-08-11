import discord
from discord import app_commands
from discord.ext import commands
from modules.utils import create_embed

class Help(commands.Cog):
    """O comando de ajuda interativo do bot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Mostra todos os comandos disponíveis em uma interface interativa.")
    async def help(self, interaction: discord.Interaction):
        initial_embed = create_embed(
            f"Eu sou o {self.bot.user.name}",
            "Sou um bot multifuncional projetado para a BELLICS.\n\n"
            "Use o menu de seleção abaixo para navegar pelas categorias e descobrir tudo o que eu posso fazer!",
            author=interaction.user
        )
        if self.bot.user.avatar:
            initial_embed.set_thumbnail(url=self.bot.user.avatar.url)

        await interaction.response.send_message(embed=initial_embed, view=HelpView(self.bot), ephemeral=True)

class HelpView(discord.ui.View):
    """A View que contém o menu de seleção (dropdown)."""
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=180)
        self.add_item(HelpDropdown(bot))

class HelpDropdown(discord.ui.Select):
    """O componente de menu de seleção (dropdown) dinâmico."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        options = [
            discord.SelectOption(label="Início", description="Voltar para a página principal.", emoji="🏠")
        ]
        
        for cog_name, cog in bot.cogs.items():
            if cog_name in ["Help"] or not cog.get_app_commands():
                continue
            
            options.append(discord.SelectOption(
                label=cog_name,
                description=cog.description if cog.description else f"Comandos da categoria {cog_name}"
            ))

        super().__init__(placeholder="Selecione uma categoria para explorar...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        """Este método é chamado quando o usuário seleciona uma opção."""
        
        selected_cog_name = self.values[0]

        if selected_cog_name == "Início":
            initial_embed = create_embed(
                f"Eu sou o {self.bot.user.name}",
                "Use o menu de seleção abaixo para navegar pelas categorias.",
                author=interaction.user
            )
            if self.bot.user.avatar:
                initial_embed.set_thumbnail(url=self.bot.user.avatar.url)
            await interaction.response.edit_message(embed=initial_embed)
            return

        cog = self.bot.get_cog(selected_cog_name)
        if not cog:
            return await interaction.response.send_message("Categoria não encontrada.", ephemeral=True)
            
        commands_list = []
        # --- CORREÇÃO APLICADA AQUI ---
        for command in cog.get_app_commands():
            if isinstance(command, app_commands.Group):
                # Formata os subcomandos de um grupo (ex: /lockdown on)
                subcommands = " | ".join([f"`/{command.name} {sub.name}`" for sub in command.commands])
                commands_list.append(f"**{subcommands}**: *{command.description}*")
            else:
                # Formata um comando normal (ex: /play)
                commands_list.append(f"`/{command.name}`: *{command.description}*")
            
        description = "\n".join(commands_list)
        
        embed = create_embed(
            f"Comandos de {selected_cog_name}",
            description if description else "Nenhum comando encontrado nesta categoria.",
            author=interaction.user
        )

        await interaction.response.edit_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))