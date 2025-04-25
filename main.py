from dotenv import load_dotenv
load_dotenv()
import asyncio
from aioclock import AioClock, Every

from utils import SiemensEnergy, Siemens, Fraunhofer
from databse import mongo_handler


app = AioClock()
@app.task(trigger=Every(minutes=10))
async def crawl():
    urls = await mongo_handler.get_all_job_urls()
    for cwl in [SiemensEnergy(), Siemens(), Fraunhofer()]:
        async for job in cwl.get_jobs():
            if job.url not in urls:
                await mongo_handler.add_job(job)


if __name__ == "__main__":
    asyncio.run(app.serve())

