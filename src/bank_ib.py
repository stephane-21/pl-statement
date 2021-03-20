'''

===============================================================================
TODO :
===============================================================================
- Stocks transfers
-
-
-

'''

import os
import json
import numpy
import pandas

from src.currency import Currency
from src.wallet import Wallet
from src.bank_stat_ib import BankStatementIB


from dotenv import load_dotenv
load_dotenv()


#%% Import
file_path_list = json.loads(os.getenv("FILEPATH_ACCOUNTS_IB"))
assert(file_path_list)
ACCOUNTS = [BankStatementIB(file_path) for file_path in file_path_list]
del(file_path_list)

#%% Export XLS
for ib_account in ACCOUNTS:
    ib_account.export_raw(f'output/output_IB_000_raw_{ib_account.get_account_nb()}.xlsx')
del(ib_account)


#%% Fusion BASE_CURR
BASE_CURR = list(set([ib_account.base_curr() for ib_account in ACCOUNTS]))
assert(len(BASE_CURR) == 1)
BASE_CURR = BASE_CURR[0]

#%% Fusion POSITIONS
POSITIONS = []
for ib_account in ACCOUNTS:
    POSITIONS += ib_account.get_all_positions()
del(ib_account)
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
POSITIONS = {key: value["nb"] for key, value in POSITIONS.items()}

#%% Fusion TRANSACTIONS
TRANSACTIONS = []
for ib_account in ACCOUNTS:
    TRANSACTIONS += ib_account.get_all_transactions()
del(ib_account)

#%% Order transactions
list_dates = [xxx["date"] for xxx in TRANSACTIONS]
sort_index = numpy.argsort(list_dates)
TRANSACTIONS = [TRANSACTIONS[iii] for iii in sort_index]
del(list_dates, sort_index)


#%% Export XLS fusion
writer = pandas.ExcelWriter("output/output_IB_001_fusion.xlsx")
pandas.DataFrame.from_dict(POSITIONS, orient='index').to_excel(writer, "POSITIONS", header=False, index=True)
pandas.DataFrame.from_dict(TRANSACTIONS).to_excel(writer, "TRANSACTIONS", header=True, index=False)
writer.save()
del(writer)


#%% Compute PL + POSITIONS
CURR = Currency()
WALLET = Wallet(BASE_CURR, 5)

WALLET.add_misc("Bank account", [ib_account.get_account_nb() for ib_account in ACCOUNTS])
for ib_account in ACCOUNTS:
    WALLET.add_misc(f'UTC ({ib_account.get_account_nb()})', ib_account.get_bank_stat_date())
    WALLET.add_misc(f'Period ({ib_account.get_account_nb()})', ib_account.get_bank_stat_period())
del(ib_account)

for transaction in TRANSACTIONS:
    if transaction["type"] == "CashTransferExt":
        assert(transaction["cash"].keys() == {BASE_CURR})
        pl = WALLET.transfer_cash(transaction["cash"])
        transaction["pl"] = pl
        transaction["fx_rate"] = 1.00
        del(pl)
    elif transaction["type"] == "CashTransferInt":
        pl = WALLET.transfer_cash(transaction["cash"])
        transaction["pl"] = pl
        transaction["fx_rate"] = "-"
        del(pl)
    elif transaction["type"] == "Stock":
        curr = list(transaction["cash"].keys())
        assert(len(curr) == 1)
        curr = curr[0]
        fx_rate = CURR.get_value(curr, transaction["date"])
        pl = WALLET.transaction_stock(date=transaction["date"],
                                     ref_pos=transaction["ticker"],
                                     nb=transaction["nb"],
                                     cash=transaction["cash"],
                                     fx_rate=fx_rate,
                                     isin=transaction["isin"],
                                     ticker=transaction["ticker"],
                                     name=transaction["name"])
        transaction["pl"] = pl
        transaction["fx_rate"] = fx_rate
        del(pl, curr, fx_rate)
    elif transaction["type"] == "Forex":
        curr = list(transaction["cash"].keys())
        assert(len(curr) == 2)
        curr.remove(BASE_CURR)
        curr = curr[0]
        pl = WALLET.transaction_forex(date=transaction["date"],
                                    ref_pos=curr,
                                    nb=transaction["cash"][curr],
                                    cash={BASE_CURR:transaction["cash"][BASE_CURR]},
                                    isin=transaction["isin"],
                                    ticker=transaction["ticker"],
                                    name=transaction["name"])
        transaction["pl"] = pl
        transaction["fx_rate"] = -transaction["cash"][curr] / transaction["cash"][BASE_CURR]
        del(pl, curr)
    elif transaction["type"] == "Split":
        WALLET.split_position(ref_pos=transaction["ticker"],
                              nb_delta=None,
                              coeff_split=transaction["split_coeff"])
        transaction["pl"] = 0
        transaction["fx_rate"] = "-"
    elif transaction["type"] in ["Dividend", "Dividend_Tax",]:
        curr = list(transaction["cash"].keys())
        assert(len(curr) == 1)
        curr = curr[0]
        fx_rate = CURR.get_value(curr, transaction["date"])
        pl = WALLET.add_cash(transaction["date"],
                             f'{transaction["ticker"]}_{transaction["type"]}',
                             transaction["cash"],
                             fx_rate,
                             transaction["isin"],
                             transaction["ticker"],
                             transaction["name"])
        transaction["pl"] = pl
        transaction["fx_rate"] = fx_rate
        del(pl, curr, fx_rate)
    else:
        print(f'ERROR : new type : {transaction["type"]}')
        assert(False)
del(transaction)

#%% Compute unrealized PL
refpos_list = WALLET.get_positions_list()
ref_pos = None
last_quotation_unit = None
for ref_pos in refpos_list:
    for ib_account in ACCOUNTS:
        last_quotation_unit = ib_account.get_last_quotation_unit(ref_pos)
        if last_quotation_unit is not None:
            curr = list(last_quotation_unit.keys())[0]
            last_quotation_unit = last_quotation_unit[curr]
            if curr != BASE_CURR:
                fx_rate = ib_account.get_last_quotation_unit(f'*_{curr}')[BASE_CURR]
                fx_rate = CURR.get_value(curr, ib_account.get_bank_stat_date())
            else:
                fx_rate = 1.00
            last_quotation_unit = last_quotation_unit / fx_rate
            WALLET.set_position_quotation(ref_pos, last_quotation_unit)
            del(curr, fx_rate)
            break
    del(ib_account)
    if last_quotation_unit is None:
        print(f'WARNING : Quotation not found : {ref_pos}')
        continue
del(ref_pos, refpos_list, last_quotation_unit)


#%% Export XLS
writer = pandas.ExcelWriter("output/output_IB_002_PL.xlsx")
WALLET_XLS = WALLET.export_into_dict_of_df()
for key in WALLET_XLS.keys():
    WALLET_XLS[key].to_excel(writer, key, header=True, index=True)
del(key, WALLET_XLS)
pandas.DataFrame.from_dict(TRANSACTIONS).to_excel(writer, "TRANSACTIONS", header=True, index=False)
writer.save()
del(writer)


#%% checksums
WALLET.checksum_positions(POSITIONS)
WALLET.checksum_realized_nav()
WALLET.checksum_total_nav(sum([ib_account.get_nav() for ib_account in ACCOUNTS]))


#%%
# WALLET = WALLET.WALLET

