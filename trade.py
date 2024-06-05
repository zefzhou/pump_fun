from pump_fun import PumpFun
from config import *
import concurrent


def split_array(array, group_size):
    start = 0
    end = len(array)
    groups = []
    while start + group_size < end:
        groups.append(array[start:start + group_size])
        start += group_size
    if start < end:
        groups.append(array[start, end])


def which_tokens(shuffle, start, batch_size, total_size):
    start += shuffle * batch_size
    if start < total_size - batch_size:
        return list(range(start, start + batch_size))
    else:
        return list(range(start, total_size)) + list(
            range(0, start + batch_size - total_size))


def trade(pk: str, tokens: list):
    pf = PumpFun(private_key=pk)
    for token in tokens:
        try:
            pf.trade(token_addr=token)
        except Exception as e:
            print(e)


def main():
    # TODO: read private_key and tokens from file
    pk_list = []

    token_list = []
    tokens_list = split_array(token_list, TOKENS_PER_WALLET)

    with concurrent.futures.ThreadPoolExecutor(
            max_workers=CONCURRENT) as executor:
        futures = [
            executor.submit(trade, pk_list[i],
                            tokens_list[(SHUFFLE + i) % len(tokens_list)])
            for i in range(len(pk_list))
        ]
        concurrent.futures.wait(futures)


if __name__ == '__main__':
    main()
