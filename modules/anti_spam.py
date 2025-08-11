import discord
import logging
from discord.ext import commands
from discord.utils import utcnow
from datetime import timedelta
from collections import defaultdict
from modules.utils import create_embed
# CORREÇÃO: Importando a variável com o nome correto
from config.settings import SPAM_MAX_REPEATS, SPAM_MUTE_MINUTES, WHITELIST

class AntiSpam(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Tracker agora é um dicionário aninhado por servidor para evitar conflitos
        self.spam_tracker = defaultdict(dict)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (
            message.author.bot or
            not message.guild or
            message.author.id in WHITELIST or
            not isinstance(message.channel, discord.TextChannel)
        ):
            return

        guild_id = message.guild.id
        author_id = message.author.id
        content = message.content.lower()
        key = (guild_id, author_id)

        # Atualiza ou cria o tracker para o usuário
        if key not in self.spam_tracker or self.spam_tracker[key]["content"] != content:
            self.spam_tracker[key] = {"content": content, "count": 1, "last_message": utcnow()}
        else:
            self.spam_tracker[key]["count"] += 1
            self.spam_tracker[key]["last_message"] = utcnow()

        # Verifica se o limite de spam foi atingido
        if self.spam_tracker[key]["count"] >= SPAM_MAX_REPEATS:
            try:
                # CORREÇÃO: Usando a variável e o cálculo corretos
                mute_duration = timedelta(minutes=SPAM_MUTE_MINUTES)
                await message.author.timeout(mute_duration, reason="Spam de mensagens detectado")
                
                embed = create_embed(
                    "🔇 Membro Silenciado por Spam",
                    f"{message.author.mention} foi silenciado por **{SPAM_MUTE_MINUTES} minutos** por enviar mensagens repetidas.",
                    discord.Color.orange()
                )
                await message.channel.send(embed=embed)
                logging.warning(f"🛡️ Anti-Spam: {message.author} mutado por spam em '{message.guild.name}'")
                
                # Limpa o tracker para este usuário após a punição
                self.spam_tracker.pop(key, None)

            except discord.Forbidden:
                logging.error(f"Anti-Spam: Sem permissão para silenciar {message.author.mention} em '{message.guild.name}'.")
            except Exception as e:
                logging.error(f"Anti-Spam: Erro inesperado ao tentar silenciar:", exc_info=e)

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))