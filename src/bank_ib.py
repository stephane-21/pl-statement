
import os
import csv
import numpy
import pandas
import datetime
import zoneinfo
import json

from src.wallet import Wallet

from dotenv import load_dotenv
load_dotenv()


#%%
def str2num(mystring):
    myfloat = float(mystring.replace(",", ""))
    return myfloat


#%%
def import_csv(file_path):
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
                print(f'ERROR : {row}')
                assert(False)
        del(iii, row)
        del(name)
    del(file, file_object, file_path)
    
    #%% About tables with duplicate names
    for key in list(TABLE.keys()):
        if len(TABLE[key]) == 1:
            TABLE[key] = TABLE[key][0]
        else:
            for iii in reversed(range(len(TABLE[key]))):
                table = TABLE[key][iii]
                if iii == 0:
                    TABLE[key] = table
                else:
                    assert(f'{key}_{iii+1:03}' not in TABLE.keys())
                    TABLE[f'{key}_{iii+1:03}'] = table
            del(iii, table)
    del(key)
    for key in list(TABLE.keys()):
        if "/" in key:
            TABLE[key.replace("/", "|")] = TABLE.pop(key)
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
    
    
    #%% Export XLS
    writer = pandas.ExcelWriter(f'output/output_IB_000_raw_{TABLE["Account Information"]["Account"]}.xlsx')
    for key, table in TABLE.items():
        try:
            if type(table) is dict:
                pandas.DataFrame.from_dict(table, orient='index').to_excel(writer, key[0:31], header=False, index=True)
            elif type(table) is pandas.core.frame.DataFrame:
                table.to_excel(writer, key[0:31], header=True, index=False)
            else:
                print(f'WARNING : Unknown content : {key} : {type(table)}')
        except ValueError:
            print(f'WARNING : Cannot export tab : {key}')
    del(key, table)
    writer.save()
    del(writer)
    
    
    
    #%% Checks and cleaning
    assert(TABLE["Statement"]["BrokerName"] == "Interactive Brokers")
    assert(TABLE["Statement"]["Title"] == "Activity Statement")
    del(TABLE["Statement"])
    BASE_CURR = TABLE["Account Information"]["Base Currency"]
    del(TABLE["Account Information"])
    del(TABLE["Notes|Legal Notes"])
    del(TABLE["Financial Instrument Information"])
    del(TABLE["Net Asset Value"])
    del(TABLE["Net Asset Value_002"])
    if "Net Asset Value_003" in TABLE:
        del(TABLE["Net Asset Value_003"])
    del(TABLE["Month & Year to Date Performance Summary"])
    del(TABLE["Mark-to-Market Performance Summary"])
    del(TABLE["Realized & Unrealized Performance Summary"])
    del(TABLE["Codes"])
    if "Change in Dividend Accruals" in TABLE:
        del(TABLE["Change in Dividend Accruals"])
    del(TABLE["Change in NAV"])
    del(TABLE["Transfers"])
    
    
    #%%
    TRANSACTIONS = []
    
    table = TABLE["Trades"]
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
                              .replace(tzinfo=zoneinfo.ZoneInfo("US/Eastern")).astimezone(datetime.timezone.utc).isoformat()
        
        TRANSACTIONS.append(transaction)
        del(transaction)
    del(row)
    del(table, TABLE["Trades"])
    
    if "Trades_002" in TABLE:
        table = TABLE["Trades_002"]
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
                                  .replace(tzinfo=zoneinfo.ZoneInfo("US/Eastern")).astimezone(datetime.timezone.utc).isoformat()
            
            TRANSACTIONS.append(transaction)
            del(transaction, curr_1, curr_2)
        del(row)
        del(table, TABLE["Trades_002"])
    
    if "Corporate Actions" in TABLE:
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
                                      .replace(tzinfo=zoneinfo.ZoneInfo("US/Eastern")).astimezone(datetime.timezone.utc).isoformat()
                
                TRANSACTIONS.append(transaction)
                del(transaction, mytext)
        del(row)
        del(table, TABLE["Corporate Actions"])
    
    table = TABLE["Deposits & Withdrawals"]
    for row in table.index:
        if not table.at[row, "Currency"].startswith("Total"):
            transaction = {}
            if table.at[row, "Description"] == "Electronic Fund Transfer":
                transaction["type"] = "CashTransferExt"
            elif "Adjustment: Cash Receipt/Disbursement/Transfer (Transfer to" in table.at[row, "Description"]:
                transaction["type"] = "CashTransferInt"
            else:
                print(f'ERROR : {table.at[row, "Description"]}')
                assert(False)
            transaction["date"] = table.at[row, "Settle Date"]
            transaction["cash"] = {table.at[row, "Currency"]: str2num(table.at[row, "Amount"])}
            
            transaction["date"] = datetime.datetime.strptime(transaction["date"], '%Y-%m-%d')\
                                  .replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc).isoformat()
            
            TRANSACTIONS.append(transaction)
            del(transaction)
    del(row)
    del(table, TABLE["Deposits & Withdrawals"])
    
    if "Dividends" in TABLE:
        table = TABLE["Dividends"]
        for row in table.index:
            if not table.at[row, "Currency"].startswith("Total"):
                transaction = {}
                transaction["type"] = "Dividend"
                transaction["date"] = table.at[row, "Date"]
                transaction["cash"] = {table.at[row, "Currency"]: str2num(table.at[row, "Amount"])}
                
                mytext = table.at[row, "Description"]
                assert(mytext.endswith(" (Ordinary Dividend)"))
                assert("Cash Dividend" in mytext)
                transaction["ticker"] = mytext.split("(")[0]
                transaction["isin"] = mytext.split("(")[1].split(")")[0]
                
                transaction["date"] = datetime.datetime.strptime(transaction["date"], '%Y-%m-%d')\
                                      .replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc).isoformat()
                
                TRANSACTIONS.append(transaction)
                del(transaction, mytext)
        del(row)
        del(table, TABLE["Dividends"])
    
    if "Withholding Tax" in TABLE:
        table = TABLE["Withholding Tax"]
        for row in table.index:
            if not table.at[row, "Currency"].startswith("Total"):
                transaction = {}
                transaction["type"] = "Dividend_Tax"
                transaction["date"] = table.at[row, "Date"]
                transaction["cash"] = {table.at[row, "Currency"]: str2num(table.at[row, "Amount"])}
                
                mytext = table.at[row, "Description"]
                assert(mytext.endswith(" Tax"))
                assert("Cash Dividend" in mytext)
                transaction["ticker"] = mytext.split("(")[0]
                transaction["isin"] = mytext.split("(")[1].split(")")[0]
                
                transaction["date"] = datetime.datetime.strptime(transaction["date"], '%Y-%m-%d')\
                                      .replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc).isoformat()
                
                TRANSACTIONS.append(transaction)
                del(transaction, mytext)
        del(row)
        del(table, TABLE["Withholding Tax"])
    
    POSITIONS = []
    if "Open Positions" in TABLE:
        table = TABLE["Open Positions"]
        for row in table.index:
            assert(table.at[row, "DataDiscriminator"] == "Summary")
            assert(table.at[row, "Asset Category"] == "Stocks")
            position = {}
            position["ticker"] = table.at[row, "Symbol"]
            position["nb"] = str2num(table.at[row, "Quantity"])
            POSITIONS.append(position)
            del(position)
        del(row)
        del(table, TABLE["Open Positions"])
    
    table = TABLE["Cash Report"]
    for row in table.index:
        if table.at[row, "Currency Summary"] == "Starting Cash" and table.at[row, "Currency"] != "Base Currency Summary":
            assert(str2num(table.at[row, "Total"]) == 0)
        elif table.at[row, "Currency Summary"] == "Ending Settled Cash" and table.at[row, "Currency"] != "Base Currency Summary":
            position = {}
            position["ticker"] = table.at[row, "Currency"]
            position["nb"] = str2num(table.at[row, "Total"])
            POSITIONS.append(position)
            del(position)
    del(row)
    del(table, TABLE["Cash Report"])
    
    
    #%%
    for key in TABLE.keys():
        print(f'WARNING : New tab : {key}')
    del(TABLE)
    
    return BASE_CURR, POSITIONS, TRANSACTIONS



#%%
def fusion_csv(file_path_list):
    BASE_CURR = []
    POSITIONS = []
    TRANSACTIONS = []
    for file_path in file_path_list:
        base_curr, positions, transactions = import_csv(file_path)
        BASE_CURR.append(base_curr)
        POSITIONS = POSITIONS + positions
        TRANSACTIONS = TRANSACTIONS + transactions
        del(base_curr, positions, transactions)
    del(file_path)
    BASE_CURR = list(set(BASE_CURR))
    assert(len(BASE_CURR) == 1)
    BASE_CURR = BASE_CURR[0]
    
    POSITIONS_2 = {}
    for pos in POSITIONS:
        ticker = pos["ticker"]
        POSITIONS_2[ticker] = POSITIONS_2.get(ticker, 0) + pos["nb"]
        del(ticker)
    del(pos)
    POSITIONS = POSITIONS_2
    del(POSITIONS_2)
    
    return BASE_CURR, POSITIONS, TRANSACTIONS




#%% Import
file_path_list = json.loads(os.getenv("FILEPATH_ACCOUNTS_IB"))
assert(file_path_list)
BASE_CURR, POSITIONS, TRANSACTIONS = fusion_csv(file_path_list)
del(file_path_list)


#%% Ordered transactions
list_dates = [xxx["date"] for xxx in TRANSACTIONS]
sort_index = numpy.argsort(list_dates)
TRANSACTIONS = [TRANSACTIONS[iii] for iii in sort_index]
del(list_dates, sort_index)


#%% Export XLS
writer = pandas.ExcelWriter("output/output_IB_001_fusion.xlsx")
pandas.DataFrame.from_dict(POSITIONS, orient='index').to_excel(writer, "POSITIONS", header=False, index=True)
pandas.DataFrame.from_dict(TRANSACTIONS).to_excel(writer, "TRANSACTIONS", header=True, index=False)
writer.save()
del(writer)


#%% Compute PL
WALLET = Wallet(BASE_CURR, 5)

for transaction in TRANSACTIONS:
    if transaction["type"] == "CashTransferExt":
        date = datetime.datetime.fromisoformat(transaction["date"])
        pl = WALLET.transfer_cash(transaction["cash"])
        transaction["pl"] = pl
    elif transaction["type"] == "CashTransferInt":
        date = datetime.datetime.fromisoformat(transaction["date"])
        pl1 = WALLET.transfer_cash(transaction["cash"])
        transaction["pl"] = pl1
    elif transaction["type"] == "Stock":
        date = datetime.datetime.fromisoformat(transaction["date"])
        pl = WALLET.transaction(date=date,
                                     ref_pos=transaction["ticker"],
                                     nb=transaction["nb"],
                                     cash=transaction["cash"],
                                     isin="",
                                     ticker=transaction["ticker"],
                                     name="")
        transaction["pl"] = pl
        del(pl)
    elif transaction["type"] == "Forex":
        curr = list(transaction["cash"].keys())
        date = datetime.datetime.fromisoformat(transaction["date"])
        assert(len(curr) == 2)
        curr.remove(BASE_CURR)
        curr = curr[0]
        pl = WALLET.transaction(date=date,
                                    ref_pos=curr,
                                    nb=transaction["cash"][curr],
                                    cash={BASE_CURR:transaction["cash"][BASE_CURR]},
                                    isin="",
                                    ticker="",
                                    name="")
        transaction["pl"] = pl
    elif transaction["type"] == "Split":
        WALLET.split_position(ref_pos=transaction["ticker"],
                              nb_delta=None,
                              coeff_split=transaction["split"])
        transaction["pl"] = 0
    elif transaction["type"] in ["Dividend", "Dividend_Tax",]:
        date = datetime.datetime.fromisoformat(transaction["date"])
        pl = WALLET.add_cash(date,
                             f'{transaction["ticker"]}_{transaction["type"]}',
                             transaction["cash"],
                             "",
                             transaction["ticker"],
                             "")
        transaction["pl"] = pl
        del(pl)
    else:
        print(f'ERROR : new type : {transaction["type"]}')
        assert(False)


#%% Export XLS
writer = pandas.ExcelWriter("output/output_IB_002_PL.xlsx")
WALLET_XLS = WALLET.export_into_dict_of_df()
for key in WALLET_XLS.keys():
    WALLET_XLS[key].to_excel(writer, key, header=True, index=True)
del(key, WALLET_XLS)
pandas.DataFrame.from_dict(POSITIONS, orient='index').to_excel(writer, "POSITIONS", header=False, index=True)
pandas.DataFrame.from_dict(TRANSACTIONS).to_excel(writer, "TRANSACTIONS", header=True, index=False)
writer.save()
del(writer)



#%%
WALLET = WALLET.WALLET














