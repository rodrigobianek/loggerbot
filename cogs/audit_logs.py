from datetime import datetime
import discord
from discord.ext import commands
import config


class AuditLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_log_channel(self):
        """Busca o canal de log garantindo que o ID seja int e usando fetch_channel caso não esteja no cache."""
        try:
            channel_id = int(config.ADMIN_LOG_CHANNEL_ID)
            channel = self.bot.get_channel(channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(channel_id)
            return channel
        except Exception as e:
            print(f"⚠️ [DEBUG] Erro ao localizar o canal de log ({config.ADMIN_LOG_CHANNEL_ID}): {e}")
            return None

    # --------------------------------------------------------
    # 1. MUDANÇAS DE CARGOS EM MEMBROS
    # --------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return

        print(f"🔍 [DEBUG] Alteração de cargos detectada para: {after.display_name}")

        admin_channel = await self._get_log_channel()
        if not admin_channel:
            return

        now = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")
        added_roles = [role.name for role in after.roles if role not in before.roles]
        removed_roles = [role.name for role in before.roles if role not in after.roles]

        executor = "Desconhecido/Sistema"
        try:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    executor = entry.user.display_name
                    break
        except Exception as e:
            print(f"⚠️ [DEBUG] Falha ao buscar Audit Log: {e}")

        if added_roles:
            await admin_channel.send(
                f"🛡️ **[{now}] Audit:** `{executor}` concedeu o(s) cargo(s) `{', '.join(added_roles)}` para `{after.display_name}`."
            )
        if removed_roles:
            await admin_channel.send(
                f"🛡️ **[{now}] Audit:** `{executor}` removeu o(s) cargo(s) `{', '.join(removed_roles)}` de `{after.display_name}`."
            )

    # ---------------------------------------------------------
    # 2. MENSAGENS DELETADAS (RAW)
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        print(f"🗑️ [DEBUG RAW] Mensagem apagada no canal ID {payload.channel_id} (Msg ID: {payload.message_id})")

        admin_channel = await self._get_log_channel()
        if not admin_channel:
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        if payload.cached_message:
            message = payload.cached_message
            if message.author.bot:
                return

            channel_name = message.channel.name if hasattr(message.channel, 'name') else "Canal Desconhecido"
            content = message.content if message.content else "*[Mensagem sem texto / apenas anexo ou embed]*"

            msg = (
                f"🗑️ **[{time_str}]** Mensagem de `{message.author.display_name}` "
                f"foi apagada no canal **#{channel_name}**:\n"
                f"> {content}"
            )
        else:
            msg = (
                f"🗑️ **[{time_str}]** Uma mensagem antiga (fora do cache) "
                f"foi apagada no canal <#{payload.channel_id}>. `(ID da msg: {payload.message_id})`"
            )

        await admin_channel.send(msg)

    # ---------------------------------------------------------
    # 3. ALTERAÇÃO EM CANAL (Nome, Tópico, Slowmode, Permissões, etc.)
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        print(f"⚙️ [DEBUG] Evento on_guild_channel_update disparado para #{after.name}")

        changes = []

        # 1. Mudança de Nome
        if before.name != after.name:
            changes.append(f"Nome alterado de `#{before.name}` para `#{after.name}`")

        # 2. Mudança de Tópico (Descrição)
        if getattr(before, 'topic', None) != getattr(after, 'topic', None):
            old_topic = before.topic if before.topic else "*[Vazio]*"
            new_topic = after.topic if after.topic else "*[Vazio]*"
            changes.append(f"Tópico alterado: de `{old_topic}` para `{new_topic}`")

        # 3. Mudança de Modo Lento (Slowmode)
        if getattr(before, 'slowmode_delay', None) != getattr(after, 'slowmode_delay', None):
            changes.append(f"Modo lento alterado de `{before.slowmode_delay}s` para `{after.slowmode_delay}s`")

        # 4. Mudança de Status NSFW
        if getattr(before, 'nsfw', None) != getattr(after, 'nsfw', None):
            changes.append(f"Status NSFW alterado de `{before.nsfw}` para `{after.nsfw}`")

        # Se nada do que acompanhamos mudou (ex: apenas sincronização de permissões internas), ignoramos
        if not changes:
            print("⚙️ [DEBUG] Alteração técnica ignorada (nenhuma mudança de nome, tópico ou configurações visíveis).")
            return

        admin_channel = await self._get_log_channel()
        if not admin_channel:
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        executor = "Desconhecido/Sistema"
        try:
            async for entry in after.guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_update):
                if entry.target.id == after.id:
                    executor = entry.user.display_name
                    break
        except Exception as e:
            print(f"⚠️ [DEBUG] Falha ao buscar Audit Log: {e}")

        detalhes = "\n> ".join(changes)
        msg = (
            f"⚙️ **[{time_str}] Audit:** Canal **#{after.name}** foi modificado por `{executor}`:\n"
            f"> {detalhes}"
        )
        await admin_channel.send(msg)

    # ---------------------------------------------------------
    # 4. CRIAÇÃO DE CANAL
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        print(f"➕ [DEBUG] Novo canal criado: #{channel.name}")

        admin_channel = await self._get_log_channel()
        if not admin_channel:
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        executor = "Desconhecido/Sistema"
        try:
            async for entry in channel.guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id:
                    executor = entry.user.display_name
                    break
        except Exception as e:
            print(f"⚠️ [DEBUG] Falha ao buscar Audit Log: {e}")

        msg = f"➕ **[{time_str}] Audit:** `{executor}` criou o canal **#{channel.name}**."
        await admin_channel.send(msg)

    # ---------------------------------------------------------
    # 5. EXCLUSÃO DE CANAL
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        print(f"➖ [DEBUG] Canal deletado: #{channel.name}")

        admin_channel = await self._get_log_channel()
        if not admin_channel:
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        executor = "Desconhecido/Sistema"
        try:
            async for entry in channel.guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    executor = entry.user.display_name
                    break
        except Exception as e:
            print(f"⚠️ [DEBUG] Falha ao buscar Audit Log: {e}")

        msg = f"➖ **[{time_str}] Audit:** `{executor}` deletou o canal **#{channel.name}**."
        await admin_channel.send(msg)


async def setup(bot):
    await bot.add_cog(AuditLogs(bot))