import discord
from discord import app_commands
from discord.ext import commands
from modules.utils import create_embed

class Engagement(commands.Cog):
    """Comandos para aumentar a interação no servidor."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="enquete", description="Cria uma enquete simples com reações.")
    @app_commands.describe(
        titulo="O título ou a pergunta da sua enquete.",
        opcoes="As opções da enquete, separadas por vírgula (ex: Sim, Não, Talvez)."
    )
    async def enquete(self, interaction: discord.Interaction, titulo: str, opcoes: str):
        # Separa as opções e remove espaços extras no início/fim de cada uma
        opcoes_lista = [opt.strip() for opt in opcoes.split(',')]
        
        if len(opcoes_lista) < 2 or len(opcoes_lista) > 10:
            embed = create_embed("❌ Erro na Enquete", "Você precisa fornecer entre 2 e 10 opções.", discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
        # Emojis numéricos para as opções, do 1 ao 10
        emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        description = []
        for i, opt in enumerate(opcoes_lista):
            description.append(f"{emojis[i]} **{opt}**")
            
        embed = create_embed(f"📊 Enquete: {titulo}", "\n\n".join(description), author=interaction.user)
        
        # Envia a mensagem da enquete
        await interaction.response.send_message(embed=embed)
        # Pega o objeto da mensagem que acabamos de enviar para poder adicionar as reações
        message = await interaction.original_response()
        
        # Adiciona as reações correspondentes a cada opção na mensagem
        for i in range(len(opcoes_lista)):
            await message.add_reaction(emojis[i])

async def setup(bot):
    await bot.add_cog(Engagement(bot))