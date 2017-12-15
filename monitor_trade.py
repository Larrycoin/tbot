#!/usr/bin/env python

import argparse
import time
import sys

from bittrex_exchange import BittrexExchange


def send_order(order, exch, func, *args, **kwargs):
    if order and exch.cancel_order(order):
        order = None
    new_order = func(*args, **kwargs)
    if new_order:
        print(new_order.data)
        order = new_order
    return order


def monitor_order_completion(exch, market):
    orders = exch.get_open_orders(market)
    if len(orders) == 0:
        print('order completed')
        return True
    else:
        print('order still in place')
        return False


def convert(s):
    if s[-1] == 's':
        val = float(s[:-1]) * 0.00000001
    elif s[-1] == 'S':
        val = float(s[:-1]) * 0.000001
    else:
        val = float(s)
    return val


def buy_pair(exch, market, stop, entry, quantity, limit_range):
    currency = market.split('-')[1]
    orders = exch.get_open_orders(market)
    if len(orders) != 0:
        for order in orders:
            if order.is_buy_order():
                print('There is already a buy order. Aborting.')
                print(order.data)
                sys.exit(1)
    position = exch.get_position(currency)
    if position and position['Balance'] > 0:
        print('There is already a position on %s (%f). Not buying.' %
              (currency, position['Balance']))
        print(position)
    else:
        val_max = entry + (entry - stop) * limit_range
        buy_order = exch.buy_limit_range(market, quantity, entry, val_max)
        print(buy_order.data)
        while True:
            orders = exch.get_open_orders(market)
            if len(orders) > 0 and orders[0].is_buy_order():
                break
            print('Waiting for the buy order to become visible')
            time.sleep(5)


def sanity_checks(exch, market, quantity, stop):
    currency = market.split('-')[1]
    while True:
        position = exch.get_position(currency)
        if position and position['Balance'] >= quantity:
            break
        orders = exch.get_open_orders(market)
        if len(orders) == 0 or not orders[0].is_buy_order():
            print('no buy order for %s' % market)
            print([order.data for order in orders])
            sys.exit(1)
        tick = exch.get_tick(market)
        if tick and tick['L'] < stop:
            print(market,
                  'Trade invalidated (low price %f), cancelling order' %
                  tick['L'])
            exch.cancel_order(orders[0])
            sys.exit(0)
        if position:
            print(market,
                  'Not the correct balance: %.2f instead of more than %.2f' %
                  (position['Balance'], quantity))
        else:
            print(market,
                  'Not the correct balance: no position '
                  'instead of more than %.2f' %
                  (quantity))
        time.sleep(60)


def get_trend(exch, market):
    orders = exch.get_open_orders(market)

    if len(orders) > 0:
        print(orders[0].data)
        order = orders[0]

        # TODO(fl): need to abstract
        if order.data['IsConditional']:
            trend = 'down'
        else:
            trend = 'up'
    else:
        trend = 'none'
        order = None
    return (trend, order)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', "--buy", help='run a buy order',
                        action="store_true")
    parser.add_argument(
        '-r', "--range",
        help='floating number to compute buy range. Default 0.09.',
        type=float, default=0.09)
    parser.add_argument('market', help='name of the market like BTC-ETH')
    parser.add_argument('quantity', help='quantity of coins', type=float)
    parser.add_argument('stop', help='stop level')
    parser.add_argument('entry', help='entry level')
    parser.add_argument('exit', help='exit level')
    args = parser.parse_args()

    market = args.market
    quantity = args.quantity
    stop = convert(args.stop)
    entry = convert(args.entry)
    exit = convert(args.exit)

    exch = BittrexExchange(True)

    # Buy order if needed
    if args.buy:
        buy_pair(exch, market, stop, entry, quantity, args.range)

    # Do some sanity checks
    sanity_checks(exch, market, quantity, stop)

    # Get trend (up, down or none) and the open order if it exists
    trend, order = get_trend(exch, market)

    print(trend)

    while True:
        tick = exch.get_tick(market)
        print(market, tick)
        # TODO(fl): need to abstract tick
        last = tick['C']
        if last < entry:
            if tick['L'] < stop and monitor_order_completion(exch, market):
                break
            elif trend != 'down':
                print('down')
                order = send_order(order, exch, exch.sell_stop,
                                   market, quantity, stop)
                trend = 'down'
        else:
            if tick['H'] > exit and monitor_order_completion(exch, market):
                break
            elif trend != 'up':
                print('up')
                order = send_order(order, exch, exch.sell_limit,
                                   market, quantity, exit)
                trend = 'up'
        time.sleep(60)


if __name__ == "__main__":
    main()
