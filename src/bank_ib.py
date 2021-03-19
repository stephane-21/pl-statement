'''

===============================================================================
TODO :
===============================================================================
- Stocks transfers
-
-
-

    # get_net_asset_value
    # 
#  '',
#  '',
# WALLET.add_misc()

checksum positions
last price


'''

import os
import numpy
import pandas
import json

from src.wallet import Wallet
from src.bank_stat_ib import BankStatementIB


from dotenv import load_dotenv
load_dotenv()


#%%
def str2num(mystring):
    myfloat = float(mystring.replace(",", ""))
    return myfloat




#%%
def fusion_csv(file_path_list):
    BASE_CURR = []
    POSITIONS = []
    TRANSACTIONS = []
    ACCOUNTS = []
    for file_path in file_path_list:
        ib_account = BankStatementIB(file_path)
        ib_account.export_raw(f'output/output_IB_000_raw_{ib_account.get_account_nb()}.xlsx')
        ACCOUNTS.append(ib_account)
        BASE_CURR.append(ib_account.base_curr())
        POSITIONS = POSITIONS + ib_account.get_all_positions()
        TRANSACTIONS = TRANSACTIONS + ib_account.get_all_transactions()
    del(file_path)
    BASE_CURR = list(set(BASE_CURR))
    assert(len(BASE_CURR) == 1)
    BASE_CURR = BASE_CURR[0]
    
    POSITIONS_2 = {}
    for pos in POSITIONS:
        ticker = pos["ticker"]
        if ticker not in POSITIONS_2:
            POSITIONS_2[ticker] = pos
        else:
            POSITIONS_2[ticker]["nb"] += pos["nb"]
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
pandas.DataFrame.from_dict(POSITIONS, orient='index').to_excel(writer, "POSITIONS", header=True, index=True)
pandas.DataFrame.from_dict(TRANSACTIONS).to_excel(writer, "TRANSACTIONS", header=True, index=False)
writer.save()
del(writer)


#%% Compute PL
WALLET = Wallet(BASE_CURR, 5)
for transaction in TRANSACTIONS:
    if transaction["type"] == "CashTransferExt":
        pl = WALLET.transfer_cash(transaction["cash"])
        transaction["pl"] = pl
    elif transaction["type"] == "CashTransferInt":
        pl1 = WALLET.transfer_cash(transaction["cash"])
        transaction["pl"] = pl1
    elif transaction["type"] == "Stock":
        pl = WALLET.transaction_stock(date=transaction["date"],
                                     ref_pos=transaction["ticker"],
                                     nb=transaction["nb"],
                                     cash=transaction["cash"],
                                     isin=transaction["isin"],
                                     ticker=transaction["ticker"],
                                     name=transaction["name"])
        transaction["pl"] = pl
        del(pl)
    elif transaction["type"] == "Forex":
        curr = list(transaction["cash"].keys())
        assert(len(curr) == 2)
        curr.remove(BASE_CURR)
        curr = curr[0]
        pl = WALLET.transaction_curr(date=transaction["date"],
                                    ref_pos=curr,
                                    nb=transaction["cash"][curr],
                                    cash={BASE_CURR:transaction["cash"][BASE_CURR]},
                                    isin=transaction["isin"],
                                    ticker=transaction["ticker"],
                                    name=transaction["name"])
        transaction["pl"] = pl
    elif transaction["type"] == "Split":
        WALLET.split_position(ref_pos=transaction["ticker"],
                              nb_delta=None,
                              coeff_split=transaction["split_coeff"])
        transaction["pl"] = 0
    elif transaction["type"] in ["Dividend", "Dividend_Tax",]:
        pl = WALLET.add_cash(transaction["date"],
                             f'{transaction["ticker"]}_{transaction["type"]}',
                             transaction["cash"],
                             transaction["isin"],
                             transaction["ticker"],
                             transaction["name"])
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
pandas.DataFrame.from_dict(POSITIONS, orient='index').to_excel(writer, "POSITIONS", header=True, index=False)
pandas.DataFrame.from_dict(TRANSACTIONS).to_excel(writer, "TRANSACTIONS", header=True, index=False)
writer.save()
del(writer)



#%%
print(WALLET.checksum()["message"])
WALLET = WALLET.WALLET














