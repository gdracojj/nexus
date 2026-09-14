import requests

def buscar_cep(cep):
    url = f"https://viacep.com.br/ws/{cep}/json/"
    response = requests.get(url)
    return response.json()

def dados_normalizados():
    return {
        "rua": dados["logradouro"],
        "bairro": dados["bairro"],
        "cidade": dados["localidade"],
        "regiao": dados["regiao"]
    }

cep_desejado = int(input('Digite o CEP desejado: '))

print('Iniciar busca de CEP')
dados = buscar_cep(cep_desejado)

