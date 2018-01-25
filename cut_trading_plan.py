'''
'''

import sys

from trading_plan import TradingPlan
from utils import btc2str
from utils import str2btc


class CutTradingPlan(TradingPlan):
    def __init__(self, exch, name, args, buy):
        if len(args) != 4:
            print('Usage: trade.py %s <pair> ALL|<quantity> '
                  '<stop price> <limit price>' % name)
            sys.exit(1)
        if buy:
            print('%s: no buy option in this trading plan.' % name)
            sys.exit(1)
        super().__init__(exch, name, args, buy)
        self.stop_price = str2btc(args[2])
        self.limit_price = str2btc(args[3])
        self.middle_price = (self.stop_price + self.limit_price) / 2
        if args[1] == 'ALL':
            if self.balance == 0:
                print('ALL specified and no existing position. Aborting.')
                sys.exit(1)
            self.quantity = self.balance
        else:
            self.quantity = float(args[1])
        self.status = 'unknown'

    def process_tick(self):
        self.check_order()
        last = self.tick['C']
        if last < self.middle_price:
            if (self.tick['L'] < self.stop_price and
               self.monitor_order_completion('Stop reached: ')):
                return False
            elif self.status != 'down':
                self.sell_stop(self.quantity, self.stop_price)
                self.status = 'down'
        else:
            if (self.tick['H'] > self.limit_price and
               self.monitor_order_completion('Limit reached: ')):
                return False
            elif self.status != 'up':
                self.sell_limit(self.quantity, self.limit_price)
                self.status = 'up'
        self.log('%s %s %s-%s' % (self.status,
                                  btc2str(self.tick['C']),
                                  btc2str(self.tick['L']),
                                  btc2str(self.tick['H'])))
        return True


trading_plan_class = CutTradingPlan

# cut_trading_plan.py ends here
