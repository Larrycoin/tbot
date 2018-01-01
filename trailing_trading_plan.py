'''
'''

import sys

import pandas as pd
from pandas.io.json import json_normalize

from trading_plan import btc2str
from trading_plan import str2btc
from trading_plan import TradingPlan


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
    def __init__(self, exch, pair, args):
        if len(args) not in (4, 5):
            print('Usage: trailing_trading_plan <pair> [-b] ALL|<quantity> '
                  '<stop price> <entry price> '
                  '<target price>')
            sys.exit(1)
        super().__init__(exch, pair, args)

        self.buy = (args[0] == '-b')

        if self.buy:
            args = args[1:]

        self.stop_price = str2btc(args[1])
        self.entry_price = str2btc(args[2])
        self.target_price = str2btc(args[3])
        self.trail_price = None
        self.trailing = False
        self.df = None
        self.period = 60

        if args[0] == 'ALL':
            if self.balance == 0:
                self.log(None,
                         'ALL specified and no existing position. Aborting.')
                sys.exit(1)
            self.quantity = self.balance
        else:
            self.quantity = float(args[0])

        if self.buy:
            if not self.do_buy_order(self.stop_price, self.entry_price):
                sys.exit(1)
        self.status = 'buying'

    def process_tick(self, tick):
        if self.status == 'buying':
            return self.process_tick_bying(tick, self.stop_price,
                                           self.quantity / 2)
        else:
            return self.process_tick_position(tick)

    def process_tick_position(self, tick):
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
                self.trailing = True
                tick['T'] = pd.to_datetime(tick['T'])

                if (self.trail_price and tick['L'] < self.trail_price and
                   self.monitor_order_completion('Stop reached: ')):
                    return False

                # do the trend following
                if self.df is None:
                    self.init_dataframes()

                frame = pd.DataFrame(tick, index=[tick['T']])
                self.df = pd.concat([self.df, frame])

                trail_price = self.compute_stop()

                if trail_price != self.trail_price:
                    self.log(tick, 'new trailing stop %s (prev %s) (period %d mn)' %
                             (btc2str(trail_price), btc2str(self.trail_price),
                              self.period))
                    self.trail_price = trail_price
                    self.sell_stop(self.quantity / 2, self.trail_price)
            elif self.status != 'up':
                self.sell_limit(self.quantity / 2, self.target_price)
                self.status = 'up'
        self.log(tick, '%s %s %s-%s' %
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

    def init_dataframes(self):
        candles = self.exch.get_candles(self.pair, 'oneMin')
        self.df = json_normalize(candles)
        self.df['T'] = pd.to_datetime(self.df['T'])
        self.df = self.df.set_index('T')
        return self.df

    def compute_stop(self):
        ohlc_dict = {'O': 'first', 'H': 'max', 'L': 'min', 'C': 'last',
                     'V': 'sum', 'BV': 'sum'}
        DOWN = {60: 30, 30: 15, 15: 15}
        risk = self.entry_price - self.stop_price

        while True:
            ndf = self.df.resample(str(self.period) + 'T').apply(ohlc_dict)
            last_row = ndf.iloc[-1]
            prev_row = ndf.iloc[-2]
            # Conditions for not down sampling:
            # - not a green candle
            # - not a candle higher than previous candle
            # - acceleration below risk
            if ((last_row['C'] < last_row['O']) or
               (prev_row['H'] > last_row['H']) or
               (prev_row['C'] > last_row['C']) or
               (last_row['H'] - last_row['L']) < risk):
                break
            else:
                self.period = DOWN[self.period]
                self.log(None, 'Downsampling to %d mn risk=%.8f size=%.8f' %
                         (self.period, risk, last_row['H'] - last_row['L']))
            if self.period == 30:
                break
        ATR_STP(ndf)
        trail_price = max(ndf.tail()['ATR_STP'].values[-1], self.entry_price)
        del ndf
        return trail_price


trading_plan_class = TrailingTradingPlan

# targets_trading_plan.py ends here
