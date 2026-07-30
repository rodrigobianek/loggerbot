from datetime import datetime
import discord
from discord.ext import commands
import config
import database

class VoiceLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}
        self.active_streams = {}

    def is_channel_private(self, channel: discord.VoiceChannel) -> bool:
        if not channel:
            return False
        everyone_overwrite = channel.overwrites_for(channel.guild.default_role)
        return everyone_overwrite.view_channel is False

    def cog_unload(self):
        """Executado automaticamente quando o bot desliga ou o Cog é descarregado (Deploy).
        Salva imediatamente a sessão de todos que estão em salas de voz."""
        now = datetime.now(config.TIMEZONE)
        to_save = []

        for user_id, session in list(self.active_sessions.items()):
            duration = int((now - session["join_time"]).total_seconds())
            if duration > 0:
                to_save.append((
                    session["user_name"],
                    session["channel"],
                    session["join_time"].strftime("%Y-%m-%d %H:%M:%S"),
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                    duration
                ))

        if to_save:
            database.save_multiple_sessions(to_save)
            print(f"💾 [DEPLOY] {len(to_save)} sessão(ões) ativa(s) salva(s) com sucesso antes do desligamento.")

    async def recover_active_sessions(self):
        """Verifica se já existem membros em canais de voz ao iniciar e começa a monitorá-los."""
        now = datetime.now(config.TIMEZONE)
        recovered_count = 0

        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                private = self.is_channel_private(channel)
                for member in channel.members:
                    if not member.bot:
                        self.active_sessions[member.id] = {
                            "user_name": member.display_name,
                            "channel": channel.name,
                            "join_time": now,
                            "is_private": private
                        }
                        recovered_count += 1

        if recovered_count > 0:
            print(f"🔄 Recuperadas {recovered_count} sessão(ões) de voz ativas após a inicialização.")

    @commands.Cog.listener()
    async def on_ready(self):
        # Reconecta quem já estava em salas de voz
        await self.recover_active_sessions()

        # Envia a mensagem de aviso no canal de logs do admin
        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if admin_channel:
            now_str = datetime.now(config.TIMEZONE).strftime("%d/%m/%Y às %H:%M:%S")
            await admin_channel.send(f"🚀 **System Update:** O bot foi atualizado e reiniciado com sucesso! `[{now_str}]`")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        public_channel = self.bot.get_channel(config.PUBLIC_LOG_CHANNEL_ID)
        
        now = datetime.now(config.TIMEZONE)
        time_str = now.strftime("%H:%M:%S")

        # 1. TRANSMISSÃO DE TELA
        if before.self_stream != after.self_stream:
            channel = after.channel or before.channel
            private = self.is_channel_private(channel) if channel else False
            
            if not before.self_stream and after.self_stream:
                self.active_streams[member.id] = now
                viewers_count = sum(1 for m in channel.members if not m.bot and m.id != member.id) if channel else 0
                
                msg = (
                    f"📺 **[{time_str}]** `{member.display_name}` começou a transmitir a tela no canal **{channel.name if channel else 'Voz'}**.\n"
                    f"👥 **Espectadores no canal:** {viewers_count} pessoa(s)"
                )
                if admin_channel: await admin_channel.send(msg)
                if public_channel and not private: await public_channel.send(msg)
                    
            elif before.self_stream and not after.self_stream:
                stream_start = self.active_streams.pop(member.id, None)
                duration_str = "Desconhecida"
                if stream_start:
                    duration_seconds = int((now - stream_start).total_seconds())
                    hours = duration_seconds // 3600
                    minutes = (duration_seconds % 3600) // 60
                    seconds = duration_seconds % 60
                    duration_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"

                msg = (
                    f"📺 **[{time_str}]** `{member.display_name}` encerrou a transmissão de tela no canal **{channel.name if channel else 'Voz'}**.\n"
                    f"⏱️ **Duração da transmissão:** `{duration_str}`"
                )
                if admin_channel: await admin_channel.send(msg)
                if public_channel and not private: await public_channel.send(msg)

        # 2. ALTERAÇÕES DE ÁUDIO
        channel = after.channel or before.channel
        if before.self_mute != after.self_mute and admin_channel:
            status = "mutou o microfone" if after.self_mute else "desmutou o microfone"
            await admin_channel.send(f"🎙️ **[{time_str}]** `{member.display_name}` {status} em **{channel.name if channel else 'Voz'}**.")

        if before.self_deaf != after.self_deaf and admin_channel:
            status = "silenciou o áudio (deaf)" if after.self_deaf else "dessilenciou o áudio"
            await admin_channel.send(f"🎧 **[{time_str}]** `{member.display_name}` {status} em **{channel.name if channel else 'Voz'}**.")

        if before.mute != after.mute and admin_channel:
            status = "teve o microfone silenciado por um mod" if after.mute else "teve o microfone liberado por um mod"
            await admin_channel.send(f"🛡️ **[{time_str}]** `{member.display_name}` {status} em **{channel.name if channel else 'Voz'}**.")

        if before.deaf != after.deaf and admin_channel:
            status = "teve o áudio bloqueado por um mod" if after.deaf else "teve o áudio liberado por um mod"
            await admin_channel.send(f"🛡️ **[{time_str}]** `{member.display_name}` {status} em **{channel.name if channel else 'Voz'}**.")

        # 3. ENTROU NO VOZ
        if before.channel is None and after.channel is not None:
            private = self.is_channel_private(after.channel)
            self.active_sessions[member.id] = {
                "user_name": member.display_name,
                "channel": after.channel.name,
                "join_time": now,
                "is_private": private
            }
            msg = f"🟢 **[{time_str}]** `{member.display_name}` entrou no canal **{after.channel.name}**."
            if admin_channel: await admin_channel.send(msg)
            if public_channel and not private: await public_channel.send(msg)

        # 4. SAIU DO VOZ
        elif before.channel is not None and after.channel is None:
            self.active_streams.pop(member.id, None)
            if member.id in self.active_sessions:
                session = self.active_sessions.pop(member.id)
                duration = int((now - session["join_time"]).total_seconds())
                
                database.save_voice_session(
                    user_name=member.display_name,
                    channel_name=session["channel"],
                    join_time=session["join_time"],
                    leave_time=now,
                    duration_seconds=duration
                )
                
                minutes, seconds = duration // 60, duration % 60
                msg = f"🔴 **[{time_str}]** `{member.display_name}` desconectou de **{session['channel']}**. (Tempo online: {minutes}m {seconds}s)"
                if admin_channel: await admin_channel.send(msg)
                if public_channel and not session["is_private"]: await public_channel.send(msg)

        # 5. TROCOU DE CANAL
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            was_private = self.is_channel_private(before.channel)
            is_private_now = self.is_channel_private(after.channel)
            
            if member.id in self.active_sessions:
                session = self.active_sessions.pop(member.id)
                duration = int((now - session["join_time"]).total_seconds())
                database.save_voice_session(
                    user_name=member.display_name,
                    channel_name=session["channel"],
                    join_time=session["join_time"],
                    leave_time=now,
                    duration_seconds=duration
                )

            self.active_sessions[member.id] = {
                "user_name": member.display_name,
                "channel": after.channel.name,
                "join_time": now,
                "is_private": is_private_now
            }
            
            if admin_channel:
                await admin_channel.send(f"🟡 **[{time_str}]** `{member.display_name}` mudou de **{before.channel.name}** para **{after.channel.name}**.")
                
            if public_channel:
                if not was_private and is_private_now:
                    await public_channel.send(f"🔴 **[{time_str}]** `{member.display_name}` desconectou de **{before.channel.name}**.")
                elif was_private and not is_private_now:
                    await public_channel.send(f"🟢 **[{time_str}]** `{member.display_name}` entrou no canal **{after.channel.name}**.")
                elif not was_private and not is_private_now:
                    await public_channel.send(f"🟡 **[{time_str}]** `{member.display_name}` mudou de **{before.channel.name}** para **{after.channel.name}**.")

async def setup(bot):
    await bot.add_cog(VoiceLogs(bot))