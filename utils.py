'''
'''


def btc2str(val):
    if val:
        return '%.2fS' % (val * 1000000)
    else:
        return val


def str2btc(s):
    if not isinstance(s, str):
        val = s
    elif s[-1] == 's':
        val = float(s[:-1]) * 0.00000001
    elif s[-1] == 'S':
        val = float(s[:-1]) * 0.000001
    else:
        val = float(s)
    return val


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


def BB(df, price='C', length=20, numsd=2):
    """ returns average, upper band, and lower band"""
    df['BBM'] = df[price].rolling(window=length, center=False).mean()
    df['BBU'] = (df[price].rolling(window=length, center=False).mean() +
                 df[price].rolling(window=length, center=False).std() * numsd)
    df['BBL'] = (df[price].rolling(window=length, center=False).mean() -
                 df[price].rolling(window=length, center=False).std() * numsd)
    df['BBW'] = df[price].rolling(window=length,
                                  center=False).std() * 2 * numsd / df['BBM']
    return df


# utils.py ends here
