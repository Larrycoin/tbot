'''
'''

import argparse
import sys

from trading_plan import TradingPlan
from utils import btc2str
from utils import str2btc


TEN8 = 100000000


def MA(df, n, price='C', name=None):
    """
    Moving Average
    """
    if not name:
        name = 'MA_' + str(n)
    df[name] = df[price].rolling(window=n, center=False).mean()
    return df


def ATR(df, n=20, name=None):
    if name is None:
        name = 'ATR_%d' % n
    df['TR1'] = abs(df['H'] - df['L'])
    df['TR2'] = abs(df['H'] - df['C'].shift())
    df['TR3'] = abs(df['L'] - df['C'].shift())
    df['TrueRange'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)
    MA(df, n, price='TrueRange', name=name)
    df[name] = ((n - 1) * df[name].shift() + df['TrueRange']) / n
    del df['TR1']
    del df['TR2']
    del df['TR3']
    del df['TrueRange']
    return df


def ATR_STP(df, name=None):
    if name is None:
        name = 'ATR_STP'
    ATR(df)
    df['L1'] = df['L'].shift()
    df['L2'] = df['L'].shift(2)
    df['L3'] = df['L'].shift(3)
    df[name] = (df[['L1', 'L2', 'L3']].min(axis=1) -
                (df['ATR_20'] / 3))
    del df['L1']
    del df['L2']
    del df['L3']
    del df['ATR_20']
    return df


class TrailingTradingPlan(TradingPlan):
    def __init__(self, exch, name, arguments, buy):
        parser = argparse.ArgumentParser(prog=name)
        parser.add_argument(
            '-r', "--range",
            help='floating number to compute buy range. Default 0.09.',
            type=float, default=0.09)
        parser.add_argument('-t', "--trailing", help='force trailing mode',
                            action="store_true")
        parser.add_argument(
            '-p', "--period",
            help='initial period to check acceleration in trailing mode.'
            ' Default 60.',
            type=int, default=60)
        parser.add_argument('pair', help='pair of crypto like BTC-ETH')
        parser.add_argument('quantity', help='quantity of coins or ALL')
        parser.add_argument('stop', help='stop level')
        parser.add_argument('entry', help='entry level')
        parser.add_argument('target', help='target level')
        args = parser.parse_args(arguments)

        self.pair = args.pair
        self.stop_price = str2btc(args.stop)
        self.entry_price = str2btc(args.entry)
        self.target_price = str2btc(args.target)
        self.trail_price = None
        self.trailing = args.trailing
        self.df = None
        self.period = args.period
        self.range = args.range
        self.tick = None

        if args.quantity == 'ALL':
            if self.balance == 0:
                self.log('ALL specified and no existing position. Aborting.')
                sys.exit(1)
            self.quantity = self.balance
        else:
            self.quantity = float(args.quantity)

        super().__init__(exch, name, arguments, buy)

        print('%s %s stop=%s entry=%s target=%s quantity=%.3f\n'
              '  trailing=%s period=%d range=%f buy=%s' %
              (self.name, self.pair, btc2str(self.stop_price),
               btc2str(self.entry_price), btc2str(self.target_price),
               self.quantity, self.trailing, self.period, self.range,
               self.buy))

        if self.buy:
            if not self.do_buy_order(self.stop_price, self.entry_price,
                                     self.range):
                sys.exit(1)
        self.status = 'buying'

    def process_tick(self):
        if self.status == 'buying':
            return self.process_tick_buying(self.tick, self.stop_price,
                                            self.quantity / 2)
        else:
            return self.process_tick_position(self.tick)

    def process_tick_position(self, tick):
        self.check_order()
        last = tick['C']
        if last < self.entry_price:
            if (tick['L'] < self.stop_price and
               self.monitor_order_completion('Stop reached: ')):
                return False
            elif self.status != 'down':
                self.sell_stop(self.quantity, self.stop_price)
                self.status = 'down'
        else:
            if self.trailing or tick['H'] > self.target_price:
                if not self.trailing:
                    if not self.monitor_order_completion('Target reached: '):
                        return True
                self.trailing = True

                if (self.trail_price and tick['L'] < self.trail_price and
                   self.monitor_order_completion('Stop reached: ')):
                    return False

                # do the trend following
                if self.df is None:
                    self.init_dataframes()

                self.update_dataframe(tick)

                trail_price = self.compute_stop()

                if trail_price != self.trail_price:
                    self.log('new trailing stop %s (prev %s) (period %d mn)' %
                             (btc2str(trail_price), btc2str(self.trail_price),
                              self.period))
                    self.trail_price = trail_price
                    self.sell_stop(self.quantity / 2, self.trail_price)
            elif self.status != 'up':
                self.sell_limit(self.quantity / 2, self.target_price)
                self.status = 'up'
        self.log('%s %s %s-%s' %
                 (self.status2str(),
                  btc2str(tick['C']),
                  btc2str(tick['L']),
                  btc2str(tick['H'])))
        return True

    def status2str(self):
        if self.trailing:
            return 'trailing(%s)' % btc2str(self.trail_price)
        elif self.status == 'down':
            return 'down(%s)' % btc2str(self.stop_price)
        elif self.status == 'up':
            return 'up(%s)' % btc2str(self.target_price)
        else:
            return self.status

    def compute_stop(self):
        risk = self.entry_price - self.stop_price
        period = self.period

        while True:
            ndf = self.resample_dataframes(period)
            last_row = ndf.iloc[-1]
            prev_row = ndf.iloc[-2]
            last = ndf.tail(4)
            high = last['H'].max()
            low = last['L'].min()

            # Climax Run test
            if ((high - low) < (3.5 * risk)):
                break
            else:
                period = period // 2
                self.log('Downsampling to %d mn risk=%.8f size=%.8f' %
                         (period, risk, last_row['H'] - last_row['L']))
            if period <= 15:
                break
        ATR_STP(ndf)
        trail_price = max(ndf.tail()['ATR_STP'].values[-1], self.entry_price)
        trail_price = int(trail_price * TEN8) / TEN8
        del ndf
        return trail_price


trading_plan_class = TrailingTradingPlan

# targets_trading_plan.py ends here
