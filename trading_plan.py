'''
'''

from datetime import datetime
import os
import re

import pandas as pd
from pandas.io.json import json_normalize

from bittrex_exchange import BittrexError
from utils import btc2str


ANSI_ESCAPE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')


class TradingPlan(object):
    def __init__(self, exch, name, args, buy):
        self.exch = exch
        self.name = name
        self.tick = None
        self.buy = buy
        if not getattr(self, 'pair', False):
            self.pair = args[0]
        self.args = args
        self.currency = self.pair.split('-')[1]
        self.sent_order = False
        self.update_open_orders()
        for order in self.open_orders:
            print(order)
        self.update_position()
        if not os.getenv('TBOT_NO_LOG'):
            self.file_log = open('%s-%s.log' %
                                 (self.pair,
                                  datetime.now().strftime('%Y%m%d%H%M%S')),
                                 'a')
        else:
            self.file_log = None
        self.log('Balance = %.3f Available = %.3f' % (self.balance,
                                                            self.available))

    def log(self, msg):
        if self.tick:
            if isinstance(self.tick['T'], str):
                line = '%s %s %s %s' % (self.tick['T'][:10],
                                        self.tick['T'][11:-3],
                                        self.pair, msg)
            else:
                line = '%s %s %s' % (self.tick['T'].strftime('%Y-%m-%d %H:%M'),
                                     self.pair, msg)
        else:
            line = '%s %s' % (self.pair, msg)
        print(line)
        if self.file_log:
            line = ANSI_ESCAPE.sub('', line) + '\n'
            self.file_log.write(line)

    def update_position(self):
        position = self.exch.get_position(self.currency)
        if position and 'Balance' in position:
            self.balance = position['Balance']
        else:
            self.balance = 0
        if position and 'Available' in position:
            self.available = position['Available']
        else:
            self.available = 0

    def update_open_orders(self):
        self.open_orders = self.exch.get_open_orders(self.pair)
        if len(self.open_orders) > 0:
            self.order = self.open_orders[0]
            self.sent_order = False
        else:
            self.order = None
        return self.open_orders

    def process_tick(self):
        self.log('%s %s-%s' % (btc2str(self.tick['C']),
                               btc2str(self.tick['L']),
                               btc2str(self.tick['H'])))
        return True

    def sell_limit(self, quantity, limit_price):
        self.send_order(self.exch.sell_limit,
                        self.pair, quantity,
                        limit_price)

    def sell_stop(self, quantity, stop_price):
        self.send_order(self.exch.sell_stop,
                        self.pair, quantity,
                        stop_price)

    def buy_range(self, quantity, entry, val_max):
        self.send_order(self.exch.buy_limit_range, self.pair,
                        quantity, entry, val_max)

    def send_order(self, func, *args, **kwargs):
        if self.order:
            self.do_cancel_order()
        else:
            self.log('no order to cancel')
        done = 10
        while done > 0:
            try:
                func(*args, **kwargs)
                break
            except BittrexError as error:
                if error.args[0] == 'INSUFFICIENT_FUNDS':
                    self.update_position()
                    self.log('Insufficient funds: available=%.3f' %
                             self.available)
                    done -= 1
                    continue
                else:
                    raise error
        if done > 0:
            self.sent_order = True
            self.update_open_orders()
            if self.order:
                self.log('New order: %s' % self.order)
        else:
            self.log('Giving up.')

    def monitor_order_completion(self, msg):
        self.update_open_orders()
        if self.order is None:
            self.log(msg + 'order completed')
            return True
        else:
            self.log(msg + 'order still in place')
            return False

    def do_buy_order(self, stop, price, limit_range=0.09):
        if self.order:
            self.log('There is already an order. Aborting.')
            print(self.order)
            return False
        if self.balance > 0:
            self.log('There is already a position on %s (%.3f). Not buying.' %
                     (self.currency, self.balance))
            return False
        else:
            self.buy_range(self.quantity, price,
                           price + (price - stop) * limit_range)
            self.update_open_orders()
            return True

    def do_cancel_order(self):
        if self.order:
            self.exch.cancel_order(self.order)
            print('Canceled order: %s' % self.order)
            self.order = None

    def process_tick_buying(self, tick, stop, quantity):
        self.check_order()
        if (self.balance < quantity and
           not (self.order and self.order.is_buy_order())):
            self.log('Waiting for the buy order to become visible')
            self.update_open_orders()
        else:
            if tick['L'] < stop:
                self.log('Trade invalidated (low price %.8f < %.8f), '
                         'cancelling order' %
                         (tick['L'], self.stop_price))
                self.do_cancel_order()
                return False
            self.update_position()
            if self.balance >= quantity:
                self.status = 'unknown'
                if self.order and self.order.is_buy_order():
                    self.order = None
                    self.sent_order = False
            else:
                self.log('Not the correct balance: %.3f instead of '
                         'more than %.3f' %
                         (self.balance, quantity))
        return True

    def check_order(self):
        if self.sent_order:
            self.update_open_orders()
            if not self.sent_order and self.order:
                print(self.order)

    def init_dataframes(self):
        candles = self.exch.get_candles(self.pair, 'oneMin')
        self.df = json_normalize(candles)
        self.df['T'] = pd.to_datetime(self.df['T'])
        self.df = self.df.set_index('T')
        return candles

    def update_dataframe(self, tick):
        tick['T'] = pd.to_datetime(tick['T'])
        frame = pd.DataFrame(tick, index=[tick['T']])
        self.df = pd.concat([self.df, frame])

    def resample_dataframes(self, period):
        ohlc_dict = {'O': 'first', 'H': 'max', 'L': 'min', 'C': 'last',
                     'V': 'sum', 'BV': 'sum'}
        return self.df.resample(str(period) + 'T').apply(ohlc_dict)

    def dispatch_tick(self, status, *args, **kwargs):
        return getattr(self, 'process_tick_' + status)(*args, **kwargs)


trading_plan_class = TradingPlan

# trading_plan.py ends here
