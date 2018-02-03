'''
'''

import argparse
import sys

from trading_plan import TradingPlan
from utils import (btc2str, ATR_STP, BB, MA, RSI, red, green)


class AutoBBRsiTradingPlan(TradingPlan):
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
                            type=int)
        args = parser.parse_args(arguments)

        self.pair = args.pair
        self.amount = args.amount
        self.period = args.period
        self.percent = args.percent
        if buy:
            self.status = 'searching'
        else:
            self.status = 'recovering'
        self.entry = None
        self.virtual_stop = None
        self.physical_stop = None
        self.cost = 0
        self.quantity = 0

        super().__init__(exch, name, arguments, buy)

        self.ticks = self.init_dataframes()

        self.log('%s amount=%s period=%d mn percent=%.2f%%' %
                 (name, btc2str(self.amount), self.period, self.percent * 100))

    def process_tick(self):
        self.update_dataframe(self.tick)
        ndf = self.resample_dataframes(self.period)
        BB(ndf)
        MA(ndf, 20, 'V', 'VMA20')
        RSI(ndf)
        ATR_STP(ndf)
        last_row = ndf.iloc[-2]

        # Put a stop if needed but let the trade logic continue if it is not
        # reached
        self.check_stop(self.tick)

        self.dispatch_tick(self.status, self.tick, last_row)

        if self.entry:
            percent = ((self.tick['C'] / self.entry) - 1) * 100
        else:
            percent = 0

        self.log('%s %s %s-%s %.3f (%f x %s) vstop=%s pstop=%s %.2f%%' %
                 (self.status,
                  btc2str(self.tick['C']),
                  btc2str(self.tick['L']),
                  btc2str(self.tick['H']),
                  self.amount, self.quantity, btc2str(self.entry),
                  btc2str(self.virtual_stop), btc2str(self.physical_stop),
                  percent))
        del ndf
        return(self.amount > 0)

    def check_stop(self, tick):
        if self.virtual_stop:
            if tick['L'] < self.virtual_stop:
                stop = tick['L'] * 0.99
                if not self.physical_stop or stop > self.physical_stop:
                    self.log('Virtual stop reached. '
                             'Putting a physical stop @ %s' %
                             btc2str(stop))
                    self.sell_stop(self.quantity, stop)
                    self.physical_stop = stop
                    self.check_order()
                else:
                    self.log('Virtual stop reached. '
                             'Not lowering physical stop %s < %s' %
                             (btc2str(stop), btc2str(self.physical_stop)))
                return True
        if self.physical_stop:
            if self.monitor_order_completion('stop '):
                past_orders = self.exch.get_order_history(self.pair)
                if len(past_orders) == 0:
                    self.log('Unable to find stop order. Aborting.')
                    sys.exit(1)
                stop_order = past_orders[0]
                self.compute_gains(tick, stop_order)
                self.physical_stop = None
                # buy order has been sent
                return True
        if self.order and self.order.is_buy_order():
            self.physical_stop = None
            return True
        return False

    def process_tick_recovering(self, tick, last_row):
        past_orders = self.exch.get_order_history(self.pair)
        for order in past_orders:
            if order.is_buy_order():
                buy_order = order
                break
        else:
            self.log('No buy order. Aborting.')
            sys.exit(1)
        self.log('Recovered order %s' % buy_order)
        if self.balance < buy_order.data['Quantity']:
            self.log('Invalid balance %s < %s. Aborting' %
                     (self.balance, buy_order.data['Quantity']))
            sys.exit(1)
        self.status = 'buying'

    @staticmethod
    def selling_pressure(row):
        if row['H'] == row['L']:
            return 0
        else:
            return (row['H'] - row['C']) / (row['H'] - row['L'])

    def process_tick_searching(self, tick, last_row):
        rsiok = (last_row['RSI'] < 30)
        priceok = (tick['L'] < last_row['BBL'])
        bbok = (last_row['BBW'] > self.percent)
        self.log('%s(%s < %s) %s(%.1f < %f) %s(%.2f > %.2f)' %
                 (green('priceok') if priceok else red('priceko'),
                  btc2str(tick['L']), btc2str(last_row['BBL']),
                  green('rsiok') if rsiok else red('rsiko'),
                  last_row['RSI'], 30,
                  green('bbok') if bbok else red('bbko'),
                  last_row['BBW'], self.percent))
        if rsiok and priceok and bbok:
            self.status = 'buying'
            self.entry = last_row['L']
            self.quantity = self.amount / self.entry
            self.send_order(self.exch.buy_limit,
                            self.pair, self.quantity,
                            self.entry)
            self.log('buying %f @ %s' %
                     (self.quantity, btc2str(self.entry)))
            self.middle = last_row['BBM']
            self.top = last_row['BBU']

    def process_tick_buying(self, tick, last_row):
        if self.monitor_order_completion('buy '):
            past_orders = self.exch.get_order_history(self.pair)
            if len(past_orders) == 0:
                self.log('Unable to find buy order. Aborting.')
                sys.exit(1)
            buy_order = past_orders[0]
            self.entry = buy_order.data['PricePerUnit']
            self.quantity = buy_order.data['Quantity']
            self.cost = buy_order.data.get('Commission', 0)
            self.log("bought %f @ %s Fees %s" %
                     (self.quantity, btc2str(self.entry),
                      btc2str(self.cost)))
            self.status = 'rsi'
            # safe bet for recovery mode
            self.set_stop(last_row['ATR_STP'])
        elif self.entry < last_row['L']:
            self.log('entry %s < low %s -> canceling order' %
                     (btc2str(self.entry), btc2str(last_row['L'])))
            self.do_cancel_order()
            self.entry = None
            self.quantity = 0
            self.status = 'searching'

    def process_tick_rsi(self, tick, last_row):
        rsiok = (last_row['RSI'] > 70)
        self.log('%s(%.1f > %f)' %
                 (green('rsiok') if rsiok else red('rsiko'),
                  last_row['RSI'], 70))
        if rsiok:
            self.sell(tick)
        else:
            self.set_stop(last_row['ATR_STP'])

    def sell(self, tick):
        self.status = 'selling'
        self.send_order(self.exch.sell_limit,
                        self.pair, self.quantity,
                        tick['L'] / 2)
        self.check_order()
        self.sell_order = self.order

    def process_tick_selling(self, tick, last_row):
        if self.monitor_order_completion('sell '):
            past_orders = self.exch.get_order_history(self.pair)
            if len(past_orders) == 0:
                self.log('Unable to find sell order. Aborting.')
                sys.exit(1)
            self.compute_gains(tick, past_orders[0])

    def compute_gains(self, tick, order):
        price = order.data['PricePerUnit']
        quantity = order.data['Quantity']
        self.cost += order.data['Commission']
        amount = price * quantity - self.cost
        self.log('sold %f @ %s => %f %f %.2f%%' %
                 (quantity, btc2str(price),
                  amount, self.amount,
                  (amount / self.amount - 1) * 100))
        self.amount = amount
        self.quantity = 0
        self.entry = None
        self.virtual_stop = None
        self.status = 'searching'

    def set_stop(self, value):
        if not self.virtual_stop or self.virtual_stop != value:
            self.virtual_stop = value
            self.log('Setting virtual stop to %s' % btc2str(value))


trading_plan_class = AutoBBRsiTradingPlan

# auto_bbrsi_tp.py ends here
