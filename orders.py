#!/usr/bin/env python

from bittrex_exchange import BittrexExchange
import sys


# for fun and others param
if len(sys.argv) < 2:
    print('Usage: %s <market> ...' % sys.argv[0])
    sys.exit(1)

exch = BittrexExchange(True)

for market in sys.argv[1:]:
    orders = exch.get_open_orders(market)
    for order in orders:
        print(order)
