#!/usr/bin/env python

import importlib
import time
import sys

from bittrex_exchange import BittrexExchange


def load_trading_plan_class(module_name):
    module = importlib.import_module(module_name)
    return module.trading_plan_class


def main():
    if len(sys.argv) < 3:
        print('Usage: %s <trading plan> <pair> [<args>]')
        sys.exit(1)
    trading_plan_class = load_trading_plan_class(sys.argv[1])
    exch = BittrexExchange(True)
    pair = sys.argv[2]
    trading_plan = trading_plan_class(exch, pair, sys.argv[3:])

    prev_tick = None
    while True:
        tick = exch.get_tick(pair)
        if tick != prev_tick:
            if not trading_plan.process_tick(tick):
                break
            prev_tick = tick
        time.sleep(30)


if __name__ == "__main__":
    main()

# trade.py ends here
