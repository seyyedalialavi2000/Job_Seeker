from dotenv import load_dotenv
load_dotenv()
import asyncio
import logging
from os import getenv
from telegram import Bot
from aioclock import AioClock, Every
from telegram.ext import Application, ApplicationBuilder

from utils import SiemensEnergy, Siemens, Fraunhofer
from databse import mongo_handler
from schemas import Job

TELEGRAM_BOT_TOKEN = getenv("BOT_TOKEN")
TELEGRAM_CHANNEL_ID = getenv("CHANNEL_ID")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")
if not TELEGRAM_CHANNEL_ID:
    raise ValueError("TELEGRAM_CHANNEL_ID environment variable not set.")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

ptb_app: Application | None = None

async def send_new_job_notification(bot: Bot, job: Job):
    logger.info(f"New job found: {job.title} - {job.url}")

    message_text = (
        f"New Job "
        f"#{job.company}\n"
        f"{job.title}\n"
        f"{job.location}\n"
        f"{job.url}\n"
    )
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            text=message_text
        )
        logger.info(f"Notification sent to channel {TELEGRAM_CHANNEL_ID} for job: {job.url}")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification for job {job.url}: {e}")


app = AioClock()
@app.task(trigger=Every(minutes=10))
async def crawl():
    global ptb_app

    logger.info("Started crawling cycle...")
    urls = await mongo_handler.get_all_job_urls()
    for cwl in [SiemensEnergy(), Siemens(), Fraunhofer()]:
        async for job in cwl.get_jobs():
            if job.url not in urls:
                await mongo_handler.add_job(job)
                await send_new_job_notification(ptb_app.bot, job)
                urls.append(job.url)
                await asyncio.sleep(10)


async def main():
    global ptb_app

    logger.info("Initializing Telegram Bot...")
    ptb_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    logger.info("Starting AioClock scheduler and Telegram Bot polling...")

    async with ptb_app:
        await ptb_app.updater.start_polling()
        logger.info("Telegram Bot polling started.")

        await app.serve()
        logger.info("AioClock scheduler started.")


if __name__ == "__main__":
    asyncio.run(main())

