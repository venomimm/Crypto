from bs4 import BeautifulSoup
import requests
import csv
import pycron

print('Enter address:')
adrress=input()
result=requests.get(adrress)

while pycron.is_now('*/5 * * * *'):
    soup = BeautifulSoup(result.text,"html.parser")

    leaderboard = soup.find_all('table')
    tbody = leaderboard[1].find('tbody')

    for tr in tbody.find_all("tr"):
        data =  tr.find_all('td')[0].text.strip()
        val =  tr.find_all('td')[2].text.strip()
        print(data,val)