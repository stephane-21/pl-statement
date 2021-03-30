'''

===============================================================================
TODO :
===============================================================================
- Stocks transfers
-
-
-

'''


import csv
import datetime
import zoneinfo  # rely on tzdata
import numpy
import pandas


class BankStatementIB:
    def __init__(self, file_path_csv):
        #%% Import as a list of tables
        TABLE = {}
        with open(file_path_csv, mode='r', encoding='utf-8-sig') as file:
            file_object = csv.reader(file, delimiter=',', lineterminator='\n')
            for iii, row in enumerate(file_object):
                if iii == 0:
                    name = row[0]
                    TABLE[name] = []  # New block
                    TABLE[name].append([])  # New table
                    TABLE[name][-1].append(row[2:])
                elif row[0] == name and row[1] in ["Header",]:
                    TABLE[name].append([])  # New table
                    TABLE[name][-1].append(row[2:])
                elif row[0] == name and row[1] in ["Data",]:
                    TABLE[name][-1].append(row[2:])
                elif row[0] == name and row[1] in ["Total", "SubTotal",]:
                    pass
                elif row[0] != name and row[1] in ["Header",]:
                    name = row[0]
                    TABLE[name] = []  # New block
                    TABLE[name].append([])  # New table
                    TABLE[name][-1].append(row[2:])
                else:
                    print(f'ERROR : {row}')
                    assert(False)
        
        ref_list = ["Account Information",
                    'Statement',
                    'Change in NAV',
                    'Mark-to-Market Performance Summary',
                    'Realized & Unrealized Performance Summary',
                    'Month & Year to Date Performance Summary',
                    'Cash Report',
                    'Corporate Actions',
                    'Transfers',
                    'Deposits & Withdrawals',
                    'Open Positions',
                    'Dividends',
                    'Withholding Tax',
                    'Change in Dividend Accruals',
                    'Financial Instrument Information',
                    'Codes',
                    'Net Asset Value',
                    'Trades',
                    'Forex Balances',
                    'Location of Customer Assets, Positions and Money',
                    'Notes/Legal Notes']
        for key in TABLE.keys():
            if key not in ref_list:
                print(f'WARNING : New tab : {key}')
        
        #%% Convert to dict of tables
        for key in list(TABLE.keys()):
            if len(TABLE[key]) == 1:
                TABLE[key] = TABLE[key][0]
            else:
                for iii in reversed(range(len(TABLE[key]))):
                    table = TABLE[key][iii]
                    if iii == 0:
                        TABLE[key] = table
                    else:
                        assert(f'{key}_{iii+1:03}' not in TABLE.keys())
                        TABLE[f'{key}_{iii+1:03}'] = table
                del(iii, table)
        del(key)
        for key in list(TABLE.keys()):
            if "/" in key:
                TABLE[key.replace("/", "|")] = TABLE.pop(key)
        del(key)
        
        #%% Convert to dict of dfs and dicts
        for key, table in TABLE.items():
            if table[0] == ['Field Name', 'Field Value']:
                my_dict = {}
                for row in table[1:]:
                    my_dict[row[0]] = row[1]
                del(row)
                TABLE[key] = my_dict
                del(my_dict)
            else:
                TABLE[key] = pandas.DataFrame(table[1:])
                nb_col = len(TABLE[key].columns)
                col_names = table[0]
                if nb_col > len(col_names):
                    col_names = col_names + list(range(len(col_names), nb_col))
                elif nb_col < len(col_names):
                    col_names = col_names[:nb_col]
                TABLE[key].columns = col_names
        del(key, table)
        
        #%%
        self.TABLE = TABLE
        self._some_checks()
        self._build_current_quotation_table()
        return
    
    
    def _some_checks(self):
        assert(self.TABLE["Statement"]["BrokerName"] == "Interactive Brokers")
        if self.TABLE["Statement"]["Title"] == "Activity Summary":
            raise NotImplementedError ("Only for individual activity statements")
        assert(self.TABLE["Statement"]["Title"] == "Activity Statement")
        
        assert("Trade execution times are displayed in Eastern Time." in list(self.TABLE["Notes|Legal Notes"]["Note"]))
        
        table = self.TABLE["Cash Report"]
        for row in table.index:
            if table.at[row, "Currency Summary"] == "Starting Cash":
                assert(str2num(table.at[row, "Total"]) == 0)
        
        assert(str2num(self.TABLE["Change in NAV"]["Starting Value"]) == 0)
        
        return
    
    
    def get_account_nb(self):
        return self.TABLE["Account Information"]["Account"]
    
    
    def base_curr(self):
        return self.TABLE["Account Information"]["Base Currency"]
    
    
    def format_date_as_us_eastern(self, date):
        # Eastern Time == -0500 -0400
        date = datetime.datetime.strptime(date, '%Y-%m-%d, %H:%M:%S').replace(tzinfo=zoneinfo.ZoneInfo("US/Eastern"))\
                                                                     .astimezone(datetime.timezone.utc).isoformat()
        return date
    
    
    def get_bank_stat_date(self):
        date = self.TABLE["Statement"]["WhenGenerated"]
        if date.endswith(" EST"):
            date = date.replace(" EST", "")  # The timezone EST is ambiguous
        elif date.endswith(" EDT"):
            date = date.replace(" EDT", "")  # The timezone EDT is ambiguous
        else:
            print(date)
            assert(False)
        date = self.format_date_as_us_eastern(date)
        return date
    
    
    def get_bank_stat_period(self):
        date = self.TABLE["Statement"]["Period"]
        return date
    
    
    def get_all_operations(self):
        TRANSACTIONS = []
        TRANSACTIONS += self._get_stock_transactions()
        TRANSACTIONS += self._get_forex_transactions()
        TRANSACTIONS += self._get_corp_operations()
        TRANSACTIONS += self._get_cash_transfers()
        TRANSACTIONS += self._get_dividends()
        TRANSACTIONS += self._get_fees_taxrev()
        return TRANSACTIONS
    
    
    def get_all_positions(self):
        POSITIONS = []
        POSITIONS += self._get_stock_positions()
        POSITIONS += self._get_cash_positions()
        return POSITIONS
    
    
    def _get_stock_transactions(self):
        OPERATIONS = []
        if "Trades" in self.TABLE:
            table = self.TABLE["Trades"]
            for row in table.index:
                operation = {}
                assert(table.at[row, "DataDiscriminator"] == "Order")
                assert(table.at[row, "Asset Category"] == "Stocks")
                operation["type"] = "Stock"
                operation["date"] = table.at[row, "Date/Time"]
                operation["date"] = self.format_date_as_us_eastern(operation["date"])
                operation["ticker"] = table.at[row, "Symbol"]
                operation["name"] = self._get_company_info(operation["ticker"])["name"]
                operation["isin"] = self._get_company_info(operation["ticker"])["isin"]
                operation["fin_place"] = self._get_company_info(operation["ticker"])["fin_place"]
                operation["nb"] = str2num(table.at[row, "Quantity"])
                operation["cash"] = {table.at[row, "Currency"]: str2num(table.at[row, "Proceeds"]) + str2num(table.at[row, "Comm/Fee"])}
                operation["fees_broker"] = {table.at[row, "Currency"]: str2num(table.at[row, "Comm/Fee"])}
                operation["fees_broker_ratio"] = str2num(table.at[row, "Comm/Fee"]) / str2num(table.at[row, "Proceeds"])
                OPERATIONS.append(operation)
        return OPERATIONS
    
    
    def _get_forex_transactions(self):
        OPERATIONS = []
        BASE_CURR = self.base_curr()
        if "Trades_002" in self.TABLE:
            table = self.TABLE["Trades_002"]
            for row in table.index:
                operation = {}
                assert(table.at[row, "DataDiscriminator"] == "Order")
                assert(table.at[row, "Asset Category"] == "Forex")
                operation["type"] = "Forex"
                operation["date"] = table.at[row, "Date/Time"]
                operation["date"] = self.format_date_as_us_eastern(operation["date"])
                curr_1 = table.at[row, "Symbol"].split(".")[0]
                curr_2 = table.at[row, "Symbol"].split(".")[1]
                assert(curr_1 == BASE_CURR)
                assert(curr_2 == table.at[row, "Currency"])
                operation["name"] = table.at[row, "Currency"]
                operation["isin"] = None
                operation["ticker"] = None
                operation["cash"] = {BASE_CURR: str2num(table.at[row, "Quantity"]) + str2num(table.at[row, f'Comm in {BASE_CURR}']),
                                       curr_2: str2num(table.at[row, "Proceeds"])}
                operation["fees_broker"] = {BASE_CURR: str2num(table.at[row, f'Comm in {BASE_CURR}'])}
                operation["fees_broker_ratio"] = str2num(table.at[row, f'Comm in {BASE_CURR}']) / str2num(table.at[row, "Quantity"])
                OPERATIONS.append(operation)
        return OPERATIONS
    
    
    def _get_corp_operations(self):
        OPERATIONS = []
        if "Corporate Actions" in self.TABLE:
            table = self.TABLE["Corporate Actions"]
            for row in table.index:
                if table.at[row, "Asset Category"] == "Stocks":
                    operation = {}
                    operation["type"] = "Split"
                    operation["date"] = table.at[row, "Date/Time"]
                    operation["date"] = self.format_date_as_us_eastern(operation["date"])
                    operation["cash"] = {table.at[row, "Currency"]: 0}
                    assert(str2num(table.at[row, "Proceeds"]) == 0)
                    operation["nb"] = str2num(table.at[row, "Quantity"])
                    mytext = table.at[row, "Description"]
                    operation["ticker"] = mytext.split("(")[0]
                    operation["isin"] = mytext.split("(")[1].split(")")[0]
                    operation["name"] = mytext.split(f'{operation["ticker"]}, ')[1].split(f', {operation["isin"]}')[0]
                    operation["split_coeff"] = str2num(mytext.split(") Split ")[1].split(" for ")[0])\
                                             / str2num(mytext.split(" for ")[1].split(f' ({operation["ticker"]}')[0])
                    OPERATIONS.append(operation)
                else:
                    assert(table.at[row, "Asset Category"].startswith("Total"))
        return OPERATIONS
    
    
    def _get_cash_transfers(self):
        OPERATIONS = []
        table = self.TABLE["Deposits & Withdrawals"]
        for row in table.index:
            if table.at[row, "Currency"].startswith("Total"):
                pass
            else:
                operation = {}
                if table.at[row, "Description"] == "Electronic Fund Transfer":
                    operation["type"] = "CashTransferExt"
                elif "Adjustment: Cash Receipt/Disbursement/Transfer (Transfer to" in table.at[row, "Description"]:
                    operation["type"] = "CashTransferInt"
                else:
                    print(f'ERROR : {table.at[row, "Description"]}')
                    assert(False)
                operation["date"] = table.at[row, "Settle Date"]
                operation["date"] = datetime.datetime.strptime(operation["date"], '%Y-%m-%d')\
                                      .replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc).isoformat()
                operation["cash"] = {table.at[row, "Currency"]: str2num(table.at[row, "Amount"])}
                OPERATIONS.append(operation)
        return OPERATIONS
    
    
    def _get_dividends(self):
        BASE_CURR = self.base_curr()
        OPERATIONS = []
        if "Dividends" in self.TABLE:
            table = self.TABLE["Dividends"]
            for row in table.index:
                if table.at[row, "Currency"].startswith("Total"):
                    pass
                else:
                    operation = {}
                    operation["type"] = "Dividend"
                    operation["date"] = table.at[row, "Date"]
                    operation["date"] = datetime.datetime.strptime(operation["date"], '%Y-%m-%d')\
                                          .replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc).isoformat()
                    operation["cash"] = {table.at[row, "Currency"]: str2num(table.at[row, "Amount"])}
                    mytext = table.at[row, "Description"]
                    assert("Cash Dividend" in mytext)
                    assert(mytext.endswith(" (Ordinary Dividend)"))
                    operation["ticker"] = mytext.split("(")[0]
                    operation["isin"] = mytext.split("(")[1].split(")")[0]
                    operation["name"] = self._get_company_info(operation["ticker"])["name"]
                    operation["fees_broker"] = {BASE_CURR: 0}
                    operation["fees_broker_ratio"] = 0
                    operation["fees_taxrev"] = None
                    operation["fees_taxrev_ratio"] = None
                    OPERATIONS.append(operation)
        return OPERATIONS
    
    
    def _get_fees_taxrev(self):
        OPERATIONS = []
        if "Withholding Tax" in self.TABLE:
            table = self.TABLE["Withholding Tax"]
            for row in table.index:
                if table.at[row, "Currency"].startswith("Total"):
                    pass
                else:
                    operation = {}
                    operation["type"] = "Dividend_Tax"
                    operation["date"] = table.at[row, "Date"]
                    operation["date"] = datetime.datetime.strptime(operation["date"], '%Y-%m-%d')\
                                          .replace(tzinfo=datetime.timezone.utc).astimezone(datetime.timezone.utc).isoformat()
                    operation["cash"] = {table.at[row, "Currency"]: str2num(table.at[row, "Amount"])}
                    mytext = table.at[row, "Description"]
                    assert("Cash Dividend" in mytext)
                    assert(mytext.endswith(" Tax"))
                    operation["ticker"] = mytext.split("(")[0]
                    operation["isin"] = mytext.split("(")[1].split(")")[0]
                    operation["name"] = self._get_company_info(operation["ticker"])["name"]
                    operation["country_taxrev"] = mytext.split(" per Share - ")[1]
                    OPERATIONS.append(operation)
        return OPERATIONS
    
    
    def _get_stock_positions(self):
        POSITIONS = []
        if "Open Positions" in self.TABLE:
            table = self.TABLE["Open Positions"]
            for row in table.index:
                assert(table.at[row, "DataDiscriminator"] == "Summary")
                assert(table.at[row, "Asset Category"] == "Stocks")
                position = {}
                position["ticker"] = table.at[row, "Symbol"]
                position["nb"] = str2num(table.at[row, "Quantity"])
                POSITIONS.append(position)
        return POSITIONS
    
    
    def _get_cash_positions(self):
        BASE_CURR = self.base_curr()
        POSITIONS = []
        table = self.TABLE["Cash Report"]
        for row in table.index:
            if table.at[row, "Currency Summary"] == "Ending Cash" and table.at[row, "Currency"] != "Base Currency Summary":
                curr = table.at[row, "Currency"]
                position = {}
                position["ticker"] = f'*_{curr}'
                position["nb"] = str2num(table.at[row, "Total"])
                if "Forex Balances" in self.TABLE:
                    table2 = self.TABLE["Forex Balances"]
                    for row in table2.index:
                        if table2.at[row, "Asset Category"] == "Forex":
                            assert(table2.at[row, "Currency"] == BASE_CURR)
                            if table2.at[row, "Description"] == curr:
                                assert(position["nb"] == str2num(table2.at[row, "Quantity"]))
                        else:
                            assert(table2.at[row, "Asset Category"].startswith("Total"))
                POSITIONS.append(position)
        return POSITIONS
    
    
    def _get_company_info(self, ticker):
        table = self.TABLE["Financial Instrument Information"]
        name = None
        isin = None
        fin_place = None
        for row in table.index:
            if table.at[row, "Symbol"] == ticker:
                assert(table.at[row, "Asset Category"] == "Stocks")
                name = table.at[row, "Description"]
                isin = table.at[row, "Security ID"]
                fin_place = table.at[row, "Listing Exch"]
                break
        return {"name": name,
                "isin": isin,
                "fin_place": fin_place,}
    
    
    def get_nav(self):
        table = self.TABLE["Net Asset Value"]
        return str2num(table.at[len(table) - 1, "Current Total"])
    
    
    def _build_current_quotation_table(self):
        BASE_CURR = self.base_curr()
        my_dict = {}
        table = self.TABLE["Mark-to-Market Performance Summary"]
        for row in table.index:
            if table.at[row, "Asset Category"] == "Stocks":
                pass  # Currency not indicated
            elif table.at[row, "Asset Category"] == "Forex":
                curr = table.at[row, "Symbol"]
                ticker = f'*_{curr}'
                quotation = str2num(table.at[row, "Current Price"])
                my_dict[ticker] = {BASE_CURR: quotation}
                if "Forex Balances" in self.TABLE:
                    table2 = self.TABLE["Forex Balances"]
                    for row in table2.index:
                        if table2.at[row, "Asset Category"] == "Forex":
                            assert(table2.at[row, "Currency"] == BASE_CURR)
                            if table2.at[row, "Description"] == curr:
                                assert(quotation == str2num(table2.at[row, "Close Price"]))
                        else:
                            assert(table2.at[row, "Asset Category"].startswith("Total"))
            else:
                assert(table.at[row, "Asset Category"].startswith("Total"))
        if "Open Positions" in self.TABLE:
            table = self.TABLE["Open Positions"]
            for row in table.index:
                if table.at[row, "Asset Category"] == "Stocks":
                    ticker = table.at[row, "Symbol"]
                    my_dict[ticker] = {table.at[row, "Currency"]: str2num(table.at[row, "Close Price"])}
                else:
                    pass
        self.TABLE_PRICE = my_dict
        return
    
    
    def get_last_quotation_unit(self, ticker):
        if ticker in self.TABLE_PRICE:
            return self.TABLE_PRICE[ticker]
        else:
            return None
    
    
    def export_raw(self, file_path):
        writer = pandas.ExcelWriter(file_path)
        iii = 1
        for key, table in self.TABLE.items():
            tab_name = f'{iii:03}_{key[0:27]}'  # max 31 char
            try:
                if type(table) is dict:
                    pandas.DataFrame.from_dict(table, orient='index').to_excel(writer, tab_name, header=False, index=True)
                elif type(table) is pandas.core.frame.DataFrame:
                    table.to_excel(writer, tab_name, header=True, index=False)
                else:
                    print(f'WARNING : Unknown content : {key} : {type(table)}')
            except ValueError:
                print(f'WARNING : Cannot export tab : {key}')
            iii = iii + 1
        del(key, table)
        writer.save()
        del(writer)


def str2num(mystring):
    myfloat = float(mystring.replace(",", ""))
    return myfloat


def sort_operations(OPERATIONS):
    list_dates = [operation["date"] for operation in OPERATIONS]
    sort_index = numpy.argsort(list_dates)
    OPERATIONS = [OPERATIONS[iii] for iii in sort_index]
    return OPERATIONS


def fusion_positions(POSITIONS):
    POSITIONS_2 = {}
    for pos in POSITIONS:
        ticker = pos["ticker"]
        if ticker not in POSITIONS_2:
            POSITIONS_2[ticker] = pos
        else:
            POSITIONS_2[ticker]["nb"] += pos["nb"]
    POSITIONS_2 = {key: value["nb"] for key, value in POSITIONS_2.items()}
    return POSITIONS_2

