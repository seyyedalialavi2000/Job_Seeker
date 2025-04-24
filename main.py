from dotenv import load_dotenv
load_dotenv()
from pydantic import HttpUrl
import asyncio

from utils import SiemensEnergy, Siemens, Fraunhofer
from schemas import Job
from databse import mongo_handler


async def main():
    # new_job = Job(
    #     title="Data Scientist",
    #     url="https://example.com/job/456",
    #     location="New York",
    #     remote_vs_office="Office"
    # )
    # await mongo_handler.ping()

    # inserted_id = await mongo_handler.add_job(new_job)
    # print(f"Inserted job with ID: {inserted_id}")

    # exists = await mongo_handler.job_exists(new_job.url)
    # print(f"Does job with URL {new_job.url} exist? {exists}")

    # non_existent_url = HttpUrl("https://example.com/job/nonexistent")
    # exists_non_existent = await mongo_handler.job_exists(non_existent_url)
    # print(f"Does job with URL {non_existent_url} exist? {exists_non_existent}")

    # await mongo_handler.close_connection()
    fraunhofer = Siemens()
    async for job in fraunhofer.get_jobs():
        print(80*"*")

if __name__ == "__main__":
    asyncio.run(main())

