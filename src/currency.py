'''

===============================================================================
TODO :
===============================================================================
- Improve date interp
-
-


CURR = Currency()
import datetime
date = datetime.datetime(2020, 12, 3, 2).replace(tzinfo=datetime.timezone.utc)
date = datetime.datetime(2021, 3, 18, 1).replace(tzinfo=datetime.timezone.utc)
fx_rate = CURR.get_value("JPY", date)
fx_rate

'''


import os
import pandas
import datetime
import io

from src.lib_os import get_url
from src.lib_os import test_file
from src.lib_os import read_file
from src.lib_os import write_file
from src.lib_os import get_file_age
from scipy.interpolate import interp1d



#%%
class Currency:
    def __init__(self):
        self.interpolators = {}
        self.BASE_CURR = os.getenv("BASE_CURR", "EUR")
    
    def dl_file(self, file, currcurr):
        t1 = 953078400
        t2 = 161256960000
        url = f'https://query1.finance.yahoo.com/v7/finance/download/{currcurr}=X?period1={t1}&period2={t2}&interval=1d&events=history&includeAdjustedClose=true'
        print(f'DB : Downloading {file}')
        bytes_data = get_url(url)
        write_file(file, bytes_data)
        return
    
    def force_update(self, file, currcurr):
        file_age = get_file_age(file)
        if file_age > 3600 * 24:  # To avoid spam
            self.dl_file(file, currcurr)
    
    def import_file(self, file, currcurr, force_update):
        if force_update is True:
            self.force_update(file, currcurr)
        if test_file(file) is False:
            self.dl_file(file, currcurr)
        bytes_data = read_file(file)
        table_quote = pandas.read_csv(io.BytesIO(bytes_data))
        return table_quote
    
    def get_curr_history(self, currcurr, force_update):
        file = f'db/{currcurr}=X.csv'
        table_quote = self.import_file(file, currcurr, force_update)
        return table_quote
    
    def get_interpolator(self, currcurr, force_update):
        if currcurr not in self.interpolators or force_update is True:
            table_quote = self.get_curr_history(currcurr, force_update)
            last_quotation = table_quote.at[len(table_quote) - 1, "Date"]
            last_quotation = datetime.datetime.strptime(last_quotation, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc)
            table_quote["Value"] = (table_quote["Low"] + table_quote["High"]) / 2
            # table_quote["Value"] = (table_quote["Open"] + table_quote["Close"]) / 2
            del(table_quote["Open"])
            del(table_quote["Close"])
            del(table_quote["Adj Close"])
            del(table_quote["Volume"])
            del(table_quote["High"])
            del(table_quote["Low"])
            table_quote['Date'] =  pandas.to_datetime(table_quote['Date'], format='%Y/%m/%d')
            table_quote = table_quote.interpolate(method='linear')  # Remove NaNs
            for iii in table_quote.index:
                table_quote.at[iii, 'Date'] = table_quote.at[iii, 'Date'].replace(tzinfo=datetime.timezone.utc).timestamp() + 12 * 3600
            del(iii)
            f2 = interp1d(table_quote['Date'], table_quote['Value'], kind='linear', bounds_error=True)
            self.interpolators[currcurr] = f2
            self.interpolators[f'{currcurr}_date'] = last_quotation
            self.interpolators[f'{currcurr}_uptodate'] = True
        return self.interpolators[currcurr], self.interpolators[f'{currcurr}_date'], self.interpolators[f'{currcurr}_uptodate']
    
    def get_value(self, curr, date):
        assert(type(curr) is str and len(curr) == 3)
        if curr == self.BASE_CURR:
            return 1.00
        date = datetime.datetime.fromisoformat(date)
        f2, last_quotation, uptodate = self.get_interpolator(f'{self.BASE_CURR}{curr}', False)
        if date > last_quotation and uptodate is False:
            f2, last_quotation, uptodate = self.get_interpolator(f'{self.BASE_CURR}{curr}', True)
            assert(uptodate)
        if date > last_quotation:
            if (date - last_quotation).total_seconds() > 24 * 3600:
                print(f'WARNING : extrapolation : {curr} : {date} > {last_quotation}')
            date = last_quotation
        date2 = date.timestamp()
        y = f2(date2)
        return float(y)

