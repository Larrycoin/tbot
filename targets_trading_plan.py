'''
'''

import sys

from trading_plan import TradingPlan
from utils import btc2str
from utils import str2btc


class TargetsTradingPlan(TradingPlan):
    def __init__(self, exch, name, args, buy):
        if len(args) < 4:
            print('Usage: %s [-b] <pair> ALL|<quantity> '
                  '<stop price> <entry price> '
                  '<target1 price> [<target2 price>...]')
            sys.exit(1)
        super().__init__(exch, name, args, buy)

        self.stop_price = str2btc(args[2])
        self.entry_price = str2btc(args[3])
        self.number = len(args) - 4
        self.targets = [str2btc(arg) for arg in args[4:]]
        reached = [-arg for arg in self.targets if arg < 0]
        stops = [self.stop_price, self.entry_price] + \
                [abs(arg) for arg in self.targets]
        self.targets = [arg if arg > 0 else None for arg in self.targets]
        self.stop_entry = {}
        for idx in range(len(stops) - 1):
            self.stop_entry[stops[idx + 1]] = stops[idx]
        if len(reached) > 0:
            self.stop_price = self.stop_entry[reached[-1]]
            self.entry_price = reached[-1]
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
                                     ' '.join([btc2str(t) if t else 'reached'
                                               for t in self.targets])))

        if self.buy:
            self.status = 'buying'
            if not self.do_buy_order(self.stop_price, self.entry_price):
                sys.exit(1)
        else:
            self.status = 'unknown'
            for order in self.update_open_orders():
                self.log(None, 'Canceling %s' % order)
                self.exch.cancel_order(order)
            self.order = None

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
                    self.log(tick, 'Canceling %s' % order)
                    self.exch.cancel_order(order)
                if len(self.update_open_orders()) != 0:
                    return True
                self.order = None
                remain = len([t for t in self.targets if t])
                self.sell_stop(self.quantity * remain / self.number,
                               self.stop_price)
                self.status = 'down'
        else:
            if (tick['H'] > self.targets[-1] and
               self.monitor_order_completion('Last target reached: ')):
                return False
            elif self.status != 'up':
                for limit in self.targets[:-1]:
                    if limit:
                        self.log(tick, 'Limit order %.3f @ %s' %
                                 (self.quantity / self.number, btc2str(limit)))
                        self.sell_limit(self.quantity / self.number, limit)
                        self.order = None
                if self.targets[-1]:
                    self.log(tick, 'Limit order %.3f @ %s' %
                             (self.quantity - (self.quantity *
                                               (self.number - 1)),
                              btc2str(self.targets[-1])))
                    self.sell_limit(self.quantity - (self.quantity *
                                                     (self.number - 1)
                                                     / self.number),
                                    self.targets[-1])
                self.status = 'up'
            else:
                for idx in range(len(self.targets)):
                    if self.targets[idx] and tick['H'] >= self.targets[idx]:
                        self.stop_price = self.stop_entry[self.targets[idx]]
                        self.entry_price = self.targets[idx]
                        self.log(tick, 'target %d reached (%s). '
                                 'new stop=%s new entry=%s' %
                                 (idx + 1, btc2str(self.targets[idx]),
                                  btc2str(self.stop_price),
                                  btc2str(self.entry_price)))
                        self.targets[idx] = None
        self.log(tick, '%s %s %s-%s' % (self.status,
                                        btc2str(tick['C']),
                                        btc2str(tick['L']),
                                        btc2str(tick['H'])))
        return True


trading_plan_class = TargetsTradingPlan

# targets_trading_plan.py ends here
