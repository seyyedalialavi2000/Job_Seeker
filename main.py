from utils import SiemensEnergy, Siemens

if __name__ == "__main__":
    se = Siemens()
    for job in se.get_jobs():
        print(job)
        print(80*'*')

