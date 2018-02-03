'''
'''

import argparse
import sys

from trading_plan import TradingPlan
from utils import (btc2str, red, green)


# Idea from https://tradingstrategyguides.com/ripple-trading-strategy/
class RippleTradingPlan(TradingPlan):
    def __init__(self, exch, name, arguments, buy):
        parser = argparse.ArgumentParser(prog=name)
        parser.add_argument('pair', help='pair of crypto like BTC-ETH')
        parser.add_argument('amount',
                            help='quantity of currency to use for the trade',
                            type=float)
        args = parser.parse_args(arguments)

        self.pair = args.pair
        self.amount = args.amount
        self.entry = None
        self.stop = None
        self.stop_order = None
        self.cost = 0
        self.quantity = 0

        super().__init__(exch, name, arguments, buy)

        self.ticks = self.init_dataframes()
        if buy:
            last_row = self.df.iloc[-1]
            if last_row.name.hour > 10:
                self.status = 'midnight'
            else:
                idx = -2
                while True:
                    row = self.df.iloc[idx]
                    if row.name.hour == 0 and row.name.minute == 0:
                        self.midnight_price = row['O']
                        self.log('Midnight price %s' %
                                 btc2str(self.midnight_price))
                        self.status = 'nine'
                        break
                    idx -= 1
                else:
                    self.status = 'midnight'
        else:
            self.status = 'recovering'

        self.log('%s amount=%s %s' %
                 (name, btc2str(self.amount), self.status))

    def process_tick(self):
        self.update_dataframe(self.tick)

        # Put a stop if needed but let the trade logic continue if it is not
        # reached
        self.check_stop(self.tick)

        self.dispatch_tick(self.status, self.tick)

        if self.status not in ('midnight', 'nine'):
            self.log('%s %s %s-%s %s (%f x %s)' %
                     (self.status,
                      btc2str(self.tick['C']),
                      btc2str(self.tick['L']),
                      btc2str(self.tick['H']),
                      btc2str(self.amount),
                      self.quantity, btc2str(self.entry)))
        return(self.amount > 0)

    def check_stop(self, tick):
        if self.stop:
            if tick['L'] < self.stop:
                stop = tick['L'] * 0.99
                self.log('stop reached. Putting a physical stop @ %s' %
                         btc2str(stop))
                self.sell_stop(self.quantity, stop)
                self.stop = None
                self.stop_order = True
                return True
        if self.stop_order:
            # buy order has been sent
            if self.order and self.order.is_buy_order():
                self.stop_order = None
            elif self.monitor_order_completion('stop '):
                self.compute_gains(tick, self.stop_order)
                past_orders = self.exch.get_order_history(self.pair)
                if len(past_orders) == 0:
                    self.log('Unable to find sell order. Aborting.')
                    sys.exit(1)
                self.compute_gains(tick, past_orders[0])
                self.stop_order = None
                return True
        return False

    def process_tick_midnight(self, tick):
        if tick['T'].hour == 0:
            self.midnight_price = tick['O']
            self.log('Midnight price %s' % btc2str(self.midnight_price))
            self.status = 'nine'

    def process_tick_nine(self, tick):
        if tick['T'].hour == 9:
            if self.midnight_price > tick['C'] * 1.05:
                self.status = 'buying'
                self.entry = tick['C']
                self.quantity = self.amount / self.entry
                self.send_order(self.exch.buy_limit,
                                self.pair, self.quantity,
                                self.entry)
                self.log('%s %f @ %s' %
                         (green('buying'), self.quantity, btc2str(self.entry)))
            else:
                self.log('%s: %s < %s. retrying tomorrow. %s' %
                         (red('no up trend'),
                          btc2str(self.midnight_price),
                          btc2str(tick['C'] * 1.05),
                          btc2str(self.amount)))
                self.status = 'midnight'

    def process_tick_buying(self, tick):
        if tick['T'].hour == 10:
            self.do_cancel_order()
        elif self.monitor_order_completion('buy'):
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
            self.target = self.entry + self.entry - self.midnight_price
            self.log('setting target to %s' % btc2str(self.target))
            self.send_order(self.exch.sell_limit,
                            self.pair, self.quantity,
                            self.target)
            self.status = 'selling'

    def process_tick_selling(self, tick):
        if self.monitor_order_completion('sell'):
            past_orders = self.exch.get_order_history(self.pair)
            if len(past_orders) == 0:
                self.log('Unable to find sell order. Aborting.')
                sys.exit(1)
            order = past_orders[0]
            price = order.data['PricePerUnit']
            quantity = order.data['Quantity']
            self.cost += order.data['Commission']
            amount = price * quantity - self.cost
            self.log('sold %f @ %s => %s %s %.2f%%' %
                     (quantity, btc2str(price),
                      btc2str(amount), btc2str(self.amount),
                      (amount / self.amount - 1) * 100))
            self.amount = amount
            self.quantity = 0
            self.entry = None
            self.stop = None
            self.stop_order = True
            self.status = 'midnight'


trading_plan_class = RippleTradingPlan

# ripple.py ends here
