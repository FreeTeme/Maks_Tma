from abc import ABC, abstractmethod
import logging

class BaseParser(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_staking_info(self, coin: str) -> dict:
        """Возвращает данные в формате: {'exchange': str, 'apy': float}"""
        pass

    def normalize_coin_name(self, coin: str) -> str:
        """Приводим название монеты к формату биржи"""
        return coin.upper()