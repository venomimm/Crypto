from pprint import pprint
from itertools import repeat
import pandas as pd
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
import os.path
import ast
import threading


account = Account("venom88")
pd.options.display.float_format = '{0:.8f}'.format


def actual_tot(cat):
    '''
    Needs an Amount instances and
    returns it's actual value in BTC
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

            tot_am = tot_am-mark['quote']['amount']
    else:
        total = Amount(cat).amount
    return Amount(total, Amount(cat).symbol)


def actual_sel(account):
    in_order = []
    sumBuy = 0.0
    sumSell = 0.0
    list_order = my_orders(account)
    for idx, cat in enumerate(list_order[0]):
        if idx+1 < len(list_order[0]) and (cat['for_sale']['asset']['id'] == list_order[0][idx+1]['for_sale']['asset']['id']):
            if cat['quote']['asset'] != Asset('1.3.1570'):
                sumSell += cat['for_sale']['amount']
            else:
                sumSell += cat['quote']['amount']
        else:
            if cat['quote']['asset'] != Asset('1.3.1570'):
                sumSell += cat['for_sale']['amount']
                sumSell = actual_tot(Amount(sumSell, cat['base']['symbol']))[
                    'amount']
            else:
                sumSell += cat['quote']['amount']

            in_order.append(
                Amount(sumSell, cat['for_sale']['symbol']))
            sumSell = 0.0

    for cat in list_order[1]:
        sumBuy += cat['for_sale']['amount']
    in_order.append(Amount(sumBuy, 'BRIDGE.BTC'))
    return in_order


def my_orders(account):
    sell_or = []
    buy_or = []
    for it in account.openorders:
        if it['base']['asset'] != Asset('1.3.1570'):
            sell_or.append(it)
        else:
            buy_or.append(it)
    return [sell_or, buy_or]


def read_history(account):
    if os.path.isfile(account['name']+'.log'):
        hist = []
        with open(account['name']+'.log') as f:
            for line in f:
                hist.append(dict(ast.literal_eval(line)))
    return hist


def write_hist(account):
    if os.path.isfile(account['name']+'.log'):
        list_hist = [cat for cat in account.history(
            only_ops=['fill_order', 'transfer', 'asset_issue'])]
        file_hist = read_history(account)
        for cat in list_hist[::-1]:
            if cat not in file_hist:
                with open(account['name']+'.log', 'r+') as f:
                    content = f.read()
                    f.seek(0, 0)
                    f.write(str(cat) + '\n' + content)
    else:
        with open(account['name']+'.log', 'w') as f:
            for cat in account.history(only_ops=['fill_order', 'transfer', 'asset_issue']):
                f.write(str(cat)+'\n')


def on_acc(account_update):
    config_lock = threading.RLock()
    config_lock.acquire()
    account = account_update.account
    if account["name"] == 'venom88':
        print(account_update)

        id_tranz = account.blockchain.rpc.get_object(account.blockchain.rpc.get_object(
            account_update['most_recent_op'])['operation_id'])

        if getOperationNameForId(id_tranz['op'][0]) in ['fill_order', 'transfer', 'asset_issue']:
            toaster = ToastNotifier()
            toaster.show_toast(getOperationNameForId(id_tranz['op'][0]).replace('_', ' ').title(),
                               print(account_update),
                               icon_path="bitshares.ico",
                               duration=5)
        write_hist(account)
    print(my_bal())

    config_lock.release()


def avail(account):
    bal = [cat for cat in account.balances]
    orde = [cat['base'] for cat in account.openorders]

    asset_tot = list(dict.fromkeys([cat['asset']['id'] for cat in bal+orde]))

    total = []
    for it in asset_tot:
        sum1 = 0.0
        for cat in bal+orde:
            if it == cat['asset']['id']:
                sum1 += cat['amount']
        total.append(Amount(sum1, it))

    return total


def my_bal(val=0.000001):
    list_bal = pd.DataFrame({'Asset': cat['asset']['id'], 'Symbol': cat['symbol'], 'Available BTC': actual_tot(
        cat)['amount']} for cat in account.balances).set_index('Asset')

    tot_ave = pd.DataFrame(
        {'Asset': cat['asset']['id'], 'Symbol': cat['symbol'], 'Amount': cat['amount'], 'Total BTC': actual_tot(cat)['amount']} for cat in avail(account))

    list_bal = list_bal.merge(tot_ave, how='outer', on=[
                              'Asset', 'Symbol']).fillna(0)

    list_ord = pd.DataFrame({'Asset': cat['asset']['id'], 'Symbol': cat['symbol'], 'In Orders': cat['amount']}
                            for cat in actual_sel(account)).set_index('Asset', 'Symbol')

    my_balance = list_bal.merge(list_ord, how='outer', on=[
                                'Asset', 'Symbol']).fillna(0)
    my_balance['Total'] = my_balance['Available BTC']+my_balance['In Orders']

    my_balance.loc['Suma', 'Total'] = my_balance['Total'].sum()
    my_balance.loc['Suma', 'Total BTC'] = my_balance['Total BTC'].sum()

    my_balance = my_balance[['Symbol', 'Amount',
                             'Total BTC', 'Available BTC', 'In Orders', 'Total']]

    return my_balance.sort_values('Total', ascending=False)[my_balance.Total > val]


def on_mark(mark_update):
    print(str(mark_update))


def get_assset_min(parit, account='venom88'):
    if isinstance(parit, str):
        parit = Market(parit)

    am_quote = Amount(0, parit['quote']['id'])
    am_base = Amount(0, parit['base']['id'])

    list_tot = []

    if Account(account) == Account('venom88'):
        write_hist(account)
        tot = read_history(account)[::-1]
    else:
        tot = Account(account).history(
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

        if getOperationNameForId(cat['op'][0]) in ['transfer'] and cat['op'][1]['amount']['asset_id'] in str(parit['base']):
            am_base -= Amount(cat['op'][1]['amount'])

        if getOperationNameForId(cat['op'][0]) in ['asset_issue'] and cat['op'][1]['asset_to_issue']['asset_id'] in str(parit['base']):
            am_base += Amount(cat['op'][1]['asset_to_issue'])

    list_tot.append([am_base, am_quote])
    return list_tot


# for it in avail(account):
#     for cat in my_orders(account.openorders)[0]:
#         if cat['base']['asset']['id'] in it['asset']['id']:
#             print(get_assset_min(Market.get_string(cat)))


market = Market('BRIDGE.SCH:BRIDGE.BTC')
ordere = market.orderbook()

dp_bids = pd.DataFrame({cat['base']['symbol']: cat['base']['amount'], 'Price': "{0:.8f}".format(
    cat['price']), cat['quote']['symbol']: cat['quote']['amount'], 'User': Account(cat['quote']['asset']['issuer']).name} for cat in ordere['bids'])
dp_asks = pd.DataFrame({cat['base']['symbol']: cat['base']['amount'], 'Price': "{0:.8f}".format(
    cat['price']), cat['quote']['symbol']: cat['quote']['amount'], 'User': Account(cat['quote']['asset']['issuer']).name} for cat in ordere['asks'])

# for cat in ordere['bids']:
#     for it in cat.blockchain:
#         print(cat)

notify = Notify(
    markets=list(dict.fromkeys([Market.get_string(cat)
                                for cat in account.openorders])),
    accounts=[account.name],
    on_market=on_mark,
    on_account=on_acc
)

notify.listen()
