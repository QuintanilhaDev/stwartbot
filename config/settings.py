from os import getenv
from dotenv import load_dotenv

load_dotenv()

# --- Configurações Anti-Raid ---
RAID_JOIN_THRESHOLD = 5  # Número de entradas para ativar o lockdown
RAID_TIME_WINDOW = 10    # Janela de tempo em segundos para detectar as entradas
MIN_ACCOUNT_AGE_DAYS = 7 # Idade mínima da conta em dias

# --- Configurações Anti-Spam ---
SPAM_MAX_REPEATS = 5     # Número máximo de mensagens repetidas
SPAM_MUTE_MINUTES = 10   # Duração do mute em minutos

# --- Configurações de Log ---
# IMPORTANTE: Pegue o ID do canal de logs (clicando com o botão direito no canal e "Copiar ID")
# e coloque no seu arquivo .env. Ex: LOG_CHANNEL_ID=123456789012345678
LOG_CHANNEL_ID = int(getenv("LOG_CHANNEL_ID", "0"))

# --- Whitelist ---
# IDs de usuários que são imunes aos sistemas de proteção (ex: outros bots, adms)
# Ex: WHITELIST_IDS="111111111111,222222222222"
WHITELIST = {int(uid) for uid in getenv("WHITELIST_IDS", "").split(',') if uid}