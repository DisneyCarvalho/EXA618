import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

dados = [

]

file = open("seeds.txt", "r")
for i in file:
    url = i.replace("\n",'')
    print(url)
    print(type(url))

    try:
        response = requests.get(url)

        soup = BeautifulSoup(response.text, "html.parser")

        img = soup.find("img")

        

        dados.append((soup.title.string.replace("\n",''),urljoin(url, img.get("src"))))
    
    except:
        print(soup.title.string," Erro")

    
html = "<html>\n<body>\n"

for title, src in dados:
    html += f"""
    <div>
        <h2>{title}</h2>
        <img src="{src}" alt="{title}" width="200">
    </div>
    """

html += "\n</body>\n</html>"


with open("index.html", "w", encoding="utf-8") as file:
    file.write(html)


    

