from tkinter import Button, Entry, Tk, StringVar, Text, END, Listbox
from cryptobridge import Account_Data

window = Tk()


def get_data():
    accont = Account_Data(val.get())
    return accont


def action_button():
    t1.insert(END, get_data().my_bal())
    t2.insert(END, get_data().my_orders()['sell'])


w, h = window.winfo_screenwidth(), window.winfo_screenheight()
window.geometry("%dx%d+0+0" % (w, h))

b1 = Button(window, text='Ok', command=lambda: action_button())
b1.grid(row=0, column=1)

val = StringVar()
entr = Entry(window, textvariable=val)
entr.grid(row=0, column=0)

t1 = Text(window, height=15, width=80)
t1.grid(row=2, column=0)

t2 = Listbox(window, height=10, width=80)
t2.grid(row=1, column=0)

window.mainloop()
