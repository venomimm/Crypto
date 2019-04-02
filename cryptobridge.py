from itertools import repeat
from collections import defaultdict
from bitshares import BitShares
from bitshares.notify import Notify
from bitshares.account import Account, AccountUpdate
from bitshares.amount import Amount
from bitshares.asset import Asset
from bitshares.market import Market
from bitshares.price import Price, Order, FilledOrder, UpdateCallOrder
from bitsharesbase.operations import getOperationNameForId
from bitshares.blockchain import Blockchain, BlockchainInstance
from win10toast import ToastNotifier
from collections import OrderedDict
import math
import os.path
import ast
import threading
import pandas as pd
from datetime import datetime
import queue


class Account_Data:

    def __init__(self, account):
        self.account = Account(account, full=True)

        notify = Notify(
            markets=list(dict.fromkeys([Market.get_string(cat)
                                        for cat in self.account.openorders])),
            accounts=[self.account.name],
            on_account=self.on_acc
            # on_market=self.on_mark,
        )

        # notify.listen()

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

    def on_acc(self, account_update):
        config_lock = threading.RLock()
        config_lock.acquire()
        account = account_update.account
        if account["name"] == self.account.name:
            id_tranz = account.blockchain.rpc.get_object(account.blockchain.rpc.get_object(
                account_update['most_recent_op'])['operation_id'])
            print(id_tranz['op'][0])

            if getOperationNameForId(id_tranz['op'][0]) in ['fill_order', 'transfer', 'asset_issue']:
                toaster = ToastNotifier()
                toaster.show_toast(getOperationNameForId(id_tranz['op'][0]).replace('_', ' ').title(),
                                   print(account_update),
                                   icon_path="bitshares.ico",
                                   duration=5)
            self.write_hist()
            print(self.my_bal())

        config_lock.release()

    def avail(self):
        tot = [{'asset': cat['asset']['id'], 'amount':cat['amount'],
                'symbol':cat['symbol']} for cat in self.account.balances+[cat['base'] for cat in self.account.openorders]]
        return pd.DataFrame(tot, columns=['asset', 'symbol', 'amount']).groupby(['asset', 'symbol']).sum()

    def my_bal(self, val=0.000001):
        tot = self.avail()

        que = queue.Queue()
        threads_list = []

        thred1 = threading.Thread(name='totalBTC', target=tot.insert, args=(0, 'total btc', [self.actual_tot(
            Amount(cat[1], cat[0][0]))['amount'] for cat in tot.iterrows()]))
        thred2 = threading.Thread(name='availableBTC', target=lambda q, arg1: q.put(pd.DataFrame(arg1)), args=(que,
                                                                                                               ({'asset': cat['asset']['id'], 'symbol': cat['symbol'], 'available BTC': self.actual_tot(cat)['amount']} for cat in self.account.balances)))
        thred3 = threading.Thread(name='ordere', target=lambda q, arg1: q.put(pd.DataFrame(arg1)), args=(
            que, ({'asset': cat['asset']['id'], 'symbol': cat['symbol'], 'orders': cat['amount']} for cat in self.actual_sel())))

        thred1.start()
        thred2.start()
        thred3.start()
        threads_list.append(thred1)
        threads_list.append(thred3)
        threads_list.append(thred2)

        for t in threads_list:
            t.join()

        while not que.empty():
            result = que.get()
            tot = tot.merge(result, how='outer', on=[
                            'asset', 'symbol']).fillna(0)

        tot['total'] = tot['available BTC'] + \
            tot['orders']

        tot.loc['Suma', 'total'] = tot['total'].sum()
        tot.loc['Suma', 'total btc'] = tot['total btc'].sum()

        tot = tot[['symbol', 'amount', 'total btc',
                   'available BTC', 'orders', 'total']][tot.total > val]
        pd.options.display.float_format = '{0:.8f}'.format

        return tot.sort_values('total', ascending=False)

    def on_mark(self, mark_update):
        print(str(mark_update))

    def get_assset_min(self, parit):
        if isinstance(parit, str):
            if 'BRIDGE.BTC' in parit.split(':')[1]:
                parit = Market(str(Market(parit).get_string().split(
                    ':')[1]+':'+Market(parit).get_string().split(':')[0]))
            else:
                parit = Market(parit)

        am_quote = Amount(0, parit['quote']['id'])
        am_base = Amount(0, parit['base']['id'])

        if os.path.isfile(self.account.name+'.log'):
            self.write_hist()
            tot = self.read_history()[::-1]
        else:
            tot = self.account.history(
                only_ops=['fill_order', 'transfer', 'asset_issue'])

        for cat in tot:
            if am_base < 0:
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

        return [Price(am_base, am_quote), am_base, am_quote]

    def get_hist(self):
        hist = []
        for cat in self.read_history():
            if cat['op'][0] == 4:
                hist.append({'Transaction ID': cat['id'], 'Transaction type': getOperationNameForId(
                    cat['op'][0]), 'Order ID': cat['op'][1]['order_id'], 'Pays': Amount(cat['op'][1]['pays']['amount'], Asset(cat['op'][1]['pays']['asset_id'])['symbol']), 'Receives': Amount(cat['op'][1]['receives']['amount'], Asset(cat['op'][1]['receives']['asset_id'])['symbol'])})
            if cat['op'][0] == 0:
                hist.append({'Transaction ID': cat['id'], 'Transaction type': getOperationNameForId(
                    cat['op'][0]), 'Pays': Amount(cat['op'][1]['amount'])})
            if cat['op'][0] == 14:
                hist.append({'Transaction ID': cat['id'], 'Transaction type': getOperationNameForId(
                    cat['op'][0]), 'Receives': Amount(cat['op'][1]['asset_to_issue'])})

        return pd.DataFrame(hist)[['Transaction ID', 'Transaction type', 'Order ID', 'Pays', 'Receives']]

    def market_ordere(self, market, limit=100):
        if isinstance(market, str):
            market = Market(market)

        bids, asks = [], []

        for cat in self.account.blockchain.rpc.get_limit_orders(market['base']['id'], market['quote']['id'], limit):
            order = Order(cat['id'])
            if order['base']['asset']['id'] == market['base']['id']:
                bids.append(Order(cat['id']))
            else:
                asks.append(Order(cat['id']))

        return {"bids": bids, "asks": asks}

    def mark_order_tot(self, list_ord=[]):
        quote_sum = Amount(0, list_ord[0]['quote']['asset']['id'])
        base_sum = Amount(0, list_ord[0]['base']['asset']['id'])
        for cat in list_ord:
            quote_sum += cat['quote']
            base_sum += cat['base']

        return (quote_sum, base_sum)

    def truncate(self, number, decimals):
        """ Change the decimal point of a number without rounding
            :param strig: A number to be cut down
            :param int | decimals: Number of decimals to be left to the float number
            :return: Price with specified precision
        """
        return float(number[:decimals]+'.'+number[6:-1])


# test = market_ordere('venom88', 'BRIDGE.PHON:BRIDGE.BTC')

# print(mark_order_tot(test['bids']))
# print(mark_order_tot(test['asks']))
# print(truncate(Asset('BRIDGE.PHON',full=True)['dynamic_asset_data']['current_supply'], Asset('BRIDGE.PHON',full=True)['precision']))

# list_asks = pd.DataFrame( OrderedDict({'Order ID': cat['id'], 'Price':str(Price(cat['price'],base=cat['quote'],quote=cat['base']))[:18], cat['base']['symbol']:cat['base']['amount'], cat['quote']['symbol']:cat['quote']['amount'], 'Seller':Account(cat['seller'])['name']}) for cat in test['asks'])
# print(list_asks)

# lista_ord = []
# for cat in account.openorders:
#     if cat.market not in lista_ord:
#         lista_ord.append(cat.market)
#         print(get_assset_min(cat.market))


accont = Account_Data('venom88')
# print(accont.get_assset_min('BRIDGE.ZNY:BRIDGE.BTC'))


start_time = datetime.now()
print(accont.my_bal())

time_elapsed = datetime.now() - start_time
print('Time elapsed (hh:mm:ss.ms) {}'.format(time_elapsed))
