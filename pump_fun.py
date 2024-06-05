import struct
from solana.transaction import AccountMeta
from spl.token.instructions import create_associated_token_account, get_associated_token_address
from solders.pubkey import Pubkey  #type: ignore
from solders.instruction import Instruction  #type: ignore
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price  #type: ignore
from solders.transaction import VersionedTransaction  #type: ignore
from solders.message import MessageV0  #type: ignore
from constants import *
from config import *
from solana.rpc.types import TokenAccountOpts
from utils import get_coin_data, get_token_balance, confirm_txn
from solana.rpc.types import TxOpts
from solders.keypair import Keypair
from solana.rpc.api import Client


class PumpFun:
    private_key: str
    key_pair: Keypair
    client: Client

    def __init__(self, private_key: str) -> None:
        self.private_key = private_key
        self.key_pair = Keypair.from_base58_string(self.private_key)
        self.client = Client(RPC)
        print(f'wallet address: {self.key_pair.pubkey()}')

    def trade(self,
              token_addr: str,
              sol_in: float = SOL_IN,
              sell_ratio: float = SELL_RATIO,
              slippage=SLIPPAGE,
              retries: int = RETRIES):
        buy_succeed = False
        sell_succeed = False
        buy_retries = retries
        while buy_retries > 0:
            buy_retries -= 1
            succeed = self.buy(mint_str=token_addr,
                               sol_in=sol_in,
                               slippage_decimal=slippage)
            if succeed == True:
                buy_succeed = True
                break
        if buy_succeed == False:
            print(f'failed to buy {token_addr}, skip selling')

        sell_retries = retries
        while sell_retries > 0:
            sell_retries -= 1
            succeed = self.sell(mint_str=token_addr,
                                sell_ratio=sell_ratio,
                                slippage_decimal=slippage)
            if succeed == True:
                sell_succeed = True
                break
        if sell_succeed == False:
            print(f'failed to sell {token_addr}')

    def buy(self, mint_str, sol_in=0.01, slippage_decimal=.02):
        try:
            # Get coin data
            coin_data = get_coin_data(mint_str)

            if not coin_data:
                print("Failed to retrieve coin data...")
                return None

            owner = self.key_pair.pubkey()
            mint = Pubkey.from_string(mint_str)
            token_account, token_account_instructions = None, None

            # Attempt to retrieve token account, otherwise create associated token account
            try:
                account_data = self.client.get_token_accounts_by_owner(
                    owner, TokenAccountOpts(mint))
                token_account = account_data.value[0].pubkey
                token_account_instructions = None
            except:
                token_account = get_associated_token_address(owner, mint)
                token_account_instructions = create_associated_token_account(
                    owner, owner, mint)

            # Calculate tokens out
            virtual_sol_reserves = coin_data['virtual_sol_reserves']
            virtual_token_reserves = coin_data['virtual_token_reserves']
            sol_in_lamports = sol_in * LAMPORTS_PER_SOL
            token_out = int(sol_in_lamports * virtual_token_reserves /
                            virtual_sol_reserves)

            # Calculate max_sol_cost and amount
            sol_in_with_slippage = sol_in * (1 + slippage_decimal)
            max_sol_cost = int(sol_in_with_slippage * LAMPORTS_PER_SOL)

            # Define account keys required for the swap
            MINT = Pubkey.from_string(coin_data['mint'])
            BONDING_CURVE = Pubkey.from_string(coin_data['bonding_curve'])
            ASSOCIATED_BONDING_CURVE = Pubkey.from_string(
                coin_data['associated_bonding_curve'])
            ASSOCIATED_USER = token_account
            USER = owner

            # Build account key list
            keys = [
                AccountMeta(pubkey=GLOBAL, is_signer=False, is_writable=False),
                AccountMeta(pubkey=FEE_RECIPIENT,
                            is_signer=False,
                            is_writable=True),
                AccountMeta(pubkey=MINT, is_signer=False, is_writable=False),
                AccountMeta(pubkey=BONDING_CURVE,
                            is_signer=False,
                            is_writable=True),
                AccountMeta(pubkey=ASSOCIATED_BONDING_CURVE,
                            is_signer=False,
                            is_writable=True),
                AccountMeta(pubkey=ASSOCIATED_USER,
                            is_signer=False,
                            is_writable=True),
                AccountMeta(pubkey=USER, is_signer=True, is_writable=True),
                AccountMeta(pubkey=SYSTEM_PROGRAM,
                            is_signer=False,
                            is_writable=False),
                AccountMeta(pubkey=TOKEN_PROGRAM,
                            is_signer=False,
                            is_writable=False),
                AccountMeta(pubkey=RENT, is_signer=False, is_writable=False),
                AccountMeta(pubkey=PUMP_FUN_ACCOUNT,
                            is_signer=False,
                            is_writable=False),
                AccountMeta(pubkey=PUMP_FUN_PROGRAM,
                            is_signer=False,
                            is_writable=False)
            ]

            # Define integer values
            buy = 16927863322537952870
            integers = [buy, token_out, max_sol_cost]

            # Pack integers into binary segments
            binary_segments = [
                struct.pack('<Q', integer) for integer in integers
            ]
            data = b''.join(binary_segments)
            swap_instruction = Instruction(PUMP_FUN_PROGRAM, data, keys)

            # Create transaction instructions
            instructions = []
            instructions.append(set_compute_unit_price(UNIT_PRICE))
            instructions.append(set_compute_unit_limit(UNIT_BUDGET))
            if token_account_instructions:
                instructions.append(token_account_instructions)
            instructions.append(swap_instruction)

            # Compile message
            compiled_message = MessageV0.try_compile(
                self.key_pair.pubkey(),
                instructions,
                [],
                self.client.get_latest_blockhash().value.blockhash,
            )

            # Create and send transaction
            transaction = VersionedTransaction(compiled_message,
                                               [self.key_pair])
            txn_sig = self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=True,
                            preflight_commitment="confirmed")).value
            print(f'buy tx: {txn_sig}')

            # Confirm transaction
            return confirm_txn(self.client, txn_sig)

        except Exception as e:
            print(e)
            return None

    def sell(self,
             mint_str,
             token_amount=None,
             sell_ratio: float = 1.0,
             slippage_decimal=.02):
        try:
            # Get coin data
            coin_data = get_coin_data(mint_str)

            if not coin_data:
                print("Failed to retrieve coin data...")
                return None

            owner = self.key_pair.pubkey()
            mint = Pubkey.from_string(mint_str)

            # Calculate token account
            token_account = get_associated_token_address(owner, mint)
            decimal = 6

            # Calculate price per Token in native SOL
            total_supply = coin_data['total_supply']
            market_cap = coin_data['market_cap']
            price_per_token = market_cap * (10**decimal) / total_supply
            print(f"Price per Token: {price_per_token:.20f} SOL")

            # Calculate token balance and minimum SOL output
            sell_amount = None
            if token_amount == None:
                token_balance = get_token_balance(mint_str,
                                                  self.key_pair.pubkey())
                print(token_balance)
                sell_amount = token_balance * sell_ratio
            print("Token Balance:", token_balance)

            if token_balance == 0:
                return

            min_sol_output = float(sell_amount) * float(price_per_token)
            slippage = 1 - slippage_decimal
            min_sol_output = int(
                (min_sol_output * slippage) * LAMPORTS_PER_SOL)
            print("Min Sol Output:", min_sol_output)
            amount = int(sell_amount * 10**decimal)

            # Define account keys required for the swap
            MINT = Pubkey.from_string(coin_data['mint'])
            BONDING_CURVE = Pubkey.from_string(coin_data['bonding_curve'])
            ASSOCIATED_BONDING_CURVE = Pubkey.from_string(
                coin_data['associated_bonding_curve'])
            ASSOCIATED_USER = token_account
            USER = owner

            # Build account key list
            keys = [
                AccountMeta(pubkey=GLOBAL, is_signer=False, is_writable=False),
                AccountMeta(pubkey=FEE_RECIPIENT,
                            is_signer=False,
                            is_writable=True),  # Writable
                AccountMeta(pubkey=MINT, is_signer=False, is_writable=False),
                AccountMeta(pubkey=BONDING_CURVE,
                            is_signer=False,
                            is_writable=True),  # Writable
                AccountMeta(pubkey=ASSOCIATED_BONDING_CURVE,
                            is_signer=False,
                            is_writable=True),  # Writable
                AccountMeta(pubkey=ASSOCIATED_USER,
                            is_signer=False,
                            is_writable=True),  # Writable
                AccountMeta(pubkey=USER, is_signer=True,
                            is_writable=True),  # Writable Signer Fee Payer
                AccountMeta(pubkey=SYSTEM_PROGRAM,
                            is_signer=False,
                            is_writable=False),
                AccountMeta(pubkey=ASSOC_TOKEN_ACC_PROG,
                            is_signer=False,
                            is_writable=False),
                AccountMeta(pubkey=TOKEN_PROGRAM,
                            is_signer=False,
                            is_writable=False),
                AccountMeta(pubkey=PUMP_FUN_ACCOUNT,
                            is_signer=False,
                            is_writable=False),
                AccountMeta(pubkey=PUMP_FUN_PROGRAM,
                            is_signer=False,
                            is_writable=False)
            ]

            # Define integer values
            sell = 12502976635542562355
            integers = [sell, amount, min_sol_output]

            # Pack integers into binary segments
            binary_segments = [
                struct.pack('<Q', integer) for integer in integers
            ]
            data = b''.join(binary_segments)
            swap_instruction = Instruction(PUMP_FUN_PROGRAM, data, keys)

            # Create transaction instructions
            instructions = []
            instructions.append(set_compute_unit_price(UNIT_PRICE))
            instructions.append(set_compute_unit_limit(UNIT_BUDGET))
            instructions.append(swap_instruction)

            # Compile message
            compiled_message = MessageV0.try_compile(
                self.key_pair.pubkey(),
                instructions,
                [],
                self.client.get_latest_blockhash().value.blockhash,
            )

            # Create and send transaction
            transaction = VersionedTransaction(compiled_message,
                                               [self.key_pair])
            txn_sig = self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=True,
                            preflight_commitment="confirmed")).value
            print(f'sell tx: {txn_sig}')

            # Confirm transaction
            return confirm_txn(self.client, txn_sig)

        except Exception as e:
            print(e)
            return None
