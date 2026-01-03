from dotenv import load_dotenv
load_dotenv()
import asyncio
from os import getenv
from aioclock import AioClock
from telegram.ext import ApplicationBuilder

from utils import setup_logging, get_logger
from database import mongo_handler
from crawlers import register_crawler_tasks
from crawlers.runner import set_telegram_app

TELEGRAM_BOT_TOKEN = getenv("BOT_TOKEN")
TELEGRAM_CHANNEL_ID = getenv("CHANNEL_ID")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")
if not TELEGRAM_CHANNEL_ID:
    raise ValueError("TELEGRAM_CHANNEL_ID environment variable not set.")

setup_logging()
logger = get_logger(__name__)

app = AioClock()
register_crawler_tasks(app)


async def main():
    logger.info("Initializing Telegram Bot...")
    ptb_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    set_telegram_app(ptb_app)

    logger.info("Starting AioClock scheduler and Telegram Bot polling...")

    async with mongo_handler:
        async with ptb_app:
            await ptb_app.updater.start_polling()
            logger.info("Telegram Bot polling started.")

            await app.serve()
            logger.info("AioClock scheduler started.")


if __name__ == "__main__":
    asyncio.run(main())

