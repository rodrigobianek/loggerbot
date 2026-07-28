import os
import sqlite3
from datetime import datetime
import pytz
import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import database

# Configuração de Intents
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Fuso horário local (exemplo: Brasil)
TIMEZONE = pytz.timezone("America/Sao_Paulo")

# ID do canal onde o bot vai postar os logs em tempo real
LOG_CHANNEL_ID = 1531654435573465318  # <--- Altere para o ID real do seu canal

# Dicionário em memória para registrar quando alguém entra no canal de voz
# Estrutura: { user_id: { "channel": name, "join_time": datetime } }
active_sessions = {}

@bot.event
async def on_ready():
    database.init_db()
    print(f"Bot conectado com sucesso como {bot.user}")
    
    # Inicia o agendador para o relatório diário
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    # Exemplo: Envia o relatório diariamente às 23:59
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

@bot.command(name="log")
async def fetch_log(ctx, date_str: str = None):
    """Comando para consultar logs. Ex: !log 2026-07-28"""
    if not date_str:
        date_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")

    logs = database.get_logs_by_date(date_str)
    
    if not logs:
        await ctx.send(f"Nenhum registro encontrado para a data: `{date_str}`. (Use o formato AAAA-MM-DD)")
        return

    response = f"📋 **Relatório de Atividade de Voz - {date_str}**\n\n"
    for user_name, channel_name, join_time, leave_time, duration in logs:
        mins = duration // 60
        secs = duration % 60
        entry_time = join_time.split(" ")[1]
        exit_time = leave_time.split(" ")[1]
        response += f"• **{user_name}** | Canal: `{channel_name}` | Permanência: {mins}m {secs}s ({entry_time} às {exit_time})\n"

    # Se a mensagem for muito longa para o Discord, envia em partes
    if len(response) > 2000:
        for chunk in [response[i:i+1900] for i in range(0, len(response), 1900)]:
            await ctx.send(chunk)
    else:
        await ctx.send(response)

async def send_daily_report():
    """Função executada pelo agendador para o relatório diário."""
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        await log_channel.send(f"⏰ **Relatório Automático Diário**")
        # Simula o contexto para reaproveitar a lógica do comando
        logs = database.get_logs_by_date(today_str)
        if not logs:
            await log_channel.send(f"Nenhuma atividade gravada hoje ({today_str}).")
            return
            
        report = f"📊 **Resumo do Dia ({today_str}):**\n"
        for user_name, channel_name, _, _, duration in logs:
            report += f"• `{user_name}` ficou {duration // 60}m no canal `{channel_name}`\n"
        await log_channel.send(report)

# Executa o bot lendo a variável de ambiente (necessário no Railway)
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO: A variável de ambiente DISCORD_TOKEN não foi definida.")