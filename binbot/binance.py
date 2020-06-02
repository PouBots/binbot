import decimal
import hmac
import time
import pandas as pd
import hashlib
from decimal import Decimal
from reqs import *

"""
Here a class is defined based on Binance API commands,
to facilitate manipulation in a client portfolio.
Args:
    full paths to a text file containing api access keys
Returns:
    data
"""



class Binance:
    
    request_delay  = 150   # tricking binance to get faster requests
    mxlimit        = 1500  # maximum possible number of data to retrive
    ORDER_STATUS_NEW = 'NEW'
    ORDER_STATUS_PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    ORDER_STATUS_FILLED = 'FILLED'
    ORDER_STATUS_CANCELED = 'CANCELED'
    ORDER_STATUS_PENDING_CANCEL = 'PENDING_CANCEL'
    ORDER_STATUS_REJECTED = 'REJECTED'
    ORDER_STATUS_EXPIRED = 'EXPIRED'

    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'

    ORDER_TYPE_LIMIT = 'LIMIT'
    ORDER_TYPE_MARKET = 'MARKET'
    ORDER_TYPE_STOP_LOSS = 'STOP_LOSS'
    ORDER_TYPE_STOP_LOSS_LIMIT = 'STOP_LOSS_LIMIT'
    ORDER_TYPE_TAKE_PROFIT = 'TAKE_PROFIT'
    ORDER_TYPE_TAKE_PROFIT_LIMIT = 'TAKE_PROFIT_LIMIT'
    ORDER_TYPE_LIMIT_MAKER = 'LIMIT_MAKER'

    KLINE_INTERVALS = ['1m', '3m', '5m', '15m', '30m',
                       '1h', '2h', '4h', '6h', '8h', '12h',
                       '1d', '3d', '1w', '1M']
        
    def __init__(self, filename=None):

        self.base = 'https://fapi.binance.com/fapi/v1/' #base api url
        self.reqs = reqs
        self.endpoints = {                            # endpoints representing each api command
            "ping":          'ping',
            "time":          'time',
            "leverage":      'leverage',
            "marginType":    'marginType',
            "order":         'order',
            "testOrder":     'order/test',
            "allOrders":     'allOrders',
            "klines":        'klines',
            "exchangeInfo":  'exchangeInfo',
            "24hrTicker" :   'ticker/24hr',
            "averagePrice" : 'avgPrice',
            "orderBook" :    'depth',
            "account" :      'account'}
        
        self.account_access = False                    #Initializing that there is no access to the api yet

        if filename == None:
            raise Exception("Cannot access api without the keys.")
            return
    
        f = open(filename, "r")
        contents = []
        if f.mode == 'r':
            contents = f.read().split('\n')

        self.binance_keys = dict(api_key = contents[0], secret_key=contents[1])
        self.headers = {"X-MBX-APIKEY": self.binance_keys['api_key']}
        self.account_access = True
    
    def test_connectivity(self):
        url1  = self.base + self.endpoints["ping"]
        url2  = self.base + self.endpoints["time"]
        #data1  = self.reqs._get(url1, headers = self.headers)
        data2  = self.reqs._get(url2)
        return True
        
    def GetAllSymbols(self, quoteAssets:list=None):
        ''' Gets All symbols and classifies them to
            online, offline and trading (currently) '''
        url  = self.base + self.endpoints["exchangeInfo"]
        data = self.reqs._get(url)
        if data.__contains__('code'):
            raise Exception("Failed to read exchange information")

        online_symbols        = []  #symbols that are currently being traded
        trading_symbols       = []  #symbols that this bot can trade based on
                                    #available qoute assets
        offline_symbols       = []  #symbols that are currently on a break
        trading_symbols_data  = []  #whole data of trading symbols

        for pair in data['symbols']:
            if pair['status'] == 'TRADING':
                online_symbols.append(pair['symbol'])
                if quoteAssets != None and pair['quoteAsset'] in quoteAssets:
                    trading_symbols.append(pair['symbol'])
                    trading_symbols_data.append(pair)
            else:
                offline_symbols.append(pair['symbol'])

        symbols = {'online':  online_symbols,
                   'trading': trading_symbols,
                   'offline': offline_symbols,
                   'tdata':   trading_symbols_data}
        
        return symbols

    def GetSymbolKlines(self, symbol:str, interval:str, limit:int=mxlimit, end_time=None):
        ''' 
        Gets trading price data for a given symbol 
        
        Parameters:
        --
            symbol str:        The symbol for which to get the trading data
            interval str:      The interval on which to get the trading data
            limit:             The number of data to get
            end_time:          The time from which to start looking backward for 'limit'
                               Number of data
        '''

        if limit > self.mxlimit:
            return self.GetSymbolKlinesExtra(symbol, interval, limit, end_time)
        
        params = {'symbol': symbol,
                  'interval': interval,
                  'limit': str(limit)}
        
        if end_time != None:
            params.update({'endTime': str(int(end_time))})

        url = self.base + self.endpoints['klines']  # creat the url
        data = self.reqs._get(url, params)               # download data
        df = pd.DataFrame(data)                     # put in dataframe pandas format
        df = df.drop(range(6, 12), axis=1)          # Droping useless columns

        
        col_names = ['time', 'open', 'high',
                     'low', 'close', 'volume']      # rename columns
        df.columns = col_names
        
        for col in col_names:                       # transform values from strings to floats
            df[col] = df[col].astype(float)

        df['date'] = pd.to_datetime(df['time'] * 1000000, infer_datetime_format=True)
                                                    #transfer date and time to human readable
        return df
    
    def GetSymbolKlinesExtra(self, symbol:str, interval:str, limit:int=mxlimit, end_time=None):
        """ it is to call the GetSymbolKlines as many times as we need 
            in order to get all the historical data required (based on
            the limit parameter) and we'll be merging the results into
            one long dataframe. """

        repeat_rounds = 0
        if limit > self.mxlimit:
            repeat_rounds = int(limit/self.mxlimit)
   
        initial_limit = limit % self.mxlimit
        if initial_limit == 0:
            initial_limit = self.mxlimit
        # First, we get the last initial_limit candles, starting at end_time and going
        # backwards (or starting in the present moment, if end_time is False)
        df = self.GetSymbolKlines(symbol, interval, limit=initial_limit, end_time=end_time)
        repeat_rounds = repeat_rounds - 1
        while repeat_rounds > 0:
            # Then, for every other maximum possible candles, we get them, but starting at the beginning
            # of the previously received candles.
            df2 = self.GetSymbolKlines(symbol, interval, limit=self.mxlimit, end_time=df['time'][0])
            df = df2.append(df, ignore_index = True)
            repeat_rounds = repeat_rounds - 1
        
        return df

    def signRequest(self, params:dict):
        ''' Signs the request using keys and sha256 '''

        query_string = '&'.join(["{}={}".format(d, params[d]) for d in params])
        signature    = hmac.new(self.binance_keys['secret_key'].encode('utf-8'),
                             query_string.encode('utf-8'), hashlib.sha256)
        params['signature'] = signature.hexdigest()

    def GetAccountData(self):
        """ Gets Balances & Account Data """

        url = self.base + self.endpoints["account"]
        
        params = { 'recvWindow': 6000,
                   'timestamp': int(round(time.time()*1000)) + self.request_delay }
        self.signRequest(params)
        data = self.reqs._get(url, params, self.headers)
        return data

    def Get24hrTicker(self, symbol:str):
        url    = self.base + self.endpoints['24hrTicker']
        params = {"symbol": symbol}
        return self.reqs._get(url, params)
    
    def setleverage(self, params):

        if not params.keys().__contains__('symbol'):
            raise Exception("Mandatory parameter 'symbol' is missing")
        if not params.keys().__contains__('leverage'):
            params['leverage'] = 10
        if not params.keys().__contains__('marginType'):
            params['marginType'] = 'ISOLATED'
        if not params.keys().__contains__('recvWindow'):
            params['recvWindow'] = 6000
        if not params.keys().__contains__('timestamp'):
            params['timestamp'] = int(round(time.time()*1000)) + self.request_delay
        if params['leverage']<1 or params['leverage']>125:
            raise Exception("leverage is not standard")
                
        url     = self.base + self.endpoints['leverage']
        params1 = params
        params1.pop('marginType')
        
        self.signRequest(params1)
        self.reqs._post(url, params=params1, headers=self.headers)
        
        url     = self.base + self.endpoints['marginType']
        params2 = params
        params2.pop('leverage')
        
        self.signRequest(params2)
        self.reqs._post(url, params=params2, headers=self.headers)
        
    
    @classmethod
    def floatToString(cls, f:float):
        ''' Converts the given float to a string,
            without resorting to the scientific notation '''

        ctx      = decimal.Context()
        ctx.prec = 12
        d1       = ctx.create_decimal(repr(f))
        return format(d1, 'f')

    def PlaceOrder(self, params, test:bool=True):
        '''
        Places an order on Binance
        Parameters
        --
            symbol str:        The symbol for which to get the trading data
            side str:          The side of the order 'BUY' or 'SELL'
            tpe str:           The type, 'LIMIT', 'MARKET', 'STOP_LIMIT', 'STOP_MARKET'
            quantity float:    The amount to be traded
        '''
        if not params.keys().__contains__('symbol'):
            raise Exception("Mandatory parameter 'symbol' is missing")
        if not params.keys().__contains__('recvWindow'):
            params['recvWindow'] = 6000
        if not params.keys().__contains__('timestamp'):
            params['timestamp'] = int(round(time.time()*1000)) + self.request_delay
            

        self.signRequest(params)
        print(params)
        url = ''
        if test: 
            url = self.base + self.endpoints['testOrder']
        else:
            url = self.base + self.endpoints['order']

        data = self.reqs._post(url, params=params, headers=self.headers)
        return data

    def CancelOrder(self, params):
        '''
            Cancels the order on a symbol based on orderId
        '''
        if not params.keys().__contains__('symbol'):
            raise Exception("Mandatory parameter 'symbol' is missing")
        if not params.keys().__contains__('orderId'):
            raise Exception("Mandatory parameter 'orderId' is missing")
        if not params.keys().__contains__('recvWindow'):
            params['recvWindow'] = 6000
        if not params.keys().__contains__('timestamp'):
            params['timestamp'] = int(round(time.time()*1000)) + self.request_delay

        self.signRequest(params)

        url  = self.base + self.endpoints['order']
        data = self.reqs._delete(url, params=params, headers=self.headers)
        return data

    def GetOrderInfo(self, params):
        '''
            Gets info about an order on a symbol based on orderId
        '''
        if not params.keys().__contains__('symbol'):
            raise Exception("Mandatory parameter 'symbol' is missing")
        if not params.keys().__contains__('orderId'):
            raise Exception("Mandatory parameter 'orderId' is missing")
        if not params.keys().__contains__('recvWindow'):
            params['recvWindow'] = 6000
        if not params.keys().__contains__('timestamp'):
            params['timestamp'] = int(round(time.time()*1000)) + self.request_delay

        self.signRequest(params)

        url = self.base + self.endpoints['order']
        data = self.reqs._get(url, params=params, headers=self.headers)
        return data

    def GetAllOrderInfo(self, symbol:str, activeOnly:bool=True):
        '''
            Gets info about all order on a symbol
        '''
        if not params.keys().__contains__('symbol'):
            raise Exception("Mandatory parameter 'symbol' is missing")
        if not params.keys().__contains__('recvWindow'):
            params['recvWindow'] = 6000
        if not params.keys().__contains__('timestamp'):
            params['timestamp'] = int(round(time.time()*1000)) + self.request_delay

        self.signRequest(params)

        url = self.base + self.endpoints['allOrders']
        data = self.reqs._get(url, params=params, headers=self.headers)
        orders = []
        if activeOnly:
            for order in data:
                if order['status'] == 'NEW':
                    orders.append(order)
        else:
            orders = data
        return orders


if __name__ == '__main__':
    symbol   = 'BTCUSDT'
    #symbol   = 'ETHUSDT'
    #client_id = '73a40bae-61c7-11ea-8e67-f40f241d61b4'
    filename = 'C:\\Users\\Pouja\\Desktop\\Assets\\Binance\\api\\keys.txt'
    exchange = Binance(filename)
    print("class creation successful")
    con = exchange.test_connectivity()
    print("connectivity test successful")
    smbl  = exchange.GetAllSymbols(['USDT'])
    print("getting all symbols successful")
    print("-------------------")
