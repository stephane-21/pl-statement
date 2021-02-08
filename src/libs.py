
import os
BASE_CURR = os.getenv("BASE_CURR", "EUR")


#%%
def parse_curr_pair(Text):
    assert(type(Text) is str)
    if len(Text) == 7 and Text[3] == "/" and BASE_CURR in Text:
        curr_1 = Text[:3]
        curr_2 = Text[4:]
        if curr_1 == BASE_CURR and curr_2 == BASE_CURR:
            return None
        return [curr_1, curr_2]
    else:
        return None


#%%
def parse_description(mystring, prod, isin, curr, ammount):
    import numpy
    Text = mystring
    if Text.startswith("Achat "):
        tr_type = "Achat"
        Text = Text[6:]
    elif Text.startswith("Vente "):
        tr_type = "Vente"
        Text = Text[6:]
    if not (Text.endswith(f'({isin})')):
        print(f'ERROR : Cannot parse Descr : {mystring}')
        assert(False)
        return None
    Text = Text.split(f'({isin})')[0].rstrip(" ")
    assert(Text.endswith(f' {curr}'))
    Text = Text.split(f' {curr}')[0]
    Text = Text.lower()
    if not (f' {prod.lower()}@' in Text):
        print(f'ERROR : Cannot parse Descr : {mystring}')
        assert(False)
        return None
    nb    = str2float(Text.split(f' {prod.lower()}@')[0])
    price = str2float(Text.split(f' {prod.lower()}@')[1])
    assert(nb > 0)
    if tr_type == "Vente":
        nb = -nb
    if not (numpy.isclose(nb * price, -ammount, rtol=0.001)):
        print(f'ERROR : Checksum = {mystring} vs {ammount}')
        assert(False)
        return None
    mydict = {"tr_type": tr_type,
              "nb": nb,
              "price": price,}
    return mydict


#%%
def str2float(mystring):
    myfloat = float(mystring.replace(" ", "").replace(u"\xa0", u"").replace(",", "."))
    return myfloat


#%%
def merge_2_amounts(Amount_1, Amount_2):
    Amount = {}
    Amount[BASE_CURR] = 0  # Take 1st place
    curr = None
    for curr in sorted(list(set(list(Amount_1.keys()) + list(Amount_2.keys())))):
        Amount[curr] = Amount_1.get(curr, 0) + Amount_2.get(curr, 0)
        Amount[curr] = round(Amount[curr], 2)
        if Amount[curr] == 0:
            del(Amount[curr])
#    Amount.setdefault(BASE_CURR, 0)
    return Amount


#%%
def convert_amount_to_base_curr(amount, fx_global_bas_for):
    val = 0
    for curr in amount.keys():
        if curr == BASE_CURR:
            val = val + amount[curr]
        else:
            val = val + amount[curr] / fx_global_bas_for
    return val


#%%
def transaction_columns_list():
    KeysList = ["type", "index", "id", "date_ope", "date_val", "prod", "isin", "cash", "fx_list", "div_brut",
                "change_accu", "fees_broker", "fees_finpla", "fees_revtax", "nb", "comment", "valid"]
    return KeysList


#%%
def block_columns_list():
    KeysList = transaction_columns_list() + ["block_type",
                                             "block_reliability",
                                             "block_fx_basfor",
                                             "block_fees_broker_ratio", "block_fees_finpla_ratio", "block_fees_revtax_ratio",
                                             "block_description",
                                             "block_price_avg",
                                             "block_pl",]
    return KeysList


#%%
def merge_2_transactions(TRAN_1, TRAN_2):
    KeysList = set(transaction_columns_list())
    TRAN = {}
    for key in KeysList:
        if type(TRAN_1[key]) is list:
            TRAN[key] = TRAN_1[key] + TRAN_2[key]
        elif type(TRAN_1[key]) in [float, int,]:
            TRAN[key] = TRAN_1[key] + TRAN_2[key]
        elif type(TRAN_1[key]) is dict:
            TRAN[key] = merge_2_amounts(TRAN_1[key], TRAN_2[key])
        elif type(TRAN_1[key]) is bool:
            TRAN[key] = TRAN_1[key] and TRAN_2[key]
        else:
            assert(False)
    TRAN["cash"].setdefault(BASE_CURR, 0)
    assert(TRAN_1.keys() == KeysList)
    assert(TRAN_2.keys() == KeysList)
    assert(TRAN.keys() == KeysList)
    return TRAN


#%%
def check_operation_change_curr_list(operation):
    if len(operation["cash"].keys()) != 2:
        operation["comment"].append(f'ERROR : Curr list: {operation["cash"]}')
        operation["valid"] = False
        return operation
    curr = list(operation["cash"].keys())
    assert(BASE_CURR in curr)
    assert(len(set(operation["prod"])) == 1 or (len(set(operation["prod"])) == 2 and "" in operation["prod"]))
    for prod in set(operation["prod"]):
        if prod not in ["", f'{curr[0]}/{curr[1]}', f'{curr[1]}/{curr[0]}',]:
            operation["comment"].append(f'ERROR : Curr pair : {set(operation["prod"])}')
            operation["valid"] = False
    return operation


#%%
def check_operation_mono(operation, column):
    if not((len(set(operation[column])) == 1) or (len(set(operation[column])) == 2 and "" in operation[column])):
        operation["comment"].append(f'ERROR : {column} : {set(operation[column])}')
        operation["valid"] = False
    return operation


#%%
def convert_block_to_operation(new_df):
    transaction_list = []
    for iii in new_df.index:
        transaction = translate_line(new_df.loc[iii].to_dict())
        transaction_list.append(transaction)
        del(transaction)
    del(iii)
    for iii, transaction in enumerate(transaction_list):
        if iii == 0:
            operation = transaction
        else:
            operation = merge_2_transactions(operation, transaction)
    del(iii)
    return operation


#%%
def checksum_operation_basecurr(operation):
    if list(operation["cash"].keys()) != [BASE_CURR,]:
        operation["comment"].append(f'ERROR : Block checksum : {operation["cash"]}')
        operation["valid"] = False
    return operation


#%%
def check_block_curr_base(new_df, operation):
    xxx_list = sorted(set(new_df["Currency"]))
    if xxx_list != [BASE_CURR,]:
        operation["comment"].append(f'ERROR : Currency : {xxx_list}')
        operation["valid"] = False
    return operation


#%%
def check_block_curr_single(new_df, operation):
    xxx_list = sorted(set(new_df["Currency"]))
    if len(xxx_list) != 1:
        operation["comment"].append(f'ERROR : Currency : {xxx_list}')
        operation["valid"] = False
    return operation


#%%
def check_block_curr_double(new_df, operation):
    xxx_list = sorted(set(new_df["Currency"]))
    if not(len(xxx_list) == 2 and BASE_CURR in xxx_list):
        operation["comment"].append(f'ERROR : Currency : {xxx_list}')
        operation["valid"] = False
    return operation


#%%
def translate_line(mydict):
    TRAN = {}
    TRAN["type"]        = None
    TRAN["index"]       = [mydict["IndexRef"],]
    TRAN["id"]          = [mydict["Id"],]
    TRAN["date_ope"]    = [mydict["DateOper"],]
    TRAN["date_val"]    = [mydict["DateValue"],]
    TRAN["prod"]        = [mydict["Product"],]
    TRAN["isin"]        = [mydict["Isin"],]
    TRAN["cash"]        = {mydict["Currency"]: mydict["Amount"]}
    if mydict["ForexRate"] is None:
        TRAN["fx_list"] = []
    else:
        TRAN["fx_list"] = [mydict["ForexRate"],]
    TRAN["div_brut"]    = {}
    TRAN["change_accu"] = {}
    TRAN["fees_broker"] = {}
    TRAN["fees_finpla"] = {}
    TRAN["fees_revtax"] = {}
    TRAN["nb"]          = 0
    TRAN["comment"]     = []
    TRAN["valid"]       = True
    assert(TRAN.keys() == set(transaction_columns_list()))
    
    assert(type(mydict["IndexRef"]) is int)
    assert(mydict["DateOper"])
    assert(mydict["DateValue"])
    assert(mydict["Description"])
    assert(mydict["Amount"] is not None)
    assert(mydict["Currency"])
    if (mydict["Description"].startswith("Achat ") or mydict["Description"].startswith("Vente ")) and mydict["Id"] and mydict["Isin"]:
        assert(mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        mydescr = parse_description(mydict["Description"], mydict["Product"], mydict["Isin"], mydict["Currency"], mydict["Amount"])
        if mydescr["tr_type"] == "Achat":
            TRAN["type"] = ["OrdreActionAchat",]
        elif mydescr["tr_type"] == "Vente":
            TRAN["type"] = ["OrdreActionVente",]
        TRAN["nb"] = mydescr["nb"]
        return TRAN
    elif (mydict["Description"].startswith("Achat ") or mydict["Description"].startswith("Vente ")) and mydict["Id"] and not mydict["Isin"]:
        assert(mydict["Id"])
        assert(mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        mydescr = parse_description(mydict["Description"], mydict["Product"], mydict["Isin"], mydict["Currency"], mydict["Amount"])
        curr_list = parse_curr_pair(mydict["Product"])
        if curr_list[0] == BASE_CURR:
            TRAN["fx_list"] = [mydescr["price"],]
        elif curr_list[1] == BASE_CURR:
            TRAN["fx_list"] = [1 / mydescr["price"],]
        else:
            assert(False)
        TRAN["change_accu"] = {mydict["Currency"]: mydict["Amount"]}
        if curr_list is None:
            TRAN["comment"] = [f'ERROR : Cannot parse Curr pair = {mydict["Product"]}',]
            TRAN["valid"] = False
            return TRAN
        if ((mydict["Currency"] != BASE_CURR and mydict["Amount"] > 0) or (mydict["Currency"] == BASE_CURR and mydict["Amount"] < 0)):
            if mydescr["tr_type"] == "Vente":
                assert(curr_list[0] == BASE_CURR)
                assert(curr_list[1] == mydict["Currency"])
            elif mydescr["tr_type"] == "Achat":
                assert(curr_list[0] == mydict["Currency"])
                assert(curr_list[1] == BASE_CURR)
            TRAN["type"] = ["OrdreMonetaireAchat",]
        elif ((mydict["Currency"] == BASE_CURR and mydict["Amount"] > 0) or (mydict["Currency"] != BASE_CURR and mydict["Amount"] < 0)):
            if mydescr["tr_type"] == "Achat":
                assert(curr_list[0] == BASE_CURR)
                assert(curr_list[1] == mydict["Currency"])
            elif mydescr["tr_type"] == "Vente":
                assert(curr_list[0] == mydict["Currency"])
                assert(curr_list[1] == BASE_CURR)
            TRAN["type"] = ["OrdreMonetaireVente",]
        else:
            assert(False)
        return TRAN
    elif mydict["Description"].startswith("Changement ISIN: "):
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["ChangementIsin",]
        mydescr = parse_description(mydict["Description"].split("Changement ISIN: ")[1],
                                    mydict["Product"], mydict["Isin"], mydict["Currency"], mydict["Amount"])
        TRAN["nb"] = mydescr["nb"]
        return TRAN
    elif mydict["Description"].startswith("Fractionnement d'actions: "):
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["Split",]
        mydescr = parse_description(mydict["Description"].split("Changement ISIN: ")[1],
                                    mydict["Product"], mydict["Isin"], mydict["Currency"], mydict["Amount"])
        TRAN["nb"] = mydescr["nb"]
        return TRAN
    elif mydict["Description"] in ["Compensation Fonds Monétaires DEGIRO",]:
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["FondsMonetairesCompensation",]
        TRAN["fees_broker"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"].startswith("Conversion Fonds Monétaires finalisée: "):
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["FondsMonetairesConversion",]
        return TRAN
    elif mydict["Description"] in ["Degiro Cash Sweep Transfer",]:
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["DegiroCashSweepTransfer",]
        return TRAN
    elif mydict["Description"] in ["Distribution Fonds Monétaires",]:
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["FondsMonetairesDistribution",]
        return TRAN
    elif mydict["Description"] == "Dividende":
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["Dividende",]
        TRAN["div_brut"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Flatex Interest",]:
        assert(not mydict["Id"])
        assert(not mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["FlatexInterest",]
        return TRAN
    elif mydict["Description"] in ["Frais d’opération sur titres",]:
        assert(not mydict["Id"])
        assert(not mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["FraisOST",]
        TRAN["fees_broker"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"].startswith("Frais de connexion aux places boursières "):
        assert(not mydict["Id"])
        assert(not mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["FraisConnexionPlacesBoursieres",]
        TRAN["fees_broker"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Frais de courtage",] and mydict["Isin"]:
        assert(mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["FraisCourtageAction",]
        TRAN["fees_broker"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Frais de courtage",] and not mydict["Isin"]:
#        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        assert(parse_curr_pair(mydict["Product"]) is not None)
        TRAN["type"] = ["FraisCourtageMonetaire",]
        TRAN["fees_broker"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] == "Impôts sur dividende":
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["ImpotsDividende",]
        TRAN["fees_revtax"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Intérêts débiteurs mensuels (Débit Argent)",]:
        assert(not mydict["Id"])
        assert(not mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["InteretsDebiteurs",]
        TRAN["fees_broker"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Operation de change - Crédit", "Opération de change - Débit",] and mydict["Isin"] and mydict["Product"]:
        assert(parse_curr_pair(mydict["Product"]) is None)
        assert(mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        if mydict["Currency"] == BASE_CURR:
            assert(not mydict["ForexRate"])
        elif mydict["Currency"] != BASE_CURR:
            assert(mydict["ForexRate"])
        if mydict["Amount"] > 0:
            if mydict["Currency"] == BASE_CURR:
                TRAN["type"] = ["OrdreActionVenteChange",]
            elif mydict["Currency"] != BASE_CURR:
                TRAN["type"] = ["OrdreActionAchatChange",]
        elif mydict["Amount"] < 0:
            if mydict["Currency"] == BASE_CURR:
                TRAN["type"] = ["OrdreActionAchatChange",]
            elif mydict["Currency"] != BASE_CURR:
                TRAN["type"] = ["OrdreActionVenteChange",]
        else:
            assert(False)
        TRAN["change_accu"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Operation de change - Crédit", "Opération de change - Débit",] and not mydict["Isin"] and mydict["Product"] and mydict["Id"]:
        assert(parse_curr_pair(mydict["Product"]) is not None)
        assert(mydict["Id"])
        assert(mydict["Product"])
        assert(not mydict["Isin"])
        if mydict["Currency"] == BASE_CURR:
            assert(not mydict["ForexRate"])
        elif mydict["Currency"] != BASE_CURR:
            assert(mydict["ForexRate"])
        if mydict["Amount"] > 0:
            if mydict["Currency"] == BASE_CURR:
                TRAN["type"] = ["OrdreMonetaireVenteChange",]
            elif mydict["Currency"] != BASE_CURR:
                TRAN["type"] = ["OrdreMonetaireAchatChange",]
        elif mydict["Amount"] < 0:
            if mydict["Currency"] == BASE_CURR:
                TRAN["type"] = ["OrdreMonetaireAchatChange",]
            elif mydict["Currency"] != BASE_CURR:
                TRAN["type"] = ["OrdreMonetaireVenteChange",]
        else:
            assert(False)
        TRAN["change_accu"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Operation de change - Crédit", "Opération de change - Débit",] and not mydict["Isin"] and mydict["Product"] and not mydict["Id"]:
        assert(parse_curr_pair(mydict["Product"]) is not None)
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(not mydict["Isin"])
        if mydict["Currency"] == BASE_CURR:
            assert(not mydict["ForexRate"])
        elif mydict["Currency"] != BASE_CURR:
            assert(mydict["ForexRate"])
        if mydict["Amount"] > 0:
            if mydict["Currency"] == BASE_CURR:
                TRAN["type"] = ["AutoMonetaireVenteChange",]
            elif mydict["Currency"] != BASE_CURR:
                TRAN["type"] = ["AutoMonetaireAchatChange",]
        elif mydict["Amount"] < 0:
            if mydict["Currency"] == BASE_CURR:
                TRAN["type"] = ["AutoMonetaireAchatChange",]
            elif mydict["Currency"] != BASE_CURR:
                TRAN["type"] = ["AutoMonetaireVenteChange",]
        else:
            assert(False)
        TRAN["change_accu"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Operation de change - Crédit", "Opération de change - Débit",] and not mydict["Isin"] and not mydict["Product"] and not mydict["Id"]:
        assert(not mydict["Id"])
        assert(not mydict["Product"])
        assert(not mydict["Isin"])
        if mydict["Currency"] == BASE_CURR:
            assert(not mydict["ForexRate"])
        elif mydict["Currency"] != BASE_CURR:
            assert(mydict["ForexRate"])
        if mydict["Amount"] > 0:
            if mydict["Currency"] == BASE_CURR:
                TRAN["type"] = ["AutoDivOuMonetaireVenteChange",]
            elif mydict["Currency"] != BASE_CURR:
                TRAN["type"] = ["AutoDivOuMonetaireAchatChange",]
        elif mydict["Amount"] < 0:
            if mydict["Currency"] == BASE_CURR:
                TRAN["type"] = ["AutoDivOuMonetaireAchatChange",]
            elif mydict["Currency"] != BASE_CURR:
                TRAN["type"] = ["AutoDivOuMonetaireVenteChange",]
        else:
            assert(False)
        TRAN["change_accu"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Processed Flatex Withdrawal",]:
        assert(not mydict["Id"])
        assert(not mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["ProcessedFlatexWithdrawal",]
        return TRAN
    elif mydict["Description"].startswith("Règlement transaction devise: ") and parse_curr_pair(mydict["Product"]) is not None:
        assert(mydict["Id"])
        assert(mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        mydescr = parse_description(mydict["Description"].split("Règlement transaction devise: ")[1],
                                    mydict["Product"], mydict["Isin"], mydict["Currency"], mydict["Amount"])
        if parse_curr_pair(mydict["Product"])[0] == BASE_CURR:
            TRAN["fx_list"] = [mydescr["price"],]
        elif parse_curr_pair(mydict["Product"])[1] == BASE_CURR:
            TRAN["fx_list"] = [1 / mydescr["price"],]
        else:
            assert(False)
        TRAN["type"] = ["ReglementTransactionDevise",]  # not CurrSell nor CurrBuy because of wrong direction
        TRAN["change_accu"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] == "Remboursement de capital":
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["RemboursementCapital",]
        return TRAN
    elif mydict["Description"] in ["Remboursement offre promotionnelle",]:
        assert(not mydict["Id"])
        assert(not mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["RemboursementOffrePromotionnelle",]
        TRAN["fees_broker"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"].startswith("Retenue à la source "):
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["ImpotsRetenueSource",]
        TRAN["fees_revtax"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Retrait de fonds", "Versement de fonds",]:
        assert(not mydict["Id"])
        assert(not mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["TransferExt",]
        return TRAN
    elif mydict["Description"] in ["Retrait flatex", "Dépôt flatex",]:
        assert(not mydict["Id"])
        assert(not mydict["Product"])
        assert(not mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["TransferExtFlatex",]
        return TRAN
    elif mydict["Description"] in ["Stamp Duty - Hong-Kong", "Taxe sur les Transactions Financières (TTF)",]:
        assert(mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["FinancialTransactionsTax",]
        TRAN["fees_finpla"] = {mydict["Currency"]: mydict["Amount"]}
        return TRAN
    elif mydict["Description"] in ["Transfert de fonds Flatex",]:
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["TransfertFondsFlatex",]
        return TRAN
    elif mydict["Description"] in [f'Variation Fonds Monétaires ({mydict["Currency"]})',]:
        assert(not mydict["Id"])
        assert(mydict["Product"])
        assert(mydict["Isin"])
        assert(not mydict["ForexRate"])
        TRAN["type"] = ["FondsMonetairesVariation",]
        return TRAN
    else:
        TRAN["valid"] = False
        TRAN["comment"].append(f'ERROR : Unknown transaction type : {mydict}')
        return TRAN


#%%
def compute_fx_global(operation):
    import numpy
    if len(operation["fx_list"]) > 1 and not numpy.isclose(min(operation["fx_list"]), max(operation["fx_list"]), rtol=0.02):
        operation["comment"].append('WARNING : fx variation')
        operation["valid"] = False
        return operation
    
    if len(operation["index"]) == 1 and operation["cash"].keys() == {BASE_CURR}:
        operation["block_fx_basfor"] = 1.00
    elif len(operation["change_accu"].keys()) == 0 and operation["cash"].keys() == {BASE_CURR}:
        assert(len(operation["fx_list"]) == 0)
        operation["block_fx_basfor"] = 1.00
    elif len(operation["index"]) == 1 and operation["cash"].keys() != {BASE_CURR}:
        operation["block_fx_basfor"] = None
    elif len(operation["change_accu"].keys()) == 0 and operation["cash"].keys() != {BASE_CURR}:
        assert(len(operation["fx_list"]) == 0)
        operation["block_fx_basfor"] = None
    elif len(operation["change_accu"].keys()) == 1 and operation["change_accu"].keys() == {BASE_CURR} and operation["cash"].keys() == {BASE_CURR}:
        assert(len(operation["fx_list"]) == 0)
        operation["block_fx_basfor"] = 1.00
    elif len(operation["change_accu"].keys()) == 2:
        curr = list(operation["change_accu"].keys())
        if curr[0] == BASE_CURR:
            operation["block_fx_basfor"] = -1 * operation["change_accu"][curr[1]] / operation["change_accu"][curr[0]]
        elif curr[1] == BASE_CURR:
            operation["block_fx_basfor"] = -1 * operation["change_accu"][curr[0]] / operation["change_accu"][curr[1]]
        else:
            operation["block_fx_basfor"] = None
            operation["comment"].append('ERROR : block_fx_basfor')
            operation["valid"] = False
            return operation
        if not numpy.isclose(operation["block_fx_basfor"], numpy.mean(operation["fx_list"]), rtol=0.005):
            operation["comment"].append('WARNING : fx rate not consistent')
#            operation["valid"] = False  # Because of Balance corr
            return operation
    else:
        operation["block_fx_basfor"] = None
        operation["comment"].append('ERROR : change_accu : {operation["change_accu"]}')
        operation["valid"] = False
    return operation


#%%
def compute_fees(operation, fees_broker_ratio_limit, fees_finpla_ratio_limit, fees_revtax_ratio_limit):
    if operation["block_fx_basfor"] is None:
        operation["block_fees_broker_ratio"] = None
        operation["block_fees_finpla_ratio"] = None
        operation["block_fees_revtax_ratio"] = None
        return operation
    fees_broker = convert_amount_to_base_curr(operation["fees_broker"], operation["block_fx_basfor"])  # Approx formula
    fees_finpla = convert_amount_to_base_curr(operation["fees_finpla"], operation["block_fx_basfor"])  # Approx formula
    fees_revtax = convert_amount_to_base_curr(operation["fees_revtax"], operation["block_fx_basfor"])  # Approx formula
    amount_before_fees = operation["cash"][BASE_CURR] - (fees_broker + fees_finpla + fees_revtax)
    if amount_before_fees == 0:
        operation["block_fees_broker_ratio"] = None
        operation["block_fees_finpla_ratio"] = None
        operation["block_fees_revtax_ratio"] = None
        return operation
    operation["block_fees_broker_ratio"] = -fees_broker / abs(amount_before_fees)
    operation["block_fees_finpla_ratio"] = -fees_finpla / abs(amount_before_fees)
    operation["block_fees_revtax_ratio"] = -fees_revtax / abs(amount_before_fees)
    if not (operation["block_fees_broker_ratio"] >= 0 and operation["block_fees_broker_ratio"] <= 1):
        operation["comment"].append("ERROR : block_fees_broker_ratio")
        operation["valid"] = False
        return operation
    if not (operation["block_fees_finpla_ratio"] >= 0 and operation["block_fees_finpla_ratio"] <= 1):
        operation["comment"].append("ERROR : block_fees_finpla_ratio")
        operation["valid"] = False
        return operation
    if not (operation["block_fees_revtax_ratio"] >= 0 and operation["block_fees_revtax_ratio"] <= 1):
        operation["comment"].append("ERROR : block_fees_revtax_ratio")
        operation["valid"] = False
        return operation
    
    if fees_broker_ratio_limit[0] is not None and operation["block_fees_broker_ratio"] < fees_broker_ratio_limit[0]:
        operation["comment"].append("WARNING : fees_broker")
    if fees_broker_ratio_limit[1] is not None and operation["block_fees_broker_ratio"] > fees_broker_ratio_limit[1]:
        operation["comment"].append("WARNING : fees_broker")
    if fees_finpla_ratio_limit[0] is not None and operation["block_fees_finpla_ratio"] < fees_finpla_ratio_limit[0]:
        operation["comment"].append("WARNING : fees_finpla")
    if fees_finpla_ratio_limit[1] is not None and operation["block_fees_finpla_ratio"] > fees_finpla_ratio_limit[1]:
        operation["comment"].append("WARNING : fees_finpla")
    if fees_revtax_ratio_limit[0] is not None and operation["block_fees_revtax_ratio"] < fees_revtax_ratio_limit[0]:
        operation["comment"].append("WARNING : fees_revtax")
    if fees_revtax_ratio_limit[1] is not None and operation["block_fees_revtax_ratio"] > fees_revtax_ratio_limit[1]:
        operation["comment"].append("WARNING : fees_revtax")
    
    return operation


#%%
def compute_price_avg(operation):
    if operation["block_type"] in ["ShareBuy", "ShareSell", "ShareBuy_For", "ShareSell_For",]:
        assert(operation["cash"].keys() == {BASE_CURR})
        assert(operation["nb"] is not None)
        operation["block_price_avg"] = -1 * operation["cash"][BASE_CURR] / operation["nb"]
    else:
        operation["block_price_avg"] = None
    return operation


#%%
def compute_block(new_df):
    operation = convert_block_to_operation(new_df)
    operation["block_type"] = None
    operation["block_reliability"] = None
    operation["block_fx_basfor"] = None
    operation["block_fees_broker_ratio"] = None
    operation["block_fees_finpla_ratio"] = None
    operation["block_fees_revtax_ratio"] = None
    operation["block_price_avg"] = None
    operation["block_description"] = None
    operation["block_pl"] = None
    
    if operation["valid"] is False:
        return operation
    
    list_isin = sorted(list(set(new_df["Isin"])))
    list_isin =[x for x in list_isin if x != ""]
    
    if operation["type"] in [["TransferExtFlatex",],
                             ["TransferExt",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_base(new_df, operation)
        operation["block_type"] = "CashTransferExt"
        fees_broker_ratio_limit = [0.00, 0.00]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 100
    elif operation["type"] in [["ProcessedFlatexWithdrawal",],
                               ["DegiroCashSweepTransfer",],
                               ["TransfertFondsFlatex",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_base(new_df, operation)
        operation["block_type"] = "CashTransferInt"
        fees_broker_ratio_limit = [0.00, 0.00]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 100
    elif operation["type"] in [["ChangementIsin", "ChangementIsin",],
                               ["Split", "Split",],]:
        operation = check_operation_mono(operation, "id")
#        operation = check_operation_mono(operation, "prod")
#        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_single(new_df, operation)
        assert(operation["cash"][BASE_CURR] == 0)
        operation["block_type"] = "Renaming/Split"
        fees_broker_ratio_limit = [0.00, 0.00]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 80
    elif operation["type"] in [["FondsMonetairesConversion",],
                               ["FondsMonetairesVariation",],
                               ["FondsMonetairesDistribution",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_block_curr_single(new_df, operation)
        operation["block_type"] = "MonetaryFund"
        fees_broker_ratio_limit = [0.00, 0.00]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 100
    elif operation["type"] in [["FraisConnexionPlacesBoursieres",],
                               ["RemboursementOffrePromotionnelle",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_block_curr_base(new_df, operation)
        operation = checksum_operation_basecurr(operation)
        operation["block_type"] = "FeesBank"
        fees_broker_ratio_limit = [None, None]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 100
    elif operation["type"] in [["FondsMonetairesCompensation",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_block_curr_single(new_df, operation)
        operation["block_type"] = "MonetaryFund"
        fees_broker_ratio_limit = [None, None]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 100
    elif set(operation["type"]) in [{"OrdreActionAchat", "FraisCourtageAction",},
                                    {"OrdreActionAchat", "FraisCourtageAction", "FinancialTransactionsTax",},]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_base(new_df, operation)
        operation["block_type"] = "ShareBuy"
        fees_broker_ratio_limit = [0.00, 0.01]
        fees_finpla_ratio_limit = [0.00, 0.01]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 90
        operation = compute_price_avg(operation)
    elif set(operation["type"]) in [{"OrdreActionAchat", "FraisCourtageAction", "OrdreActionAchatChange",},
                                    {"OrdreActionAchat", "FraisCourtageAction", "OrdreActionAchatChange", "FinancialTransactionsTax",},]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "ShareBuy_For"
        fees_broker_ratio_limit = [0.00, 0.01]
        fees_finpla_ratio_limit = [0.00, 0.01]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 90
        operation = compute_price_avg(operation)
    elif set(operation["type"]) in [{"OrdreActionVente", "FraisCourtageAction",},
                                    {"OrdreActionVente", "FraisCourtageAction", "FinancialTransactionsTax",},]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_base(new_df, operation)
        operation["block_type"] = "ShareSell"
        fees_broker_ratio_limit = [0.00, 0.01]
        fees_finpla_ratio_limit = [0.00, 0.01]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 90
        operation = compute_price_avg(operation)
    elif set(operation["type"]) in [{"OrdreActionVente", "FraisCourtageAction", "OrdreActionVenteChange",},
                                    {"OrdreActionVente", "FraisCourtageAction", "OrdreActionVenteChange", "FinancialTransactionsTax",},]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "ShareSell_For"
        fees_broker_ratio_limit = [0.00, 0.01]
        fees_finpla_ratio_limit = [0.00, 0.01]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 90
        operation = compute_price_avg(operation)
    elif set(operation["type"]) in [{"OrdreMonetaireAchat", "OrdreMonetaireAchatChange", "FraisCourtageMonetaire", "ReglementTransactionDevise",},]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_operation_change_curr_list(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "CurrBuy_withId"
        fees_broker_ratio_limit = [0.00, 0.01]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 90
    elif set(operation["type"]) in [{"OrdreMonetaireVente", "OrdreMonetaireVenteChange", "FraisCourtageMonetaire", "ReglementTransactionDevise",},]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_operation_change_curr_list(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "CurrSell_withId"
        fees_broker_ratio_limit = [0.00, 0.01]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 90
    elif operation["type"] in [["AutoMonetaireAchatChange", "AutoMonetaireAchatChange", "FraisCourtageMonetaire",],
                               ["AutoMonetaireAchatChange", "AutoMonetaireAchatChange",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_operation_change_curr_list(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "CurrBuy_withProd"
        fees_broker_ratio_limit = [0.00, 0.01]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 80
    elif operation["type"] in [["AutoMonetaireVenteChange", "AutoMonetaireVenteChange", "FraisCourtageMonetaire",],
                               ["AutoMonetaireVenteChange", "AutoMonetaireVenteChange",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_operation_change_curr_list(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "CurrSell_withProd"
        fees_broker_ratio_limit = [0.00, 0.01]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 80
    elif operation["type"] in [["AutoDivOuMonetaireAchatChange", "AutoDivOuMonetaireAchatChange",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_operation_change_curr_list(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "CurrBuy"
        fees_broker_ratio_limit = [0.00, 0.00]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 20
    elif operation["type"] in [["AutoDivOuMonetaireVenteChange","AutoDivOuMonetaireVenteChange",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_operation_change_curr_list(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "CurrSell"
        fees_broker_ratio_limit = [0.00, 0.00]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 20
    elif operation["type"] in [["RemboursementCapital", "FraisOST",],
                               ["RemboursementCapital",            ],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_base(new_df, operation)
        operation["block_type"] = "Roc_Bas"
        fees_broker_ratio_limit = [0.00, 0.10]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 80
    elif operation["type"] in [["RemboursementCapital", "FraisOST", "AutoDivOuMonetaireVenteChange", "AutoDivOuMonetaireVenteChange",],
                               ["RemboursementCapital",             "AutoDivOuMonetaireVenteChange", "AutoDivOuMonetaireVenteChange",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_single(new_df, operation)
        operation["block_type"] = "Roc_For"
        fees_broker_ratio_limit = [0.00, 0.10]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 80
    elif set(operation["type"]) in [{"Dividende", "FraisOST", "ImpotsDividende",},
                                    {"Dividende",             "ImpotsDividende",},
                                    {"Dividende", "FraisOST",                   },
                                    {"Dividende",                               },]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_base(new_df, operation)
        operation["block_type"] = "Div_Bas"
        fees_broker_ratio_limit = [0.00, 0.10]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.30]
        operation["block_reliability"] = 40
    elif set(operation["type"]) in [{"Dividende", "AutoDivOuMonetaireVenteChange", "FraisOST", "ImpotsDividende","AutoDivOuMonetaireAchatChange",},  # Specific
                                    {"Dividende", "AutoDivOuMonetaireVenteChange", "FraisOST", "ImpotsDividende","ImpotsRetenueSource",},  # Specific
                                    {"Dividende", "AutoDivOuMonetaireVenteChange", "FraisOST",                   },
                                    {"Dividende", "AutoDivOuMonetaireVenteChange", "FraisOST", "ImpotsDividende",},
                                    {"Dividende", "AutoDivOuMonetaireVenteChange",                               },
                                    {"Dividende", "AutoDivOuMonetaireVenteChange",             "ImpotsDividende",},] and len(list_isin) == 1:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "Div_For"
        fees_broker_ratio_limit = [0.00, 0.10]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.30]
        operation["block_reliability"] = 50
    elif set(operation["type"]) in [{"Dividende", "AutoDivOuMonetaireVenteChange", "FraisOST",                   },
                                    {"Dividende", "AutoDivOuMonetaireVenteChange", "FraisOST", "ImpotsDividende",},
                                    {"Dividende", "AutoDivOuMonetaireVenteChange",                               },
                                    {"Dividende", "AutoDivOuMonetaireVenteChange",             "ImpotsDividende",},] and len(list_isin) > 1:
        operation = check_operation_mono(operation, "id")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "Div_For_Multi"
        fees_broker_ratio_limit = [0.00, 0.10]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.30]
        operation["block_reliability"] = 50
    elif set(operation["type"]) in [{"Dividende", "FraisOST",                    "RemboursementCapital",},
                                    {"Dividende", "FraisOST", "ImpotsDividende", "RemboursementCapital",},
                                    {"Dividende",                                "RemboursementCapital",},
                                    {"Dividende",             "ImpotsDividende", "RemboursementCapital",},]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_base(new_df, operation)
        operation["block_type"] = "DivRoc_Bas"
        fees_broker_ratio_limit = [0.00, 0.10]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.30]
        operation["block_reliability"] = 40
    elif set(operation["type"]) in [{"Dividende", "AutoDivOuMonetaireVenteChange", "FraisOST",                    "RemboursementCapital",},
                                    {"Dividende", "AutoDivOuMonetaireVenteChange", "FraisOST", "ImpotsDividende", "RemboursementCapital",},
                                    {"Dividende", "AutoDivOuMonetaireVenteChange",                                "RemboursementCapital",},
                                    {"Dividende", "AutoDivOuMonetaireVenteChange",             "ImpotsDividende", "RemboursementCapital",},]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = checksum_operation_basecurr(operation)
        operation = check_block_curr_double(new_df, operation)
        operation["block_type"] = "DivRoc_For"
        fees_broker_ratio_limit = [0.00, 0.10]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.30]
        operation["block_reliability"] = 50
    elif operation["type"] in [["FlatexInterest",],
                               ["InteretsDebiteurs",],]:
        operation = check_operation_mono(operation, "id")
        operation = check_operation_mono(operation, "prod")
        operation = check_operation_mono(operation, "isin")
        operation = check_block_curr_single(new_df, operation)
        operation["block_type"] = "Interests"
        fees_broker_ratio_limit = [0.00, 0.00]
        fees_finpla_ratio_limit = [0.00, 0.00]
        fees_revtax_ratio_limit = [0.00, 0.00]
        operation["block_reliability"] = 100
    else:
        operation["comment"].append(f'ERROR : Unknown block : {set(operation["type"])} : {new_df.index}')
        operation["valid"] = False
        return operation
    
    if operation["valid"] is False:
        return operation
    
    operation = compute_fx_global(operation)
    if operation["valid"] is False:
        return operation
    
    operation = compute_fees(operation, fees_broker_ratio_limit, fees_finpla_ratio_limit, fees_revtax_ratio_limit)
    operation["block_description"] = str(new_df)[0:9999]
    
    return operation

