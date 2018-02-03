#!/usr/bin/env python

from bittrex_exchange import BittrexExchange
from trade import main
from replay import FakeExchange


class PaperExchange(FakeExchange):
    def __init__(self, real_exch):
        self.real_exch = real_exch
        super().__init__(100, 100, [])

    def get_tick(self, pair):
        return self.real_exch.get_tick(pair)

    def get_candles(self, pair, duration):
        return self.real_exch.get_candles(pair, duration)


if __name__ == "__main__":
    main(PaperExchange(BittrexExchange(False)))

# paper.py ends here
