#!/usr/bin/env python

from bittrex_exchange import BittrexExchange
import sys

from utils import btc2str


if len(sys.argv) != 2:
    print('Usage: %s <market>' % sys.argv[0])
    sys.exit(1)

market = sys.argv[1]

currency = market.split('-')[1]

exch = BittrexExchange(True)

orders = exch.get_order_history(market)

for idx in range(len(orders)):
    if orders[idx].is_buy_order():
        break

print(orders[idx])
entry = orders[idx].quantity() * orders[idx].price_per_unit()
total = 0

for i in range(idx):
    print(orders[i])
    total += orders[i].quantity() * orders[i].price_per_unit()

print('delta=%s percent=%.2f%%' % (btc2str(total - entry),
                                 (total / entry - 1) * 100))

price = orders[idx].price_per_unit() + (total - entry) / orders[idx].quantity()

print('equivalent to have sold at %s x %.3f' % (btc2str(price),
                                                orders[idx].quantity()))
