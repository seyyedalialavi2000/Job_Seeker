import asyncio
from aioclock import AioClock, Every

from crawlers.registry import CrawlerMetadata, CRAWLER_REGISTRY
from databse import mongo_handler
from utils import get_logger
from utils.telegram import send_new_job_notification

logger = get_logger(__name__)

# Global reference to Telegram bot app
ptb_app = None


def set_telegram_app(app):
    """Set the global Telegram bot application reference."""
    global ptb_app
    ptb_app = app


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
            await asyncio.sleep(5)
        else:
            pass  # TO DO: break the cycle on first existing job to avoid redundant checks
    
    logger.info(f"Completed {crawler_meta.name} crawl cycle")


def register_crawler_tasks(app: AioClock):
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
