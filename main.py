from dotenv import load_dotenv
load_dotenv()
import asyncio
from os import getenv
from dataclasses import dataclass
from typing import Type
from telegram import Bot
from aioclock import AioClock, Every
from telegram.ext import Application, ApplicationBuilder

from utils import SiemensEnergy, Siemens, Fraunhofer, setup_logging, get_logger
from databse import mongo_handler
from schemas import Job

TELEGRAM_BOT_TOKEN = getenv("BOT_TOKEN")
TELEGRAM_CHANNEL_ID = getenv("CHANNEL_ID")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")
if not TELEGRAM_CHANNEL_ID:
    raise ValueError("TELEGRAM_CHANNEL_ID environment variable not set.")

setup_logging()
logger = get_logger(__name__)

@dataclass
class CrawlerMetadata:
    """Metadata for registering a crawler with scheduling info."""
    name: str
    cls: Type
    interval: int  # minutes


CRAWLER_REGISTRY = [
    CrawlerMetadata("SiemensEnergy", SiemensEnergy, interval=10),
    CrawlerMetadata("Siemens", Siemens, interval=10),
    CrawlerMetadata("Fraunhofer", Fraunhofer, interval=10),
]

ptb_app: Application | None = None

async def send_new_job_notification(bot: Bot, job: Job):
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


async def run_crawler(crawler_meta: CrawlerMetadata):
    """Generic runner logic for any crawler - runs independently."""
    global ptb_app
    
    logger.info(f"Starting {crawler_meta.name} crawl cycle")
    
    crawler = crawler_meta.cls()
    urls = await mongo_handler.get_all_job_urls()
    
    async for job in crawler.get_jobs():
        if job.url not in urls:
            await mongo_handler.add_job(job)
            await send_new_job_notification(ptb_app.bot, job)
            urls.append(job.url)
            await asyncio.sleep(5)
    
    logger.info(f"Completed {crawler_meta.name} crawl cycle")


def register_crawler_tasks():
    """Dynamically register each crawler as an independent scheduled task."""
    for meta in CRAWLER_REGISTRY:
        # Create a proper closure by using a factory function
        def make_task(crawler_meta: CrawlerMetadata):
            @app.task(trigger=Every(minutes=crawler_meta.interval))
            async def crawler_task():
                await run_crawler(crawler_meta)
            # Give it a proper name for debugging
            crawler_task.__name__ = f"crawl_{crawler_meta.name}"
            return crawler_task
        
        make_task(meta)


app = AioClock()
register_crawler_tasks()


async def main():
    global ptb_app

    logger.info("Initializing Telegram Bot...")
    ptb_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    logger.info("Starting AioClock scheduler and Telegram Bot polling...")

    async with mongo_handler:
        async with ptb_app:
            await ptb_app.updater.start_polling()
            logger.info("Telegram Bot polling started.")

            await app.serve()
            logger.info("AioClock scheduler started.")


if __name__ == "__main__":
    asyncio.run(main())

