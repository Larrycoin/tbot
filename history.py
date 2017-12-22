#!/usr/bin/env python

import sys

from bittrex_exchange import BittrexExchange


def display_orders(orders):
    for order in orders:
        if order.data['Condition'] != 'NONE':
            print('%s %s(%.3f) %s(%.8f) %s(%2.8f) => %.8f x %.3f = %.8f '
                  'Fees: %.8f' %
                  (order.data['Closed'], order.data['Exchange'],
                   order.data['Quantity'], order.data['OrderType'],
                   order.data['Limit'], order.data['Condition'],
                   order.data['ConditionTarget'], order.data['PricePerUnit'],
                   order.data['Quantity'], order.data['Price'],
                   order.data['Commission']))
        else:
            print('%s %s(%.3f) %s(%.8f) => %.8f x %.3f = %.8f '
                  'Fees: %.8f' %
                  (order.data['Closed'], order.data['Exchange'],
                   order.data['Quantity'], order.data['OrderType'],
                   order.data['Limit'], order.data['PricePerUnit'],
                   order.data['Quantity'], order.data['Price'],
                   order.data['Commission']))


exch = BittrexExchange(True)

if len(sys.argv) > 1:
    for market in sys.argv[1:]:
        orders = exch.get_order_history(market)
        display_orders(orders)
else:
    orders = exch.get_order_history()
    display_orders(orders)
