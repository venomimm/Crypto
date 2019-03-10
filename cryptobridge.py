from pprint import pprint
from itertools import repeat
import pandas as pd
from bitshares import BitShares
from bitshares.notify import Notify
from bitshares.account import Account
from bitshares.amount import Amount
from bitshares.asset import Asset
from bitshares.market import Market
from bitshares.price import Order, Price
from bitsharesbase.operations import getOperationNameForId
import os.path
import ast
import threading

# market = Market("BRIDGE.SCH:BRIDGE.BTC")
# ordere = market.orderbook(50)

account = Account("venom88")
pd.options.display.float_format = '{0:.8f}'.format


def actual_tot(cat):
    total = 0.0
    tot_am = Amount(cat).amount
    if Amount(cat).asset != Asset('1.3.1570'):
        for mark in Market(Amount(cat).asset, Asset('1.3.1570')).orderbook()['bids']:
            if tot_am > 0:
                if tot_am > mark['quote']['amount']:
                    total += (mark['quote']['amount']*mark['price'])
                else:
                    total += (tot_am*mark['price'])

            tot_am = tot_am-mark['quote']['amount']
    else:
        total = Amount(cat).amount
    return Amount(total, Amount(cat).symbol)


def actual_sel(list_ord):
    in_order = []
    sumBuy = 0.0
    sumSell = 0.0
    list_order = my_orders(list_ord)
    for idx, cat in enumerate(list_order[0]):
        if idx+1 < len(list_order[0]) and (cat['for_sale']['asset']['id'] == list_order[0][idx+1]['for_sale']['asset']['id']):
            sumSell += cat['quote']['amount']
        else:
            sumSell += cat['quote']['amount']
            in_order.append(
                Amount(sumSell, cat['for_sale']['symbol']))
            sumSell = 0.0

    for cat in list_order[1]:
        sumBuy += cat['for_sale']['amount']
    in_order.append(Amount(sumBuy, 'BRIDGE.BTC'))
    return in_order


def my_orders(list_ord):
    sell_or = []
    buy_or = []
    for it in list_ord:
        if it['base']['asset'] != Asset('1.3.1570'):
            sell_or.append(it)
        else:
            buy_or.append(it)
    return [sell_or, buy_or]


def read_history(file):
    if os.path.isfile(file):
        hist = []
        with open(file) as f:
            for line in f:
                hist.append(dict(ast.literal_eval(line)))
    return hist


def write_hist(file):
    if os.path.isfile(file):
        list_hist = [cat for cat in account.history() if getOperationNameForId(
            cat['op'][0]) in ['fill_order', 'transfer', 'asset_issue']]
        file_hist = read_history(file)
        for cat in list_hist[::-1]:
            if cat not in file_hist:
                with open(file, 'r+') as f:
                    content = f.read()
                    f.seek(0, 0)
                    f.write(str(cat) + '\n' + content)
    else:
        with open(file, 'w') as f:
            for cat in account.history(limit=100):
                if getOperationNameForId(cat['op'][0]) in ['fill_order', 'transfer', 'asset_issue']:
                    f.write(str(cat)+'\n')


def on_account(account_update):
    config_lock = threading.RLock()
    config_lock.acquire()

    config_lock.release()


test = ''
notify = Notify(
    markets=["BRIDGE.SCH:BRIDGE.BTC"],
    accounts=['venom88'],
    on_market=print,
    on_account=print
)

t1 = threading.Thread(target=notify.listen())
t1.start()


# write_hist('hist.log')

# list_bal = pd.DataFrame({'Asset': cat['asset']['id'], 'Symbol': cat['symbol'],
#                          'Amount': cat['amount'], 'Total BTC': actual_tot(cat)['amount']} for cat in account.balances).set_index('Asset')

# list_ord = pd.DataFrame({'Asset': cat['asset']['id'], 'In Orders': cat['amount']}
#                         for cat in actual_sel(account.openorders)).set_index('Asset')

# my_balance = list_bal.merge(list_ord, how='left', on='Asset').fillna(0)
# my_balance['Total'] = my_balance['Total BTC']+my_balance['In Orders']

# my_balance = my_balance[['Symbol', 'Amount',
#                          'Total BTC', 'In Orders', 'Total']]
# print(my_balance.sort_values('Total', ascending=False))

# dp_bids = pd.DataFrame({cat['base']['symbol']: cat['b ase']['amount'], 'Price': "{0:.8f}".format(
#     cat['price']), cat['quote']['symbol']: cat['quote']['amount'], 'User': Account(cat['quote']['asset']['issuer']).name} for cat in ordere['bids'])
# dp_asks = pd.DataFrame({cat['base']['symbol']: cat['base']['amount'], 'Price': "{0:.8f}".format(
#     cat['price']), cat['quote']['symbol']: cat['quote']['amount'], 'User': Account(cat['quote']['asset']['issuer']).name} for cat in ordere['asks'])

# print(dp_bids)
# print(dp_asks)
