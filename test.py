.from urllib.request import urlopen as uReq
from bs4 import BeautifulSoup
import requests

result=requests.get("http://explorer.worldcryptoforumcoin.com/address/WcidA7rARPiczwhajfhuer7VDeywhAZgtt")

print(result.status_code) 

src=result.content
soup = BeautifulSoup(src,"lxml")

tag=soup.find_all("tr",{"role":"row"})
print(tag)
