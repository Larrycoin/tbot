TBot
====

TBot is a set of tools to implement trading bots for crypto
currencies. The supported exchange is bittrex.

Trading strategies are implemented as Python modules. To use these
trading strategies, there are 3 launchers:

1. paper.py to do paper trading
2. trade.py to do live trading
3. replay.py to backtest

You can use paper.py or replay.py without any Bittrex account. Of
course for trade.py you need a Bittrex account. API keys need to be
stored in the ``bittrex.key`` file, first line being the API_KEY and
second line being the API_SECRET.

Trading strategies
++++++++++++++++++

There are automatic and assisted startegies. Assisted strategies
follow trading plan for one trade and then exit. Automatic strategies
continuously find entry positions and follow the trading plan each
time a position has been taken.

Here is the list of existing automatic strategies:

- auto_bb_tp: trade ranges according to Bollinger Bands.
- auto_bbrsi_tp: trade ranges according to Bollinger Bands and RSI
  with a trailing stop based on ATR.
- ripple: time based strategy.
  
Here is the list of existing assisted strategies:

- targets_tp: sell on targets.
- trailing_tp: sell with a trailing stop.
- cut_tp: sell between 2 levels.
