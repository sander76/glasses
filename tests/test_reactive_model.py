import gc
from unittest.mock import Mock

from glasses.reactive_model import Reactr, ReactrModel


class Model(ReactrModel):
    value1 = Reactr[int](10)
    value2 = Reactr[int](12)


class Controller:
    def __init__(self, values: Model) -> None:
        self._values = values
        self.value_1_mock = Mock()
        self.value_2_mock = Mock()

        values.subscribe("value1", self._update_value1)
        values.subscribe("value2", self._update_value_2)

    def _update_value1(self, value):
        self.value_1_mock(value)

    def _update_value_2(self, value):
        self.value_2_mock(value)


def test_default_reactr_values():
    model = Model()

    assert model.value1 == 10
    assert model.value2 == 12


def test_subscription_working():
    values = Model()
    controller = Controller(values=values)

    values.value1 = 20
    values.value2 = 30

    controller.value_1_mock.assert_called_once_with(20)
    controller.value_2_mock.assert_called_once_with(30)


def test_unsubscribe_on_object_destroy():
    values = Model()
    controller = Controller(values=values)

    assert len(values._subscriptions["value1"]) == 1
    assert len(values._subscriptions["value2"]) == 1

    del controller
    gc.collect()

    values.value1 = 20
    values.value2 = 30

    assert len(values._subscriptions["value1"]) == 0
    assert len(values._subscriptions["value2"]) == 0


def test_multiple_controllers():
    values = Model()

    controller_1 = Controller(values=values)
    controller_2 = Controller(values=values)

    values.value1 = 20

    controller_1.value_1_mock.assert_called_once_with(20)
    controller_2.value_1_mock.assert_called_once_with(20)
