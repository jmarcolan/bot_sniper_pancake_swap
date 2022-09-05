
#https://github.com/beeb/pancaketrade/blob/e9933bcd6a81ad92163168ebc33b1989402742f1/pancaketrade/network/bsc.py#L378
# def get_tx_params(self, value: Wei = Wei(0), gas: Wei = Wei(100000), gas_price: Optional[Wei] = None) -> TxParams:
#     """Build a transaction parameters dictionary from the provied parameters.
#     The default gas limit of 100k is enough for a normal approval transaction.
#     Args:
#         value (Wei, optional): value (BNB) of the transaction, in Wei. Defaults to Wei(0).
#         gas (Wei, optional): gas limit to use, in Wei. Defaults to Wei(100000).
#         gas_price (Optional[Wei], optional): gas price to use, in Wei, or None for network default. Defaults to
#             None.
#     Returns:
#         TxParams: a transaction parameters dictionary
#     """
#     nonce = max(self.last_nonce, self.w3.eth.get_transaction_count(self.wallet))
#     params: TxParams = {
#         'from': self.wallet,
#         'value': value,
#         'gas': gas,
#         'nonce': nonce,
#     }
#     if gas_price:
#         params['gasPrice'] = gas_price
#     return params

# def get_bnb_balance(self) -> Decimal:
#         """Get the balance of the account in native coin (BNB).
#         Returns:
#             Decimal: the balance in BNB units (=ether)
#         """
#         return Decimal(self.w3.eth.get_balance(self.wallet)) / Decimal(10 ** 18)

from typing import Dict, List, NamedTuple, Optional, Set, Tuple
import time

from pathlib import Path
from decimal import Decimal
from toolz.functoolz import return_none
import web3


from web3.contract import Contract, ContractFunction

from web3 import Web3
from web3.types import ChecksumAddress, HexBytes, Nonce, TxParams, TxReceipt, Wei
from web3.exceptions import ABIFunctionNotFound, ContractLogicError

# from loguru import logger
GAS_LIMIT_FAILSAFE = Wei(2000000)


# @dataclass
# class ConfigSecrets:
#     """Class to hold secrets from the config file."""

#     telegram_token: str
#     admin_chat_id: int
#     rpc_auth_user: Optional[str] = None
#     rpc_auth_password: Optional[str] = None
#     _pk: str = field(repr=False, default='')


RPC = "https://speedy-nodes-nyc.moralis.io/a7c60dc1e16277c3fad979a0/bsc/mainnet"

# RPC = "https://bsc-dataseed.binance.org/"

class Robo:
    def __init__(self,  wallet: ChecksumAddress, _pk) -> None:
        
        rpc = RPC
        self.w3 = Web3(Web3.HTTPProvider(rpc))
        self.wallet = wallet

        #pq é global?
        self.max_approval_hex = f"0x{64 * 'f'}"
        self.max_approval_int = int(self.max_approval_hex, 16)
        self.max_approval_check_hex = f"0x{15 * '0'}{49 * 'f'}"
        self.max_approval_check_int = int(self.max_approval_check_hex, 16)

        self.approved: Set[str] = set() 

        self.addr ={
                "wbnb": Web3.toChecksumAddress('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'),
                "busd": Web3.toChecksumAddress('0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56'),
                "router_v2" :Web3.toChecksumAddress('0x10ed43c718714eb63d5aa57b78b54704e256024e')
        }

        self.contracts ={
            # "wbnb": self.get_token_contract(token_address=Web3.toChecksumAddress('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c')),
            "wbnb": self.get_contract(Web3.toChecksumAddress('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'), "./abi/wbnb.abi"),
            "busd": self.get_token_contract(token_address=Web3.toChecksumAddress('0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56')),
            "factory_v2": self.get_contract(Web3.toChecksumAddress('0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73'), "./abi/alguma_lib_factory_cake.abi"), #alguma lib
            "router_v2": self.get_contract(Web3.toChecksumAddress('0x10ed43c718714eb63d5aa57b78b54704e256024e'), "./abi/pancake_v2.abi") #pancake
        }

        self.lp_cache: Dict[Tuple[str, str], ChecksumAddress] = {}
        self.supported_base_tokens: List[ChecksumAddress] = [self.addr["wbnb"], self.addr["busd"]]


        self.last_nonce = self.w3.eth.get_transaction_count(self.wallet)
        self.secrets = {"_pk":_pk }


    def update_nonce(self):
        """Update the stored account nonce if it's higher than the existing cached version."""
        self.last_nonce = max(self.last_nonce, self.w3.eth.get_transaction_count(self.wallet))

    def get_contract(self, token_address, str_path):
        with Path(str_path).open('r') as f:
            abi = f.read()
        return self.w3.eth.contract(address=token_address, abi=abi)
        


    def get_token_balance(self, token_address: ChecksumAddress) -> Decimal:
            """The size of the user's position for a given token contract.
            Args:
                token_address (ChecksumAddress): address of the token contract
            Returns:
                Decimal: the number of tokens owned by the user's wallet (human-readable, decimal)
            """
            token_contract = self.get_token_contract(token_address)
            try:
                balance = Decimal(token_contract.functions.balanceOf(self.wallet).call()) / Decimal(
                    10 ** self.get_token_decimals(token_address=token_address)
                )
            except (ABIFunctionNotFound, ContractLogicError):
                print(f'Contract {token_address} does not have function "balanceOf"')
                return Decimal(0)
            return balance

    def get_token_contract(self, token_address: ChecksumAddress) -> Contract:
        """Get a contract instance for a given token address.
        Args:
            token_address (ChecksumAddress): address of the token
        Returns:
            Contract: a web3 contract instance that can be used to perform calls and transactions
        """
        with Path('./abi/bep20.abi').open('r') as f:
            abi = f.read()
        return self.w3.eth.contract(address=token_address, abi=abi)


    def get_token_decimals(self, token_address: ChecksumAddress) -> int:
        """Get the number of decimals used by the token for human representation.
        Args:
            token_address (ChecksumAddress): the address of the token
        Returns:
            int: the number of decimals
        """
        token_contract = self.get_token_contract(token_address=token_address)
        decimals = token_contract.functions.decimals().call()
        return int(decimals)

    def get_base_token_price_adrees(self, token_address: ChecksumAddress) -> Decimal:
        """Get the price in BNB per token for a given base token of some LP.
        This is a simplified version of the token price function that doesn't support non-BNB pairs.
        Args:
            token (Contract): contract instance for the base token
        Returns:
            Decimal: the price in BNB per token for the given base token.
        """
        token_contract = self.get_token_contract(token_address=token_address)

        if token_contract.address == self.addr["wbnb"]:  # special case for BNB, price is always 1.
            return Decimal(1)
        lp = self.find_lp_address(token_contract.address, self.addr["wbnb"])
        if not lp:
            return Decimal(0)
        token_decimals = self.get_token_decimals(token_contract.address)
        bnb_amount = Decimal(self.contracts["wbnb"].functions.balanceOf(lp).call())
        # bnb_amount = Decimal(self.contracts["busd"].functions.balanceOf(lp).call())

        token_amount = Decimal(token_contract.functions.balanceOf(lp).call()) * Decimal(10 ** (18 - token_decimals))
        r_token_zero = token_amount == 0
        if r_token_zero:
            return 0
        else:
            return bnb_amount / token_amount

    def find_lp_address(self, token_address: ChecksumAddress,
             base_token_address: ChecksumAddress) -> Optional[ChecksumAddress]:
        """Get the LP address for a given pair of tokens, if it exists.
        The function will cache its results in case an LP was found, but not cache anything otherwise.
        Args:
            token_address (ChecksumAddress): address of the token to buy/sell
            base_token_address (ChecksumAddress): address of the base token of the pair
        Returns:
            Optional[ChecksumAddress]: the address of the LP if it exists, ``None`` otherwise.
        """
        cached = self.lp_cache.get((str(token_address), str(base_token_address)))
        if cached is not None:
            return cached
        pair = self.contracts["factory_v2"].functions.getPair(token_address, base_token_address).call()
        if pair == '0x' + 40 * '0':  # not found, don't cache
            return None
        checksum_pair = Web3.toChecksumAddress(pair)
        self.lp_cache[(str(token_address), str(base_token_address))] = checksum_pair
        return checksum_pair

    def get_bnb_price(self) -> Decimal:
        """Get the price of the native token in USD/BNB.
        Returns:
            Decimal: the price of the chain's native token in USD per BNB.
        """
        lp = self.find_lp_address(token_address=self.addr["busd"], base_token_address=self.addr["wbnb"])
        if not lp:
            return Decimal(0)
        bnb_amount = Decimal(self.contracts["wbnb"].functions.balanceOf(lp).call())
        busd_amount = Decimal(self.contracts["busd"].functions.balanceOf(lp).call())
        return busd_amount / bnb_amount

    def buy_tokens(
        self,
        token_address: ChecksumAddress,
        amount_bnb: Wei,
        slippage_percent: Decimal,
        gas_price: Optional[str],
    ) -> Tuple[bool, Decimal, str]:
        """Buy tokens with a given amount of BNB, enforcing a maximum slippage, and using the best swap path.
        Args:
            token_address (ChecksumAddress): address of the token to buy
            amount_bnb (Wei): amount of BNB used for buying
            slippage_percent (Decimal): maximum allowable slippage due to token tax, price action and price impact
            gas_price (Optional[str]): optional gas price to use, or use the network's default suggested price if None.
        Returns:
            Tuple[bool, Decimal, str]: a tuple containing:
                - bool: wether the buy was successful
                - Decimal: the amount of tokens received (human-readable, decimal)
                - str: the transaction hash if transaction was mined, or an error message
        """
        balance_bnb = self.w3.eth.get_balance(self.wallet)
        if amount_bnb > balance_bnb - Wei(2000000000000000):  # leave 0.002 BNB for future gas fees
            print('Not enough BNB balance')
            return False, Decimal(0), 'Not enough BNB balance'

                
        def calcula_gaz():
            final_gas_price = self.w3.eth.gas_price
            if gas_price is not None and gas_price.startswith('+'):
                offset = Web3.toWei(Decimal(gas_price) * Decimal(10 ** 9), unit='wei')
                final_gas_price = Wei(final_gas_price + offset)
            elif gas_price is not None:
                final_gas_price = Web3.toWei(gas_price, unit='wei')
            print(f'o gaz ficou de {final_gas_price}')
            return final_gas_price

        final_gas_price = calcula_gaz()

        receipt = None
        for soma_slip in range(0,8,2):
            try:
                best_path, predicted_out = self.get_best_swap_path(
                    token_address=token_address, amount_in=amount_bnb, sell=False)
            except ValueError as e:
                print(e)
                return (False, Decimal(0),'No compatible LP was found',)

            print(f'a quantidade preditiva {predicted_out}')
            
            slip_inicial = slippage_percent
            def det_predicted(pre):
                r_pre_0 = pre == 0
                if r_pre_0:
                    v_token = self.get_base_token_price_adrees(token_address)
                    r_ve_token_0 = v_token == 0
                    if not r_ve_token_0:
                        a= amount_bnb/v_token
                        saida = Web3.toWei(int(a), unit='wei')
                        return saida
                    else:
                        return pre
                else:
                    return pre
            
            slip_inicial += soma_slip

            predicted_out = det_predicted(predicted_out)
            slippage_ratio = (Decimal(100) - slip_inicial) / Decimal(100)
            min_output_tokens = Web3.toWei(slippage_ratio * predicted_out, unit='wei')
            print(f'A menor quantidade {min_output_tokens}')
            receipt = self.buy_tokens_with_params(
                path=best_path, amount_bnb=amount_bnb, min_output_tokens=min_output_tokens, gas_price=final_gas_price
            )
            if receipt is None:
                print(f'Can\'t get gas estimate, check if slippage is set correctly (currently {slip_inicial}%)')
            else:
                break # termina o looping 

        
        # se mesmo tentando um monte nao tem uma recipt
        if receipt is None:
            print('Can\'t get gas estimate')
            return (
                False,
                Decimal(0),
                f'Can\'t get gas estimate, check if slippage is set correctly (currently {slippage_percent}%)',
            )


        txhash = Web3.toHex(primitive=receipt["transactionHash"])
        if receipt['status'] == 0:  # fail
            print(f'Buy transaction failed at tx {txhash}')
            return False, Decimal(0), txhash
        amount_out = Decimal(0)
        logs = self.get_token_contract(token_address=token_address).events.Transfer().processReceipt(receipt)
        for log in reversed(logs):  # only get last withdrawal call
            if log['address'] != token_address:
                continue
            if log['args']['to'] != self.wallet:
                continue
            amount_out = Decimal(log['args']['value']) / Decimal(10 ** self.get_token_decimals(token_address))
            break
        print(f'Buy transaction succeeded at tx {txhash}')
        return True, amount_out, txhash
    
    def buy_tokens_with_params(
        self,
        path: List[ChecksumAddress],
        amount_bnb: Wei,
        min_output_tokens: Wei,
        gas_price: Wei,
    ) -> Optional[TxReceipt]:
        """Craft and submit a transaction to buy tokens through a given swapping path, enforcing a minimum output.
        The function will estimate the gas needed for the transaction and use 120% of that as the gas limit.
        Args:
            path (List[ChecksumAddress]): path to use for swapping (needs to start with WBNB address)
            amount_bnb (Wei): amount of BNB to use for buying, in Wei
            min_output_tokens (Wei): minimum output allowed, in Wei, normally calculated from slippage
            gas_price (Wei): gas price to use, in Wei
        Returns:
            Optional[TxReceipt]: a transaction receipt if transaction was mined, ``None`` otherwise.
        """
        print(f'o minimo de tokens {min_output_tokens}')
        func = self.contracts["router_v2"].functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
            min_output_tokens, path, self.wallet, self.deadline(60)
        )
        try:
            gas_limit = Wei(int(Decimal(func.estimateGas({'from': self.wallet, 'value': amount_bnb})) * Decimal(1.2)))
        except Exception as e:
            print(f'Can\'t get gas estimate, cancelling transaction: {e}')
            return None
        if gas_limit > GAS_LIMIT_FAILSAFE:
            gas_limit = GAS_LIMIT_FAILSAFE
        params = self.get_tx_params(value=amount_bnb, gas=gas_limit, gas_price=gas_price)
        tx = self.build_and_send_tx(func=func, tx_params=params)
        return self.w3.eth.wait_for_transaction_receipt(tx, timeout=60)

    def build_and_send_tx(self, func: ContractFunction, tx_params: Optional[TxParams] = None) -> HexBytes:
        """Build a transaction from a contract's function call instance and transaction parameters, then submit it.
        Args:
            func (ContractFunction): a function call instance from a contract
            tx_params (Optional[TxParams], optional): optional transaction parameters. Defaults to None.
        Returns:
            HexBytes: the transaction hash
        """
        if not tx_params:
            tx_params = self.get_tx_params()
        transaction = func.buildTransaction(tx_params)
        signed_tx = self.w3.eth.account.sign_transaction(transaction, private_key=self.secrets["_pk"])
        try:
            return self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        finally:
            self.last_nonce = Nonce(tx_params["nonce"] + 1)


    def get_tx_params(self, value: Wei = Wei(0), gas: Wei = Wei(100000), gas_price: Optional[Wei] = None) -> TxParams:
        """Build a transaction parameters dictionary from the provied parameters.
        The default gas limit of 100k is enough for a normal approval transaction.
        Args:
            value (Wei, optional): value (BNB) of the transaction, in Wei. Defaults to Wei(0).
            gas (Wei, optional): gas limit to use, in Wei. Defaults to Wei(100000).
            gas_price (Optional[Wei], optional): gas price to use, in Wei, or None for network default. Defaults to
                None.
        Returns:
            TxParams: a transaction parameters dictionary
        """
        nonce = max(self.last_nonce, self.w3.eth.get_transaction_count(self.wallet))
        params: TxParams = {
            'from': self.wallet,
            'value': value,
            'gas': gas,
            'nonce': nonce,
        }
        if gas_price:
            params['gasPrice'] = gas_price
        return params

    def deadline(self, seconds: int = 60) -> int:
        """Get the unix timestamp for a point in time x seconds in the future.
        Args:
            seconds (int, optional): how many seconds in the future. Defaults to 60.
        Returns:
            int: a unix timestamp x seconds in the future
        """
        return int(time.time()) + seconds


    def get_best_swap_path(
        self, token_address: ChecksumAddress, amount_in: Wei, sell: bool
    ) -> Tuple[List[ChecksumAddress], Wei]:
        """Find the most advantageous path to swap from a token to BNB, or from BNB to a token.
        The algorithm tries to estimate the direct output from BNB to token swap (or vice-versa), or to first swap to
        another supported token that has a pair for the token of interest, and then swap from that token to BNB/token
        (multihop). The path that gives the largest output will be returned.
        Args:
            token_address (ChecksumAddress): address of the token to buy/sell
            amount_in (Wei): input amount, in Wei, representing either the number of BNB to use for buying, or number
                of tokens to sell.
            sell (bool): wether we are trying to sell tokens (``True``), or buy tokens (``False``).
        Raises:
            ValueError: if one of the tokens in the path doesn't provide a liquidity pool, thus making this path invalid
        Returns:
            Tuple[List[ChecksumAddress], Wei]: a tuple containing:
                - List[ChecksumAddress]: the best path to use for maximum output
                - Wei: the estimated output for the best path (doesn't take into account any token fees, but takes into
                    account the AMM fee)
        """
        if sell:
            paths = [[token_address, self.addr["wbnb"]]]
            for base_token_address in [bt for bt in self.supported_base_tokens if bt != self.addr["wbnb"]]:
                paths.append([token_address, base_token_address, self.addr["wbnb"]])
        else:
            paths = [[self.addr["wbnb"], token_address]]
            for base_token_address in [bt for bt in self.supported_base_tokens if bt != self.addr["wbnb"]]:
                paths.append([self.addr["wbnb"], base_token_address, token_address])
        amounts_out: List[Wei] = []
        valid_paths: List[List[ChecksumAddress]] = []
        for path in paths:
            try:
                amount_out = self.contracts["router_v2"].functions.getAmountsOut(amount_in, path).call()[-1]
            except ContractLogicError:  # invalid pair
                continue
            amounts_out.append(amount_out)
            valid_paths.append(path)

        if not valid_paths:
            raise ValueError('No valid pair was found')
        argmax = max(range(len(amounts_out)), key=lambda i: amounts_out[i])
        return valid_paths[argmax], amounts_out[argmax]


    ############################## checcar se foi aprovado
    def is_approved(self, token_address: ChecksumAddress) -> bool:
        """Check wether the pancakeswap router is allowed to spend a given token.
        Args:
            token_address (ChecksumAddress): the token address
        Returns:
            bool: wether the token was approved
        """
        if str(token_address) in self.approved:
            return True
        token_contract = self.get_token_contract(token_address=token_address)
        amount = token_contract.functions.allowance(self.wallet, self.addr["router_v2"]).call()
        approved = amount >= self.max_approval_check_int
        if approved:
            self.approved.add(str(token_address))
        return approved


    def get_token_symbol(self, token_address: ChecksumAddress) -> str:
        """Get the symbol for a given token.
        Args:
            token_address (ChecksumAddress): the address of the token
        Returns:
            str: the symbol for that token
        """
        token_contract = self.get_token_contract(token_address=token_address)
        symbol = token_contract.functions.symbol().call()
        return symbol


    def approve(self, token_address: ChecksumAddress, max_approval: Optional[int] = None) -> bool:
        """Set the allowance of the pancakeswap router to spend a given token.
        Args:
            token_address (ChecksumAddress): the token to approve
            max_approval (Optional[int], optional): an optional maximum amount to give as allowance. Will use the
                maximum uint256 bound (0xffff....) if set to ``None``. Defaults to None.
        Returns:
            bool: wether the approval transaction succeeded
        """
        max_approval = self.max_approval_int if not max_approval else max_approval
        token_contract = self.get_token_contract(token_address=token_address)
        func = token_contract.functions.approve(self.addr["router_v2"], max_approval)
        print(f'Approving {self.get_token_symbol(token_address=token_address)} - {token_address}...')
        try:
            gas_limit = Wei(int(Decimal(func.estimateGas({'from': self.wallet, 'value': Wei(0)})) * Decimal(1.2)))
        except Exception:
            gas_limit = Wei(100000)
        tx_params = self.get_tx_params(
            gas=gas_limit,
            gas_price=Wei(self.w3.eth.gas_price + Web3.toWei(Decimal('0.1') * Decimal(10 ** 9), unit='wei')),
        )
        tx = self.build_and_send_tx(func, tx_params=tx_params)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx, timeout=6000)
        if receipt['status'] == 0:  # fail
            print(f'Approval call failed at tx {Web3.toHex(primitive=receipt["transactionHash"])}')
            return False
        self.approved.add(str(token_address))
        time.sleep(5)  # let tx propagate
        print('Approved wallet for trading.')
        return True


    def sell_tokens(
        self, token_address: ChecksumAddress, amount_tokens: Wei, slippage_percent: Decimal, gas_price: Optional[str]
    ) -> Tuple[bool, Decimal, str]:
        """Sell a given amount of tokens, enforcing a maximum slippage, and using the best swap path.
        Args:
            token_address (ChecksumAddress): token to be sold
            amount_tokens (Wei): amount of tokens to sell, in Wei
            slippage_percent (Decimal): maximum allowable slippage due to token tax, price action and price impact
            gas_price (Optional[str]): optional gas price to use, or use the network's default suggested price if None.
        Returns:
            Tuple[bool, Decimal, str]: a tuple containing:
                - bool: wether the sell was successful
                - Decimal: the amount of BNB received (human-readable, decimal)
                - str: the transaction hash if transaction was mined, or an error message
        """
        balance_tokens = self.get_token_balance_wei(token_address=token_address)
        amount_tokens = min(amount_tokens, balance_tokens)  # partially fill order if possible
        slippage_ratio = (Decimal(100) - slippage_percent) / Decimal(100)
        final_gas_price = self.w3.eth.gas_price
        if gas_price is not None and gas_price.startswith('+'):
            offset = Web3.toWei(Decimal(gas_price) * Decimal(10 ** 9), unit='wei')
            final_gas_price = Wei(final_gas_price + offset)
        elif gas_price is not None:
            final_gas_price = Web3.toWei(gas_price, unit='wei')
        try:
            best_path, predicted_out = self.get_best_swap_path(
                token_address=token_address, amount_in=amount_tokens, sell=True
            )
        except ValueError as e:
            print(e)
            return (
                False,
                Decimal(0),
                'No compatible LP was found',
            )
        min_output_bnb = Web3.toWei(slippage_ratio * predicted_out, unit='wei')
        receipt = self.sell_tokens_with_params(
            path=best_path, amount_tokens=amount_tokens, min_output_bnb=min_output_bnb, gas_price=final_gas_price
        )
        if receipt is None:
            print('Can\'t get gas estimate')
            return (
                False,
                Decimal(0),
                f'Can\'t get gas estimate, check if slippage is set correctly (currently {slippage_percent}%)',
            )
        txhash = Web3.toHex(primitive=receipt["transactionHash"])
        if receipt['status'] == 0:  # fail
            print(f'Sell transaction failed at tx {txhash}')
            return False, Decimal(0), txhash
        amount_out = Decimal(0)
        logs = self.contracts["wbnb"].events.Withdrawal().processReceipt(receipt)
        for log in reversed(logs):  # only get last withdrawal call
            if log['address'] != self.addr["wbnb"]:
                continue
            if log['args']['src'] != self.addr["router_v2"]:
                continue
            amount_out = Decimal(Web3.fromWei(log['args']['wad'], unit='ether'))
            break
        print(f'Sell transaction succeeded at tx {txhash}')
        return True, amount_out, txhash

    def get_token_balance_wei(self, token_address: ChecksumAddress) -> Wei:
        """The size of the user's position for a given token contract, in Wei units.
        Args:
            token_address (ChecksumAddress): address of the token contract
        Returns:
            Wei: the number of tokens owned by the user's wallet, in Wei
        """
        token_contract = self.get_token_contract(token_address)
        try:
            return Wei(token_contract.functions.balanceOf(self.wallet).call())
        except (ABIFunctionNotFound, ContractLogicError):
            print(f'Contract {token_address} does not have function "balanceOf"')
        return Wei

    def sell_tokens_with_params(
        self,
        path: List[ChecksumAddress],
        amount_tokens: Wei,
        min_output_bnb: Wei,
        gas_price: Wei,
    ) -> Optional[TxReceipt]:
        """Craft and submit a transaction to sell tokens through a given swapping path, enforcing a minimum output.
        The function will estimate the gas needed for the transaction and use 120% of that as the gas limit.
        Args:
            path (List[ChecksumAddress]): path to use for swapping (needs to start with the token address)
            amount_tokens (Wei): amount of tokens to sell, in Wei
            min_output_bnb (Wei): minimum output allowed, in Wei, normally calculated from slippage
            gas_price (Wei): gas price to use, in Wei
        Returns:
            Optional[TxReceipt]: a transaction receipt if transaction was mined, ``None`` otherwise.
        """
        func = self.contracts["router_v2"].functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
            amount_tokens, min_output_bnb, path, self.wallet, self.deadline(60)
        )
        try:
            gas_limit = Wei(int(Decimal(func.estimateGas({'from': self.wallet, 'value': Wei(0)})) * Decimal(1.2)))
        except Exception as e:
            print(f'Can\'t get gas estimate, cancelling transaction: {e}')
            return None
        if gas_limit > GAS_LIMIT_FAILSAFE:
            gas_limit = GAS_LIMIT_FAILSAFE
        params = self.get_tx_params(value=Wei(0), gas=gas_limit, gas_price=gas_price)
        tx = self.build_and_send_tx(func=func, tx_params=params)
        return self.w3.eth.wait_for_transaction_receipt(tx, timeout=60)


# funções implementadas

def bnb_to_wei(valor_bnb, token_decimals=18):
    saida = Wei( int(valor_bnb* 10**token_decimals) )
    return saida

def compra(CONTRATO, carteira, _pk, qnt_bnb_da_compra, fast=False):
    # CONTRATO =   "0x04260673729c5f2b9894a467736f3d85f8d34fc8" # "0x50332bdca94673f33401776365b66cc4e81ac81d"


    saida = (False, 0, "error")
    token_str = Web3.toChecksumAddress(CONTRATO)
    token_carteira = Web3.toChecksumAddress(carteira)
    r = Robo(token_carteira, _pk)

    qnt_decimal = r.get_token_decimals(token_str)
    print(qnt_decimal)
    valor_compra_wei = bnb_to_wei(qnt_bnb_da_compra, qnt_decimal)
    print("Quanto é o bnb to wei: ",   valor_compra_wei )
    
    if fast:
        saida = r.buy_tokens( token_str , Wei(valor_compra_wei), Decimal(10), "+25") #FAST
    else:
        saida = r.buy_tokens( token_str , Wei(valor_compra_wei), Decimal(1), None) #FAST
    print(saida)
    return saida
    # r.buy_tokens( token_str , Wei(valor_compra_wei), Decimal(1), None) # 1%




def helper_function():
    pass
    #     amount_bnb: Wei,
    #     slippage_percent: Decimal,
    #     gas_price: Optional[str],
    # ) -> Tuple[bool, Decimal, str]:


    # print(r.get_token_decimals(token_str))
    # print("qntindade de balance do token eu tenho :", r.get_token_balance(token_str))
    # token_bnn_price = r.get_base_token_price_adrees(token_str)
    # bnb_price = r.get_bnb_price()
    # print("Qual é preco base dele em bnb:  ", token_bnn_price)
    # print("Quanto é o preco do bnb : ",bnb_price )
    # print("Quanto é o preco do busd : ",  bnb_price * token_bnn_price )

def aprova_venda(CONTRATO, carteira, _pk):
    token_str = Web3.toChecksumAddress(CONTRATO)
    token_carteira = Web3.toChecksumAddress(carteira)
    r = Robo(token_carteira, _pk)
    r.approve(token_str)
    r_aprovado =r.is_approved(token_str)
    return r_aprovado




def venda(CONTRATO, carteira, _pk, valor_venda_token, fast= False):
    # CONTRATO = "0x0ccd575bf9378c06f6dca82f8122f570769f00c2" #king # "0x50332bdca94673f33401776365b66cc4e81ac81d"
    token_str = Web3.toChecksumAddress(CONTRATO)
    token_carteira = Web3.toChecksumAddress(carteira)
    r = Robo(token_carteira, _pk)

    r_aprovado =r.is_approved(token_str)
    
    print(r_aprovado)
    qnt_decimal = r.get_token_decimals(token_str)
    valor_venda = bnb_to_wei(valor_venda_token, qnt_decimal)

    saida = (False, 0, "error")
    if not r_aprovado:
        r.approve(token_str)
        r_aprovado_novo = r.is_approved(token_str)
        if r_aprovado_novo:
            if fast:
                saida = r.sell_tokens( token_str , Wei(valor_venda), Decimal(18), "+12") #FAST
            else:
                saida = r.sell_tokens( token_str , Wei(valor_venda), Decimal(1), None) #FAST

    else:
        if fast:
            saida = r.sell_tokens( token_str , Wei(valor_venda), Decimal(18), "+12") #FAST
        else:
            saida = r.sell_tokens( token_str , Wei(valor_venda), Decimal(1), None) #FAST

    
    print(saida)
    return saida
    # fast
    # r.sell_tokens( token_str , Wei(valor_venda), Decimal(20), "+6") #FAST


def get_valor_moeda(CONTRATO, carteira, _pk):
    token_str = Web3.toChecksumAddress(CONTRATO)
    token_carteira = Web3.toChecksumAddress(carteira)
    r = Robo(token_carteira, _pk)
    # print(r.find_lp_address(token_str, r.addr["busd"]))
    # print(r.find_lp_address(token_str, r.addr["wbnb"]))
    bnb_price_in_usd = r.get_bnb_price()
    token_price_in_bnb = r.get_base_token_price_adrees(token_str)
    return bnb_price_in_usd * token_price_in_bnb

def verifica_path(contrato, carteira, _pk, qnt_bnb_da_compra):
    token_str = Web3.toChecksumAddress(contrato)
    token_carteira = Web3.toChecksumAddress(carteira)
    r = Robo(token_carteira, _pk)

    token_address = token_str
    valor_compra_wei = bnb_to_wei(qnt_bnb_da_compra)
    amount_bnb = valor_compra_wei

    try:
        best_path, predicted_out = r.get_best_swap_path(
                    token_address=token_address, amount_in=amount_bnb, sell=False
                )

        print("best path :", best_path)
    except:
        
        print("best path :", [])
        return []

    return best_path

def tenta_aprova(CONTRATO, carteira, _pk):

    token_str = Web3.toChecksumAddress(CONTRATO)
    token_carteira = Web3.toChecksumAddress(carteira)
    r = Robo(token_carteira, _pk)
    r_aprovado = r.is_approved(token_str)

    if not r_aprovado:
        r.approve(token_str)
        r_aprovado_novo = r.is_approved(token_str)
        return r_aprovado_novo
    else:
        return r_aprovado

    



def tenta_info(contrato, carteira, _pk, bnb_amount):
    rpc = RPC
    w3 = Web3(Web3.HTTPProvider(rpc))
    saida = (False, 0, "error")
    valor_moeda = get_valor_moeda(contrato, carteira, _pk)
    blk = w3.eth.block_number
    best_path = verifica_path(contrato, carteira, _pk, bnb_amount)
    return blk, best_path, valor_moeda


def tenta_get_wallet_token(contrato, carteira, _pk):
    saida = (False, 0, "error")
    token_str = Web3.toChecksumAddress(contrato)
    token_carteira = Web3.toChecksumAddress(carteira)
    r = Robo(token_carteira, _pk)
    saida = r.get_token_balance(token_str)
    return saida

def tenta_get_bnb_usd(contrato, carteira, _pk):
    token_str = Web3.toChecksumAddress(contrato)
    token_carteira = Web3.toChecksumAddress(carteira)
    r = Robo(token_carteira, _pk)
    saida = r.get_bnb_price()
    return saida

def tenta_uma_compra(contrato, carteira, _pk, bnb_amount = 0.13, fast=False):
    rpc = RPC
    w3 = Web3(Web3.HTTPProvider(rpc))
    r_not_realizou_compra =  True
    saida = (False, 0, "error")
    saida = compra(contrato, carteira, _pk, bnb_amount, fast) # ta ativado a compra (JESUS!!!)
    return saida
    


def tenta_ate_comprar_preco_determinado(contrato, carteira, _pk):
    rpc = RPC
    w3 = Web3(Web3.HTTPProvider(rpc))
    r_not_realizou_compra =  True
    saida = (False, 0, "error")

    while r_not_realizou_compra:
        valor_moeda = get_valor_moeda(contrato, carteira, _pk)
        r_tem_liquidez = valor_moeda >= 0.0001
        print(f"{w3.eth.block_number}: ***************************")
        print(f"Tentando compra a moeda :{contrato}")
        # print(valor_moeda)
        # print( r_tem_liquidez)

        if(r_tem_liquidez):
            
            saida = compra(contrato, carteira, _pk, 0.13) # ta ativado a compra (JESUS!!!)

            
            r_not_realizou_compra = False
            print(f"{time.ctime()}; comprouu")
            print(f"{saida}")
            r_saida_compro = saida[0] == True
            print(r_saida_compro)
            break

        else:
            print(f"{time.ctime()}; ainda não realizou nenhuma compra {saida};")
            print(f"valor da moeda:{valor_moeda}")
            print("------------------------"*3)
            # r_not_realizou_compra = False
            

        time.sleep(1)      



def tenta_ate_comprar_caminho_apareceu(contrato, carteira, _pk, bnb_amount = 0.13, fast=False):

    rpc = RPC
    w3 = Web3(Web3.HTTPProvider(rpc))
    r_not_realizou_compra =  True
    saida = (False, 0, "error")

    while r_not_realizou_compra:
        try:
            time.sleep(0.8)
            print(f"{w3.eth.block_number}: ***************************")
            print(f"Tentando compra a moeda :{contrato}")
            valor_moeda = get_valor_moeda(contrato, carteira, _pk)
            # r_tem_liquidez = valor_moeda >= 0.0001
            best_path = verifica_path(contrato, carteira, _pk, bnb_amount)
            r_tem_liquidez = len(best_path) != 0 
            print(f'o melhor caminho :{best_path}, tem o token no valor {valor_moeda}')

            # print(valor_moeda)
            # print( r_tem_liquidez)

            if(r_tem_liquidez):
                
                saida = compra(contrato, carteira, _pk, bnb_amount, fast) # ta ativado a compra (JESUS!!!)

                r_not_realizou_compra = False
                print(f"{time.ctime()}")
                print(f"{saida}")
                r_saida_compro = saida[0] == True
                print(r_saida_compro)
                r_not_realizou_compra = not saida[0]

            else:
                print(f"{time.ctime()}; ainda não realizou nenhuma compra {saida};")
                print(f"valor da moeda:{valor_moeda}")
                print("------------------------"*3)

            
            time.sleep(0.8) 
                # r_not_realizou_compra = False
        except:
            print("deu erro em algo")
            time.sleep(0.8)    
    
    return saida
           

def tenta_bloco_number(contrato, carteira):
    rpc = RPC
    w3 = Web3(Web3.HTTPProvider(rpc))
    while True:
        print(f"{12477615- w3.eth.block_number}: ***************************")
        time.sleep(1)    

