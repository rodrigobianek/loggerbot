import os
import sqlite3
from datetime import datetime
import pytz
import discord
from discord import app_commands
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import database

# Configuração de Intents
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Fuso horário local (Brasil)
TIMEZONE = pytz.timezone("America/Sao_Paulo")

# ID do canal onde o bot vai postar os logs em tempo real
LOG_CHANNEL_ID = 123456789012345678  # <--- Altere para o ID real do seu canal

# Dicionário em memória para registrar quando alguém entra no canal de voz
# Estrutura: { user_id: { "channel": name, "join_time": datetime } }
active_sessions = {}

@bot.event
async def on_ready():
    database.init_db()
    
    # Sincroniza os Slash Commands (comandos com /) com o Discord
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comando(s) de barra (/)")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
        
    print(f"Bot conectado com sucesso como {bot.user}")
    
    # Inicia o agendador para o relatório diário
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    # Envia o relatório diariamente às 23:59
    scheduler.add_job(send_daily_report, "cron", hour=23, minute=59)
    scheduler.start()

@bot.event
async def on_voice_state_update(member, before, after):
    """Registra entrada, saída e troca de canais de voz."""
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    now = datetime.now(TIMEZONE)
    time_str = now.strftime("%H:%M:%S")

    # 1. Usuário ENTROU em um canal de voz
    if before.channel is None and after.channel is not None:
        active_sessions[member.id] = {
            "channel": after.channel.name,
            "join_time": now
        }
        if log_channel:
            await log_channel.send(f"🟢 **[{time_str}]** `{member.display_name}` entrou no canal **{after.channel.name}**.")

    # 2. Usuário SAIU de um canal de voz
    elif before.channel is not None and after.channel is None:
        if member.id in active_sessions:
            session = active_sessions.pop(member.id)
            duration = int((now - session["join_time"]).total_seconds())
            
            # Salva no Banco de Dados
            database.save_voice_session(
                user_name=member.display_name,
                channel_name=session["channel"],
                join_time=session["join_time"],
                leave_time=now,
                duration_seconds=duration
            )
            
            minutes = duration // 60
            seconds = duration % 60
            if log_channel:
                await log_channel.send(
                    f"🔴 **[{time_str}]** `{member.display_name}` desconectou de **{session['channel']}**. "
                    f"(Tempo online: {minutes}m {seconds}s)"
                )

    # 3. Usuário TROCOU de canal
    elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
        if member.id in active_sessions:
            session = active_sessions.pop(member.id)
            duration = int((now - session["join_time"]).total_seconds())
            
            database.save_voice_session(
                user_name=member.display_name,
                channel_name=session["channel"],
                join_time=session["join_time"],
                leave_time=now,
                duration_seconds=duration
            )

        # Inicia nova sessão no canal de destino
        active_sessions[member.id] = {
            "channel": after.channel.name,
            "join_time": now
        }
        if log_channel:
            await log_channel.send(
                f"🟡 **[{time_str}]** `{member.display_name}` mudou do canal **{before.channel.name}** para **{after.channel.name}**."
            )

# Slash Command: /log
@bot.tree.command(name="log", description="Consulta os registros de voz de uma data específica ou de hoje.")
@app_commands.describe(data="Data da consulta no formato AAAA-MM-DD. Deixe em branco para ver o dia de hoje.")
async def fetch_log(interaction: discord.Interaction, data: str = None):
    # Se nenhuma data for informada, assume a data atual
    if not data:
        data = datetime.now(TIMEZONE).strftime("%Y-%m-%d")

    logs = database.get_logs_by_date(data)
    
    if not logs:
        await interaction.response.send_message(
            f"Nenhum registro encontrado para a data: `{data}`. (Formato esperado: AAAA-MM-DD)",
            ephemeral=False
        )
        return

    response = f"📋 **Relatório de Atividade de Voz - {data}**\n\n"
    for user_name, channel_name, join_time, leave_time, duration in logs:
        mins = duration // 60
        secs = duration % 60
        entry_time = join_time.split(" ")[1]
        exit_time = leave_time.split(" ")[1]
        response += f"• **{user_name}** | Canal: `{channel_name}` | Permanência: {mins}m {secs}s ({entry_time} às {exit_time})\n"

    # Envia a resposta (lidando com o limite de 2000 caracteres do Discord)
    if len(response) > 2000:
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.channel.send(chunk)
    else:
        await interaction.response.send_message(response)

async def send_daily_report():
    """Função executada pelo agendador para o relatório diário."""
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        logs = database.get_logs_by_date(today_str)
        if not logs:
            await log_channel.send(f"⏰ **Relatório Diário ({today_str}):** Nenhuma atividade gravada hoje.")
            return
            
        report = f"📊 **Relatório Automático Diário ({today_str}):**\n"
        for user_name, channel_name, _, _, duration in logs:
            report += f"• `{user_name}` ficou {duration // 60}m no canal `{channel_name}`\n"
        await log_channel.send(report)

# Executa o bot lendo a variável de ambiente
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO: A variável de ambiente DISCORD_TOKEN não foi definida.")