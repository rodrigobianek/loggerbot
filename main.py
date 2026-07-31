import os
import signal
import asyncio
import discord
from discord.ext import commands
import config
import database
from utils.scheduler import start_scheduler

# Configuração de Intents
intents = discord.Intents.default()
intents.guilds = True           # Para criação, alteração e exclusão de canais
intents.messages = True         # Para detecção de mensagens deletadas
intents.message_content = True # Para ler o conteúdo das mensagens deletadas
intents.moderation = True      # Para buscar executores no Audit Log
intents.members = True         # Para alterações de cargos de membros
intents.voice_states = True    # Para logs de voz

bot = commands.Bot(command_prefix="!", intents=intents)
bot.has_notified_startup = False


@bot.event
async def setup_hook():
    database.init_db()
    
    initial_extensions = [
        "cogs.voice_logs",
        "cogs.audit_logs",
        "cogs.admin"
    ]
    
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            print(f"Módulo carregado com sucesso: {extension}")
        except Exception as e:
            print(f"❌ Erro ao carregar o módulo {extension}: {e}")
        
    synced = await bot.tree.sync()
    print(f"Sincronizados {len(synced)} comando(s) de barra (/)")


@bot.event
async def on_ready():
    print(f"✅ Bot conectado com sucesso como {bot.user}")
    
    # Inicia o agendador de tarefas
    start_scheduler(bot)

    # Notificação de reinicialização (apenas na primeira conexão do processo)
    if not bot.has_notified_startup:
        try:
            channel_id = int(config.ADMIN_LOG_CHANNEL_ID)
            admin_channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
            if admin_channel:
                await admin_channel.send("🚀 **Bot reiniciado / Atualização concluída**")
        except Exception as e:
            print(f"⚠️ Erro ao enviar mensagem de inicialização: {e}")
        
        bot.has_notified_startup = True


async def main():
    async with bot:
        # Registra desligamento gracioso para capturar SIGTERM (comum em hosts como Railway)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.close()))
            except NotImplementedError:
                # Windows não suporta add_signal_handler completamente
                pass

        if config.TOKEN:
            await bot.start(config.TOKEN)
        else:
            print("❌ ERRO: A variável de ambiente DISCORD_TOKEN não foi definida.")

if __name__ == "__main__":
    asyncio.run(main())