#!/usr/bin/env python

from bittrex_exchange import BittrexExchange
import sys


def get_orders(conn, market):
    return conn.get_open_orders(market)


if len(sys.argv) != 2:
    print('Usage: %s <market>' % sys.argv[0])
    sys.exit(1)

market = sys.argv[1]
exch = BittrexExchange(True)
orders = exch.get_open_orders(market)
if len(orders) > 0:
    print('CANCELLING : %s' % orders[0])
    exch.cancel_order(orders[0])
else:
    print('no order found.')
