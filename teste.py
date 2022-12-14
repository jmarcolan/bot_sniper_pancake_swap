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
    contrato = "0xf94819686F7f71e1EB69e373D3C442AAe9783883"
    qnt_bnb_compra = 0.01

    # valor_moeda = pk.tenta_info(contrato, carteira, _pk, 0.1)
    
    # ligar no momento certo
    saida = pk.tenta_uma_compra(contrato, carteira, _pk, qnt_bnb_compra, True)
    print(saida)

    print("---------"*4)
    # sys.argv
    print(str(sys.argv))

    print(f'acabo o compra, contrato = {contrato}, bnb_compra = {qnt_bnb_compra}')
    print("---------"*4)
