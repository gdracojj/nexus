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

def main():
    print('NEXUS - iniciado com sucesso')

    estado = input('Digite o estado: ').upper()
    produto = input('Digite o produto desejado:').lower()
    encontrado = False
    quantidade = 0

    for licitacao in licitacoes():
        if licitacao["uf"] == estado and produto in licitacao["descricao"].lower():
            print(f'Número: {licitacao["numero"]}')
            print(f'Descrição: {licitacao["descricao"]}')
            print(f'UF: {licitacao["uf"]}')
            encontrado = True
            quantidade += 1
    print(f'NEXUS - Quantidade de licitações encontradas: {quantidade}')

    if encontrado == False:
        print('NEXUS - Nenhuma licitação encontrada com os filtros informados.')
    else:
        print(f'NEXUS - Licitações em {estado} encontradas.')

    
if __name__ == '__main__':
    main()

## PROXIMO PASSO:
# aprender a separar a lógica de filtro em uma função própria
# e começar a preparar os dados para futura integração com o PNCP
#1. transformar o filtro em uma função
#2. entender parâmetros de função
#3. fazer essa função receber estado e produto
#4. retornar as licitações encontradas
#5. só depois começar a olhar API/JSON

