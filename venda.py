import sys
import time
import os
from dotenv import load_dotenv

load_dotenv()

import winsound


import pancake as pk


if __name__ == "__main__":
    
    carteira = os.getenv('CARTEIRA') 
    _pk = os.getenv('_PK')
    contrato = sys.argv[2]
    qnt_token_venda =  float(sys.argv[4])


    saida = pk.venda(contrato, carteira, _pk, qnt_token_venda, True)
    print(saida)


    print("---------"*4)
    print(str(sys.argv))
    print(f'acabo o {sys.argv[1]}, contrato = {contrato}, bnb_compra = {qnt_token_venda}')
    print("---------"*4)
