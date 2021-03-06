from bs4 import BeautifulSoup
import requests
import csv
import time

adrress = input('Enter address: ')
result = requests.get(adrress)
soup = BeautifulSoup(result.text, "html.parser")


def parsData():
    date1 = []
    date1.append(['Data', 'Valoare'])
    leaderboard = soup.find_all('table')
    tbody = leaderboard[1].find('tbody')

    for tr in tbody.find_all("tr"):
        data = tr.find_all('td')[0].text.strip()
        val = tr.find_all('td')[2].text.strip()
        date1.append([data,  val])
    return date1


def write_to_file(output_list, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for row in output_list:
            writer.writerow(row)


while True:
    write_to_file(parsData(), 'export.csv')
    print(parsData())
    time.sleep(60)
