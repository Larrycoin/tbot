#!/usr/bin/env python

from bittrex_exchange import BittrexExchange

# API call allows an optional parameter: market,
# but this parameter has no impact on the output
# so, all histrical orders will be displayed without parameter in this version.

exch = BittrexExchange(True)
orders = exch.get_order_history('None')
for order in orders:
    if order.data['Condition'] != 'NONE':
        print('%s %s (%2.1f) %s(%2.8f) %s(%2.8f) Price:%2.8f Fees:%2.8f' %
              (order.data['Exchange'], order.data['TimeStamp'],
               order.data['Quantity'], order.data['OrderType'],
               order.data['Limit'], order.data['Condition'],
               order.data['ConditionTarget'], order.data['PricePerUnit'],
               order.data['Commission']))
    else:
        print('%s %s (%2.1f) %s(%2.8f) Price:%2.8f Fees:%2.8f' %
              (order.data['Exchange'], order.data['TimeStamp'],
               order.data['Quantity'], order.data['OrderType'],
               order.data['Limit'], order.data['PricePerUnit'],
               order.data['Commission']))
