import os
import sys
import asyncio
import discord
import logging
from pathlib import Path
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from modules.utils import setup_logging, create_embed

# Configura o caminho e carrega variáveis de ambiente
sys.path.append(str(Path(__file__).parent))
load_dotenv()

# Validação do Token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("❌ O token do Discord não foi encontrado no arquivo .env")

# Configuração do Bot com as intents necessárias
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Lista de módulos (Cogs) a serem carregados
COGS_TO_LOAD = [
    "modules.music",
    "modules.moderation",
    "modules.anti_spam",
    "modules.anti_raid",
    "modules.god_eye",
    "modules.logs_system",
    "modules.info",
    "modules.engagement",
    "modules.help"
]

@bot.event
async def on_ready():
    """Evento chamado quando o bot está online e pronto."""
    logging.info(f"✅ Bot conectado como {bot.user}")
    logging.info(f"✅ Sincronizando comandos com a API do Discord...")
    try:
        synced = await bot.tree.sync()
        logging.info(f"✅ Sincronizados {len(synced)} comandos.")
    except Exception as e:
        logging.error(f"❌ Falha ao sincronizar comandos: {e}")

async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Tratador de erros global para todos os slash commands."""
    if isinstance(error, app_commands.errors.CommandNotFound):
        return  # Ignora comandos não encontrados
    
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = create_embed(
            "🚫 Acesso Negado",
            "Você não tem as permissões necessárias para usar este comando.",
            discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Loga o erro completo no console/arquivo de log
    logging.error(f"Erro não tratado para o comando /{interaction.command.name if interaction.command else 'desconhecido'}:", exc_info=error)

    # Envia uma mensagem de erro amigável e genérica para o usuário
    error_embed = create_embed(
        "❌ Ops! Ocorreu um erro.",
        "Algo deu errado ao executar este comando. Minha equipe de desenvolvimento já foi notificada!",
        discord.Color.dark_red()
    )
    
    if interaction.response.is_done():
        await interaction.followup.send(embed=error_embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# Atribui o tratador de erros à árvore de comandos do bot
bot.tree.on_error = on_tree_error

async def main():
    """Função principal para carregar cogs e iniciar o bot."""
    async with bot:
        setup_logging()  # Configura nosso novo sistema de logs
        logging.info("▶️ Iniciando o bot e carregando módulos...")
        for cog_path in COGS_TO_LOAD:
            try:
                await bot.load_extension(cog_path)
                logging.info(f"  -> ✅ Módulo '{cog_path}' carregado.")
            except Exception as e:
                logging.error(f"  -> ❌ Falha ao carregar o módulo '{cog_path}':", exc_info=e)
        
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🔴 Bot desligado pelo usuário.")