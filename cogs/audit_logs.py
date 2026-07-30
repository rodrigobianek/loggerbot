from datetime import datetime
import discord
from discord.ext import commands
import config

class AuditLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Captura QUALQUER erro interno que aconteça dentro dos listeners desse Cog
    async def cog_command_error(self, ctx, error):
        print(f"❌ [ERRO NO COG]: {error}")

    # Listener Genérico de Erros para Eventos Async
    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        import traceback
        print(f"❌ [ERRO NO EVENTO]: {event}")
        traceback.print_exc()

    # ---------------------------------------------------------
    # TESTE DIRETO: MENSAGENS DELETADAS (RAW)
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        print("\n==========================================")
        print(f"🔥 [EVENTO DETECTADO] Mensagem Deletada!")
        print(f"   Canal ID: {payload.channel_id} | Msg ID: {payload.message_id}")
        print("==========================================\n")

    # ---------------------------------------------------------
    # TESTE DIRETO: QUALQUER ATUALIZAÇÃO EM CANAIS
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        print("\n==========================================")
        print(f"🔥 [EVENTO DETECTADO] Canal Alterado!")
        print(f"   Nome Antes: {before.name} | Nome Depois: {after.name}")
        print(f"   Tipo de Objeto: {type(after)}")
        print("==========================================\n")

    # ---------------------------------------------------------
    # TESTE DIRETO: ATUALIZAÇÃO DE CATEGORIAS
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        print(f"🔥 [EVENTO DETECTADO] Canal Criado: {channel.name}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        print(f"🔥 [EVENTO DETECTADO] Canal Deletado: {channel.name}")

async def setup(bot):
    await bot.add_cog(AuditLogs(bot))
    