'''
'''

from abc import ABC
from abc import ABCMeta
from abc import abstractmethod


class Exchange(ABC):
    @abstractmethod
    def sell_limit(self, pair, quantity, value):
        pass

    @abstractmethod
    def sell_market(self, pair, quantity):
        pass

    @abstractmethod
    def sell_stop(self, pair, quantity, value):
        pass

    @abstractmethod
    def buy_limit(self, pair, quantity, value):
        pass

    @abstractmethod
    def buy_limit_range(self, pair, quantity, min_val, max_val):
        pass

    @abstractmethod
    def get_tick(self, pair):
        pass

    @abstractmethod
    def get_open_orders(self, pair):
        pass

    @abstractmethod
    def cancel_order(self, order):
        pass

    @abstractmethod
    def get_position(self, pair):
        pass

    @abstractmethod
    def update_order(self, order):
        pass


class OrderMeta(ABCMeta):
    _orders = {}

    def __call__(cls, *args, **kwargs):
        orderid = kwargs['id']
        if orderid not in cls._orders:
            cls._orders[orderid] = super(OrderMeta, cls).__call__(*args,
                                                                  **kwargs)
        else:
            cls._orders[orderid].update(*args, **kwargs)
        return cls._orders[orderid]


class Order(ABC, metaclass=OrderMeta):
    def __init__(self, *args, **kwargs):
        self.id = kwargs['id']
        self.update(*args, **kwargs)

    @abstractmethod
    def update(*args, **kwargs):
        pass

    @abstractmethod
    def is_buy_order(self):
        return False

    @abstractmethod
    def is_sell_order(self):
        return False
