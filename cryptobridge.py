from bitshares import BitShares
from bitshares.notify import Notify
from bitshares.account import Account, AccountUpdate
from bitshares.amount import Amount
from bitshares.asset import Asset
from bitshares.market import Market
from bitshares.price import Price, Order, FilledOrder, UpdateCallOrder
from bitsharesbase.operations import getOperationNameForId
from bitshares.blockchain import Blockchain, BlockchainInstance
from collections import OrderedDict
from datetime import datetime
from sklearn import preprocessing
from sklearn.datasets.samples_generator import make_blobs
from sklearn.cluster import MeanShift
from multiprocessing import Process, Queue
from flask_socketio import SocketIO, emit
from collections.abc import Iterable
import copy
import math
import os.path
import ast
import threading
import multiprocessing
import pandas as pd
import numpy as np
import queue
import re

class Account_Data(threading.Thread):    


    def __init__(self, account):
        super(Account_Data, self).__init__()
        pd.options.display.float_format = '{:,.8f}'.format
        self.order_data=pd
        self.account = Account(account, full=True)
        self.notify = None
        self.markets= [] 
        self.log = []


    def get_order(self):
        return self.order_data


    def set_order(self, date):      
        self.order_data=date


    def update_notify(self):   
        if self.notify:
            # Update the notification instance
            self.notify.reset_subscriptions(list(self.account), list(self.markets))
        else:
            # Initialize the notification instance
            self.notify = Notify(
                markets=list(self.markets),
                accounts=[self.account.name],
                on_market=self.on_mark,
                on_account=self.on_account
                # on_block=self.on_block,
                # bitshares_instance=self.bitshares
            ) 

    def run(self):
        self.update_notify()
        self.notify.listen()            

    def actual_tot(self, cat):
        ''' Transforms Amount in actual BTC value
            :param an Amount instances
            :returns it's actual value in BTC
        '''
        total = 0.0
        tot_am = Amount(cat).amount
        if Amount(cat).asset != Asset('1.3.1570'):
            for mark in Market(Amount(cat).asset, Asset('1.3.1570')).orderbook()['bids']:
                if tot_am > 0:
                    if tot_am > mark['quote']['amount']:
                        total += (mark['quote']['amount']*mark['price'])
                    else:
                        total += (tot_am*mark['price'])
                else:
                    break

                tot_am = tot_am-mark['quote']['amount']
        else:
            total = Amount(cat).amount
        return Amount(total, Amount(cat).symbol)

    def actual_sel(self):
        ''' Returns amounts in open orders at actual sell value
        '''
        in_order = []
        sumBuy = 0.0
        sumSell = 0.0
        list_order = self.my_orders()
        for idx, cat in enumerate(list_order['sell']):
            if idx+1 < len(list_order['sell']) and (cat['for_sale']['asset']['id'] == list_order['sell'][idx+1]['for_sale']['asset']['id']):
                if cat['quote']['asset'] != Asset('1.3.1570'):
                    sumSell += cat['for_sale']['amount']
                else:
                    sumSell += cat['quote']['amount']
            else:
                if cat['quote']['asset'] != Asset('1.3.1570'):
                    sumSell += cat['for_sale']['amount']
                    sumSell = self.actual_tot(Amount(sumSell, cat['base']['symbol']))[
                        'amount']
                else:
                    sumSell += cat['quote']['amount']

                in_order.append(
                    Amount(sumSell, cat['for_sale']['symbol']))
                sumSell = 0.0

        for cat in list_order['buy']:
            sumBuy += cat['for_sale']['amount']
        in_order.append(Amount(sumBuy, 'BRIDGE.BTC'))
        return in_order

    def my_orders(self):
        ''' Returns lists for buy and sell open orders
        '''
        sell_or = []
        buy_or = []
        for it in self.account.openorders:
            if it['base']['asset'] != Asset('1.3.1570'):
                sell_or.append(it)
            else:
                buy_or.append(it)
        return {'sell': sell_or, 'buy': buy_or}

    @staticmethod
    def open_orders_display (data):
        lista=[]
        if isinstance(data, Iterable):
            for i in data:
                lista.append(OrderedDict({'ID':i['id'],'Buy':i['quote']['symbol'], 'Sell':i['base']['symbol'], 'Price':Price(i['base'],i['quote'])['price']}))
                        
        if isinstance(data, Order):
            pass

        return lista

    def read_history(self):
        if os.path.isfile(self.account.name+'.log'):
            hist = []
            with open(self.account.name+'.log') as f:
                for line in f:
                    hist.append(dict(ast.literal_eval(line)))
        return hist

    def write_hist(self):
        if os.path.isfile(self.account.name+'.log'):
            list_hist = [cat for cat in self.account.history(
                only_ops=['fill_order', 'transfer', 'asset_issue'])]
            file_hist = self.read_history()
            for cat in list_hist[::-1]:
                if cat not in file_hist:
                    with open(self.account.name+'.log', 'r+') as f:
                        content = f.read()
                        f.seek(0, 0)
                        f.write(str(cat) + '\n' + content)
        else:
            with open(self.account.name+'.log', 'w') as f:
                for cat in self.account.history(only_ops=['fill_order', 'transfer', 'asset_issue']):
                    f.write(str(cat)+'\n')

    def on_account(self, account_update):
        config_lock = threading.RLock()
        config_lock.acquire()
        account = account_update.account
        if account["name"] == self.account.name:
            id_tranz = account.blockchain.rpc.get_object(account.blockchain.rpc.get_object(
                account_update['most_recent_op'])['operation_id'])

            self.write_hist()
            print(id_tranz)
            self.log.append(id_tranz)

        config_lock.release()

    def avail(self):
        tot = [{'asset': cat['asset']['id'], 'amount':cat['amount'],
                'symbol':cat['symbol']} for cat in self.account.balances+[cat['base'] for cat in self.account.openorders]]
        return pd.DataFrame(tot, columns=['asset', 'symbol', 'amount']).groupby(
            ['asset', 'symbol']).sum()

    def my_bal(self, val=0.0000001):
        tot = self.avail()
        que = Queue()

        thred1 = threading.Thread(name='totalBTC1', target=tot.insert, args=(0, 'total btc', [self.actual_tot(
            Amount(cat[1], cat[0][0]))['amount'] for cat in tot.iterrows()]))
        thred2 = threading.Thread(name='availableBTC1', target=lambda q, arg1: q.put(pd.DataFrame(arg1)), args=(
            que, ({'asset': cat['asset']['id'], 'symbol': cat['symbol'], 'available BTC': self.actual_tot(cat)['amount']} for cat in self.account.balances)))
        thred3 = threading.Thread(name='ordere1', target=lambda q, arg1: q.put(pd.DataFrame(arg1)), args=(
            que, ({'asset': cat['asset']['id'], 'symbol': cat['symbol'], 'orders': cat['amount']} for cat in self.actual_sel())))

        thred1.start()
        thred3.start()
        thred2.start()
        thred1.join()
        thred3.join()
        thred2.join()

        while not que.empty():
            result = que.get()
            tot = tot.merge(result, how='outer', on=[
                            'asset', 'symbol']).fillna(0)

        tot['total'] = tot['available BTC'] + \
            tot['orders']

        tot = tot[['symbol', 'amount', 'total btc',
                   'available BTC', 'orders', 'total']][tot.total > val]

        return tot.sort_values('total', ascending=False)

    def on_mark(self, mark_update):
        config_lock = threading.RLock()
        config_lock.acquire()        

        if mark_update.get("deleted", False):
            self.order_data=self.order_data.drop(index=mark_update['id'], level=1)
            print('Cancel '+str(mark_update))

        if mark_update.get("for_sale", False):
            if mark_update['sell_price']['base']['asset_id'] != Market(self.markets[0])['base']['id']:
                dict_date={'ID':[mark_update['id']], 'Side':['Sell'],'Price': [mark_update.invert()['price']], mark_update['base']['symbol']:[mark_update['base']['amount']], mark_update['quote']['symbol']:[mark_update['quote']['amount']], 'Seller':[Account(mark_update['seller']).name]}
            else:
                dict_date={'ID':[mark_update['id']], 'Side':['Buy'],'Price': [mark_update['price']], mark_update['base']['symbol']:[mark_update['base']['amount']], mark_update['quote']['symbol']:[mark_update['quote']['amount']], 'Seller':[Account(mark_update['seller']).name]}
            
            if mark_update['id'] in self.order_data.index.get_level_values(1):
                self.order_data.at[(dict_date['Side'][0], mark_update['id']), mark_update['base']['symbol']]= mark_update['for_sale']
                self.order_data.at[(dict_date['Side'][0], mark_update['id']), mark_update['quote']['symbol']]=mark_update['for_sale']/mark_update['price']
                
                print('Update ID '+mark_update['id']+' '+Account(mark_update['seller']).name+' '+str(mark_update))
            else:
                self.order_data = pd.concat([self.order_data, pd.DataFrame(dict_date).set_index(['Side','ID'])], sort=True)
                print('Add/remove ID '+mark_update['id']+' '+Account(mark_update['seller']).name+' '+str(mark_update))
                
            self.order_data.sort_values(by=['Price'], inplace=True)

        config_lock.release()

    def get_assset_min(self, parit, acc='venom88'):
        if isinstance(parit, str):
            if 'BRIDGE.BTC' in re.split(':|/', parit)[1]:
                parit = Market(str(Market(parit).get_string().split(
                    ':')[1]+':'+Market(parit).get_string().split(':')[0]))
            else:
                parit = Market(parit)

        am_quote = Amount(0, parit['quote']['id'])
        am_base = Amount(0, parit['base']['id'])

        if os.path.isfile(Account(acc).name+'.log'):
            self.write_hist()
            tot = self.read_history()[::-1]
        else:
            tot = Account(acc).history(
                only_ops=['fill_order', 'transfer', 'asset_issue'])

        for cat in tot:
            if am_base < 0.1:
                am_quote = Amount(0, parit['quote']['id'])
                am_base = Amount(0, parit['base']['id'])

            if parit['base']['id'] in str(cat) and parit['quote']['id'] in str(cat):
                if "pays" and "receives" in cat['op'][1]:
                    if parit['base']['id'] == cat['op'][1]['receives']['asset_id']:
                        am_base += Amount(cat['op'][1]['receives'])
                        am_quote -= Amount(cat['op'][1]['pays'])
                    if parit['base']['id'] == cat['op'][1]['pays']['asset_id']:
                        am_base -= Amount(cat['op'][1]['pays'])
                        am_quote += Amount(cat['op'][1]['receives'])

            # if getOperationNameForId(cat['op'][0]) in ['transfer'] and cat['op'][1]['amount']['asset_id'] in str(parit['base']):
            #     am_base -= Amount(cat['op'][1]['amount'])

            # if getOperationNameForId(cat['op'][0]) in ['asset_issue'] and cat['op'][1]['asset_to_issue']['asset_id'] in str(parit['base']):
            #     am_base += Amount(cat['op'][1]['asset_to_issue'])

        return [Price(quote=am_base, base=am_quote), am_base, am_quote]

    def market_ordere(self, market, limit=300):
        if isinstance(market, str):
            if 'BRIDGE.BTC' in re.split(':|/', market)[1]:
                market = Market(str(Market(market).get_string().split(
                    ':')[1]+':'+Market(market).get_string().split(':')[0]))
            else:
                market = Market(market)

        order_book = [] 
        orders = self.account.blockchain.rpc.get_limit_orders(market['base']['id'], market['quote']['id'], limit)
        orders = [self.get_updated_limit_order(o) for o in orders]
        orders = [Order(o) for o in orders]

        for order in orders:
            if 'for_sale' in order:
                if order['base']['asset']['id'] == market['base']['id']:
                    order_book.append({'ID':order['id'], 'Side':'Sell','Price': order.invert()['price'], order['base']['symbol']:order['base']['amount'], order['quote']['symbol']:order['quote']['amount'], 'Seller':Account(order['seller']).name})
                else:
                    order_book.append({'ID':order['id'], 'Side':'Buy','Price': order['price'], order['base']['symbol']:order['base']['amount'], order['quote']['symbol']:order['quote']['amount'], 'Seller':Account(order['seller']).name})

        return order_book

    @staticmethod
    def get_hist(cat):
        hist = OrderedDict()
        if cat['op'][0] == 1:
            hist={'Transaction ID': cat['id'], 'Transaction type': getOperationNameForId(
                cat['op'][0]), 'Sell': Amount(cat['op'][1]['amount_to_sell']), 'Buy': Amount(cat['op'][1]['min_to_receive'])}
        if cat['op'][0] == 2:
            hist={'Transaction ID': cat['id'], 'Transaction type': getOperationNameForId(
                cat['op'][0]), 'Amount': Amount(cat['result'][1])}
        if cat['op'][0] == 4:
            hist={'Transaction ID': cat['id'], 'Transaction type': getOperationNameForId(
                cat['op'][0]), 'Order ID': cat['op'][1]['order_id'], 'Pays': Amount(cat['op'][1]['pays']['amount'], Asset(cat['op'][1]['pays']['asset_id'])['symbol']), 'Receives': Amount(cat['op'][1]['receives']['amount'], Asset(cat['op'][1]['receives']['asset_id'])['symbol'])}
        if cat['op'][0] == 0:
            hist={'Transaction ID': cat['id'], 'Transaction type': getOperationNameForId(
                cat['op'][0]), 'Pays': Amount(cat['op'][1]['amount'])}
        if cat['op'][0] == 14:
            hist={'Transaction ID': cat['id'], 'Transaction type': getOperationNameForId(
                cat['op'][0]), 'Receives': Amount(cat['op'][1]['asset_to_issue'])}

        return hist

    @staticmethod
    def market_set (mark):
        markets=["BRIDGE.BTC","BRIDGE.USDT","BRIDGE.ETH","BRIDGE.LTC","BRIDGE.RVN","BTS"]

        if isinstance(mark, str):
            if len(re.split(':|/', mark))==1:
                if mark==markets[0]:
                    market=mark+"/"+markets[1]
                else:
                    market=mark+"/"+markets[0]
                
            if len(re.split(':|/', mark))==2:
                for mrk in markets:
                    if mrk in mark:
                        temp=re.split(':|/', mark)
                        temp.remove(mrk)
                        market=temp[0]+"/"+mrk
                        break
            
        print(market)
        return market

    @staticmethod
    def get_updated_limit_order(limit_order):
        """ Returns a modified limit_order so that when passed to Order class,
            will return an Order object with updated amount values
            :param limit_order: an item of Account['limit_orders'] or bitshares.rpc.get_limit_orders()
            :return: Order
        """
        order = copy.deepcopy(limit_order)
        order = limit_order
        price = float(order['sell_price']['base']['amount']) / float(order['sell_price']['quote']['amount'])
        base_amount = float(order['for_sale'])
        quote_amount = base_amount / price
        order['sell_price']['base']['amount'] = base_amount
        order['sell_price']['quote']['amount'] = quote_amount
        return order        
    
    @staticmethod
    def truncate(number, decimals):
        """ Change the decimal point of a number without rounding
            :param strig: A number to be cut down
            :param int | decimals: Number of decimals to be left to the float number
            :return: Price with specified precision
        """
        return float(number[:decimals]+'.'+number[decimals:-1])

    def get_market_data(self, mark):
        date = self.market_ordere(mark)
        order_book = pd.DataFrame(date).set_index(['Side','ID'])
        order_book.sort_values(by=['Price'], inplace=True)

        return self.set_order(order_book)

    def process_pd (self, panda):  
        # panda=panda[panda.Seller !=self.account.name]      
        sell = panda.loc['Sell']
        buy = panda.loc['Buy']
        buy=buy.sort_values(by=['Price'], ascending=False)
        
        sell=sell.assign(Total=pd.Series(sell[buy.columns[0]].rolling(window=sell[buy.columns[0]].count(), min_periods=1).sum()))
        buy=buy.assign(Total=pd.Series(buy[buy.columns[0]].rolling(window=buy[buy.columns[0]].count(), min_periods=1).sum()))      

        #print(buy)
        #clustering_buy = MeanShift().fit(np.column_stack([buy.Price.array, buy.Total.array]))
        #buy=buy.groupby(clustering_buy.labels_).agg({buy.columns[0]: 'sum', buy.columns[1]: 'sum', 'Price': 'max'})
        #buy=buy.sort_values(by=['Price'], ascending=False)
        #print(buy)
        #print(buy.iloc[1:2, 2])
        
        #print(sell)
        #clustering_sell = MeanShift(bandwidth=sell.iloc[:,0].median()).fit(np.column_stack([sell.Price.array, sell.Total.array]))
        #sell=sell.groupby(clustering_sell.labels_).agg({sell.columns[0]: 'sum', sell.columns[1]: 'sum', 'Price': 'min'})
        #sell=sell.sort_values(by=['Price'], ascending=True)
        #print(sell)
        #print(sell.iloc[1:2, 2])

        return [buy, sell]
        

