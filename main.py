import os
import signal
import asyncio
import discord
from discord.ext import commands
import config
import database
from utils.scheduler import start_scheduler

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True
intents.moderation = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.has_notified_startup = False

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

    # Envia a mensagem apenas na PRIMEIRA vez que o processo do bot liga
    if not bot.has_notified_startup:
        admin_channel = bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if admin_channel:
            await admin_channel.send("🚀 **Bot reiniciado / Atualização concluída com sucesso!**")
        
        bot.has_notified_startup = True

@bot.event
async def setup_hook():
    database.init_db()
    
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

async def main():
    async with bot:
        # Registra desligamento gracioso para capturar SIGTERM (comum em deploys)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.close()))
            except NotImplementedError:
                # Windows não suporta add_signal_handler completamente para todos os sinais
                pass

        if config.TOKEN:
            await bot.start(config.TOKEN)
        else:
            print("ERRO: A variável de ambiente DISCORD_TOKEN não foi definida.")

if __name__ == "__main__":
    asyncio.run(main())