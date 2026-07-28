import os
import sqlite3
import io
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
intents.moderation = True  # Necessário para eventos de auditoria e banimentos

bot = commands.Bot(command_prefix="!", intents=intents)

TIMEZONE = pytz.timezone("America/Sao_Paulo")

# --- CANAIS DE LOG DEFINIDOS ---
ADMIN_LOG_CHANNEL_ID = 1531654435573465318   # Canal exclusivo de Admin
PUBLIC_LOG_CHANNEL_ID = 1531674099708072098  # Canal público de Notificações

# Estrutura em memória: { user_id: { "channel": name, "join_time": datetime, "is_private": bool } }
active_sessions = {}

def is_channel_private(channel: discord.VoiceChannel) -> bool:
    """Verifica se o cargo @everyone NÃO tem permissão de ver o canal."""
    if not channel:
        return False
    everyone_overwrite = channel.overwrites_for(channel.guild.default_role)
    return everyone_overwrite.view_channel is False

@bot.event
async def on_ready():
    database.init_db()
    
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comando(s) de barra (/)")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
        
    print(f"Bot conectado com sucesso como {bot.user}")
    
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_daily_report, "cron", hour=23, minute=59)
    scheduler.start()

# ==========================================
# 1. LOGS DE CANAL DE VOZ, STREAM E ÁUDIO
# ==========================================

@bot.event
async def on_voice_state_update(member, before, after):
    """Registra entrada, saída, troca de canal, transmissões de tela e estados de áudio."""
    admin_channel = bot.get_channel(ADMIN_LOG_CHANNEL_ID)
    public_channel = bot.get_channel(PUBLIC_LOG_CHANNEL_ID)
    
    now = datetime.now(TIMEZONE)
    time_str = now.strftime("%H:%M:%S")

    # ---------------------------------------------------------
    # 1. TRANSMISSÃO DE TELA (STREAMING)
    # ---------------------------------------------------------
    if before.self_stream != after.self_stream:
        channel = after.channel or before.channel
        private = is_channel_private(channel) if channel else False
        
        if not before.self_stream and after.self_stream:
            msg = f"📺 **[{time_str}]** `{member.display_name}` começou a transmitir a tela no canal **{channel.name}**."
            if admin_channel:
                await admin_channel.send(msg)
            if public_channel and not private:
                await public_channel.send(msg)
                
        elif before.self_stream and not after.self_stream:
            msg = f"📺 **[{time_str}]** `{member.display_name}` encerrou a transmissão de tela no canal **{channel.name}**."
            if admin_channel:
                await admin_channel.send(msg)
            if public_channel and not private:
                await public_channel.send(msg)

    # ---------------------------------------------------------
    # 2. ALTERAÇÕES DE ÁUDIO (MUTE / DEAFEN)
    # ---------------------------------------------------------
    channel = after.channel or before.channel
    
    # Microfone Pessoal (Self Mute)
    if before.self_mute != after.self_mute:
        if admin_channel:
            status = "mutou o microfone" if after.self_mute else "desmutou o microfone"
            await admin_channel.send(f"🎙️ **[{time_str}]** `{member.display_name}` {status} em **{channel.name if channel else 'Voz'}**.")

    # Ensurdecimento Pessoal (Self Deaf)
    if before.self_deaf != after.self_deaf:
        if admin_channel:
            status = "silenciou o áudio (deaf)" if after.self_deaf else "dessilenciou o áudio"
            await admin_channel.send(f"🎧 **[{time_str}]** `{member.display_name}` {status} em **{channel.name if channel else 'Voz'}**.")

    # Mute por Servidor/Moderador (Server Mute)
    if before.mute != after.mute:
        if admin_channel:
            status = "teve o microfone silenciado por um mod" if after.mute else "teve o microfone liberado por um mod"
            await admin_channel.send(f"🛡️ **[{time_str}]** `{member.display_name}` {status} em **{channel.name if channel else 'Voz'}**.")

    # Deaf por Servidor/Moderador (Server Deaf)
    if before.deaf != after.deaf:
        if admin_channel:
            status = "teve o áudio bloqueado por um mod" if after.deaf else "teve o áudio liberado por um mod"
            await admin_channel.send(f"🛡️ **[{time_str}]** `{member.display_name}` {status} em **{channel.name if channel else 'Voz'}**.")

    # ---------------------------------------------------------
    # 3. ENTROU EM UM CANAL DE VOZ
    # ---------------------------------------------------------
    if before.channel is None and after.channel is not None:
        private = is_channel_private(after.channel)
        active_sessions[member.id] = {
            "channel": after.channel.name,
            "join_time": now,
            "is_private": private
        }
        
        msg = f"🟢 **[{time_str}]** `{member.display_name}` entrou no canal **{after.channel.name}**."
        
        if admin_channel:
            await admin_channel.send(msg)
        if public_channel and not private:
            await public_channel.send(msg)

    # ---------------------------------------------------------
    # 4. SAIU TOTALMENTE DO VOZ
    # ---------------------------------------------------------
    elif before.channel is not None and after.channel is None:
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
            
            minutes = duration // 60
            seconds = duration % 60
            msg = (
                f"🔴 **[{time_str}]** `{member.display_name}` desconectou de **{session['channel']}**. "
                f"(Tempo online: {minutes}m {seconds}s)"
            )
            
            if admin_channel:
                await admin_channel.send(msg)
            if public_channel and not session["is_private"]:
                await public_channel.send(msg)

    # ---------------------------------------------------------
    # 5. TROCOU DE CANAL
    # ---------------------------------------------------------
    elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
        was_private = is_channel_private(before.channel)
        is_private_now = is_channel_private(after.channel)
        
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

        active_sessions[member.id] = {
            "channel": after.channel.name,
            "join_time": now,
            "is_private": is_private_now
        }
        
        if admin_channel:
            await admin_channel.send(
                f"🟡 **[{time_str}]** `{member.display_name}` mudou de **{before.channel.name}** para **{after.channel.name}**."
            )
            
        if public_channel:
            if not was_private and is_private_now:
                await public_channel.send(f"🔴 **[{time_str}]** `{member.display_name}` desconectou de **{before.channel.name}**.")
            elif was_private and not is_private_now:
                await public_channel.send(f"🟢 **[{time_str}]** `{member.display_name}` entrou no canal **{after.channel.name}**.")
            elif not was_private and not is_private_now:
                await public_channel.send(
                    f"🟡 **[{time_str}]** `{member.display_name}` mudou de **{before.channel.name}** para **{after.channel.name}**."
                )

# ==========================================
# 2. LOGS DE REGISTRO DE AUDITORIA & MENSAGENS
# ==========================================

@bot.event
async def on_member_update(before, after):
    """Monitora alterações de cargos em membros."""
    admin_channel = bot.get_channel(ADMIN_LOG_CHANNEL_ID)
    if not admin_channel:
        return

    if before.roles != after.roles:
        now = datetime.now(TIMEZONE).strftime("%H:%M:%S")
        added_roles = [role.name for role in after.roles if role not in before.roles]
        removed_roles = [role.name for role in before.roles if role not in after.roles]

        executor = "Desconhecido/Sistema"
        try:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    executor = entry.user.display_name
                    break
        except Exception:
            pass

        if added_roles:
            await admin_channel.send(
                f"🛡️ **[{now}] Audit:** `{executor}` concedeu o(s) cargo(s) `{', '.join(added_roles)}` para `{after.display_name}`."
            )
        if removed_roles:
            await admin_channel.send(
                f"🛡️ **[{now}] Audit:** `{executor}` removeu o(s) cargo(s) `{', '.join(removed_roles)}` de `{after.display_name}`."
            )

@bot.event
async def on_message_delete(message):
    """Captura a exclusão de mensagens em qualquer canal do servidor."""
    if message.author.bot:
        return

    admin_channel = bot.get_channel(ADMIN_LOG_CHANNEL_ID)
    if not admin_channel:
        return

    channel_name = message.channel.name if hasattr(message.channel, 'name') else "Canal Desconhecido"
    content = message.content if message.content else "*[Mensagem sem texto / apenas anexo ou embed]*"
    
    time_str = datetime.now(TIMEZONE).strftime("%H:%M:%S")

    msg = (
        f"🗑️ **[{time_str}]** Mensagem de `{message.author.display_name}` "
        f"foi apagada no canal **#{channel_name}**:\n"
        f"> {content}"
    )

    await admin_channel.send(msg)

# ==========================================
# 3. COMANDOS ADMINISTRATIVOS & BANCO DE DADOS
# ==========================================

# ==========================================
# 3. COMANDOS ADMINISTRATIVOS & BANCO DE DADOS
# ==========================================

@bot.tree.command(name="log", description="[ADMIN] Consulta os registros de voz do servidor.")
@app_commands.describe(data="Data da consulta no formato AAAA-MM-DD. Deixe em blank para o dia de hoje.")
async def fetch_log(interaction: discord.Interaction, data: str = None):
    # Checagem manual de Administrador (Garante que o Dono ou Admins passem sem erro de cache)
    if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ Permissão negada. Comando restrito a Administradores.", ephemeral=True)
        return

    if not data:
        data = datetime.now(TIMEZONE).strftime("%Y-%m-%d")

    logs = database.get_logs_by_date(data)
    
    if not logs:
        await interaction.response.send_message(f"Nenhum registro encontrado para a data: `{data}`.", ephemeral=True)
        return

    response = f"📋 **[ADMIN] Relatório de Atividade de Voz - {data}**\n\n"
    for user_name, channel_name, join_time, leave_time, duration in logs:
        mins = duration // 60
        secs = duration % 60
        entry_time = join_time.split(" ")[1]
        exit_time = leave_time.split(" ")[1]
        response += f"• **{user_name}** | Canal: `{channel_name}` | Permanência: {mins}m {secs}s ({entry_time} às {exit_time})\n"

    if len(response) > 2000:
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        await interaction.response.send_message(chunks[0], ephemeral=True)
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk, ephemeral=True)
    else:
        await interaction.response.send_message(response, ephemeral=True)


@bot.tree.command(name="export_db", description="[ADMIN] Faz o download do arquivo do banco de dados SQLite.")
async def export_db(interaction: discord.Interaction):
    user = interaction.user
    guild = interaction.guild

    # ---------------------------------------------------------
    # PRINT DE DEBUG NO CONSOLE (Aparecerá nos logs do Railway/Terminal)
    # ---------------------------------------------------------
    print("=" * 50)
    print(f"DEBUG /export_db executado por: {user.name} ({user.id})")
    if guild:
        print(f"Servidor: {guild.name} ({guild.id})")
        print(f"É o dono do servidor? {user.id == guild.owner_id} (Dono ID: {guild.owner_id})")
        
        # Lista as permissões
        is_admin = user.guild_permissions.administrator
        print(f"Tem permissão de Administrador? {is_admin}")
        
        # Lista os cargos do usuário
        roles = [r.name for r in user.roles]
        print(f"Cargos do usuário: {roles}")
    else:
        print("Executado fora de uma Guild (DM).")
    print("=" * 50)

    # ---------------------------------------------------------
    # VERIFICAÇÃO DE PERMISSÃO
    # ---------------------------------------------------------
    # Checa se é administrador OU se é o dono do servidor
    if not user.guild_permissions.administrator and user.id != guild.owner_id:
        await interaction.response.send_message(
            f"❌ Permissão negada para `{user.display_name}`. Este comando exige o cargo de Administrador.",
            ephemeral=True
        )
        return

    # Se passou na permissão, continua o envio do banco de dados
    await interaction.response.defer(ephemeral=True)
    
    db_path = getattr(database, 'DB_NAME', 'database.db')
    
    if os.path.exists(db_path):
        file = discord.File(db_path, filename="database_backup.db")
        await interaction.followup.send("📁 Aqui está a cópia atualizada da sua base de dados SQLite:", file=file, ephemeral=True)
    else:
        await interaction.followup.send("❌ Arquivo de banco de dados não encontrado no caminho.", ephemeral=True)

@fetch_log.error
@export_db.error
async def admin_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        if interaction.response.is_done():
            await interaction.followup.send("❌ Permissão negada. Comando restrito a Administradores.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Permissão negada. Comando restrito a Administradores.", ephemeral=True)

async def send_daily_report():
    admin_channel = bot.get_channel(ADMIN_LOG_CHANNEL_ID)
    if admin_channel:
        today_str = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        logs = database.get_logs_by_date(today_str)
        if not logs:
            await admin_channel.send(f"⏰ **Relatório Diário ({today_str}):** Nenhuma atividade gravada hoje.")
            return
            
        report = f"📊 **Relatório Automático Diário Admin ({today_str}):**\n"
        for user_name, channel_name, _, _, duration in logs:
            report += f"• `{user_name}` ficou {duration // 60}m no canal `{channel_name}`\n"
        await admin_channel.send(report)

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO: A variável de ambiente DISCORD_TOKEN não foi definida.")