import json
import time
import requests
from config import RPC
from solana.transaction import Signature
from solders.pubkey import Pubkey


def find_data(data, field):
    if isinstance(data, dict):
        if field in data:
            return data[field]
        else:
            for value in data.values():
                result = find_data(value, field)
                if result is not None:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = find_data(item, field)
            if result is not None:
                return result
    return None


def get_token_balance(base_mint: str, pub_key: Pubkey):
    try:
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        payload = {
            "id":
            1,
            "jsonrpc":
            "2.0",
            "method":
            "getTokenAccountsByOwner",
            "params": [
                pub_key.__str__(),
                {
                    "mint": base_mint
                },
                {
                    "encoding": "jsonParsed"
                },
            ],
        }

        response = requests.post(RPC, json=payload, headers=headers)
        ui_amount = find_data(response.json(), "uiAmount")
        return float(ui_amount)
    except Exception as e:
        print(e)
        return None


def get_coin_data(mint_str):
    url = f"https://frontend-api.pump.fun/coins/{mint_str}"
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.pump.fun/",
        "Origin": "https://www.pump.fun",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def confirm_txn(client, txn_sig, max_retries=10, retry_interval=10):
    retries = 0
    if isinstance(txn_sig, str):
        txn_sig = Signature.from_string(txn_sig)
    while retries < max_retries:
        try:
            txn_res = client.get_transaction(
                txn_sig,
                encoding="json",
                commitment="confirmed",
                max_supported_transaction_version=0)
            txn_json = json.loads(txn_res.value.transaction.meta.to_json())
            if txn_json['err'] is None:
                print("Transaction confirmed... try count:", retries + 1)
                return True
            print("Error: Transaction not confirmed. Retrying...")
            if txn_json['err']:
                print("Transaction failed.")
                return False
        except Exception as e:
            print("Awaiting confirmation... try count:", retries + 1)
            retries += 1
            time.sleep(retry_interval)
    print("Max retries reached. Transaction confirmation failed.")
    return None
