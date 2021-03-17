import numpy
import datetime
import pandas


def import_table(file_path):
    #%% Import CSV
    print("")
    print("=================================")
    print("Read CSV")
    print("=================================")
    TABLE = pandas.read_csv(file_path, delimiter=",", header=[0], quotechar='"')
    TABLE.reset_index(inplace=True, drop=True)
    
    
    #%%
    print("")
    print("=================================")
    print("Repair bugs of CSV export")
    print("=================================")
    TABLE_col = list(TABLE.columns.values)
    lines_to_delete = []
    for iii in TABLE.index:
        if type(TABLE.at[iii, "Date"]) is float and numpy.isnan(TABLE.at[iii, "Date"]):
            assert(iii > 0)
            for jjj in TABLE_col:
                if type(TABLE.at[iii, jjj]) is str:
                    assert(type(TABLE.at[iii-1, jjj]) is str)
                    assert(type(TABLE.at[iii, jjj]) is str)
                    if jjj != "ID Ordre":
                        print(f'INFO : Merge lines = {TABLE.at[iii-1, jjj]} +++++++ {TABLE.at[iii, jjj]}')
                    TABLE.at[iii-1, jjj] = TABLE.at[iii-1, jjj] + TABLE.at[iii, jjj]
                else:
                     assert(numpy.isnan(TABLE.at[iii, jjj]))
            del(jjj)
            lines_to_delete.append(iii)
    del(iii)
    TABLE = TABLE.drop(lines_to_delete)
    del(lines_to_delete)
    del(TABLE_col)
    TABLE.reset_index(inplace=True, drop=True)
    
    
    #%% 
    print("")
    print("=================================")
    print("Reverse index")
    print("=================================")
    TABLE = TABLE.reindex(index=TABLE.index[::-1])  # reverse order
    TABLE.reset_index(inplace=True, drop=True)
    
    
    #%% 
    print("")
    print("=================================")
    print("Rename columns")
    print("=================================")
    if set(TABLE.columns) != {'Code ISIN','Date','Date de','Description','FX','Heure','ID Ordre','Mouvements','Produit','Solde','Unnamed: 10','Unnamed: 8'}:
        print(f'ERROR : Unexpected columns = {list(TABLE.columns)}')
        assert(False)
    TABLE["IndexRef"] = TABLE.index.astype(object)
    TABLE = TABLE.rename(columns={"Date": "DateOper"})
    TABLE = TABLE.rename(columns={"Heure": "HourOper"})
    TABLE = TABLE.rename(columns={"Date de": "DateValue"})
    TABLE = TABLE.rename(columns={"Produit": "Product"})
    TABLE = TABLE.rename(columns={"Code ISIN": "Isin"})
    TABLE = TABLE.rename(columns={"Description": "Description"})
    TABLE = TABLE.rename(columns={"FX": "ForexRate"})
    TABLE = TABLE.rename(columns={"Mouvements": "AmountCurr"})
    TABLE = TABLE.rename(columns={"Unnamed: 8": "Amount"})
    TABLE = TABLE.rename(columns={"Solde": "BalanceCurr"})
    TABLE = TABLE.rename(columns={"Unnamed: 10": "BalanceVal"})
    TABLE = TABLE.rename(columns={"ID Ordre": "Id"})
    # TABLE.columns.tolist()
    TABLE = TABLE[['IndexRef', 'Id', 'DateOper', 'HourOper', 'DateValue', 'Product', 'Isin',
                   'Description', 'ForexRate', 'AmountCurr', 'Amount', 'BalanceCurr', 'BalanceVal']]
    
    
    #%%
    print("")
    print("=================================")
    print("Cells format")
    print("=================================")
    for iii in TABLE.index:
        TABLE.at[iii, "DateOper"] = datetime.datetime.strptime(f'{TABLE.at[iii, "DateOper"]} {TABLE.at[iii, "HourOper"]}', '%d-%m-%Y %H:%M').replace(tzinfo=datetime.timezone.utc).isoformat()
    del(iii)
    del(TABLE["HourOper"])
    for iii in TABLE.index:
        TABLE.at[iii, "DateValue"] = datetime.datetime.strptime(f'{TABLE.at[iii, "DateValue"]}', '%d-%m-%Y').replace(tzinfo=datetime.timezone.utc).isoformat()
    del(iii)
    
    for iii in TABLE.index:
        for col in ["Id", "Isin", "Product",]:
            if type(TABLE.at[iii, col]) is str:
                pass
            else:
                assert(numpy.isnan(TABLE.at[iii, col]))
                TABLE.at[iii, col] = ""
        del(col)
    del(iii)
    
    for iii in TABLE.index:
        if type(TABLE.at[iii, "Amount"]) is str:
            TABLE.at[iii, "Amount"] = TABLE.at[iii, "Amount"].replace(",", ".")
            TABLE.at[iii, "Amount"] = float(TABLE.at[iii, "Amount"])
        else:
            assert(numpy.isnan(TABLE.at[iii, "Amount"]))
            assert(numpy.isnan(TABLE.at[iii, "AmountCurr"]))
            TABLE.at[iii, "Amount"] = None
            TABLE.at[iii, "AmountCurr"] = None
        
        assert(type(TABLE.at[iii, "BalanceVal"]) is str)
        TABLE.at[iii, "BalanceVal"] = TABLE.at[iii, "BalanceVal"].replace(",", ".")
        TABLE.at[iii, "BalanceVal"] = float(TABLE.at[iii, "BalanceVal"])
    del(iii)
    
    for iii in TABLE.index:
        if type(TABLE.at[iii, "ForexRate"]) is str:
            TABLE.at[iii, "ForexRate"] = TABLE.at[iii, "ForexRate"].replace(",", ".")
            TABLE.at[iii, "ForexRate"] = float(TABLE.at[iii, "ForexRate"])
        else:
            assert(numpy.isnan(TABLE.at[iii, "ForexRate"]))
            TABLE.at[iii, "ForexRate"] = None
    del(iii)
    
    
    #%%
    print("")
    print("=================================")
    print("Merge currency columns")
    print("=================================")
    for iii in TABLE.index:
        if type(TABLE.at[iii, "AmountCurr"]) is str and type(TABLE.at[iii, "BalanceCurr"]) is str:
            assert(TABLE.at[iii, "AmountCurr"] == TABLE.at[iii, "BalanceCurr"])
        elif TABLE.at[iii, "AmountCurr"] is None and type(TABLE.at[iii, "BalanceCurr"]) is str:
            assert(TABLE.at[iii, "Description"].startswith("Conversion Fonds Monétaires finalisée: "))
            assert(TABLE.at[iii, "Amount"] is None)
            TABLE.at[iii, "Amount"] = 0
        else:
            print(f'ERROR : Unexpected currency : {TABLE.loc[iii]}')
            assert(False)
    del(iii)
    del TABLE["AmountCurr"]
    TABLE = TABLE.rename(columns={"BalanceCurr": "Currency"})
    
    TABLE["Currency"] = TABLE["Currency"].str.replace("NO", "NOK")
    
    
    #%%
    print("")
    print("=================================")
    print("Delete useless lines")
    print("=================================")
    lines_to_delete = []
    for iii in TABLE.index:
        if TABLE.at[iii, "Amount"] == 0:
            assert(TABLE.at[iii, "Description"].startswith("Variation Fonds Monétaires (")\
                            or TABLE.at[iii, "Description"].startswith("Conversion Fonds Monétaires finalisée: ")\
                            or TABLE.at[iii, "Description"].startswith("Conversion Fonds Monétaires finalisée: "))
            lines_to_delete.append(iii)
    del(iii)
    TABLE = TABLE.drop(lines_to_delete)
    del(lines_to_delete)
    TABLE.reset_index(inplace=True, drop=True)
    
    
    return TABLE