'''
'''


def btc2str(val):
    if val:
        return '%.2fS' % (val * 1000000)
    else:
        return val


def str2btc(s):
    if s[-1] == 's':
        val = float(s[:-1]) * 0.00000001
    elif s[-1] == 'S':
        val = float(s[:-1]) * 0.000001
    else:
        val = float(s)
    return val


class TradingPlan(object):
    def __init__(self, exch, pair, args):
        self.exch = exch
        self.pair = pair
        self.args = args
        self.currency = self.pair.split('-')[1]
        self.sent_order = False
        self.update_open_orders()
        for order in self.open_orders:
            print(order)
        self.update_position()
        self.log(None, 'Balance = %.3f Available = %.3f' % (self.balance,
                                                            self.available))

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

    def log(self, tick, msg):
        if tick:
            if isinstance(tick['T'], str):
                print('%s %s %s' % (tick['T'][11:-3], self.pair, msg))
            else:
                print('%s %s %s' % (tick['T'].strftime('%H:%M'), self.pair, msg))
        else:
            print('%s %s' % (self.pair, msg))

    def process_tick(self, tick):
        self.log(tick, '%s %s-%s' % (btc2str(tick['C']),
                                     btc2str(tick['L']),
                                     btc2str(tick['H'])))
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
        new_order = func(*args, **kwargs)
        self.sent_order = True
        self.update_open_orders()
        if self.order:
            print('New order: %s' % self.order)

    def monitor_order_completion(self, msg):
        self.update_open_orders()
        if self.order is None:
            self.log(None, msg + 'order completed')
            return True
        else:
            self.log(None, msg + 'order still in place')
            return False

    def do_buy_order(self, stop, price, limit_range=0.09):
        if self.order:
            self.log(None,
                     'There is already an order. Aborting.')
            print(self.order)
            return False
        if self.balance > 0:
            self.log(None,
                     'There is already a position on %s (%.3f). Not buying.' %
                     (self.currency, self.balance))
            return False
        else:
            self.buy_range(self.quantity, price,
                           price + (price - stop) * limit_range)
            self.update_open_orders()
            return True

    def do_cancel_order(self):
        self.exch.cancel_order(self.order)
        print('Canceled order: %s' % self.order)
        self.order = None

    def process_tick_bying(self, tick, stop, quantity):
        self.check_order()
        if (self.balance < quantity and
           not (self.order and self.order.is_buy_order())):
            self.log(tick, 'Waiting for the buy order to become visible')
            self.update_open_orders()
        else:
            if tick['L'] < stop:
                self.log(tick, 'Trade invalidated (low price %.8f < %.8f), '
                         'cancelling order' %
                         (tick['L'], self.stop_price))
                self.do_cancel_order()
                return False
            self.update_position()
            if self.balance >= quantity:
                self.status = 'unknown'
            else:
                self.log(tick, 'Not the correct balance: %.3f instead of '
                         'more than %.3f' %
                         (self.balance, quantity))
        return True

    def check_order(self):
        if self.sent_order:
            self.update_open_orders()
            if not self.sent_order and self.order:
                print(self.order)

trading_plan_class = TradingPlan

# trading_plan.py ends here
