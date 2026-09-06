import json
import requests 


texto = '[{"uf": "RJ"}]'

dados = json.loads(texto)

print(type(texto))
print(type(dados))
print(type(dados[0]))


def licitacoes():
    return [
    {   "numero": "Pregão 001", 
        "uf": "RJ", 
        "descricao":"Luvas cirúrgicas"
    },
    {   "numero": "Pregão 002", 
        "uf": "SP", 
        "descricao":"Máscaras cirúrgicas"
    },
    {   "numero": "Pregão 003", 
        "uf": "RJ", 
        "descricao":"Bisturis"
    },      
    {  "numero": "Pregão 005",
        "uf": "SP", 
        "descricao":"Toucas cirúrgicas"
    }

]

def filtrar_licitacoes(dados, estado, produto):
    resultado = [] 

    for licitacao in dados:
        if licitacao["uf"] == estado and produto in licitacao['descricao'].lower():  print('NEXUS - iniciado com sucesso')
        resultado.append(licitacao)

        return resultado
 
def main():    

    print("NEXUS - iniciado com sucesso")

    estado = input('Digite o estado: ').upper()
    produto = input('Digite o produto desejado:').lower()

    dados = licitacoes()
    
    resultado = filtrar_licitacoes(dados, estado, produto)

    quantidade = len(resultado)

    for licitacao in resultado:
        print(f'Número: {licitacao["numero"]}')
        print(f'Descrição: {licitacao["descricao"]}')
        print(f'UF: {licitacao["uf"]}')

    print(f'NEXUS - Quantidade de licitações encontradas: {quantidade}')

    if quantidade == 0:
        print('NEXUS - Nenhuma licitação encontrada com os filtros informados.')
    else:
        print(f'NEXUS - Licitações em {estado} encontradas.')

    
if __name__ == '__main__':
    main()


#4. retornar as licitações encontradas
#5. só depois começar a olhar API/JSON

