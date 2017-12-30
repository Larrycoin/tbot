#!/usr/bin/env python

import importlib
import gzip
import json
import time
import sys

from trading_plan import btc2str
from trade import load_trading_plan_class


class FakeExchange(object):
    def __init__(self, balance, available):
        self.balance = balance
        self.available = available

    def get_position(self, pair):
        return {'Balance': self.balance}

    def get_open_orders(self, pair):
        return []

    def sell_limit(self, pair, quantity, limit_price):
        print('SELL LMT %.3f %s %s' % (quantity, pair, btc2str(limit_price)))

    def sell_stop(self, pair, quantity, stop_price):
        print('SELL STP %.3f %s %s' % (quantity, pair, btc2str(stop_price)))

    def buy_limit_range(self, pair, quantity, entry, val_max):
        print('BUY RNG %.3f %s %s-%s' % (quantity, pair,
                                         btc2str(entry), btc2str(val_max)))


def main():
    if len(sys.argv) < 2:
        print('Usage: %s <trading plan>|- <filename> [<args>]' % sys.argv[0])
        sys.exit(1)

    with gzip.open(sys.argv[2], 'r') as fin:
        json_bytes = fin.read()
        json_str = json_bytes.decode('utf-8')
        data = json.loads(json_str)

    if sys.argv[1] == '-':
        trading_plan_class = load_trading_plan_class(data['plan'])
    else:
        trading_plan_class = load_trading_plan_class(sys.argv[1])

    exch = FakeExchange(data['balance'], data['available'])
    pair = data['pair']
    if len(sys.argv) == 2:
        trading_plan = trading_plan_class(exch, pair, data['args'])
    else:
        trading_plan = trading_plan_class(exch, pair, sys.argv[3:])

    for tick in data['candles']:
        if not trading_plan.process_tick(tick):
            break
        time.sleep(1)


if __name__ == "__main__":
    main()

# replay.py ends here
