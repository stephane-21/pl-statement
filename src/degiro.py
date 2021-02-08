
import os
import pandas
from src.libs import parse_curr_pair
from src.libs import compute_block
from src.libs import block_columns_list
from src.libs import translate_line
from src.libs import merge_2_amounts
from src.config import MANUAL_BLOCKS
from src.import_table import import_table
from src.repair_balance import repair_balance
from dotenv import load_dotenv
load_dotenv()
BASE_CURR = os.getenv("BASE_CURR", "EUR")

pandas.set_option('display.max_rows', None)
pandas.set_option('display.max_columns', None)
pandas.set_option('display.width', None)
pandas.set_option('display.max_colwidth', None)

#%% INPUT (Masquer les transactions sur les Fonds Monétaires == OFF)
file_path = os.getenv("FILEPATH_ACCOUNTS_DEGIRO")
assert(file_path is not None)
TABLE = import_table(file_path)
TABLE = repair_balance(TABLE)
del(file_path)

TABLE_2 = []


#%% 
print("")
print("=================================")
print("Export XLS")
print("=================================")
writer = pandas.ExcelWriter("output/output_1_cleaned.xlsx")
TABLE.to_excel(writer, "TABLE", header=True, index=False)
writer.save()
del(writer)


#%%
print("")
print("=================================")
print("Detect manual curr convs (not rigorous)")
print("=================================")
Balance_div_for = {}
iii = TABLE.index[0]
BLOCK_SIZE = 2
curr = None
operation = None
while iii <= TABLE.index[-1] - BLOCK_SIZE + 1:
    transaction = translate_line(TABLE.loc[iii].to_dict())
    assert(transaction["valid"] is True)
    curr = TABLE.at[iii, "Currency"]
    if curr == BASE_CURR:
        iii = iii + 1
        continue
    elif transaction["type"][0] in ["Dividende", "ImpotsDividende", "ImpotsRetenueSource", "FraisOST", "RemboursementCapital",]:
        Balance_div_for = merge_2_amounts(Balance_div_for, transaction["cash"])
        iii = iii + 1
        continue
    elif transaction["type"][0] in ["AutoDivOuMonetaireAchatChange", "AutoDivOuMonetaireVenteChange",]:
        if curr in Balance_div_for:  # CurrConv Div
            if Balance_div_for[curr] != -transaction["cash"][curr]:
                print(f'WARNING : {TABLE.at[iii, "IndexRef"]} : Suspicious Div Change : {transaction["cash"]}')
            Balance_div_for = merge_2_amounts(Balance_div_for, transaction["cash"])
            iii = iii + 1
            continue
        else:
            new_df = TABLE.loc[[iii, iii + 1]].copy()
            operation = compute_block(new_df)
            del(new_df)
            if operation["valid"] is True and operation["block_type"] in ["CurrSell", "CurrBuy",] and TABLE.at[iii, "Product"] == "" and TABLE.at[iii + 1, "Product"] == "":
                TABLE.at[iii    , "Product"] = f'{BASE_CURR}/{curr}'
                TABLE.at[iii + 1, "Product"] = f'{BASE_CURR}/{curr}'
                print(f'INFO : {TABLE.at[iii, "IndexRef"]} : Manual CurrConv found : {transaction["cash"]}')
                iii = iii + 2
                continue
            else:
                iii = iii + 1
                continue
    else:
        iii = iii + 1
        continue
del(iii)
del(Balance_div_for, curr, operation, transaction, BLOCK_SIZE)



#%% 
print("")
print("=================================")
print("Export XLS")
print("=================================")
writer = pandas.ExcelWriter("output/output_2_cleaned.xlsx")
TABLE.to_excel(writer, "TABLE", header=True, index=False)
writer.save()
del(writer)


#%%
print("")
print("=================================")
print("Extract blocks with id (Shares + Curr Conv Manual)")
print("=================================")
list_id = list(set(TABLE["Id"]))
for id_num in list_id:
    if id_num == "":
        continue
    new_df = TABLE[TABLE["Id"] == id_num]
    operation = compute_block(new_df)
    if operation["valid"] is True:
        ind_list = list(new_df.index)
        TABLE = TABLE.drop(ind_list)
        TABLE_2.append(operation)
        del(ind_list)
    del(new_df, operation)
del(id_num)
TABLE.reset_index(inplace=True, drop=True)
list_id = list(set(TABLE["Id"]))
if len(list_id) > 0 and "" not in list_id:
    print(f'WARNING : {len(list_id) - 1} ids remaining')
del(list_id)


#%%
print("")
print("=================================")
print("Extract input blocks")
print("=================================")
block = None
for block in MANUAL_BLOCKS:
    new_df = TABLE[TABLE['IndexRef'].isin(block)]
    operation = compute_block(new_df)
    if operation["valid"] is True:
        ind_list = new_df.index
        TABLE = TABLE.drop(ind_list)
        TABLE_2.append(operation)
        del(ind_list)
    else:
        print(f'WARNING : Invalid input : {block}')
    del(new_df, operation)
del(block)
del(MANUAL_BLOCKS)
TABLE.reset_index(inplace=True, drop=True)


#%%
print("")
print("=================================")
print("Export XLS")
print("=================================")
writer = pandas.ExcelWriter("output/output_3_extraction_id.xlsx")
TABLE.to_excel(writer, "Todo", header=True, index=False)
pandas.DataFrame.from_dict(TABLE_2).reindex(columns= block_columns_list()).to_excel(writer, "Done", header=True, index=False)
writer.save()
del(writer)


#%%
print("")
print("=================================")
print("Extract blocks without id (single lines)")
print("=================================")
for iii in list(TABLE.index):
    new_df = TABLE[TABLE.index == iii]
    operation = compute_block(new_df)
    del(new_df)
    if operation["valid"] is True and operation["block_reliability"] == 100:
        TABLE = TABLE.drop(iii)
        TABLE_2.append(operation)
    del(operation)
del(iii)
TABLE.reset_index(inplace=True, drop=True)


#%%
print("")
print("=================================")
print("Sort by value dates")
print("=================================")
TABLE = TABLE.sort_values(by=["DateValue", "DateOper", "IndexRef"], ascending=[True, True, True])
TABLE.reset_index(inplace=True, drop=True)


#%%
print("")
print("=================================")
print("Extract OST")
print("=================================")
BLOCK_SIZE = 2
ind_list = None
new_df = None
operation = None
xxx = None
iii = TABLE.index[0]
while iii + BLOCK_SIZE - 1 <= TABLE.index[-1]:
    ind_list = list(range(iii, iii + BLOCK_SIZE))
    new_df = TABLE.loc[ind_list].copy()
    xxx = sorted(list(set(new_df["Description"])))
    if not (xxx[0].startswith("Changement ISIN: ") and xxx[1].startswith("Changement ISIN: ")):
        iii = iii + 1
        continue
    operation = compute_block(new_df)
    if operation["valid"] is False:
        iii = iii + 1
        continue
    if operation["block_type"] not in ["Renaming/Split",]:
        iii = iii + 1
        continue
    TABLE = TABLE.drop(ind_list)
    TABLE_2.append(operation)
    iii = iii + BLOCK_SIZE
del(iii)
del(ind_list, new_df, operation, xxx)
del(BLOCK_SIZE)
TABLE.reset_index(inplace=True, drop=True)


#%%
print("")
print("=================================")
print("Export XLS")
print("=================================")
writer = pandas.ExcelWriter("output/output_4_extraction_single.xlsx")
TABLE.to_excel(writer, "Todo", header=True, index=False)
pandas.DataFrame.from_dict(TABLE_2).reindex(columns= block_columns_list()).to_excel(writer, "Done", header=True, index=False)
writer.save()
del(writer)


#%%
print("")
print("=================================")
print("Extract blocks without id (Curr Conv with Prod) (not rigorous)")
print("=================================")
for BLOCK_SIZE in [3, 2]:
    ind_list = None
    new_df = None
    operation = None
    xxx = None
    iii = TABLE.index[0]
    while iii + BLOCK_SIZE - 1 <= TABLE.index[-1]:
        ind_list = list(range(iii, iii + BLOCK_SIZE))
        new_df = TABLE.loc[ind_list].copy()
        xxx = sorted(list(set(new_df["Product"])))
        if len(xxx) != 1 or (parse_curr_pair(xxx[0]) is None):
            iii = iii + 1
            continue
        operation = compute_block(new_df)
        if operation["valid"] is False:
            iii = iii + 1
            continue
        if operation["block_type"] not in ["CurrBuy_withProd", "CurrSell_withProd",]:
            iii = iii + 1
            continue
        TABLE = TABLE.drop(ind_list)
        TABLE_2.append(operation)
        iii = iii + BLOCK_SIZE
    del(iii)
    del(ind_list, new_df, operation, xxx)
    TABLE.reset_index(inplace=True, drop=True)
del(BLOCK_SIZE)


#%%
#print("")
#print("=================================")
#print("Sort by oper dates")
#print("=================================")
#TABLE = TABLE.sort_values(by=["DateOper", "IndexRef"], ascending=[True, True])
#TABLE.reset_index(inplace=True, drop=True)


#%%
print("")
print("=================================")
print("Export XLS")
print("=================================")
writer = pandas.ExcelWriter("output/output_5_extraction_curr.xlsx")
TABLE.to_excel(writer, "Todo", header=True, index=False)
pandas.DataFrame.from_dict(TABLE_2).reindex(columns= block_columns_list()).to_excel(writer, "Done", header=True, index=False)
writer.save()
del(writer)


#%%
print("")
print("=================================")
print("Extract blocks without id (Mono Div) (not rigorous)")
print("=================================")
df_test = None
xxx = None
new_df = None
operation = None
ind_list = None
MIN_BLOCK_SIZE = 2
for yyy in range(3):
    for zzz in range(10):
        if len(TABLE) == 0:
            break
        iii = TABLE.index[0]
        while len(TABLE) > 0 and iii + MIN_BLOCK_SIZE - 1 <= TABLE.index[-1]:
            BLOCK_SIZE = MIN_BLOCK_SIZE - 1
            while iii + BLOCK_SIZE <= TABLE.index[-1]:
                ind_list = list(range(iii, iii + BLOCK_SIZE + 1))
                df_test = TABLE.loc[ind_list].copy()
                
                if not df_test["Product"].iloc[0]:
                    break
                xxx = sorted(list(set(df_test["Product"])))
                if yyy < 2:
                    if len(xxx) > 2 or (len(xxx) == 2 and ("" not in xxx)):
                        break
                if yyy == 1:
                    if len(xxx) == 2 and df_test["Product"].iloc[-1]:
                        break
                if yyy < 2:
                    xxx = sorted(list(set(df_test["Isin"])))
                    if len(xxx) > 2 or (len(xxx) == 2 and ("" not in xxx)):
                        break
    #            xxx = sorted(list(set(df_test["DateValue"])))
    #            if (max(xxx) - min(xxx)).total_seconds() > 6.10 * 24*3600:
    #                break
                xxx = sorted(list(set(df_test["Currency"])))
                if len(xxx) > 2 or (len(xxx) == 2 and (BASE_CURR not in xxx)):
                    break
                if len(xxx) > 1 and df_test["Currency"].iloc[0] == BASE_CURR:
                    break
                if yyy == 2 and df_test["Currency"].iloc[-2] == BASE_CURR:
                    break
                BLOCK_SIZE = BLOCK_SIZE + 1
            
            if BLOCK_SIZE < MIN_BLOCK_SIZE:
                iii = iii + 1
                continue
            
            ind_list = list(range(iii, iii + BLOCK_SIZE))
            new_df = TABLE.loc[ind_list].copy()
            
            xxx = sorted(list(set(new_df["Currency"])))
            if BASE_CURR not in xxx:
                iii = iii + 1
                continue
            
            if yyy == 0:
                operation = compute_block(new_df)
            elif yyy == 1:
                operation = compute_block(new_df)
            elif yyy == 2:
                operation = compute_block(new_df)
            if operation["valid"] is False:
    #            print(f'bug : {iii} : {BLOCK_SIZE}')
                iii = iii + 1
                continue
            if operation["block_type"] not in ["Roc_Bas", "Roc_For", "Div_For", "Div_Bas", "Div_For_Multi", "DivRoc_Bas", "DivRoc_For"]:
                iii = iii + 1
                continue
            TABLE = TABLE.drop(ind_list)
            TABLE_2.append(operation)
            iii = iii + BLOCK_SIZE
        del(iii)
        del(BLOCK_SIZE)
        TABLE.reset_index(inplace=True, drop=True)
    del(zzz)
del(yyy)
del(df_test, xxx, operation, new_df, ind_list)
del(MIN_BLOCK_SIZE)

if len(TABLE) > 0:
    print(f'WARNING : {len(TABLE)} lines not computed')


#%%
print("")
print("=================================")
print("Export XLS")
print("=================================")
writer = pandas.ExcelWriter("output/output_6_extraction_div.xlsx")
TABLE.to_excel(writer, "Todo", header=True, index=False)
pandas.DataFrame.from_dict(TABLE_2).reindex(columns= block_columns_list()).to_excel(writer, "Done", header=True, index=False)
writer.save()
del(writer)


#%%
print("")
print("=================================")
print("Compute P/L")
print("=================================")
PROFITS = {"_Shares": {},
           "_Currs": {},
           "_Divs": {},}
TABLE_3 = pandas.DataFrame.from_dict(TABLE_2)
TABLE_3 = TABLE_3.sort_values(by=["index"], ascending=[True,])
TABLE_3.reset_index(inplace=True, drop=True)
for iii in TABLE_3.index:
    block_type = TABLE_3.at[iii, "block_type"]
    if block_type in ["CashTransferExt", "CashTransferInt",]:
        PROFITS.setdefault(block_type, {})
        PROFITS[block_type] = merge_2_amounts(PROFITS[block_type], TABLE_3.at[iii, "cash"])
        TABLE_3.at[iii, "block_pl"] = 0
    elif block_type in ["FeesBank",]:
        PROFITS.setdefault(block_type, {})
        PROFITS[block_type] = merge_2_amounts(PROFITS[block_type], TABLE_3.at[iii, "cash"])
        TABLE_3.at[iii, "block_pl"] = TABLE_3.at[iii, "cash"][BASE_CURR]
    elif block_type in ["Renaming/Split",]:
        PROFITS["_Shares"][TABLE_3.at[iii, "isin"][1]] = PROFITS["_Shares"].pop(TABLE_3.at[iii, "isin"][0])
        PROFITS["_Shares"][TABLE_3.at[iii, "isin"][1]]["nb"] = TABLE_3.at[iii, "nb"][1]
        TABLE_3.at[iii, "block_pl"] = 0
    elif block_type in ["ShareBuy", "ShareBuy_For",]:
        nb = TABLE_3.at[iii, "nb"]
        name = TABLE_3.at[iii, "isin"][0]
        PROFITS["_Shares"].setdefault(name, {"name": TABLE_3.at[iii, "prod"][0], "nb": 0, "price": 0, "pl": 0})
        PROFITS["_Shares"][name]["nb"] = PROFITS["_Shares"][name]["nb"] + nb
        PROFITS["_Shares"][name]["price"] = PROFITS["_Shares"][name]["price"] - TABLE_3.at[iii, "cash"][BASE_CURR]
        del(name, nb)
        TABLE_3.at[iii, "block_pl"] = 0
    elif block_type in ["ShareSell", "ShareSell_For",]:
        name = TABLE_3.at[iii, "isin"][0]
        nb = -TABLE_3.at[iii, "nb"]
        price = TABLE_3.at[iii, "cash"][BASE_CURR]
        pu = PROFITS["_Shares"][name]["price"] / PROFITS["_Shares"][name]["nb"]
        pl = price - pu * nb
        PROFITS["_Shares"][name]["pl"] = PROFITS["_Shares"][name]["pl"] + pl
        PROFITS["_Shares"][name]["nb"] = PROFITS["_Shares"][name]["nb"] - nb
        PROFITS["_Shares"][name]["price"] = PROFITS["_Shares"][name]["price"] - nb * pu
        assert(PROFITS["_Shares"][name]["nb"] >= 0)
        assert(round(PROFITS["_Shares"][name]["price"], 2) >= 0)
        if PROFITS["_Shares"][name]["nb"] == 0:
            assert(round(PROFITS["_Shares"][name]["price"], 2) == 0)
        TABLE_3.at[iii, "block_pl"] = pl
        del(name, nb, price, pu, pl)
    elif block_type in ["CurrBuy_withId", "CurrBuy_withProd", "CurrBuy",]:
        curr = TABLE_3.at[iii, "prod"][0][4:7]
        PROFITS["_Currs"].setdefault(curr, {"nb": 0, "price": 0, "pl": 0})
        PROFITS["_Currs"][curr]["nb"] = PROFITS["_Currs"][curr]["nb"] + TABLE_3.at[iii, "cash"][curr]
        PROFITS["_Currs"][curr]["nb"] = round(PROFITS["_Currs"][curr]["nb"], 2)
        PROFITS["_Currs"][curr]["price"] = PROFITS["_Currs"][curr]["price"] - TABLE_3.at[iii, "cash"][BASE_CURR]
        del(curr)
        TABLE_3.at[iii, "block_pl"] = 0
    elif block_type in ["CurrSell_withId", "CurrSell_withProd", "CurrSell",]:
        curr = TABLE_3.at[iii, "prod"][0][4:7]
        nb = -TABLE_3.at[iii, "cash"][curr]
        price = TABLE_3.at[iii, "cash"][BASE_CURR]
        pu = PROFITS["_Currs"][curr]["price"] / PROFITS["_Currs"][curr]["nb"]
        pl = price - pu * nb
        PROFITS["_Currs"][curr]["pl"] = PROFITS["_Currs"][curr]["pl"] + pl
        PROFITS["_Currs"][curr]["nb"] = PROFITS["_Currs"][curr]["nb"] - nb
        PROFITS["_Currs"][curr]["nb"] = round(PROFITS["_Currs"][curr]["nb"], 2)
        PROFITS["_Currs"][curr]["price"] = PROFITS["_Currs"][curr]["price"] - nb * pu
#        assert(PROFITS["_Currs"][curr]["nb"] >= 0)
        if PROFITS["_Currs"][curr]["nb"] == 0:
            assert(round(PROFITS["_Currs"][curr]["price"], 2) == 0)
        TABLE_3.at[iii, "block_pl"] = pl
        del(curr, nb, price, pu, pl)
    elif block_type in ["MonetaryFund", "Interests",]:
        curr = list(TABLE_3.at[iii, "cash"].keys())[0]
        PROFITS["_Currs"].setdefault(curr, {"nb": 0, "price": 0, "pl": 0})
        if curr == BASE_CURR:
            PROFITS["_Currs"][curr]["pl"] = PROFITS["_Currs"][curr]["pl"] + TABLE_3.at[iii, "cash"][curr]
            TABLE_3.at[iii, "block_pl"] = TABLE_3.at[iii, "cash"][curr]
        else:
            PROFITS["_Currs"][curr]["nb"] = PROFITS["_Currs"][curr]["nb"] + TABLE_3.at[iii, "cash"][curr]
            PROFITS["_Currs"][curr]["nb"] = round(PROFITS["_Currs"][curr]["nb"], 2)
            TABLE_3.at[iii, "block_pl"] = 0
        del(curr)
    elif block_type in ["Roc_Bas", "Roc_For", "Div_Bas", "Div_For", "Div_For_Multi", "DivRoc_Bas", "DivRoc_For",]:
        curr = list(TABLE_3.at[iii, "cash"].keys())[0]
        PROFITS["_Divs"] = merge_2_amounts(PROFITS["_Divs"], TABLE_3.at[iii, "cash"])
        TABLE_3.at[iii, "block_pl"] = TABLE_3.at[iii, "cash"][curr]
        del(curr)
    else:
        assert(False)
    del(block_type)
del(iii)


#%%
print("")
print("=================================")
print("Export XLS")
print("=================================")
writer = pandas.ExcelWriter("output/output_7_profits.xlsx")
TABLE.to_excel(writer, "Todo", header=True, index=False)
pandas.DataFrame.from_dict(TABLE_3).reindex(columns= block_columns_list()).to_excel(writer, "Done", header=True, index=False)
writer.save()
del(writer)






