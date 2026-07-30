from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import config
import database

async def send_daily_report(bot):
    admin_channel = bot.get_channel(config.ADMIN_LOG_CHANNEL_ID)
    if not admin_channel:
        return

    today_str = datetime.now(config.TIMEZONE).strftime("%Y-%m-%d")
    logs = database.get_logs_by_date(today_str)
    
    if not logs:
        await admin_channel.send(f"⏰ **Relatório Diário ({today_str}):** Nenhuma atividade gravada hoje.")
        return

    report = f"📊 **Relatório Automático Diário Admin ({today_str}):**\n"
    for user_name, channel_name, _, _, duration in logs:
        report += f"• `{user_name}` ficou {duration // 60}m no canal `{channel_name}`\n"
        
    await admin_channel.send(report)

def start_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
    scheduler.add_job(send_daily_report, "cron", hour=23, minute=59, args=[bot])
    scheduler.start()