#!/usr/bin/env python

from bittrex_exchange import BittrexExchange

exch = BittrexExchange(True)

balances = exch.get_balances()
total = 0

for b in balances:
    bb = b['Balance']
    if bb['Balance'] > 0 or bb['Available'] > 0:
        btc = b.get('BitcoinMarket', None)
        if btc:
            val = btc['Last'] * bb['Balance']
            print('[%s] balance: %.8f available %.8f value %.8f BTC' %
                  (bb['Currency'], bb['Balance'], bb['Available'], val))
            total += val
        else:
            print('[%s] balance: %.8f available %.8f' %
                  (bb['Currency'], bb['Balance'], bb['Available']))
            if bb['Currency'] == 'BTC':
                total += bb['Balance']
print()
print('Total %.8f BTC' % total)
