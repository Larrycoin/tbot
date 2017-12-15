#!/usr/bin/env python

import argparse
import time

from bittrex_exchange import BittrexExchange
import pandas as pd
from pandas.io.json import json_normalize

from monitor_trade import (send_order, monitor_order_completion, convert,
                           buy_pair, sanity_checks, get_trend)


def ATR(df, n=20, name=None):
    if name is None:
        name = 'ATR_%d' % n
    df['TR1'] = abs(df['H'] - df['L'])
    df['TR2'] = abs(df['H'] - df['C'].shift())
    df['TR3'] = abs(df['L'] - df['C'].shift())
    df['TrueRange'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)
    df[name] = df['TrueRange']
    df[name] = ((n - 1) * df[name].shift() + df['TrueRange']) / n
    del df['TR1']
    del df['TR2']
    del df['TR3']
    del df['TrueRange']
    return df


def ATR_STP(df, name=None):
    if name is None:
        name = 'ATR_STP'
    ATR(df)
    df['L1'] = df['L'].shift()
    df['L2'] = df['L'].shift(2)
    df['L3'] = df['L'].shift(3)
    df[name] = (df[['L1', 'L2', 'L3']].min(axis=1) -
                (df['ATR_20'] / 3))
    del df['L1']
    del df['L2']
    del df['L3']
    del df['ATR_20']
    return df


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
    sanity_checks(exch, market, quantity / 2, stop)

    # Get trend (up, down or none) and the open order if it exists
    trend, order = get_trend(exch, market)

    print(trend)

    trailing = False
    df = None
    prev_trail = trail = None

    ohlc_dict = {'O': 'first', 'H': 'max', 'L': 'min', 'C': 'last',
                 'V': 'sum', 'BV': 'sum'}

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
            if trailing or tick['H'] > exit:
                trailing = True
                # do the trend following
                tick['T'] = pd.to_datetime(tick['T'])
                if df is None:
                    candles = exch.get_candles(market, 'oneMin')
                    df = json_normalize(candles)
                    df['T'] = pd.to_datetime(df['T'])
                    df = df.set_index('T')
                    prev_tick = tick
                if tick != prev_tick:
                    frame = pd.DataFrame(tick, index=[tick['T']])
                    df = pd.concat([df, frame])
                    ndf = df.resample('1H').apply(ohlc_dict)
                    ATR_STP(ndf)
                    trail = ndf.tail()['ATR_STP'].values[-1]
                    if trail != prev_trail:
                        order = send_order(order, exch, exch.sell_stop,
                                           market, quantity / 2, trail)
                        prev_trail = trail
                    del ndf
            elif trend != 'up':
                print('up')
                order = send_order(order, exch, exch.sell_limit,
                                   market, quantity / 2, exit)
                trend = 'up'
        time.sleep(60)


if __name__ == "__main__":
    main()
