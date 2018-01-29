#!/usr/bin/env python

from datetime import datetime
import gzip
import json
import os
import sys

from bittrex_exchange import BittrexOrder
from trade import load_trading_plan_class
from utils import btc2str


class FakeExchange(object):
    def __init__(self, balance, available, candles):
        self.balance = balance
        self.available = available
        self.candles = candles
        self.order = None
        self.orders = []
        self.percent_fee = 0.0025

    def get_position(self, pair):
        return {'Balance': self.balance}

    def get_open_orders(self, pair):
        return [self.order]

    def sell_limit(self, pair, quantity, limit_price):
        print('SELL LMT %.3f %s %s' % (quantity, pair, btc2str(limit_price)))
        self.order = BittrexOrder({'OrderId': '1',
                                   'Quantity': quantity,
                                   'Limit': limit_price,
                                   'Commission':
                                   limit_price * quantity * self.percent_fee,
                                   'OrderType': 'LIMIT_SELL',
                                   'IsConditional': False,
                                   'Condition': 'NONE',
                                   'Exchange': pair,
                                   'PricePerUnit': limit_price},
                                  id='1')
        self.orders.insert(0, self.order)
        return self.order

    def sell_stop(self, pair, quantity, stop_price):
        print('SELL STP %.3f %s %s' % (quantity, pair, btc2str(stop_price)))
        self.order = BittrexOrder({'OrderId': '1',
                                   'Quantity': quantity,
                                   'Limit': stop_price / 2,
                                   'Commission':
                                   stop_price * quantity * self.percent_fee,
                                   'OrderType': 'LIMIT_SELL',
                                   'IsConditional': True,
                                   'Condition': 'LESSTHAN',
                                   'ConditionTarget': stop_price,
                                   'Exchange': pair,
                                   'PricePerUnit': stop_price},
                                  id='2')

    def buy_limit(self, pair, quantity, limit_price):
        print('BUY LMT %.3f %s %s' % (quantity, pair, btc2str(limit_price)))
        self.order = BittrexOrder({'OrderId': '1',
                                   'Quantity': quantity,
                                   'Limit': limit_price,
                                   'Commission':
                                   limit_price * quantity * self.percent_fee,
                                   'OrderType': 'LIMIT_BUY',
                                   'IsConditional': False,
                                   'Condition': 'NONE',
                                   'Exchange': pair,
                                   'PricePerUnit': limit_price},
                                  id='3')
        self.orders.insert(0, self.order)
        return self.order

    def buy_limit_range(self, pair, quantity, entry, val_max):
        print('BUY RNG %.3f %s %s-%s' % (quantity, pair,
                                         btc2str(entry), btc2str(val_max)))

    def get_candles(self, pair, duration):
        return self.candles

    def get_order_history(self, pair=None):
        return self.orders

    def update_order(self, order):
        return order

    def cancel_order(self, order):
        self.order = None
        return self.order

    def process_tick(self, tick):
        if self.order:
            if self.order.is_buy_order() and self.order.limit() >= tick['L']:
                self.order = None
            elif self.order.is_sell_order():
                if (not self.order.data['IsConditional'] and
                   tick['H'] > self.order.limit()):
                    self.order.data['PricePerUnit'] = (tick['H'] + tick['L']) / 2
                    self.order = None
                elif (self.order.data['IsConditional'] and
                      self.order.limit() > tick['L']):
                    self.order = None


def main():
    if len(sys.argv) < 3:
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

    if os.getenv('TBOT_START_DATE'):
        dt = datetime.strptime(os.getenv('TBOT_START_DATE'),
                               '%Y-%m-%d %H:%M')
        for idx in range(len(data['candles'])):
            if datetime.strptime(data['candles'][idx]['T'],
                                 '%Y-%m-%dT%H:%M:%S') >= dt:
                break
        else:
            idx = 20
    else:
        idx = 20

    exch = FakeExchange(data['balance'], data['available'],
                        data['candles'][:idx])
    print(data['plan'], data['args'])
    if len(sys.argv) == 3:
        trading_plan = trading_plan_class(exch, data['plan'],
                                          data['args'], False)
    else:
        if sys.argv[3] == '-b':
            buy = True
            args = sys.argv[4:]
        else:
            buy = False
            args = sys.argv[3:]
        trading_plan = trading_plan_class(exch, data['plan'],
                                          args, buy)

    for tick in data['candles'][idx:]:
        exch.candles.append(tick)
        exch.process_tick(tick)
        trading_plan.tick = tick
        if not trading_plan.process_tick():
            break


if __name__ == "__main__":
    main()

# replay.py ends here
