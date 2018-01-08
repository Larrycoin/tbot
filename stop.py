#!/usr/bin/env python

from bittrex_exchange import BittrexExchange
import sys

from utils import str2btc


def get_orders(conn, market):
    return conn.get_open_orders(market)


def send_order(order, exch, func, *args, **kwargs):
    if order and exch.cancel_order(order):
        order = None
    new_order = func(*args, **kwargs)
    if new_order:
        print(new_order)
        order = new_order
    return order


if len(sys.argv) != 3:
    print('Usage: %s <market> <stop>' % sys.argv[0])
    sys.exit(1)

market = sys.argv[1]
stop = str2btc(sys.argv[2])

currency = market.split('-')[1]

exch = BittrexExchange(True)

position = exch.get_position(currency)

if not position:
    print('No open position on %s' % currency)
    sys.exit(1)

quantity = position['Balance']

orders = exch.get_open_orders(market)

if len(orders) > 0:
    print(orders[0].data)
    order = orders[0]
else:
    order = None

order = send_order(order, exch, exch.sell_stop,
                   market, quantity, stop)
