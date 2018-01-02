#!/usr/bin/env python

import copy
import importlib
import gzip
import json
import time
import traceback
import sys

from bittrex_exchange import BittrexExchange


def load_trading_plan_class(module_name):
    module = importlib.import_module(module_name)
    return module.trading_plan_class


def main():
    if len(sys.argv) < 3:
        print('Usage: %s <trading plan> [-b] <pair> [<args>]' % sys.argv[0])
        sys.exit(1)
    trading_plan_class = load_trading_plan_class(sys.argv[1])
    buy = (sys.argv[2] == '-b')
    if buy:
        args = sys.argv[3:]
    else:
        args = sys.argv[2:]
    exch = BittrexExchange(True)
    trading_plan = trading_plan_class(exch, sys.argv[1], args, buy)
    ticks = []

    try:
        main_loop(exch, trading_plan.pair, trading_plan, ticks)
    except KeyboardInterrupt:
        print('\nInterrupted by user')
    except BaseException:
        print(traceback.format_exc())

    if len(ticks) > 0:
        filename = '%s-%s.trade' % (trading_plan.pair, ticks[0]['T'])
        with gzip.open(filename, 'w') as fout:
            data = {'candles': ticks,
                    'plan': sys.argv[1],
                    'pair': trading_plan.pair,
                    'balance': trading_plan.balance,
                    'available': trading_plan.available,
                    'args': trading_plan.args}
            json_str = json.dumps(data) + '\n'
            json_bytes = json_str.encode('utf-8')
            fout.write(json_bytes)
        print('Trade saved in %s' % filename)


def main_loop(exch, pair, trading_plan, ticks):
    prev_tick = None
    while True:
        tick = exch.get_tick(pair)
        if tick and tick != prev_tick:
            prev_tick = tick
            ticks.append(tick)
            if not trading_plan.process_tick(copy.deepcopy(tick)):
                break
        time.sleep(30)


if __name__ == "__main__":
    main()

# trade.py ends here
