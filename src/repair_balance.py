
from src.libs_dg import merge_2_amounts


def repair_balance(TABLE):
    print("")
    print("=================================")
    print("Check and repair balance errors (sorted oper dates)")
    print("=================================")
    TABLE["Balance"] = None
    Balance_a = {}
    Balance_b = {}
    for iii in TABLE.index:
        curr = TABLE.at[iii, "Currency"]
        TABLE.at[iii, "Balance"] = {}
        TABLE.at[iii, "Balance"]["from"] = Balance_b.copy()
        if curr not in Balance_a.keys():
            Balance_a.setdefault(curr, 0)
        if curr not in Balance_b.keys():
            Balance_b.setdefault(curr, 0)
        amount_a = TABLE.at[iii, "Amount"]
        amount_b = TABLE.at[iii, "BalanceVal"] - Balance_b[curr]
        error_value = amount_b - amount_a
        if abs(error_value) > 0.015:
            print(f'WARNING : {TABLE.at[iii, "IndexRef"]} {TABLE.at[iii, "DateOper"]} diff=={error_value:.2f}{curr}')
        Balance_a[curr] = round(Balance_a[curr] + TABLE.at[iii, "Amount"], 2)
        Balance_b[curr] = round(TABLE.at[iii, "BalanceVal"], 2)
        TABLE.at[iii, "Amount"] = round(amount_b, 2)
        del(error_value, amount_a, amount_b)
        del(curr)
        Balance_a = merge_2_amounts(Balance_a, {})  # delete empty currs
        Balance_b = merge_2_amounts(Balance_b, {})  # delete empty currs
        TABLE.at[iii, "Balance"]["to"] = Balance_b.copy()
    del(iii)
    del TABLE["BalanceVal"]
    
    print("")
    print('INFO : Final balance according to amount column :')
    print(Balance_a)
    print("")
    print('INFO : Final balance according to balance column :')
    print(Balance_b)
    del(Balance_a, Balance_b)
    
    return TABLE