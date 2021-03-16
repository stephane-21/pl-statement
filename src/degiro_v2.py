
import os
import numpy
import pandas
from src.import_table import import_table
from src.repair_balance import repair_balance
from src.libs import translate_line
from src.libs import merge_2_transactions
from src.wallet import Wallet
from src.currency import Currency
from dotenv import load_dotenv
load_dotenv()
BASE_CURR = os.getenv("BASE_CURR", "EUR")


#%% INPUT (Masquer les transactions sur les Fonds Monétaires == OFF)
file_path = os.getenv("FILEPATH_ACCOUNTS_DEGIRO")
assert(file_path is not None)
TABLE = import_table(file_path)
TABLE = repair_balance(TABLE)
del(file_path)


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
print("Fusion double lines")
print("=================================")
TABLE_2 = []
del TABLE["Balance"]

iii = 0
while len(TABLE) > 0 and iii <= TABLE.index[-1]:
    transaction = translate_line(TABLE.loc[iii].to_dict())
    if transaction["valid"] is False:
        print(f'ERROR : {TABLE.loc[iii]}')
        assert(False)
    if set(transaction["type"]) in [{"TransferExt"}, {"TransferExtFlatex"},]:
        pass
    elif set(transaction["type"]) in [{"DegiroCashSweepTransfer"}, {"TransfertFondsFlatex"}, {"ProcessedFlatexWithdrawal"},]:
        pass
    elif set(transaction["type"]) in [{"OrdreActionAchat"},]:
        pass
    elif set(transaction["type"]) in [{"OrdreActionVente"},]:
        pass
    elif set(transaction["type"]) in [{"FondsMonetairesCompensation"}, {"FondsMonetairesConversion"}, {"FondsMonetairesDistribution"},\
                                    {"FlatexInterest"}, {"FondsMonetairesVariation"}, {"InteretsDebiteurs"}, {"FinancialTransactionsTax"}, {"FraisOST"},
                                    {"RemboursementOffrePromotionnelle"}, {"Dividende"}, {"ImpotsRetenueSource"}, {"ImpotsDividende"},
                                    {"RemboursementCapital"}, {"FraisCourtageAction"}, {"FraisConnexionPlacesBoursieres"}, {"FraisCourtageMonetaire"},]:
        pass
    else:
        iii = iii + 1
        continue
    TABLE = TABLE.drop(iii)
    TABLE_2.append(transaction)
    iii = iii + 1
del(iii)
del(transaction)
TABLE.reset_index(inplace=True, drop=True)

iii = 0
while len(TABLE) > 0 and iii <= TABLE.index[-1]:
    transaction = translate_line(TABLE.loc[iii].to_dict())
    if transaction["valid"] is False:
        print(f'ERROR : {TABLE.loc[iii]}')
        assert(False)
    if set(transaction["type"]) in [{"ReglementTransactionDevise"},]:
        assert(TABLE.at[iii, "Amount"] == -TABLE.at[iii + 1, "Amount"])
        assert(TABLE.at[iii, "Currency"] == TABLE.at[iii + 1, "Currency"])
        assert(TABLE.at[iii, "Currency"] != BASE_CURR)
        jjj = iii - 1
        while True:
            if TABLE.at[iii + 1, "Amount"] == TABLE.at[jjj, "Amount"] and TABLE.at[iii + 1, "Currency"] == TABLE.at[jjj, "Currency"]:
                TABLE.at[jjj, "ForexRate"] = TABLE.at[iii + 1, "ForexRate"]
                TABLE.at[jjj, "Description"] = "Opération de change - Débit"
                del(jjj)
                break
            jjj = jjj - 1
        TABLE = TABLE.drop([iii, iii + 1])
        iii = iii + 2
    else:
        iii = iii + 1
del(iii)
del(transaction)
TABLE.reset_index(inplace=True, drop=True)

iii = 0
while len(TABLE) > 0 and iii <= TABLE.index[-1]:
    transaction_1 = translate_line(TABLE.loc[iii].to_dict())
    transaction_2 = translate_line(TABLE.loc[iii + 1].to_dict())
    transaction = merge_2_transactions(transaction_1, transaction_2)
    if transaction["valid"] is False:
        print(f'ERROR : {transaction}')
        assert(False)
    if set(transaction["type"]) in [{"OrdreMonetaireAchat"},
                                    {"OrdreActionAchatChange"},
                                    {"OrdreMonetaireAchatChange"},
                                    {"AutoDivOuMonetaireAchatChange"},
                                    {"AutoMonetaireAchatChange"},
                                    {"OrdreMonetaireVente"},
                                    {"OrdreActionVenteChange"},
                                    {"OrdreMonetaireVenteChange"},
                                    {"AutoDivOuMonetaireVenteChange"},
                                    {"AutoMonetaireVenteChange"},]:
        assert(len(transaction["fx_list"]) == 1)
        assert(len(set(transaction["date_val"])) == 1)
        
        curr = list(transaction["cash"].keys())
        curr.remove(BASE_CURR)
        curr = curr[0]
        assert(transaction["cash"].keys() == {curr, BASE_CURR})
        if not (numpy.isclose(transaction["fx_list"][0], -transaction["cash"][curr] / transaction["cash"][BASE_CURR], rtol=0.01)):
            print(f'WARNING : {transaction["index"]} : {transaction["cash"]} : {transaction["fx_list"]}')
        del(curr)
        TABLE = TABLE.drop([iii, iii + 1])
        TABLE_2.append(transaction)
        iii = iii + 2
    elif set(transaction["type"]) in [{"ChangementIsin"}, {"Split"},]:
        assert(transaction["cash"] == {BASE_CURR: 0})
        TABLE = TABLE.drop([iii, iii + 1])
        TABLE_2.append(transaction)
        iii = iii + 2
    else:
        iii = iii + 1
del(iii)
del(transaction_1, transaction_2, transaction)
TABLE.reset_index(inplace=True, drop=True)

assert(len(TABLE) == 0)
TABLE = TABLE_2
del(TABLE_2)

TABLE = sorted(TABLE, key=lambda k: k["index"])  # Sort list


#%% 
print("")
print("=================================")
print("Export XLS")
print("=================================")
writer = pandas.ExcelWriter("output/output_2_formatted.xlsx")
pandas.DataFrame.from_dict(TABLE).to_excel(writer, "TABLE", header=True, index=False)
writer.save()
del(writer)


#%%
print("")
print("=================================")
print("Compute P/L")
print("=================================")
WALLET = Wallet(BASE_CURR, 4)
CURR = Currency()

for transaction in TABLE:
    if transaction["valid"] is False:
        print(f'ERROR : {transaction}')
        assert(False)
    
    curr = list(transaction["cash"].keys())
    if len(curr) == 2:
        curr.remove(BASE_CURR)
        curr = curr[0]
        fx_rate =  -transaction["cash"][curr] / transaction["cash"][BASE_CURR]
    elif len(curr) == 1:
        curr = curr[0]
        fx_rate = CURR.get_value(curr, transaction["date_ope"][0])
    else:
        assert(False)
    transaction["fx_rate"] = fx_rate
    
    if set(transaction["type"]) in [{"TransferExt"}, {"TransferExtFlatex"},]:
        pl = WALLET.transfer_cash(transaction["cash"])
        transaction["pl"] = pl
    elif set(transaction["type"]) in [{"DegiroCashSweepTransfer"}, {"TransfertFondsFlatex"}, {"ProcessedFlatexWithdrawal"},]:
        assert(curr == BASE_CURR)
        pl = WALLET.add_cash(transaction["date_ope"][0],
                             "#_CashTransferInt",
                             transaction["cash"],
                             "",
                             "",
                             "")
        transaction["pl"] = pl
    elif set(transaction["type"]) in [{"ChangementIsin"},]:
        assert(transaction["cash"] == {BASE_CURR: 0})
        WALLET.rename_position(transaction["isin"][0],
                               transaction["isin"][1],
                               transaction["prod"][0],
                               transaction["prod"][1])
        transaction["pl"] = 0
    elif set(transaction["type"]) in [{"Split"},]:
        assert(transaction["cash"] == {BASE_CURR: 0})
        WALLET.split_position(ref_pos=transaction["isin"][0],
                              nb_delta=transaction["nb"],
                              coeff_split=None)
        transaction["pl"] = 0
    elif set(transaction["type"]) in [{"OrdreActionAchat"}, {"OrdreActionVente"},]:
        pl2 = WALLET.transaction(date=transaction["date_ope"][0],
                                     ref_pos=transaction["isin"][0],
                                     nb=transaction["nb"],
                                     cash=transaction["cash"],
                                     isin=transaction["isin"][0],
                                     ticker="",
                                     name=transaction["prod"][0])
        transaction["pl"] = pl2
        del(pl2)
    elif set(transaction["type"]) in [{"OrdreActionAchatChange"}, {"OrdreActionVenteChange"},
                                      {"OrdreMonetaireAchat"}, {"OrdreMonetaireVente"},
                                      {"OrdreMonetaireAchatChange"}, {"OrdreMonetaireVenteChange"},
                                      {"AutoMonetaireAchatChange"}, {"AutoMonetaireVenteChange"},
                                      {"AutoDivOuMonetaireAchatChange"}, {"AutoDivOuMonetaireVenteChange"},]:
        pl = WALLET.transaction(date=transaction["date_ope"][0],
                                    ref_pos=f'*_{curr}',
                                    nb=transaction["cash"][curr],
                                    cash={BASE_CURR: transaction["cash"][BASE_CURR]},
                                    isin="",
                                    ticker="",
                                    name="")
        transaction["pl"] = pl
        del(pl)
    elif set(transaction["type"]) in [{"FondsMonetairesCompensation"}, {"FondsMonetairesConversion"}, {"FondsMonetairesDistribution"},\
                                      {"FlatexInterest"}, {"FondsMonetairesVariation"}, {"InteretsDebiteurs"}, {"FinancialTransactionsTax"}, {"FraisOST"},\
                                      {"RemboursementOffrePromotionnelle"}, {"Dividende"}, {"ImpotsRetenueSource"}, {"ImpotsDividende"},\
                                      {"RemboursementCapital"}, {"FraisCourtageAction"},\
                                      {"FraisConnexionPlacesBoursieres"}, {"FraisCourtageMonetaire"},]:
        pl1 = WALLET.add_cash(transaction["date_ope"][0],
                             f'#_{transaction["type"][0]}',
                             transaction["cash"],
                             "",
                             "",
                             "")
        transaction["pl"] = pl1
        del(pl1)
    del(curr)
    del(fx_rate)
del(transaction)
del(CURR)


#%%
print("")
print("=================================")
print("Export XLS")
print("=================================")
writer = pandas.ExcelWriter("output/output_3_profits.xlsx")
pandas.DataFrame.from_dict(TABLE).to_excel(writer, "TABLE", header=True, index=False)
WALLET_XLS = WALLET.export_into_dict_of_df()
for key in WALLET_XLS.keys():
    WALLET_XLS[key].to_excel(writer, key, header=True, index=True)
del(key, WALLET_XLS)
writer.save()
del(writer)



#%%
WALLET = WALLET.WALLET


