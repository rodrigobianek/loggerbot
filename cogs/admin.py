from datetime import datetime
import csv
import io
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
import config
import database

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="log", description="[ADMIN] Consulta os registros de voz do servidor.")
    @app_commands.describe(data="Data da consulta no formato AAAA-MM-DD. Deixe em branco para o dia de hoje.")
    async def fetch_log(self, interaction: discord.Interaction, data: str = None):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Permissão negada. Comando restrito a Administradores.", ephemeral=True)
            return

        if not data:
            data = datetime.now(config.TIMEZONE).strftime("%Y-%m-%d")

        logs = database.get_logs_by_date(data)
        if not logs:
            await interaction.response.send_message(f"Nenhum registro encontrado para a data: `{data}`.", ephemeral=True)
            return

        response = f"📋 **[ADMIN] Relatório de Atividade de Voz - {data}**\n\n"
        for user_name, channel_name, join_time, leave_time, duration in logs:
            mins, secs = duration // 60, duration % 60
            entry_time = join_time.split(" ")[1] if " " in join_time else join_time
            exit_time = leave_time.split(" ")[1] if " " in leave_time else leave_time
            response += f"• **{user_name}** | Canal: `{channel_name}` | Permanência: {mins}m {secs}s ({entry_time} às {exit_time})\n"

        if len(response) > 2000:
            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
            await interaction.response.send_message(chunks[0], ephemeral=True)
            for chunk in chunks[1:]:
                await interaction.followup.send(chunk, ephemeral=True)
        else:
            await interaction.response.send_message(response, ephemeral=True)

    @app_commands.command(name="export_db", description="[CARGO BOT] Exporta os dados do banco em formato CSV para Excel/Planilhas.")
    async def export_db(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        is_owner = (guild and user.id == guild.owner_id)
        has_bot_role = hasattr(user, "roles") and any(role.name.lower() == "bot" for role in user.roles)

        if not is_owner and not has_bot_role:
            await interaction.response.send_message(
                f"❌ Permissão negada para `{user.display_name}`. Este comando exige o cargo **Bot**.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM voice_logs ORDER BY id DESC")
            rows = cursor.fetchall()
            column_names = [description[0] for description in cursor.description]
            conn.close()
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao ler a base de dados: `{e}`", ephemeral=True)
            return

        if not rows:
            await interaction.followup.send("⚠️ Nenhum registro encontrado na base de dados para exportar.", ephemeral=True)
            return

        output = io.StringIO()
        output.write('\ufeff')  # BOM para o Excel identificar UTF-8
        writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(column_names)
        writer.writerows(rows)

        output.seek(0)
        file_bytes = io.BytesIO(output.getvalue().encode('utf-8-sig'))
        
        file_name = f"relatorio_voz_{datetime.now(config.TIMEZONE).strftime('%Y-%m-%d_%H%M')}.csv"
        discord_file = discord.File(fp=file_bytes, filename=file_name)

        await interaction.followup.send(
            f"📊 Aqui está o seu relatório extraído em **CSV** ({len(rows)} registros encontrados):",
            file=discord_file,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))