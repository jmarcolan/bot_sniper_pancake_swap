import os
from dotenv import load_dotenv
import time

load_dotenv()


import winsound


# python app_robo_mult_process.py

import pancake as pk
from subprocess import call, Popen

import json

def robo_ativo():
    pass

if __name__ == "__main__":
    
    carteira = os.getenv('CARTEIRA') 
    _pk = os.getenv('_PK')
    def get_dados():
        ls_bomber ={
            "contrato": "",
            "qnt_bnb_compra": 0.01,
            "trheshold_moeda": 1}

        try:
            with open('bot_confi.json', "r") as json_data:
                ls_bomber = json.load(json_data)
                json_data.close()
        except:
            pass

        return ls_bomber["contrato"], ls_bomber["qnt_bnb_compra"], ls_bomber["trheshold_moeda"]
    
    
    grava_preco = []
    r_realizou_venda = False
    r_realizou_compra = False
    while not r_realizou_venda:
        contrato,qnt_bnb_compra,trheshold_moeda = get_dados()
        
        r_tem_contrato = contrato != ""


        if r_tem_contrato:

            def compra(info):
                r_caminho = len(info[1]) != 1
                if r_caminho:
                    cmd_str = f'python compra.py {info[0]} {contrato} {qnt_bnb_compra} {info[2]}'
                    # call(f'python hello.py {info[0]} {r_caminho} {info[2]}', shell=True)
                    proc = Popen(cmd_str, shell=True,
                        stdin=None, stdout=None, stderr=None, close_fds=True)

                    print("nova tentativa")    

            def venda(info, qnt_moedas_wallet):
                def requisita_venda():
                    cmd_str = f'python venda.py {info[0]} {contrato} {qnt_bnb_compra} {qnt_moedas_wallet}'
                    # call(f'python hello.py {info[0]} {r_caminho} {info[2]}', shell=True)
                    proc = Popen(cmd_str, shell=True,
                        stdin=None, stdout=None, stderr=None, close_fds=True)


                def r_caindo_calc(valor_atual):
                    periodo = 40
                    porcentagem_limiar = 0.92
                    r_ja_tem_muito = len(grava_preco) > periodo
                    if r_ja_tem_muito:
                        maior = max(grava_preco[-periodo:])
                        # print(grava_preco[-periodo:] )
                    else:
                        maior = max(grava_preco)

                    r_caindo = valor_atual < maior * porcentagem_limiar
                    print(f'o valor atual {valor_atual}, o {maior}, o tamnha {len(grava_preco)} e o limiar de queda {maior * porcentagem_limiar}, entao esta caindo? {r_caindo}')
                    

                    # print(f'o preco mais alto {maior* float(qnt_moedas_wallet)} e foi pago {qnt_paga_moeda}')
                    return r_caindo
                
                valor_moeda_usd = info[2]
                grava_preco.append(float(valor_moeda_usd))

                
                valor_bnb_usd = pk.tenta_get_bnb_usd(contrato, carteira, _pk)
                qnt_paga_moeda =  float(valor_bnb_usd) * qnt_bnb_compra
                valor_atual = qnt_moedas_wallet * valor_moeda_usd


                r_lucrando = valor_atual >= qnt_paga_moeda * 10
                r_ativa_stop_loss = float(valor_atual)  <= qnt_paga_moeda * 0.7
                r_caindo =  r_caindo_calc(valor_moeda_usd)

                print(f'stop loss = {r_ativa_stop_loss}, r_lucro={r_lucrando}, caindo = {r_caindo}')

                if r_ativa_stop_loss or r_lucrando or r_caindo or True:

                    requisita_venda()
                    # print(f'stop loss = {r_ativa_stop_loss}, r_lucro={r_lucrando}, caindo = {r_caindo}')
            

            info = pk.tenta_info(contrato, carteira, _pk, qnt_bnb_compra)
            print(f'blocok {info[0]}')
            qnt_moedas_wallet = pk.tenta_get_wallet_token(contrato, carteira, _pk)
            print(f'carteira tem {qnt_moedas_wallet}')


            r_venda = qnt_moedas_wallet >= trheshold_moeda
            
            if r_venda or r_realizou_compra:
                r_realizou_compra = True
                r_realizou_venda = qnt_moedas_wallet <= trheshold_moeda
                if not r_realizou_venda:
                    pk.tenta_aprova(contrato, carteira, _pk)
                    venda(info, qnt_moedas_wallet)
                else:
                    r_realizou_venda = True
                    break
                    
                
            else:
                compra(info)


            print("---**---"*4)
