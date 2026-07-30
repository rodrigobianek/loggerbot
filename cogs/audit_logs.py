from datetime import datetime
import discord
from discord.ext import commands
import config


class AuditLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------------------------------------
    # 1. MUDANÇAS DE CARGOS EM MEMBROS
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles == after.roles:
            return

        print(f"🔍 [DEBUG] Alteração de cargos detectada para: {after.display_name}")

        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
            print("⚠️ [DEBUG] Canal de log não encontrado. Verifique config.ADMIN_LOG_CHANNEL_ID.")
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
            print(f"⚠️ [DEBUG] Falha ao buscar Audit Log (Falta de permissão?): {e}")

        if added_roles:
            await admin_channel.send(
                f"🛡️ **[{now}] Audit:** `{executor}` concedeu o(s) cargo(s) `{', '.join(added_roles)}` para `{after.display_name}`."
            )
        if removed_roles:
            await admin_channel.send(
                f"🛡️ **[{now}] Audit:** `{executor}` removeu o(s) cargo(s) `{', '.join(removed_roles)}` de `{after.display_name}`."
            )

    # ---------------------------------------------------------
    # 2. MENSAGENS DELETADAS
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        print(f"🗑️ [DEBUG] Mensagem apagada no canal #{getattr(message.channel, 'name', 'Desconhecido')}")

        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
            print("⚠️ [DEBUG] Canal de log não encontrado. Verifique config.ADMIN_LOG_CHANNEL_ID.")
            return

        channel_name = message.channel.name if hasattr(message.channel, 'name') else "Canal Desconhecido"
        content = message.content if message.content else "*[Mensagem sem texto / apenas anexo ou embed]*"
        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        msg = (
            f"🗑️ **[{time_str}]** Mensagem de `{message.author.display_name}` "
            f"foi apagada no canal **#{channel_name}**:\n"
            f"> {content}"
        )
        await admin_channel.send(msg)

    # ---------------------------------------------------------
    # 3. ALTERAÇÃO EM CANAL (Ex: Mudou de nome)
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if before.name == after.name:
            return

        print(f"⚙️ [DEBUG] Canal renomeado: #{before.name} -> #{after.name}")

        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
            print("⚠️ [DEBUG] Canal de log não encontrado. Verifique config.ADMIN_LOG_CHANNEL_ID.")
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        executor = "Desconhecido/Sistema"
        try:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
                if entry.target.id == after.id:
                    executor = entry.user.display_name
                    break
        except Exception as e:
            print(f"⚠️ [DEBUG] Falha ao buscar Audit Log: {e}")

        msg = (
            f"⚙️ **[{time_str}] Audit:** `{executor}` renomeou o canal "
            f"de **#{before.name}** para **#{after.name}**."
        )
        await admin_channel.send(msg)

    # ---------------------------------------------------------
    # 4. CRIAÇÃO DE CANAL
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        print(f"➕ [DEBUG] Novo canal criado: #{channel.name}")

        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
            print("⚠️ [DEBUG] Canal de log não encontrado. Verifique config.ADMIN_LOG_CHANNEL_ID.")
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        executor = "Desconhecido/Sistema"
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
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
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        print(f"➖ [DEBUG] Canal deletado: #{channel.name}")

        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
            print("⚠️ [DEBUG] Canal de log não encontrado. Verifique config.ADMIN_LOG_CHANNEL_ID.")
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        executor = "Desconhecido/Sistema"
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    executor = entry.user.display_name
                    break
        except Exception as e:
            print(f"⚠️ [DEBUG] Falha ao buscar Audit Log: {e}")

        msg = f"➖ **[{time_str}] Audit:** `{executor}` deletou o canal **#{channel.name}**."
        await admin_channel.send(msg)


async def setup(bot):
    await bot.add_cog(AuditLogs(bot))