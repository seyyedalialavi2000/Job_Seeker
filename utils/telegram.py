from os import getenv
from telegram import Bot

from schemas import Job
from utils import get_logger

logger = get_logger(__name__)

TELEGRAM_CHANNEL_ID = getenv("CHANNEL_ID")


async def send_new_job_notification(bot: Bot, job: Job):
    """
    Sends a notification to the configured Telegram channel about a new job.
    
    Args:
        bot: The Telegram Bot instance
        job: The Job object to notify about
    """
    logger.info(f"New job found: {job.title} - {job.url}")

    message_text = (
        f"#{job.company}\n\n"
        f"Title: {job.title}\n\n"
        f"ID: {job.job_id}\n\n"
        f"Location: {job.location}\n\n"
        f"Created at: {job.create_time}\n\n"
        f"Updated at: {job.update_time}\n\n"
        f"Remote Vs Office: {job.remote_vs_office}\n\n"
        f"URL: {job.url}"
    )
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            text=message_text
        )
        logger.info(f"Notification sent to channel {TELEGRAM_CHANNEL_ID} for job: {job.url}")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification for job {job.url}: {e}")
