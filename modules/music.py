import discord
import asyncio
import yt_dlp
import logging
from discord import app_commands
from discord.ext import commands
from collections import defaultdict
from modules.utils import create_embed

def get_audio_source(url: str):
    """Extrai informações do áudio usando yt_dlp."""
    ydl_opts = {
        'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True,
        'ignoreerrors': False, 'logtostderr': False, 'quiet': True,
        'no_warnings': True, 'default_search': 'ytsearch', 'source_address': '0.0.0.0'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info: info = info['entries'][0]
            return {
                'url': info['url'], 
                'title': info.get('title', 'Título desconhecido'),
                'thumbnail': info.get('thumbnail', ''),
                'webpage_url': info.get('webpage_url', url)
            }
    except Exception as e:
        logging.error(f"Erro ao obter source do yt_dlp para '{url}': {e}")
        return None

class MusicControls(discord.ui.View):
    """View com os botões de controle de música."""
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice or not interaction.guild.voice_client or interaction.user.voice.channel != interaction.guild.voice_client.channel:
            await interaction.response.send_message("Você precisa estar no mesmo canal de voz que eu para usar os controles.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Pausar", style=discord.ButtonStyle.primary, emoji="⏸️")
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message(embed=create_embed("⏸️ Pausado", "A música foi pausada.", author=interaction.user), ephemeral=True)

    @discord.ui.button(label="Retomar", style=discord.ButtonStyle.success, emoji="▶️")
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message(embed=create_embed("▶️ Retomado", "A música voltou a tocar.", author=interaction.user), ephemeral=True)

    @discord.ui.button(label="Pular", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message(embed=create_embed("⏭️ Pulado", author=interaction.user), ephemeral=True)

    @discord.ui.button(label="Parar", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.cleanup(interaction.guild)
        await interaction.response.send_message(embed=create_embed("⏹️ Player Parado", "A música foi parada e a fila foi limpa.", author=interaction.user, color=discord.Color.red()), ephemeral=True)

class Music(commands.Cog):
    """Comandos para tocar músicas no canal de voz."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.player_tasks = {}
        self.music_queues = defaultdict(list)
        self.song_queues = defaultdict(asyncio.Queue)
        self.play_next_song_events = defaultdict(asyncio.Event)
        self.now_playing_messages = {}
        self.current_song_info = defaultdict(dict)

    async def cleanup(self, guild: discord.Guild):
        """Limpa todos os recursos de música de um servidor."""
        if guild.id in self.player_tasks:
            self.player_tasks[guild.id].cancel()
        if guild.voice_client:
            await guild.voice_client.disconnect()
        self.music_queues.pop(guild.id, None)
        self.song_queues.pop(guild.id, None)
        self.play_next_song_events.pop(guild.id, None)
        self.player_tasks.pop(guild.id, None)
        self.now_playing_messages.pop(guild.id, None)
        self.current_song_info.pop(guild.id, None)
        logging.info(f"Recursos de música limpos para o servidor {guild.name}")

    async def audio_player_task(self, initial_interaction: discord.Interaction):
        guild_id = initial_interaction.guild.id
        while True:
            self.play_next_song_events[guild_id].clear()
            vc = self.bot.get_guild(guild_id).voice_client
            if not vc: break

            try:
                requester_interaction, song_search = await asyncio.wait_for(self.song_queues[guild_id].get(), timeout=300.0)
                
                self.music_queues[guild_id].pop(0)

                song_info = get_audio_source(song_search)
                if not song_info:
                    await requester_interaction.channel.send(embed=create_embed("❌ Erro", f"Não consegui encontrar informações para `{song_search}`. Pulando.", discord.Color.red()))
                    continue
                
                self.current_song_info[guild_id] = song_info

                source = discord.FFmpegPCMAudio(song_info['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
                vc.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next_song_events[guild_id].set))

                embed = create_embed("🎶 Tocando Agora", f"**[{song_info['title']}]({song_info['webpage_url']})**", author=requester_interaction.user)
                if song_info['thumbnail']: embed.set_thumbnail(url=song_info['thumbnail'])
                
                if guild_id in self.now_playing_messages:
                    msg = self.now_playing_messages[guild_id]
                    try: await msg.edit(embed=embed, view=MusicControls(self))
                    except discord.NotFound: self.now_playing_messages[guild_id] = await requester_interaction.channel.send(embed=embed, view=MusicControls(self))
                else:
                    self.now_playing_messages[guild_id] = await requester_interaction.channel.send(embed=embed, view=MusicControls(self))

                await self.play_next_song_events[guild_id].wait()

            except asyncio.TimeoutError:
                await self.cleanup(initial_interaction.guild)
                await initial_interaction.channel.send(embed=create_embed("🕒 Inatividade", "Saindo do canal por inatividade.", discord.Color.light_grey()))
                break
            except Exception as e:
                logging.error("Erro inesperado no player de áudio:", exc_info=e)
                await self.cleanup(initial_interaction.guild)
                break
    
    @app_commands.command(name="play", description="Toca uma música no seu canal de voz.")
    @app_commands.describe(busca="O nome ou URL da música que você quer tocar.")
    async def play(self, interaction: discord.Interaction, busca: str):
        if not interaction.user.voice:
            return await interaction.response.send_message(embed=create_embed("❌ Erro", "Você precisa estar em um canal de voz.", discord.Color.red()), ephemeral=True)
        
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()
            self.player_tasks[interaction.guild.id] = self.bot.loop.create_task(self.audio_player_task(interaction))

        await self.song_queues[interaction.guild.id].put((interaction, busca))
        self.music_queues[interaction.guild.id].append(busca)

        await interaction.followup.send(embed=create_embed("🎵 Adicionado à Fila", f"`{busca}` foi adicionado.", author=interaction.user))

    @app_commands.command(name="queue", description="Mostra a fila de músicas atual.")
    async def queue(self, interaction: discord.Interaction):
        queue_list = self.music_queues.get(interaction.guild.id, [])
        if not queue_list:
            return await interaction.response.send_message(embed=create_embed("📭 Fila Vazia", "Não há nenhuma música na fila.", discord.Color.orange()))

        description = "\n".join(f"`{i+1}.` {song}" for i, song in enumerate(queue_list[:10]))
        embed = create_embed("📃 Fila de Reprodução", description, author=interaction.user)
        if len(queue_list) > 10: embed.set_footer(text=f"e mais {len(queue_list) - 10} música(s)...")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="Pula a música que está tocando.")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message(embed=create_embed("❌ Erro", "Não há nenhuma música tocando para pular.", discord.Color.red()), ephemeral=True)
        
        vc.stop()
        embed = create_embed("⏭️ Música Pulada", "Pulando para a próxima música da fila.", author=interaction.user)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Mostra informações sobre a música que está tocando.")
    async def nowplaying(self, interaction: discord.Interaction):
        song_info = self.current_song_info.get(interaction.guild.id)
        if not song_info:
            return await interaction.response.send_message(embed=create_embed("🤔 Nada Tocando", "Não há nenhuma música no momento.", discord.Color.orange()))
        
        embed = create_embed("🎶 Tocando Agora", f"**[{song_info['title']}]({song_info['webpage_url']})**", author=interaction.user)
        if song_info['thumbnail']: embed.set_thumbnail(url=song_info['thumbnail'])
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="stop", description="Para a música, limpa a fila e desconecta o bot.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stop(self, interaction: discord.Interaction):
        await self.cleanup(interaction.guild)
        await interaction.response.send_message(embed=create_embed("⏹️ Player Parado", author=interaction.user, color=discord.Color.red()))

async def setup(bot):
    await bot.add_cog(Music(bot))