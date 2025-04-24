from utils import SiemensEnergy, Siemens, Fraunhofer
import asyncio


async def main():
    fraunhofer = SiemensEnergy()
    async for job in fraunhofer.get_jobs():
        print(job)

if __name__ == "__main__":
    asyncio.run(main())

