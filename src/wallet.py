import numpy
import pandas

from src.currency import Currency


class Wallet:
    def __init__(self, BASE_CURR, ACCURACY_CURR):
        self.BASE_CURR = BASE_CURR
        self.CURR = Currency()
        self.ACCURACY_CURR = ACCURACY_CURR
        self.ACCURACY_POS = ACCURACY_CURR
        self.WALLET = {
                       "_Misc": {"BASE_CURR": {"value": BASE_CURR,}},
                       "_Positions": {BASE_CURR: {"isin": None, "ticker": None, "name": None, "nb": 0, "price": 0, "current_price": None, "current_pl": 0,}},
                       "_Transfers": {BASE_CURR: {"isin": None, "ticker": None, "name": None, "nb": 0, "price": 0,}},
                       "_PL": {},
                      }
    
    def transaction(self, date, ref_pos, nb, cash, isin, ticker, name):
        curr = list(cash.keys())
        assert(len(curr) == 1)
        curr = curr[0]
        amount_curr = cash[curr]
        amount_curr = round(amount_curr, self.ACCURACY_CURR)
        fx_rate = self.CURR.get_value(curr, date)
        amount_base_curr = amount_curr / fx_rate
        amount_base_curr = round(amount_base_curr, self.ACCURACY_CURR)
        if curr != self.BASE_CURR:
            pl2 = self.transaction(date=date,
                                   ref_pos=curr,
                                   nb=amount_curr,
                                   cash={self.BASE_CURR:-amount_base_curr},
                                   isin="",
                                   ticker="",
                                   name="")
        else:
            pl2 = 0
        if numpy.sign(nb) * numpy.sign(amount_base_curr) == 1:
            print(f'WARNING : suspicious transaction : {nb} {amount_base_curr}')
        nb = round(nb, self.ACCURACY_POS)
        self.WALLET["_Positions"][self.BASE_CURR]["nb"] += amount_base_curr
        self.WALLET["_Positions"][self.BASE_CURR]["price"] += amount_base_curr
        self.WALLET["_Positions"].setdefault(ref_pos, {"isin": isin, "ticker": ticker, "name": name, "nb": 0, "price": 0,})
        if nb == 0:
            pl = self._increase_position(date, ref_pos, nb, amount_base_curr, isin, ticker, name)
        elif nb > 0 and self.WALLET["_Positions"][ref_pos]["nb"] >= 0:
            pl = self._increase_position(date, ref_pos, nb, amount_base_curr, isin, ticker, name)
        elif nb < 0 and self.WALLET["_Positions"][ref_pos]["nb"] <= 0:
            pl = self._increase_position(date, ref_pos, nb, amount_base_curr, isin, ticker, name)
        elif nb < 0 and self.WALLET["_Positions"][ref_pos]["nb"] + nb >= 0:
            pl = self._decrease_position(date, ref_pos, nb, amount_base_curr, isin, ticker, name)
        elif nb > 0 and self.WALLET["_Positions"][ref_pos]["nb"] + nb <= 0:
            pl = self._decrease_position(date, ref_pos, nb, amount_base_curr, isin, ticker, name)
        else:  # Overshoot
            nb_1 = -self.WALLET["_Positions"][ref_pos]["nb"]
            nb_2 = nb - nb_1
            ratio_1 = -self.WALLET["_Positions"][ref_pos]["nb"] / nb
            amount_1 = round(amount_base_curr * ratio_1, self.ACCURACY_CURR)
            amount_2 = amount_base_curr - amount_1
            pl_1 = self._decrease_position(date, ref_pos, nb_1, amount_1, isin, ticker, name)
            pl_2 = self._increase_position(date, ref_pos, nb_2, amount_2, isin, ticker, name)
            pl = pl_1 + pl_2
        if abs(self.WALLET["_Positions"][ref_pos]["nb"]) < 10**-8:
            assert(abs(self.WALLET["_Positions"][ref_pos]["price"]) < 10**-8)
            del(self.WALLET["_Positions"][ref_pos])
        else:
            if numpy.sign(self.WALLET["_Positions"][ref_pos]["nb"]) * numpy.sign(self.WALLET["_Positions"][ref_pos]["price"]) == 1:
                print(f'WARNING : suspicious position : {ref_pos} : {self.WALLET["_Positions"][ref_pos]}')
        return pl + pl2
    
    def _increase_position(self, date, ref_pos, nb, amount_base_curr, isin, ticker, name):
        self.WALLET["_Positions"][ref_pos]["nb"] += nb
        self.WALLET["_Positions"][ref_pos]["price"] += amount_base_curr
        pl = 0
        return pl
    
    def _decrease_position(self, date, ref_pos, nb, amount_base_curr, isin, ticker, name):
        amount_0 = round(self.WALLET["_Positions"][ref_pos]["price"] * nb / self.WALLET["_Positions"][ref_pos]["nb"], self.ACCURACY_CURR)
        pl = amount_base_curr - amount_0
        self.WALLET["_Positions"][ref_pos]["nb"] += nb
        self.WALLET["_Positions"][ref_pos]["price"] += amount_0
        self._register_pl(date, ref_pos, pl, isin, ticker, name)
        return pl
    
    def rename_position(self, ref_pos_1, ref_pos_2, name_1, name_2):
        self.WALLET["_Positions"][ref_pos_2] = self.WALLET["_Positions"].pop(ref_pos_1)
        self.WALLET["_Positions"][ref_pos_2]["name"] = name_2
        return
    
    def split_position(self, ref_pos, nb_delta, coeff_split):
        if not nb_delta is None:
            self.WALLET["_Positions"][ref_pos]["nb"] = self.WALLET["_Positions"][ref_pos]["nb"] + nb_delta
        elif not coeff_split is None:
            self.WALLET["_Positions"][ref_pos]["nb"] = self.WALLET["_Positions"][ref_pos]["nb"] * coeff_split
        else:
            assert(False)
        return
    
    def add_cash(self, date, ref_pl, cash, isin, ticker, name):
        curr = list(cash.keys())
        assert(len(curr) == 1)
        curr = curr[0]
        amount_curr = cash[curr]
        amount_curr = round(amount_curr, self.ACCURACY_CURR)
        fx_rate = self.CURR.get_value(curr, date)
        amount_base_curr = round(amount_curr / fx_rate, self.ACCURACY_CURR)
        self.WALLET["_Positions"][self.BASE_CURR]["nb"] += amount_base_curr
        self.WALLET["_Positions"][self.BASE_CURR]["price"] += amount_base_curr
        self._register_pl(date, ref_pl, amount_base_curr, isin, ticker, name)
        if curr != self.BASE_CURR:
            pl2 = self.transaction(date=date,
                                   ref_pos=curr,
                                   nb=amount_curr,
                                   cash={self.BASE_CURR:-amount_base_curr},
                                   isin="",
                                   ticker="",
                                   name="")
        else:
            pl2 = 0
        pl = amount_base_curr + pl2
        return pl
    
    def _register_pl(self, date, ref_pl, amount_base_curr, isin, ticker, name):
        year = str(date.year)
        self.WALLET["_PL"].setdefault(ref_pl, {"isin": [], "ticker": [], "name": [], "value": 0})
        self.WALLET["_PL"][ref_pl]["value"] += amount_base_curr
        self.WALLET["_PL"][ref_pl]["isin"] += [isin,]
        self.WALLET["_PL"][ref_pl]["ticker"] += [ticker,]
        self.WALLET["_PL"][ref_pl]["name"] += [name,]
        self.WALLET["_PL"][ref_pl]["isin"] = list(set(self.WALLET["_PL"][ref_pl]["isin"]))
        self.WALLET["_PL"][ref_pl]["ticker"] = list(set(self.WALLET["_PL"][ref_pl]["ticker"]))
        self.WALLET["_PL"][ref_pl]["name"] = list(set(self.WALLET["_PL"][ref_pl]["name"]))
        self.WALLET["_PL"][ref_pl].setdefault(year, 0)
        self.WALLET["_PL"][ref_pl][year] += amount_base_curr
        self.WALLET["_PL"].setdefault("_GLOBAL", {"value": 0})
        self.WALLET["_PL"]["_GLOBAL"]["value"] += amount_base_curr
        self.WALLET["_PL"]["_GLOBAL"].setdefault(year, 0)
        self.WALLET["_PL"]["_GLOBAL"][year] += amount_base_curr
        return
    
    def transfer_cash(self, cash):
        curr = list(cash.keys())
        assert(len(curr) == 1)
        curr = curr[0]
        amount = cash[curr]
        amount = round(amount, self.ACCURACY_CURR)
        if curr == self.BASE_CURR:
            pl = self._transfer_base_curr(amount)
        else:
            pl = self._transfer_position(curr, amount)
        return pl
    
    def _transfer_base_curr(self, amount_base_curr):
        self.WALLET["_Positions"][self.BASE_CURR]["nb"] += amount_base_curr
        self.WALLET["_Positions"][self.BASE_CURR]["price"] += amount_base_curr
        self.WALLET["_Transfers"][self.BASE_CURR]["nb"] += -amount_base_curr
        self.WALLET["_Transfers"][self.BASE_CURR]["price"] += -amount_base_curr
        pl = 0
        return pl
    
    def _transfer_position(self, ref_pos, nb):
        self.WALLET["_Transfers"].setdefault(ref_pos, {"isin": self.WALLET["_Positions"][ref_pos]["isin"],
                                                       "ticker": self.WALLET["_Positions"][ref_pos]["ticker"],
                                                       "name": self.WALLET["_Positions"][ref_pos]["name"],
                                                       "nb": 0,
                                                       "price": 0,})
        self.WALLET["_Positions"][ref_pos]["nb"] += nb
        self.WALLET["_Positions"][ref_pos]["price"] += 0
        self.WALLET["_Transfers"][ref_pos]["nb"] += -nb
        self.WALLET["_Transfers"][ref_pos]["price"] += 0
        if self.WALLET["_Transfers"][ref_pos]["nb"] == 0:
            del(self.WALLET["_Transfers"][ref_pos])
        pl = 0
        return pl
    
    def export_into_dict_of_df(self):
        mydict = {}
        for key in self.WALLET.keys():
            df = pandas.DataFrame.from_dict(self.WALLET[key], orient='index')
            df = df.sort_index(axis = 0)
            mydict[key] = df
        return mydict

