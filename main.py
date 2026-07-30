import os
import discord
from discord.ext import commands
import config
import database
from utils.scheduler import start_scheduler

# Configuração de Intents
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    """Carrega dinamicamente todos os Cogs e sincroniza a árvore de comandos."""
    database.init_db()
    
    # Carrega os Cogs
    initial_extensions = [
        "cogs.voice_logs",
        "cogs.audit_logs",
        "cogs.admin"
    ]
    
    for extension in initial_extensions:
        await bot.load_extension(extension)
        print(f"Módulo carregado: {extension}")
        
    synced = await bot.tree.sync()
    print(f"Sincronizados {len(synced)} comando(s) de barra (/)")

@bot.event
async def on_ready():
    print(f"Bot conectado com sucesso como {bot.user}")
    start_scheduler(bot)

if __name__ == "__main__":
    if config.TOKEN:
        bot.run(config.TOKEN)
    else:
        print("ERRO: A variável de ambiente DISCORD_TOKEN não foi definida.")