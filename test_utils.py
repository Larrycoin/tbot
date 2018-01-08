import unittest

from utils import str2btc


class TestUtils(unittest.TestCase):

    def test_str2btc_float(self):
        self.assertEquals(str2btc('0.02'), 0.02)

    def test_str2btc_satoshi(self):
        self.assertEquals(str2btc('13200s'), 0.00013200)

    def test_str2btc_hundred_satoshi(self):
        self.assertEquals(str2btc('146.61S'), 0.00014661)


if __name__ == "__main__":
    unittest.main()

# test_monitor_trade.py ends here
