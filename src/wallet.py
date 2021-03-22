'''

===============================================================================
TODO :
===============================================================================
- Improve transfers
-
-
-

'''



import datetime
import numpy
import pandas

from src.lib_os import get_utc


class Wallet:
    def __init__(self, BASE_CURR, ACCURACY):
        self.date_wallet = ""
        self.BASE_CURR = BASE_CURR
        self.ACCURACY = ACCURACY
        self.WALLET = {
                       "_Misc": {},
                       "_Positions": {f'*_{BASE_CURR}': {"isin": "-", "ticker": "-", "name": BASE_CURR, "nb": 0, "price": 0, "last_quotation": None, "unrealized_pl": 0,}},
                       "_Transfers": {f'*_{BASE_CURR}': {"isin": "-", "ticker": "-", "name": BASE_CURR, "nb": 0, "price": 0,}},
                       "_Realized_PL": {},
                      }
        self.add_misc("Base currency", BASE_CURR)
        self.add_misc("UTC now", get_utc().isoformat())
    
    def add_misc(self, ref, value):
        self.WALLET["_Misc"][ref] = {"text": value,}
        return
    
    def _check_date(self, date):
        assert(self.date_wallet <= date)
        self.date_wallet = date
        return
    
    def transaction_stock(self, date, ref_pos, nb, cash, fx_rate, isin, ticker, name):
        self._check_date(date)
        pl = self._transaction(date, ref_pos, nb, cash, fx_rate, isin, ticker, name)
        return round(pl, self.ACCURACY)
    
    def transaction_forex(self, date, curr, nb, cash):
        self._check_date(date)
        ref_pos = f'*_{curr}'
        fx_rate = 1.0
        name = curr
        pl = self._transaction(date, ref_pos, nb, cash, fx_rate, "-", "-", name)
        return round(pl, self.ACCURACY)
    
    def _transaction(self, date, ref_pos, nb, cash, fx_rate, isin, ticker, name):
        curr = list(cash.keys())
        assert(len(curr) == 1)
        curr = curr[0]
        amount_curr = cash[curr]
        amount_curr = round(amount_curr, self.ACCURACY)
        amount_base_curr = amount_curr / fx_rate
        amount_base_curr = round(amount_base_curr, self.ACCURACY)
        if curr != self.BASE_CURR:
            pl2 = self.transaction_forex(date=date,
                                         curr=curr,
                                         nb=amount_curr,
                                         cash={self.BASE_CURR:-amount_base_curr})
        else:
            pl2 = 0
        if numpy.sign(nb) * numpy.sign(amount_base_curr) == 1:
            print(f'WARNING : suspicious transaction : {nb} {amount_base_curr}')
        nb = round(nb, self.ACCURACY)
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["nb"] += amount_base_curr
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["price"] += -amount_base_curr
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["nb"] = round(self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["nb"], self.ACCURACY)
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["price"] = round(self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["price"], self.ACCURACY)
        self.WALLET["_Positions"].setdefault(ref_pos, {"isin": isin, "ticker": ticker, "name": name, "nb": 0, "price": 0, "last_quotation": None, "unrealized_pl": None,})
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
            amount_1 = round(amount_base_curr * ratio_1, self.ACCURACY)
            amount_2 = amount_base_curr - amount_1
            pl_1 = self._decrease_position(date, ref_pos, nb_1, amount_1, isin, ticker, name)
            pl_2 = self._increase_position(date, ref_pos, nb_2, amount_2, isin, ticker, name)
            pl = pl_1 + pl_2
        if self.WALLET["_Positions"][ref_pos]["nb"] == 0:
            if abs(self.WALLET["_Positions"][ref_pos]["price"]) > 0:
                print(f'WARNING : accur : {self.WALLET["_Positions"][ref_pos]["price"]}')
            del(self.WALLET["_Positions"][ref_pos])
        else:
            if numpy.sign(self.WALLET["_Positions"][ref_pos]["nb"]) * numpy.sign(self.WALLET["_Positions"][ref_pos]["price"]) == 1:
                print(f'WARNING : suspicious position : {ref_pos} : {self.WALLET["_Positions"][ref_pos]}')
        return pl + pl2
    
    def _increase_position(self, date, ref_pos, nb, amount_base_curr, isin, ticker, name):
        self.WALLET["_Positions"][ref_pos]["nb"] += nb
        self.WALLET["_Positions"][ref_pos]["price"] += amount_base_curr
        self.WALLET["_Positions"][ref_pos]["nb"] = round(self.WALLET["_Positions"][ref_pos]["nb"], self.ACCURACY)
        self.WALLET["_Positions"][ref_pos]["price"] = round(self.WALLET["_Positions"][ref_pos]["price"], self.ACCURACY)
        pl = 0
        return pl
    
    def _decrease_position(self, date, ref_pos, nb, amount_base_curr, isin, ticker, name):
        amount_0 = round(self.WALLET["_Positions"][ref_pos]["price"] * nb / self.WALLET["_Positions"][ref_pos]["nb"], self.ACCURACY)
        pl = amount_base_curr - amount_0
        self.WALLET["_Positions"][ref_pos]["nb"] += nb
        self.WALLET["_Positions"][ref_pos]["price"] += amount_0
        self.WALLET["_Positions"][ref_pos]["nb"] = round(self.WALLET["_Positions"][ref_pos]["nb"], self.ACCURACY)
        self.WALLET["_Positions"][ref_pos]["price"] = round(self.WALLET["_Positions"][ref_pos]["price"], self.ACCURACY)
        self._register_pl(date, ref_pos, pl, isin, ticker, name)
        return pl
    
    def rename_position(self, date, ref_pos_1, ref_pos_2, name_1, name_2):
        self._check_date(date)
        self.WALLET["_Positions"][ref_pos_2] = self.WALLET["_Positions"].pop(ref_pos_1)
        self.WALLET["_Positions"][ref_pos_2]["name"] = name_2
        return
    
    def split_position(self, date, ref_pos, nb_delta, coeff_split):
        self._check_date(date)
        if not nb_delta is None:
            self.WALLET["_Positions"][ref_pos]["nb"] = self.WALLET["_Positions"][ref_pos]["nb"] + nb_delta
        elif not coeff_split is None:
            self.WALLET["_Positions"][ref_pos]["nb"] = self.WALLET["_Positions"][ref_pos]["nb"] * coeff_split
        else:
            assert(False)
        self.WALLET["_Positions"][ref_pos]["nb"] = round(self.WALLET["_Positions"][ref_pos]["nb"], self.ACCURACY)
        return
    
    def add_cash(self, date, ref_pl, cash, fx_rate, isin, ticker, name):
        self._check_date(date)
        curr = list(cash.keys())
        assert(len(curr) == 1)
        curr = curr[0]
        amount_curr = cash[curr]
        amount_curr = round(amount_curr, self.ACCURACY)
        amount_base_curr = round(amount_curr / fx_rate, self.ACCURACY)
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["nb"] += amount_base_curr
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["price"] += -amount_base_curr
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["nb"] = round(self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["nb"], self.ACCURACY)
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["price"] = round(self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["price"], self.ACCURACY)
        self._register_pl(date, ref_pl, amount_base_curr, isin, ticker, name)
        if curr != self.BASE_CURR:
            pl2 = self.transaction_forex(date=date,
                                         curr=curr,
                                         nb=amount_curr,
                                         cash={self.BASE_CURR:-amount_base_curr})
        else:
            pl2 = 0
        pl = amount_base_curr + pl2
        return round(pl, self.ACCURACY)
    
    def _register_pl(self, date, ref_pl, amount_base_curr, isin, ticker, name):
        year_utc = datetime.datetime.fromisoformat(date).astimezone(datetime.timezone.utc).year
        if "_GLOBAL" not in self.WALLET["_Realized_PL"]:
            utc_now = get_utc()
            self.year_min = year_utc
            self.year_max = utc_now.year
            self.WALLET["_Realized_PL"]["_GLOBAL"] = {"isin": "-", "ticker": "-", "name": "-", "TOTAL": 0,}
            for year in range(self.year_min, self.year_max + 1):
                self.WALLET["_Realized_PL"]["_GLOBAL"][str(year)] = 0
        if ref_pl not in self.WALLET["_Realized_PL"]:
            self.WALLET["_Realized_PL"][ref_pl] = {"isin": [], "ticker": [], "name": [], "TOTAL": 0}
            for year in range(self.year_min, self.year_max + 1):
                self.WALLET["_Realized_PL"][ref_pl][str(year)] = 0
        year_utc = str(year_utc)
        self.WALLET["_Realized_PL"][ref_pl]["TOTAL"] += amount_base_curr
        self.WALLET["_Realized_PL"][ref_pl]["isin"] += [isin,]
        self.WALLET["_Realized_PL"][ref_pl]["ticker"] += [ticker,]
        self.WALLET["_Realized_PL"][ref_pl]["name"] += [name,]
        self.WALLET["_Realized_PL"][ref_pl]["isin"] = list(set(self.WALLET["_Realized_PL"][ref_pl]["isin"]))
        self.WALLET["_Realized_PL"][ref_pl]["ticker"] = list(set(self.WALLET["_Realized_PL"][ref_pl]["ticker"]))
        self.WALLET["_Realized_PL"][ref_pl]["name"] = list(set(self.WALLET["_Realized_PL"][ref_pl]["name"]))
        self.WALLET["_Realized_PL"][ref_pl][year_utc] += amount_base_curr
        self.WALLET["_Realized_PL"]["_GLOBAL"]["TOTAL"] += amount_base_curr
        self.WALLET["_Realized_PL"]["_GLOBAL"][year_utc] += amount_base_curr
        self.WALLET["_Realized_PL"][ref_pl]["TOTAL"] = round(self.WALLET["_Realized_PL"][ref_pl]["TOTAL"], self.ACCURACY)
        self.WALLET["_Realized_PL"][ref_pl][year_utc] = round(self.WALLET["_Realized_PL"][ref_pl][year_utc], self.ACCURACY)
        self.WALLET["_Realized_PL"]["_GLOBAL"]["TOTAL"] = round(self.WALLET["_Realized_PL"]["_GLOBAL"]["TOTAL"], self.ACCURACY)
        self.WALLET["_Realized_PL"]["_GLOBAL"][year_utc] = round(self.WALLET["_Realized_PL"]["_GLOBAL"][year_utc], self.ACCURACY)
        return
    
    def transfer_cash(self, date, cash):
        self._check_date(date)
        curr = list(cash.keys())
        assert(len(curr) == 1)
        curr = curr[0]
        amount = cash[curr]
        amount = round(amount, self.ACCURACY)
        if curr == self.BASE_CURR:
            pl = self._transfer_base_curr(amount)
        else:
            pl = self._transfer_position(f'*_{curr}', amount)
        return round(pl, self.ACCURACY)
    
    def _transfer_base_curr(self, amount_base_curr):
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["nb"] += amount_base_curr
        self.WALLET["_Positions"][f'*_{self.BASE_CURR}']["price"] += -amount_base_curr
        self.WALLET["_Transfers"][f'*_{self.BASE_CURR}']["nb"] += -amount_base_curr
        self.WALLET["_Transfers"][f'*_{self.BASE_CURR}']["price"] += amount_base_curr
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
        self.WALLET["_Positions"][ref_pos]["nb"] = round(self.WALLET["_Positions"][ref_pos]["nb"], self.ACCURACY)
        self.WALLET["_Positions"][ref_pos]["price"] = round(self.WALLET["_Positions"][ref_pos]["price"], self.ACCURACY)
        self.WALLET["_Transfers"][ref_pos]["nb"] = round(self.WALLET["_Transfers"][ref_pos]["nb"], self.ACCURACY)
        self.WALLET["_Transfers"][ref_pos]["price"] = round(self.WALLET["_Transfers"][ref_pos]["price"], self.ACCURACY)
        if self.WALLET["_Transfers"][ref_pos]["nb"] == 0:
            del(self.WALLET["_Transfers"][ref_pos])
        pl = 0
        return pl
    
    def get_positions_list(self):
        return list(self.WALLET["_Positions"].keys())
    
    def set_position_quotation(self, ref_pos, last_quotation_unit):
        assert(ref_pos in self.WALLET["_Positions"])
        self.WALLET["_Positions"][ref_pos]["last_quotation"] = round(last_quotation_unit * self.WALLET["_Positions"][ref_pos]["nb"], self.ACCURACY)
        self.WALLET["_Positions"][ref_pos]["unrealized_pl"] = round(self.WALLET["_Positions"][ref_pos]["last_quotation"] + self.WALLET["_Positions"][ref_pos]["price"], self.ACCURACY)
        return
    
    def export_into_dict_of_df(self):
        mydict = {}
        for key in self.WALLET.keys():
            df = pandas.DataFrame.from_dict(self.WALLET[key], orient='index')
            df = df.sort_index(axis = 0)
            mydict[key] = df
        return mydict
    
    def _get_total_nav(self):
        value = [pos["last_quotation"] for _, pos in self.WALLET["_Positions"].items()]
        if None in value:
            print("ERROR : Cannot compute NAV")
            return None
        value = sum(value)
        value = round(value, self.ACCURACY)
        return value
    
    def _get_realized_nav(self):
        value = [pos["price"] for _, pos in self.WALLET["_Positions"].items()]
        value = -sum(value)
        value = round(value, self.ACCURACY)
        return value
    
    def checksum_realized_nav(self):
        realized_net_assets = round(self.WALLET["_Realized_PL"]["_GLOBAL"]["TOTAL"], self.ACCURACY)
        realized_assets = self._get_realized_nav()
        debt = round(self.WALLET["_Transfers"][f'*_{self.BASE_CURR}']["nb"], self.ACCURACY)
        diff_error = realized_assets + debt - realized_net_assets
        print("================================")
        print("Checksum : Realized NAV")
        print("================================")
        print(f'realized nav = {realized_assets:.2f} {self.BASE_CURR}')
        print(f'realized PL  = {realized_net_assets:.2f} {self.BASE_CURR}')
        if round(diff_error, self.ACCURACY) == 0:
            print("Checksum OK")
        else:
            print("ERROR : Checksum NOK")
            print(f'diff = {diff_error}')
        print("")
        return
    
    def checksum_total_nav(self, nav_ref):
        print("================================")
        print("Checksum : Total NAV")
        print("================================")
        nav_ref = round(nav_ref, self.ACCURACY)
        total_nav = self._get_total_nav()
        if total_nav is None:
            return
        debt = self.WALLET["_Transfers"][f'*_{self.BASE_CURR}']["nb"]
        print(f'total PL  = {(total_nav+debt):.2f} {self.BASE_CURR}')
        print(f'total nav = {total_nav:.2f} {self.BASE_CURR}')
        print(f'    (ref) = {nav_ref:.2f} {self.BASE_CURR}')
        diff = abs((nav_ref / total_nav) - 1)
        if diff == 0:
            print("Checksum OK")
        elif diff < 0.001:
            print(f'diff = {round(diff * 100, 4)} %')
            print("Checksum ~OK")
        else:
            print(f'diff = {round(diff * 100, 4)} %')
            print("ERROR : Checksum NOK")
        print("")
        return
    
    def checksum_positions(self, positions_ref):
        print("================================")
        print("Checksum : Current positions")
        print("================================")
        A = self.WALLET["_Positions"]
        B = positions_ref
        set_A = set(A.keys())
        set_B = set(B.keys())
        if set_A != set_B:
            print("ERROR : Checksum NOK")
            print(f'diff A-B = {set_A.difference(set_B)}')
            print(f'diff B-A = {set_B.difference(set_A)}')
            print("")
            return
        else:
            valid = True
            for key in set_A:
                if A[key]["nb"] != B[key]:
                    print(f'ERROR : Checksum NOK : {key} == {A[key]["nb"]} != {B[key]}')
                    valid = False
            if valid is True:
                print("Checksum OK")
                print("")
        return


