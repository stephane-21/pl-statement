import pandas


class Wallet:
    def __init__(self):
        self.WALLET = {
                       "_Positions": {},
                       "_PL": {},
                       "_Misc": {},
                      }
    
    def update(self, date, isin, name, nb, price):
        if nb == 0 and price == 0:
            return 0
        self.WALLET["_Positions"].setdefault(isin, {"name": name, "nb": 0, "price": 0,})
        if nb > 0 and self.WALLET["_Positions"][isin]["nb"] >= 0:  # Buy std
            pl = self.increase(date, isin, name, nb, price)
        elif nb < 0 and self.WALLET["_Positions"][isin]["nb"] <= 0:  # Sell short
            pl = self.increase(date, isin, name, nb, price)
        elif nb < 0 and self.WALLET["_Positions"][isin]["nb"] >= 0:  # Sell std
            if self.WALLET["_Positions"][isin]["nb"] + nb >= 0:
                pl = self.decrease(date, isin, name, nb, price)
            else:
                ratio = -self.WALLET["_Positions"][isin]["nb"] / nb
                pl_1 = self.decrease(date, isin, name, round(nb * ratio      , 4), round(price * ratio      , 4))
                pl_2 = self.increase(date, isin, name, round(nb * (1 - ratio), 4), round(price * (1 - ratio), 4))
                pl = pl_1 + pl_2
        elif nb > 0 and self.WALLET["_Positions"][isin]["nb"] <= 0:  # Buy short
            if self.WALLET["_Positions"][isin]["nb"] + nb <= 0:
                pl = self.decrease(date, isin, name, nb, price)
            else:
                ratio = -self.WALLET["_Positions"][isin]["nb"] / nb
                pl_1 = self.decrease(date, isin, name, round(nb * ratio      , 4), round(price * ratio      , 4))
                pl_2 = self.increase(date, isin, name, round(nb * (1 - ratio), 4), round(price * (1 - ratio), 4))
                pl = pl_1 + pl_2
        else:
            assert(False)
        if self.WALLET["_Positions"][isin]["nb"] == 0:
            assert(round(self.WALLET["_Positions"][isin]["price"], 2) == 0)
            del(self.WALLET["_Positions"][isin])
        elif self.WALLET["_Positions"][isin]["nb"] > 0:
            assert(self.WALLET["_Positions"][isin]["price"] < 0)
        elif self.WALLET["_Positions"][isin]["nb"] < 0:
            assert(self.WALLET["_Positions"][isin]["price"] > 0)
        return pl
    
    def increase(self, date, isin, name, nb, price):
        assert(nb != 0)
        assert(price != 0)
        self.WALLET["_Positions"][isin]["nb"]    = self.WALLET["_Positions"][isin]["nb"] + nb
        self.WALLET["_Positions"][isin]["price"] = self.WALLET["_Positions"][isin]["price"] + price
        self.WALLET["_Positions"][isin]["nb"] = round(self.WALLET["_Positions"][isin]["nb"], 4)
        self.WALLET["_Positions"][isin]["price"] = round(self.WALLET["_Positions"][isin]["price"], 4)
        pl = 0
        return pl
    
    def decrease(self, date, isin, name, nb, price):
        assert(nb != 0)
        assert(price != 0)
        pu = self.WALLET["_Positions"][isin]["price"] / self.WALLET["_Positions"][isin]["nb"]
        pl = price - pu * nb
        self.WALLET["_Positions"][isin]["nb"]    = self.WALLET["_Positions"][isin]["nb"] + nb
        self.WALLET["_Positions"][isin]["price"] = self.WALLET["_Positions"][isin]["price"] + pu * nb
        self.WALLET["_Positions"][isin]["nb"] = round(self.WALLET["_Positions"][isin]["nb"], 4)
        self.WALLET["_Positions"][isin]["price"] = round(self.WALLET["_Positions"][isin]["price"], 4)
        self.add_pl(date, isin, name, pl)
        return pl
    
    def rename(self, isin_1, isin_2, name_1, name_2, nb_1, nb_2):
        self.WALLET["_Positions"][isin_2] = self.WALLET["_Positions"].pop(isin_1)
        self.WALLET["_Positions"][isin_2]["name"] = name_2
        assert(self.WALLET["_Positions"][isin_2]["nb"] + nb_1 == 0)
        self.WALLET["_Positions"][isin_2]["nb"] = nb_2
        pl = 0
        return pl
    
    def add_pl(self, date, ref, description, cash):
        self.WALLET["_PL"].setdefault(ref, {"description": [], "value": 0})
        self.WALLET["_PL"][ref]["value"] = self.WALLET["_PL"][ref]["value"] + cash
        self.WALLET["_PL"][ref]["description"] = list(set(self.WALLET["_PL"][ref]["description"] + [description,]))
        self.WALLET["_PL"].setdefault("_GLOBAL", {"description": [], "value": 0})
        self.WALLET["_PL"]["_GLOBAL"]["value"] = self.WALLET["_PL"]["_GLOBAL"]["value"] + cash
        year = str(date.year)
        self.WALLET["_PL"][ref].setdefault(year, 0)
        self.WALLET["_PL"][ref][year] = self.WALLET["_PL"][ref][year] + cash
        self.WALLET["_PL"]["_GLOBAL"].setdefault(year, 0)
        self.WALLET["_PL"]["_GLOBAL"][year] = self.WALLET["_PL"]["_GLOBAL"][year] + cash
        return
    
    def add_misc(self, date, ref, description, cash):
        self.WALLET["_Misc"].setdefault(ref, {"description": [], "value": 0,})
        self.WALLET["_Misc"][ref]["value"] = self.WALLET["_Misc"][ref]["value"] + cash
        self.WALLET["_Misc"][ref]["description"] = list(set(self.WALLET["_Misc"][ref]["description"] + [description,]))
        return
    
    def export(self):
        mydict = {}
        mydict["_Positions"] = pandas.DataFrame.from_dict(self.WALLET["_Positions"], orient='index')
        mydict["_PL"] = pandas.DataFrame.from_dict(self.WALLET["_PL"], orient='index')
        mydict["_Misc"] = pandas.DataFrame.from_dict(self.WALLET["_Misc"], orient='index')
        
        mydict["_Positions"].reset_index(inplace=True)  # Create index column
        mydict["_PL"].reset_index(inplace=True)  # Create index column
        mydict["_Misc"].reset_index(inplace=True)  # Create index column
        
        mydict["_Positions"] = mydict["_Positions"].sort_values(by=["index"], ascending=[True,])
        mydict["_PL"] = mydict["_PL"].sort_values(by=["index"], ascending=[True,])
        mydict["_Misc"] = mydict["_Misc"].sort_values(by=["index"], ascending=[True,])
        
        mydict["_Positions"].reset_index(inplace=True, drop=True)
        mydict["_PL"].reset_index(inplace=True, drop=True)
        mydict["_Misc"].reset_index(inplace=True, drop=True)
        return mydict

