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
        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
            return

        if before.roles != after.roles:
            now = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")
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

    # ---------------------------------------------------------
    # 2. MENSAGENS DELETADAS
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
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
        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        # Tenta buscar no Registro de Auditoria quem alterou
        executor = "Desconhecido/Sistema"
        try:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
                if entry.target.id == after.id:
                    executor = entry.user.display_name
                    break
        except Exception:
            pass

        # Detecta mudança no NOME do canal
        if before.name != after.name:
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
        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        executor = "Desconhecido/Sistema"
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
                if entry.target.id == channel.id:
                    executor = entry.user.display_name
                    break
        except Exception:
            pass

        msg = f"➕ **[{time_str}] Audit:** `{executor}` criou o canal **#{channel.name}**."
        await admin_channel.send(msg)

    # ---------------------------------------------------------
    # 5. EXCLUSÃO DE CANAL
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        admin_channel = self.bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
        if not admin_channel:
            return

        time_str = datetime.now(config.TIMEZONE).strftime("%H:%M:%S")

        executor = "Desconhecido/Sistema"
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                if entry.target.id == channel.id:
                    executor = entry.user.display_name
                    break
        except Exception:
            pass

        msg = f"➖ **[{time_str}] Audit:** `{executor}` deletou o canal **#{channel.name}**."
        await admin_channel.send(msg)


async def setup(bot):
    await bot.add_cog(AuditLogs(bot))