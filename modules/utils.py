import discord
import logging
from datetime import datetime

# Cor padrão para os embeds
EMBED_COLOR = 0x5865F2  # Azul do Discord

def create_embed(
    title: str,
    description: str = "",
    color: discord.Color = EMBED_COLOR,
    author: discord.User = None
) -> discord.Embed:
    """Cria um embed padronizado para o bot."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now()
    )
    if author:
        embed.set_author(name=f"Requisitado por {author.display_name}", icon_url=author.avatar.url)

    embed.set_footer(text="Stwart") # Personalize com o nome do seu bot
    return embed

def setup_logging():
    """Configura o sistema de logging para o bot."""
    # Define o formato do log
    log_format = logging.Formatter('[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    
    # Configura o logger para imprimir no console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    
    # Configura o logger para salvar em um arquivo
    file_handler = logging.FileHandler('data/bot.log', encoding='utf-8', mode='w')
    file_handler.setFormatter(log_format)

    # Pega o logger raiz e adiciona os handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)