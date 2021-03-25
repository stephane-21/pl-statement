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
import pandas

from src.currency import Currency
from src.wallet import Wallet
from src.bank_stat_ib import BankStatementIB
from src.bank_stat_ib import fusion_positions
from src.bank_stat_ib import sort_operations


from dotenv import load_dotenv
load_dotenv()


#%% Import CSV
file_path_list = json.loads(os.getenv("FILEPATH_ACCOUNTS_IB"))
assert(file_path_list)
ACCOUNTS = [BankStatementIB(file_path) for file_path in file_path_list]
del(file_path_list)

#%% Export XLS
for ib_account in ACCOUNTS:
    ib_account.export_raw(f'output/output_IB_000_raw_{ib_account.get_account_nb()}.xlsx')
del(ib_account)


#%% Fusion
BASE_CURR = list(set([ib_account.base_curr() for ib_account in ACCOUNTS]))
assert(len(BASE_CURR) == 1)
BASE_CURR = BASE_CURR[0]

POSITIONS = []
for ib_account in ACCOUNTS:
    POSITIONS += ib_account.get_all_positions()
del(ib_account)
POSITIONS = fusion_positions(POSITIONS)

OPERATIONS = []
for ib_account in ACCOUNTS:
    OPERATIONS += ib_account.get_all_operations()
del(ib_account)
OPERATIONS = sort_operations(OPERATIONS)

#%% Export XLS
writer = pandas.ExcelWriter("output/output_IB_001_fusion.xlsx")
pandas.DataFrame.from_dict(POSITIONS, orient='index').to_excel(writer, "POSITIONS", header=False, index=True)
pandas.DataFrame.from_dict(OPERATIONS).to_excel(writer, "OPERATIONS", header=True, index=False)
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

for operation in OPERATIONS:
    if operation["type"] == "CashTransferExt":
        assert(operation["cash"].keys() == {BASE_CURR})
        pl = WALLET.transfer_cash(operation["date"],
                                  operation["cash"])
        operation["pl"] = pl
        operation["fx_rate"] = 1.00
        del(pl)
    elif operation["type"] == "CashTransferInt":
        pl = WALLET.transfer_cash(operation["date"],
                                  operation["cash"])
        operation["pl"] = pl
        operation["fx_rate"] = "-"
        del(pl)
    elif operation["type"] == "Stock":
        curr = list(operation["cash"].keys())
        assert(len(curr) == 1)
        curr = curr[0]
        fx_rate = CURR.get_value(curr, operation["date"])
        pl = WALLET.transaction_stock(date=operation["date"],
                                     ref_pos=operation["ticker"],
                                     nb=operation["nb"],
                                     cash=operation["cash"],
                                     fx_rate=fx_rate,
                                     isin=operation["isin"],
                                     ticker=operation["ticker"],
                                     name=operation["name"])
        operation["pl"] = pl
        operation["fx_rate"] = fx_rate
        del(pl, curr, fx_rate)
    elif operation["type"] == "Forex":
        curr = list(operation["cash"].keys())
        assert(len(curr) == 2)
        curr.remove(BASE_CURR)
        curr = curr[0]
        pl = WALLET.transaction_forex(date=operation["date"],
                                      curr=curr,
                                      nb=operation["cash"][curr],
                                      cash={BASE_CURR:operation["cash"][BASE_CURR]})
        operation["pl"] = pl
        operation["fx_rate"] = -operation["cash"][curr] / operation["cash"][BASE_CURR]
        del(pl, curr)
    elif operation["type"] == "Split":
        WALLET.split_position(date=operation["date"],
                              ref_pos=operation["ticker"],
                              nb_delta=None,
                              coeff_split=operation["split_coeff"])
        operation["pl"] = 0
        operation["fx_rate"] = "-"
    elif operation["type"] in ["Dividend", "Dividend_Tax",]:
        curr = list(operation["cash"].keys())
        assert(len(curr) == 1)
        curr = curr[0]
        fx_rate = CURR.get_value(curr, operation["date"])
        pl = WALLET.add_cash(operation["date"],
                             f'{operation["ticker"]}_{operation["type"]}',
                             operation["cash"],
                             fx_rate,
                             operation["isin"],
                             operation["ticker"],
                             operation["name"])
        operation["pl"] = pl
        operation["fx_rate"] = fx_rate
        del(pl, curr, fx_rate)
    else:
        print(f'ERROR : new type : {operation["type"]}')
        assert(False)
del(operation)

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
pandas.DataFrame.from_dict(OPERATIONS).to_excel(writer, "OPERATIONS", header=True, index=False)
writer.save()
del(writer)


#%% checksums
WALLET.checksum_positions(POSITIONS)
WALLET.checksum_realized_nav()
WALLET.checksum_total_nav(sum([ib_account.get_nav() for ib_account in ACCOUNTS]))


#%%
# WALLET = WALLET.WALLET

