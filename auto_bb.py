'''
'''

import argparse
import sys

from trading_plan import TradingPlan
from utils import btc2str
from utils import BB
from utils import MA


TEN8 = 100000000


class AutoBBTradingPlan(TradingPlan):
    def __init__(self, exch, name, arguments, buy):
        parser = argparse.ArgumentParser(prog=name)
        parser.add_argument(
            '-p', "--percent",
            help='percentage of the Bollinger band width to look for.'
            ' Default 0.05.',
            type=float, default=0.05)
        parser.add_argument('pair', help='pair of crypto like BTC-ETH')
        parser.add_argument('amount',
                            help='quantity of currency to use for the trade',
                            type=float)
        parser.add_argument('period',
                            help='number of minutes to take decisions',
                            type=int, default=5)
        args = parser.parse_args(arguments)

        self.pair = args.pair
        self.amount = args.amount
        self.period = args.period
        self.percent = args.percent
        self.status = 'searching'
        self.entry = None
        self.stop = None
        self.stop_order = None
        self.cost = 0
        self.quantity = 0

        super().__init__(exch, name, arguments, buy)

        self.ticks = self.init_dataframes()

        self.log(None, '%s amount=%s period=%d mn percent=%.2f%%' %
                 (name, btc2str(self.amount), self.period, self.percent * 100))

    def process_tick(self, tick):
        self.update_dataframe(tick)
        ndf = self.resample_dataframes(self.period)
        BB(ndf)
        MA(ndf, 20, 'V', 'VMA20')

        # Put a stop if needed but let the trade logic continue if it is not
        # reached
        self.check_stop(tick)

        if self.status == 'searching':
            self.process_tick_searching(tick, ndf)
        elif self.status == 'buying':
            self.process_tick_buying(tick, ndf)
        elif self.status == 'middle':
            self.process_tick_exit_middle(tick, ndf)
        elif self.status == 'top':
            self.process_tick_exit_top(tick, ndf)
        elif self.status == 'selling':
            self.process_selling(tick, ndf)

        self.log(tick, '%s %s %s-%s %.3f (%f x %s)' %
                 (self.status,
                  btc2str(tick['C']),
                  btc2str(tick['L']),
                  btc2str(tick['H']),
                  self.amount, self.quantity, btc2str(self.entry)))
        del ndf
        return(self.amount > 0)

    def check_stop(self, tick):
        if self.stop:
            if tick['L'] < self.stop:
                stop = tick['L'] * 0.99
                self.log(tick, 'stop reached. Putting a physical stop @ %s' %
                         btc2str(stop))
                self.sell_stop(self.quantity, stop)
                self.stop = None
                self.check_order()
                self.stop_order = self.order or True
                return True
        if self.stop_order:
            self.check_order()
            if self.stop_order is True:
                self.stop_order = self.order or True
            if self.stop_order is not True:
                # order is no longer open
                if not self.order:
                    self.exch.update_order(self.stop_order)
                    self.compute_gains(self.stop_order)
                    self.stop_order = None
                # buy order has been sent
                elif self.order.is_buy_order():
                    self.stop_order = None
            return True
        return False

    def process_tick_searching(self, tick, df):
        last_row = df.iloc[-1]
        volok = (last_row['V'] > last_row['VMA20'])
        priceok = (last_row['L'] < last_row['BBL'])
        bbok = (last_row['BBW'] > self.percent)
        self.log(tick, '%s(%.2f > %.2f) %s(%s < %s) %s(%.2f > %.2f)' %
                 ('volok' if volok else 'volko',
                  last_row['V'], last_row['VMA20'],
                  'priceok' if priceok else 'priceko',
                  btc2str(last_row['L']), btc2str(last_row['BBL']),
                  'bbok' if bbok else 'bbko',
                  last_row['BBW'], self.percent))
        if volok and priceok and bbok:
            self.status = 'buying'
            self.entry = last_row['L']
            self.quantity = self.amount / self.entry
            self.send_order(self.exch.buy_limit,
                            self.pair, self.quantity,
                            self.entry)
            self.stop = tick['L'] * 0.95
            self.log(tick, 'buying %f @ %s' %
                     (self.quantity, btc2str(self.entry)))

    def process_tick_buying(self, tick, df):
        if self.monitor_order_completion('buy '):
            self.entry = self.order.data['PricePerUnit']
            self.quantity = self.order.data['Quantity']
            self.cost = self.order.data['Commission']
            self.log(tick, "bought %f @ %s Fees %s" %
                     (self.quantity, btc2str(self.entry),
                      btc2str(self.cost)))
            self.status = 'middle'
        elif self.entry < tick['L']:
            self.log(tick, 'entry %s < low %s -> canceling order' %
                     (btc2str(self.entry), btc2str(tick['L'])))
            self.do_cancel_order()
            self.status = 'searching'

    def process_tick_exit_middle(self, tick, df):
        last_row = df.iloc[-1]
        volok = (last_row['V'] > last_row['VMA20'])
        priceok = (tick['H'] > last_row['BBM'])
        if priceok:
            if volok:
                self.status = 'top'
                self.stop = self.entry
            else:
                self.sell(tick)

    def process_tick_exit_top(self, tick, df):
        last_row = df.iloc[-1]
        volok = (last_row['V'] < last_row['VMA20'])
        priceok = (tick['H'] > last_row['BBU'])
        if priceok:
            if volok:
                self.sell(tick)
            else:
                self.stop = last_row['BBM']

    def sell(self, tick):
        self.status = 'selling'
        self.send_order(self.exch.sell_limit,
                        self.pair, self.quantity,
                        tick['L'] / 2)

    def process_selling(self, tick, ndf):
        if self.monitor_order_completion():
            self.compute_gains(self.order)

    def compute_gains(self, order):
        price = order.data['PricePerUnit']
        quantity = order.data['Quantity']
        self.cost += order.data['Commission']
        amount = price * quantity - self.cost
        self.log(tick, 'sold %f @ %s => %f %f %.2f%%' %
                 (quantity, btc2str(price),
                  amount, self.amount,
                  (amount / self.amount - 1) * 100))
        self.amount = amount
        self.quantity = 0
        self.entry = None
        self.stop = None
        self.status = 'searching'


trading_plan_class = AutoBBTradingPlan

# auto_bb.py ends here
