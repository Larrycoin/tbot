'''
'''

import sys

from trading_plan import btc2str
from trading_plan import str2btc
from trading_plan import TradingPlan


class TargetsTradingPlan(TradingPlan):
    def __init__(self, exch, name, args, buy):
        if len(args) < 4:
            print('Usage: %s [-b] <pair> ALL|<quantity> '
                  '<stop price> <entry price> '
                  '<target1 price> [<target2 price>...]')
            sys.exit(1)
        super().__init__(exch, name, args, buy)

        self.number = len(args) - 4
        self.stop_price = str2btc(args[2])
        self.entry_price = str2btc(args[3])
        self.targets = [str2btc(arg) for arg in args[4:]]

        if args[1] == 'ALL':
            if self.balance == 0:
                self.log(None,
                         'ALL specified and no existing position. Aborting.')
                sys.exit(1)
            self.quantity = self.balance
        else:
            self.quantity = float(args[1])

        self.log(None,
                 '%s %s stop=%s entry=%s quantity=%.3f buy=%s' %
                 (self.name, self.pair, btc2str(self.stop_price),
                  btc2str(self.entry_price),
                  self.quantity, self.buy))

        self.log(None,
                 '%d targets: %s' % (self.number,
                                     ' '.join([btc2str(t)
                                               for t in self.targets])))

        if self.buy:
            self.status = 'buying'
            if not self.do_buy_order(self.stop_price, self.entry_price):
                sys.exit(1)
        else:
            self.status = 'unknown'

    def process_tick(self, tick):
        if self.status == 'buying':
            return self.process_tick_bying(tick, self.stop_price,
                                           self.quantity / self.number)
        else:
            return self.process_tick_position(tick)

    def process_tick_position(self, tick):
        self.check_order()
        last = tick['C']
        if last < self.entry_price:
            if (tick['L'] < self.stop_price and
               self.monitor_order_completion('Stop reached: ')):
                return False
            elif self.status != 'down':
                for order in self.update_open_orders():
                    self.exch.cancel_order(self.order)
                self.order = None
                self.sell_stop(self.quantity, self.stop_price)
                self.status = 'down'
        else:
            if (tick['H'] > self.targets[-1] and
               self.monitor_order_completion('Last target reached: ')):
                return False
            elif self.status != 'up':
                for limit in self.targets[:-1]:
                    if limit:
                        self.sell_limit(self.quantity / self.number, limit)
                        self.order = None
                self.sell_limit(self.quantity - (self.quantity *
                                                 (self.number - 1)
                                                 / self.number),
                                self.targets[-1])
                self.status = 'up'
            else:
                for idx in range(len(self.targets)):
                    if tick['H'] > self.targets[idx]:
                        self.log(tick, 'target %d reached (%s)' %
                                 (idx + 1, btc2str(self.targets[idx])))
                        self.targets[idx] = None
        self.log(tick, '%s %s %s-%s' % (self.status,
                                        btc2str(tick['C']),
                                        btc2str(tick['L']),
                                        btc2str(tick['H'])))
        return True


trading_plan_class = TargetsTradingPlan

# targets_trading_plan.py ends here
