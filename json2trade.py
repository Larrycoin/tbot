#!/usr/bin/env python

import gzip
import json
import os
import sys

from bittrex_exchange import BittrexExchange


def main(args):
    if os.path.isfile(args[0]):
        with open(args[0]) as json_file:
            ticks = json.loads(json_file.read(-1))
    else:
        exch = BittrexExchange(False)
        ticks = exch.get_candles(args[0], 'oneMin')

    with gzip.open(args[1], 'w') as fout:
        data = {'candles': ticks,
                'plan': args[2],
                'pair': args[3],
                'balance': 0,
                'available': 0,
                'args': args[3:]}
        json_str = json.dumps(data) + '\n'
        json_bytes = json_str.encode('utf-8')
        fout.write(json_bytes)
    print('Trade saved')


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print('Usage: %s <json filename|pair name> <trade filename> '
              '<plan> <pair> [<args>...]' % sys.argv[0])
        sys.exit(1)
    main(sys.argv[1:])

# json2trade.py ends here
