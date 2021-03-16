'''

CURR = Currency()
import datetime
date = datetime.datetime(2020, 12, 3, 0).replace(tzinfo=datetime.timezone.utc)
fx_rate = CURR.get_value("JPY", date)
fx_rate

'''



import os
import pandas
import datetime
import requests
import io
from scipy.interpolate import interp1d


#%%
def test_file(file):
    if os.path.exists(file):
        if os.path.isfile(file):
            return True
        else:
            assert(False)
    else:
        return False

def read_file(file):
    assert(isinstance(file, str))
    with open(file, "rb") as f:
        bytes_data = f.read()
    return bytes_data

def write_file(file, bytes_data):
    assert(isinstance(file, str))
    with open(file, 'wb') as f:
        f.write(bytes_data)
    return

def get_url(url):
    http_answer = requests.get(url, timeout=(5, 10))
    assert(http_answer.status_code == 200)
    bytes_data = http_answer.content
    return bytes_data


#%%
class Currency:
    def __init__(self):
        self.interpolators = {}
    
    def dl_data(self, currcurr):
        t1 = 953078400
        t2 = 161256960000
        url = f'https://query1.finance.yahoo.com/v7/finance/download/{currcurr}=X?period1={t1}&period2={t2}&interval=1d&events=history&includeAdjustedClose=true'
        bytes_data = get_url(url)
        return bytes_data
    
    def get_curr_history(self, currcurr, update):
        file = f'db/{currcurr}=X.csv'
        if test_file(file) is False or update is True:
            print(f'DB : Downloading {file}')
            bytes_data = self.dl_data(currcurr)
            write_file(file, bytes_data)
        bytes_data = read_file(file)
        table_quote = pandas.read_csv(io.BytesIO(bytes_data))
        
        last_date = table_quote.at[len(table_quote) - 1, "Date"]
        last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        nb_days = (now_utc - last_date).total_seconds() / 3600 / 24
        if nb_days > 10:
            table_quote = self.get_curr_history(currcurr, True)
        return table_quote
    
    def get_interpolator(self, currcurr):
        if currcurr not in self.interpolators:
            table_quote = self.get_curr_history(currcurr, False)
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
            f2 = interp1d(table_quote['Date'], table_quote['Value'], kind='nearest', bounds_error=True)
            self.interpolators[currcurr] = f2
        return self.interpolators[currcurr]
    
    def get_value(self, curr, date):
        BASE_CURR = os.getenv("BASE_CURR", "EUR")
        if curr == BASE_CURR:
            return 1.00
        f2 = self.get_interpolator(f'{BASE_CURR}{curr}')
        y = float(f2(date.replace(tzinfo=datetime.timezone.utc).timestamp()))
        return y

