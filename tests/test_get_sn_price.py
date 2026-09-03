from utils.index import get_sn_price


class DummyBalance:
    def __init__(self, tao):
        self.tao = tao


class DummySubtensor:
    def __init__(self):
        self.subnet_calls = []

    def subnet(self, netuid, block=None):
        self.subnet_calls.append((netuid, block))
        raise RuntimeError("Invalid type for data: 98 of type <class 'int'>")

    def get_subnet_prices(self, block=None):
        return {3: DummyBalance(1.23)}


def test_get_sn_price_falls_back_to_subnet_prices_when_subnet_call_fails():
    subtensor = DummySubtensor()

    price = get_sn_price(subtensor, 3)

    assert price == 1.23
    assert subtensor.subnet_calls == [(3, None)]

if __name__ == '__main__':
    test_get_sn_price_falls_back_to_subnet_prices_when_subnet_call_fails()
    print("Test passed.")