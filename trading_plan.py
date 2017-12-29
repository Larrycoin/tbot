'''
'''


def btc2str(val):
    return '%.2fS' % (val * 1000000)


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
        self.update_open_orders()
        for order in self.open_orders:
            print(order)
        self.update_position()
        print('Balance = %.3f Available = %.3f' % (self.balance,
                                                   self.available))

    def update_position(self):
        position = self.exch.get_position(self.pair.split('-')[1])
        if 'Balance' in position:
            self.balance = position['Balance']
        else:
            self.balance = 0
        if 'Available' in position:
            self.available = position['Available']
        else:
            self.available = 0

    def update_open_orders(self):
        self.open_orders = self.exch.get_open_orders(self.pair)
        if len(self.open_orders) > 0:
            self.order = self.open_orders[0]
        else:
            self.order = None

    def process_tick(self, tick):
        print('%s %s %s %s-%s' % (tick['T'][11:], self.pair,
                                  btc2str(tick['C']),
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
        if self.order and self.exch.cancel_order(self.order):
            self.order = None
        new_order = func(*args, **kwargs)
        if new_order:
            print(new_order)
            self.order = new_order
        return self.order

    def monitor_order_completion(self, msg):
        self.update_open_orders()
        if self.order is None:
            print(msg + 'order completed')
            return True
        else:
            print(msg + 'order still in place')
            return False


trading_plan_class = TradingPlan

# trading_plan.py ends here
