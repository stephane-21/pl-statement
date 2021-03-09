
import os
import csv
import pandas
import datetime
import zoneinfo

from dotenv import load_dotenv
load_dotenv()

BASE_CURR = os.getenv("BASE_CURR", "EUR")


#%%
def str2num(mystring):
    myfloat = float(mystring.replace(",", ""))
    return myfloat


#%% Import CSV
file_path = os.getenv("FILEPATH_ACCOUNTS_IB")
assert(file_path)

TABLE = {}
with open(file_path, mode='r', encoding='utf-8-sig') as file:
    file_object = csv.reader(file, delimiter=',', lineterminator='\n')
    for iii, row in enumerate(file_object):
        if iii == 0:
            name = row[0]
            TABLE[name] = []  # New block
            TABLE[name].append([])  # New table
            TABLE[name][-1].append(row[2:])
        elif row[0] == name and row[1] in ["Header",]:
            TABLE[name].append([])  # New table
            TABLE[name][-1].append(row[2:])
        elif row[0] == name and row[1] in ["Data",]:
            TABLE[name][-1].append(row[2:])
        elif row[0] == name and row[1] in ["Total", "SubTotal",]:
            pass
        elif row[0] != name and row[1] in ["Header",]:
            name = row[0]
            TABLE[name] = []  # New block
            TABLE[name].append([])  # New table
            TABLE[name][-1].append(row[2:])
        else:
            print(row)
            assert(False)
    del(iii, row)
    del(name)
del(file, file_object, file_path)

#%% About tables with duplicate names
for key in list(TABLE.keys()):
    if len(TABLE[key]) == 1:
        TABLE[key] = TABLE[key][0]
    else:
        for iii, table in enumerate(TABLE[key]):
            assert(f'{key}_{iii:03}' not in TABLE.keys())
            TABLE[f'{key}_{iii:03}'] = table
        del(iii, table)
        del(TABLE[key])
del(key)

#%% Format to dict or df
for key, table in TABLE.items():
    if table[0] == ['Field Name', 'Field Value']:
        my_dict = {}
        for row in table[1:]:
            my_dict[row[0]] = row[1]
        del(row)
        TABLE[key] = my_dict
        del(my_dict)
    else:
        TABLE[key] = pandas.DataFrame(table[1:])
        TABLE[key].columns = table[0][:len(TABLE[key].columns)]
del(key, table)

#%% Checks and cleaning
assert(TABLE["Statement"]["BrokerName"] == "Interactive Brokers")
assert(TABLE["Statement"]["Title"] == "Activity Statement")
del(TABLE["Statement"])
assert(TABLE["Account Information"]["Base Currency"] == BASE_CURR)
del(TABLE["Account Information"])
assert(str2num(TABLE["Change in NAV"]["Starting Value"]) == 0)
del(TABLE["Notes/Legal Notes"])
del(TABLE["Financial Instrument Information"])
del(TABLE["Net Asset Value_001"])
del(TABLE["Month & Year to Date Performance Summary"])
del(TABLE["Mark-to-Market Performance Summary"])
del(TABLE["Realized & Unrealized Performance Summary"])
del(TABLE["Codes"])


#%%
TRANSACTIONS = []

table = TABLE["Trades_000"]
for row in table.index:
    transaction = {}
    assert(table.at[row, "DataDiscriminator"] == "Order")
    assert(table.at[row, "Asset Category"] == "Stocks")
    transaction["type"] = "Stock"
    transaction["date"] = table.at[row, "Date/Time"]
    transaction["ticker"] = table.at[row, "Symbol"]
    transaction["nb"] = str2num(table.at[row, "Quantity"])
    transaction["cash"] = {table.at[row, "Currency"]: str2num(table.at[row, "Proceeds"]) + str2num(table.at[row, "Comm/Fee"])}
    
    # Trade execution times are displayed in Eastern Time == -0500 -0400
    transaction["date"] = datetime.datetime.strptime(transaction["date"], '%Y-%m-%d, %H:%M:%S')\
                          .replace(tzinfo=zoneinfo.ZoneInfo("US/Eastern")).astimezone(datetime.timezone.utc)
    
    TRANSACTIONS.append(transaction)
    del(transaction)
del(row)
del(table, TABLE["Trades_000"])

table = TABLE["Trades_001"]
for row in table.index:
    transaction = {}
    assert(table.at[row, "DataDiscriminator"] == "Order")
    assert(table.at[row, "Asset Category"] == "Forex")
    transaction["type"] = "Forex"
    transaction["date"] = table.at[row, "Date/Time"]
    curr_1 = table.at[row, "Symbol"].split(".")[0]
    curr_2 = table.at[row, "Symbol"].split(".")[1]
    assert(curr_1 == BASE_CURR)
    assert(curr_2 == table.at[row, "Currency"])
    transaction["cash"] = {curr_1: str2num(table.at[row, "Quantity"]),
                           curr_2: str2num(table.at[row, "Proceeds"])}
    transaction["cash"][BASE_CURR] += str2num(table.at[row, f'Comm in {BASE_CURR}'])
    
    # Trade execution times are displayed in Eastern Time == -0500 or DST -0400
    transaction["date"] = datetime.datetime.strptime(transaction["date"], '%Y-%m-%d, %H:%M:%S')\
                          .replace(tzinfo=zoneinfo.ZoneInfo("US/Eastern")).astimezone(datetime.timezone.utc)
    
    TRANSACTIONS.append(transaction)
    del(transaction, curr_1, curr_2)
del(row)
del(table, TABLE["Trades_001"])

table = TABLE["Corporate Actions"]
for row in table.index:
    if table.at[row, "Asset Category"] == "Stocks":
        transaction = {}
        transaction["type"] = "Split"
        assert(str2num(table.at[row, "Proceeds"]) == 0)
        transaction["date"] = table.at[row, "Date/Time"]
        transaction["cash"] = {table.at[row, "Currency"]: 0}
        transaction["nb"] = str2num(table.at[row, "Quantity"])
        
        mytext = table.at[row, "Description"]
        transaction["ticker"] = mytext.split("(")[0]
        transaction["isin"] = mytext.split("(")[1].split(")")[0]
        transaction["name"] = mytext.split(f'{transaction["ticker"]}, ')[1].split(f', {transaction["isin"]}')[0]
        transaction["split"] = str2num(mytext.split(") Split ")[1].split(" for ")[0])\
                               / str2num(mytext.split(" for ")[1].split(f' ({transaction["ticker"]}')[0])
        
        # Trade execution times are displayed in Eastern Time == -0500 or DST -0400
        transaction["date"] = datetime.datetime.strptime(transaction["date"], '%Y-%m-%d, %H:%M:%S')\
                              .replace(tzinfo=zoneinfo.ZoneInfo("US/Eastern")).astimezone(datetime.timezone.utc)
        
        TRANSACTIONS.append(transaction)
        del(transaction, mytext)
del(row)
del(table, TABLE["Corporate Actions"])

table = TABLE["Deposits & Withdrawals"]
for row in table.index:
    if not table.at[row, "Currency"].startswith("Total"):
        transaction = {}
        transaction["type"] = "CashTransfer"
        transaction["date"] = table.at[row, "Settle Date"]
        transaction["cash"] = {table.at[row, "Currency"]: str2num(table.at[row, "Amount"])}
        
        # Trade execution times are displayed in Eastern Time == -0500 or DST -0400
        transaction["date"] = datetime.datetime.strptime(transaction["date"], '%Y-%m-%d')\
                              .replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc)
        
        TRANSACTIONS.append(transaction)
        del(transaction)
del(row)
del(table, TABLE["Deposits & Withdrawals"])























TABLE["Dividends"]
TABLE["Change in Dividend Accruals"]






