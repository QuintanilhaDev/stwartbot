import discord
import logging
import sqlite3
import os
from discord import Embed, app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from typing import List, Tuple
from modules.utils import create_embed

class ActivityDatabase:
    """Classe para gerenciar o banco de dados de atividade."""
    def __init__(self, db_path="data/activity.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS member_activity (
            member_id INTEGER, guild_id INTEGER, last_active TEXT,
            daily_count INTEGER DEFAULT 0, weekly_count INTEGER DEFAULT 0,
            monthly_count INTEGER DEFAULT 0, total_count INTEGER DEFAULT 0,
            PRIMARY KEY (member_id, guild_id)
        )""")
        self.conn.commit()

    def update_activity(self, member_id: int, guild_id: int):
        now_iso = datetime.utcnow().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO member_activity (member_id, guild_id, last_active) VALUES (?, ?, ?)", (member_id, guild_id, now_iso))
        cursor.execute("""
            UPDATE member_activity SET
            last_active = ?, daily_count = daily_count + 1, weekly_count = weekly_count + 1,
            monthly_count = monthly_count + 1, total_count = total_count + 1
            WHERE member_id = ? AND guild_id = ?
        """, (now_iso, member_id, guild_id))
        self.conn.commit()
    
    # ... (outros métodos do DB como get_top_members, get_inactive_members, etc. permanecem os mesmos) ...
    def get_top_members(self, guild_id: int, period: str, limit: int = 5) -> List[Tuple[int, int]]:
        cursor = self.conn.cursor()
        column = {"daily": "daily_count", "weekly": "weekly_count", "monthly": "monthly_count"}.get(period, "total_count")
        cursor.execute(f"SELECT member_id, {column} FROM member_activity WHERE guild_id = ? AND {column} > 0 ORDER BY {column} DESC LIMIT ?", (guild_id, limit))
        return cursor.fetchall()

    def has_any_data(self, guild_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM member_activity WHERE guild_id = ? LIMIT 1", (guild_id,))
        return cursor.fetchone() is not None

class GodEye(commands.Cog):
    """Sistema para rastrear e exibir a atividade dos membros."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = ActivityDatabase()
        self.reset_counts.start()

    def cog_unload(self):
        self.reset_counts.cancel()

    @tasks.loop(hours=1)
    async def reset_counts(self):
        now = datetime.utcnow()
        # Roda uma vez por dia, perto da meia-noite UTC
        if now.hour == 0:
            logging.info("Realizando reset dos contadores de atividade diária.")
            cursor = self.db.conn.cursor()
            cursor.execute("UPDATE member_activity SET daily_count = 0")
            # Segunda-feira
            if now.weekday() == 0:
                logging.info("Realizando reset dos contadores de atividade semanal.")
                cursor.execute("UPDATE member_activity SET weekly_count = 0")
            # Primeiro dia do mês
            if now.day == 1:
                logging.info("Realizando reset dos contadores de atividade mensal.")
                cursor.execute("UPDATE member_activity SET monthly_count = 0")
            self.db.conn.commit()

    @reset_counts.before_loop
    async def before_reset_counts(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.author.bot and message.guild:
            self.db.update_activity(message.author.id, message.guild.id)
    
    async def create_activity_embed(self, guild: discord.Guild) -> Embed:
        if not self.db.has_any_data(guild.id):
            return create_embed("📈 Atividade do Servidor", "Ainda não há dados de atividade registrados.", discord.Color.orange())

        top_daily_data = self.db.get_top_members(guild.id, "daily", 5)
        top_weekly_data = self.db.get_top_members(guild.id, "weekly", 5)

        def format_list(data: List[Tuple[int, int]]) -> str:
            lines = []
            for idx, (member_id, count) in enumerate(data, 1):
                member = guild.get_member(member_id)
                if member:
                    lines.append(f"{idx}. {member.mention} - `{count}` msg(s)")
            return "\n".join(lines) if lines else "Nenhuma atividade registrada."

        embed = Embed(title=f"📈 Atividade de {guild.name}", color=0x2ECC71, timestamp=datetime.utcnow())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="🔥 Top 5 Diário", value=format_list(top_daily_data), inline=False)
        embed.add_field(name="📅 Top 5 Semanal", value=format_list(top_weekly_data), inline=False)
        embed.set_footer(text="A atividade é contada a partir do número de mensagens enviadas.")
        
        return embed

    @app_commands.command(name="activity", description="Mostra os rankings de atividade dos membros no servidor.")
    @app_commands.checks.has_permissions(administrator=True)
    async def activity(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = await self.create_activity_embed(interaction.guild)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GodEye(bot))