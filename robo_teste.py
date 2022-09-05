import os
from dotenv import load_dotenv

load_dotenv()


import winsound




import pancake as pk


if __name__ == "__main__":
    
    carteira = os.getenv('CARTEIRA') 
    _pk = os.getenv('_PK')
    contrato = "0x5e2689412fae5c29bd575fbe1d5c1cd1e0622a8f" 


    qnt_bnb_compra = 0.1
    saida = pk.tenta_ate_comprar_caminho_apareceu(contrato, carteira, _pk, qnt_bnb_compra, True)


    # saida = pk.tenta_ate_comprar_caminho_apareceu(contrato, carteira, _pk, qnt_bnb_compra, True)
    # print(saida)

    # duration = 1000  # milliseconds
    # freq = 250  # Hz
    # winsound.Beep(freq, duration)

    # pk.venda(contrato, carteira, _pk, 2, True)
    # print(carteira, _pk)
    # 0x5E2689412Fae5c29BD575fbe1d5C1CD1e0622A8f
    # python robo_teste.py