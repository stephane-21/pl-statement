
import os
import csv
from dotenv import load_dotenv

load_dotenv()
BASE_CURR = os.getenv("BASE_CURR", "EUR")


#%%
file_path = os.getenv("FILEPATH_ACCOUNTS_IB")
assert(file_path)

TABLE = []
with open(file_path) as file:
    file_object = csv.reader(file, delimiter=',', lineterminator='\n')
    for iii, row in enumerate(file_object):
        if iii == 0:
            TABLE.append([])
            TABLE[-1].append(row)
        elif row[1] =="Header":
            TABLE.append([])
            TABLE[-1].append(row)
        else:
            TABLE[-1].append(row)










