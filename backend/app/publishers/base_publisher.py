from abc import ABC, abstractmethod


class BasePublisher(ABC):

    @abstractmethod
    def publish(
        self,
        title: str,
        content: str,
    ):
        pass

    @abstractmethod
    def update(
        self,
        content_id: int,
        title: str,
        content: str,
    ):
        pass

    @abstractmethod
    def delete(
        self,
        content_id: int,
    ):
        pass