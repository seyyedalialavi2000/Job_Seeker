from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, date
from pydantic import HttpUrl
from typing import Optional, List
from os import getenv

from schemas import Job


class MongoDBManager:
    def __init__(
            self,
            mongo_uri: str=getenv("URI"),
            db_name: str=getenv("DB_NAME"),
            collection_name: str=getenv("COLECTION_NAME")
        ):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    async def ping(self):
        """
        Pings the MongoDB deployment to check the connection.
        """
        try:
            await self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")

    async def close_connection(self):
        """Closes the MongoDB connection."""
        self.client.close()

    async def add_job(self, job: Job) -> str:
        """
        Adds a single Job object to the database.

        Args:
            job: The Job object to add.

        Returns:
            The inserted document's ObjectId as a string.
        """
        job_dict = job.model_dump()

        if 'create_time' not in job_dict or job_dict['create_time'] is None:
            job_dict['create_time'] = datetime.utcnow()

        if 'update_time' not in job_dict or job_dict['update_time'] is None:
            job_dict['update_time'] = job_dict['create_time']

        result = await self.collection.insert_one(job_dict)
        return str(result.inserted_id)

    async def job_exists(self, job_url: HttpUrl) -> bool:
        """
        Checks if a job with the given URL exists in the database.

        Args:
            job_url: The URL of the job to check.

        Returns:
            True if the job exists, False otherwise.
        """
        count = await self.collection.count_documents({"url": str(job_url)})
        return count > 0

    async def get_job_by_url(self, job_url: HttpUrl) -> Optional[Job]:
        """
        Retrieves a job by its URL.

        Args:
            job_url: The URL of the job.

        Returns:
            The Job object if found, None otherwise.
        """
        document = await self.collection.find_one({"url": str(job_url)})
        if document:
            return Job(**document)
        return None

    async def find_jobs(self, query: dict = None, limit: int = 0) -> List[Job]:
        """
        Finds jobs based on a query.

        Args:
            query: A MongoDB query dictionary. Defaults to an empty query (all jobs).
            limit: The maximum number of results to return. Defaults to 0 (no limit).

        Returns:
            A list of Job objects.
        """
        query = query or {}
        cursor = self.collection.find(query)

        if limit > 0:
            cursor = cursor.limit(limit)

        documents = await cursor.to_list(length=None)
        return [Job(**doc) for doc in documents]

    async def delete_job(self, job_url: HttpUrl) -> bool:
        """
        Deletes a job document by its URL.

        Args:
            job_url: The URL of the job to delete.

        Returns:
            True if the job was deleted, False otherwise.
        """
        try:
            result = await self.collection.delete_one({"url": str(job_url)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting job: {e}")
            return False

    async def get_last_n_days_update(self, days: int) -> List[Job]:
        """
        Retrieves jobs updated in the last n days.

        Args:
            days: The number of days to look back.

        Returns:
            A list of Job objects.
        """
        if days < 0:
            return []
        
        time_threshold = datetime.utcnow() - timedelta(days=days)

        query = {"update_time": {"$gte": time_threshold}}
        return await self.find_jobs(query)

    async def get_last_n_days_create(self, days: int) -> List[Job]:
        """
        Retrieves jobs created in the last n days.

        Args:
            days: The number of days to look back.

        Returns:
            A list of Job objects.
        """
        if days < 0:
            return []
        
        time_threshold = datetime.utcnow() - timedelta(days=days)

        query = {"create_time": {"$gte": time_threshold}}
        return await self.find_jobs(query)

    async def get_jobs_by_date(self, target_date: date) -> List[Job]:
        """
        Retrieves jobs created or updated on a specific date.

        Args:
            target_date: The specific date to search for jobs.

        Returns:
            A list of Job objects.
        """
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())

        query = {
            "$or": [
                {"create_time": {"$gte": start_of_day, "$lt": end_of_day}},
                {"update_time": {"$gte": start_of_day, "$lt": end_of_day}}
            ]
        }
        return await self.find_jobs(query)

    async def get_all_job_urls(self) -> List[HttpUrl]:
        """
        Retrieves a list of all job URLs from the database as HttpUrl objects.

        Returns:
            A list of job URLs as HttpUrl objects.
        """
        cursor = self.collection.find({}, {'url': 1, '_id': 0})
        documents = await cursor.to_list(length=None)
        return [HttpUrl(doc['url']) for doc in documents if 'url' in doc]

mongo_handler = MongoDBManager()

