UNIT_PRICE = 100_000
UNIT_BUDGET = 250_000
RPC = "https://api.mainnet-beta.solana.com"
RETRIES = 10  # 买卖重复次数
SLIPPAGE = 0.02  # 滑点2%
SOL_IN = 0.01  # 购买多少sol
SELL_RATIO = 1.0  # 购买的代币售出多少比例,1.0表示全卖出
TOKENS_PER_WALLET = 2  # 每个钱包交互2个不同的合约
SHUFFLE = 0  # 交互偏移,每次新交互时,自增+1即可. 比如第一天交互，第1个钱包和第1、2个合约交互，第二个钱包和第3、4个合约交互，第二天的时候，shuffle=1, 第一个钱包和第3、4个合约交互，第二个钱包和第5、6个合约交互
CONCURRENT = 5  # 最多5个钱包并发交易
BUY_SELL_MIN_SECONDS = 60
BUY_SELL_MAX_SECONDS = 120
