from tkinter import ttk, NO, Button, Entry, Tk, RIGHT, LEFT, StringVar, Text, END, Listbox, Frame, Label, RIDGE, E, X
from datetime import datetime
from cryptobridge import Account_Data
from collections import OrderedDict
from bitshares.price import Price
from bitshares.account import Account
from bitshares.asset import Asset
import multiprocessing
import queue
import threading
import pandas as pd

window = Tk()
window.configure(background='black')
w, h = window.winfo_screenwidth(), window.winfo_screenheight()
window.geometry("%dx%d+0+0" % (w, h))

frame1 = Frame(window, relief=RIDGE)
frame1.grid(row=0, rowspan=5, column=0)
frame2 = Frame(window, relief=RIDGE)
frame2.grid(column=1, row=0)


def get_data():
    return Account_Data(val.get())


def insert_my_orders():
    if t2.size() > 0:
        t2.delete(0, END)

    for cat in get_data().my_orders()['buy']:
        t2.insert(END, cat)
        t2.itemconfig(END, fg='green')
    for cat in get_data().my_orders()['sell']:
        t2.insert(END, cat)
        t2.itemconfig(END, fg='red')


def insert_asset_orders(**kwargs):

    t4.heading(1, text='Order ID')
    t4.heading(2, text='Price')
    t4.heading(3, text=kwargs['bids'][0]['base']['symbol'])
    t4.heading(4, text=kwargs['bids'][0]['quote']['symbol'])
    t4.heading(5, text='Seller')

    for cat in kwargs['bids']:
        t4.insert('', END, value=(cat['id'], str(cat.invert()).split('@')[1].split(' ')[
                  1], cat['base']['amount'], cat['quote']['amount'], Account(cat['seller'])['name']))

    t3.heading(1, text='Order ID')
    t3.heading(2, text='Price')
    t3.heading(3, text=kwargs['asks'][0]['base']['symbol'])
    t3.heading(4, text=kwargs['asks'][0]['quote']['symbol'])
    t3.heading(5, text='Seller')

    for cat in kwargs['asks']:
        t3.insert('', END, value=(cat['id'], str(cat).split('@')[1].split(' ')[1],
                                  cat['base']['amount'], cat['quote']['amount'], Account(cat['seller'])['name']))


def insert_my_balance():
    t1.delete(1.0, END)
    t1.insert(END, get_data().my_bal())


def insert_log():
    pass
    # get_data().notify.listen()
    # t3.insert(END, get_data().on_acc)


def action_button():
    p1 = threading.Thread(name='balanta', target=insert_my_balance)
    p2 = threading.Thread(name='ordere', target=insert_my_orders)
    # p3 = threading.Thread(name='log', target=insert_log)
    p1.start()
    p2.start()
    # p3.start()


def onselect_list(evt):
    w = evt.widget
    index = w.curselection()
    value = w.get(index)
    market = value.split('@')[1].split(' ')[2]
    # result = get_data().market_ordere(market)
    # insert_asset_orders(bids=result['bids'], asks=result['asks'])

    val_min = get_data().get_assset_min(market)
    textmin.set('Price:'+str(val_min[0])+'  Amount:' +
                str(val_min[1])+'  Paid:'+str(val_min[2])+'  Current supply:'+str(get_data().truncate(Asset('BRIDGE.PHON', full=True)['dynamic_asset_data']['current_supply'], Asset('BRIDGE.PHON', full=True)['precision'])))


labelAcont = Label(frame1, text='Account',
                   relief=RIDGE, padx=20, pady=5)
labelAcont.grid(row=0, column=0)
labelBuy = Label(frame2, text='Buy orders',
                 relief=RIDGE, padx=50, pady=5)
labelBuy.grid(row=2, column=0)
labelSell = Label(frame2, text='Sell orders',
                  relief=RIDGE, padx=50, pady=5)
labelSell.grid(row=2, column=1)

textmin = StringVar()
labelMin = Label(frame2, padx=10, pady=5, textvariable=textmin)
labelMin.grid(row=0, columnspan=3)

val = StringVar()
entr = Entry(master=frame1, textvariable=val, width=35)
entr.grid(row=0, column=1)
entr.bind('<Return>', lambda event: action_button())

b1 = Button(frame1, text='Ok', command=lambda: action_button(), width=10)
b1.grid(row=0, column=2)
t1 = Text(frame1, height=15, width=80)
t1.grid(row=1, columnspan=3)
t2 = Listbox(frame1, height=15, width=100)
t2.grid(row=2, columnspan=3)
t2.bind('<<ListboxSelect>>', onselect_list)

t3 = ttk.Treeview(frame2, columns=(1, 2, 3, 4, 5), height=15)
t3['show'] = 'headings'
t3.grid(row=3, column=0)

t4 = ttk.Treeview(frame2, columns=(1, 2, 3, 4, 5), height=15)
t4['show'] = 'headings'
t4.grid(row=3, column=1)

for i in (1, 2, 3, 4, 5):
    t4.column(i, minwidth=0, width=120, stretch=NO)
    t3.column(i, minwidth=0, width=120, stretch=NO)

window.mainloop()
