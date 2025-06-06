"""
Модуль для работы с RabbitMQ
Обеспечивает асинхронную обработку задач и интеграцию с очередями сообщений
"""
import os
import json
import logging
import asyncio
from typing import Any, Dict, Optional
import aio_pika
from aio_pika import Message, connect_robust
from aio_pika.abc import AbstractIncomingMessage

# Настройки подключения к RabbitMQ
DEFAULT_HOST = "localhost"
DEFAULT_USER = "guest"
DEFAULT_PASS = "guest"

class RabbitMQClient:
    """
    Клиент для работы с RabbitMQ
    Обеспечивает асинхронное взаимодействие с очередями сообщений
    """    
    def __init__(self, host=None, user=None, password=None):
        self.host = host or os.getenv("RABBITMQ_HOST", DEFAULT_HOST)
        self.user = user or os.getenv("RABBITMQ_DEFAULT_USER", DEFAULT_USER)
        self.password = password or os.getenv("RABBITMQ_DEFAULT_PASS", DEFAULT_PASS)
        self.connection = None
        self.channel = None
        self._logger = logging.getLogger(__name__)
        
    async def connect(self) -> None:
        """
        Установка соединения с RabbitMQ
        Создает устойчивое подключение и канал для обмена сообщениями
        """
        max_retries = 10
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                # Формируем URL для подключения
                rabbitmq_url = f"amqp://{self.user}:{self.password}@{self.host}:5672/"
                
                # Создаем устойчивое соединение, которое автоматически восстанавливается при разрыве
                self.connection = await connect_robust(rabbitmq_url)
                # Создаем канал для обмена сообщениями
                self.channel = await self.connection.channel()
                self._logger.info(f"Успешное подключение к RabbitMQ по адресу {self.host}")
                return
                
            except Exception as e:
                self._logger.warning(f"Attempt {attempt + 1}/{max_retries} to connect to RabbitMQ failed: {e}")
                if attempt < max_retries - 1:
                    self._logger.info(f"Waiting {retry_delay} seconds before next attempt...")
                    await asyncio.sleep(retry_delay)
                else:
                    self._logger.error("All connection attempts to RabbitMQ failed")
                    raise

    async def close(self) -> None:
        """
        Закрытие соединения с RabbitMQ
        Корректно закрывает канал и соединение
        """
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
        self._logger.info("Соединение с RabbitMQ закрыто")

    async def declare_queue(self, queue_name: str) -> aio_pika.Queue:
        """
        Объявление очереди в RabbitMQ
        
        Args:
            queue_name (str): Название очереди
            
        Returns:
            aio_pika.Queue: Объект очереди
        """
        # Создаем очередь с параметром durable=True для сохранения сообщений при перезапуске
        queue = await self.channel.declare_queue(
            queue_name,
            durable=True  # Очередь и сообщения сохраняются при перезапуске брокера
        )
        self._logger.info(f"Очередь {queue_name} объявлена")
        return queue

    async def publish_message(self, queue_name: str, message: Dict[str, Any]) -> None:
        """
        Публикация сообщения в очередь
        
        Args:
            queue_name (str): Название очереди
            message (Dict[str, Any]): Сообщение для отправки
        """
        try:
            # Создаем сообщение с persistent=True для гарантии доставки
            message_body = Message(
                json.dumps(message).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            # Публикуем сообщение в очередь
            await self.channel.default_exchange.publish(
                message_body,
                routing_key=queue_name
            )
            self._logger.info(f"Сообщение отправлено в очередь {queue_name}")
        except Exception as e:
            self._logger.error(f"Ошибка при отправке сообщения: {e}")
            raise

    async def consume_messages(
        self,
        queue_name: str,
        callback
    ) -> None:
        """
        Настройка получения сообщений из очереди
        
        Args:
            queue_name (str): Название очереди
            callback: Функция обработки сообщений
        """
        queue = await self.declare_queue(queue_name)
        
        async def process_message(message: AbstractIncomingMessage):
            """
            Внутренняя функция обработки сообщений
            Декодирует сообщение и вызывает пользовательский обработчик
            """
            async with message.process():
                try:
                    # Декодируем сообщение из JSON
                    message_body = json.loads(message.body.decode())
                    # Вызываем пользовательский обработчик
                    await callback(message_body)
                except Exception as e:
                    self._logger.error(f"Ошибка обработки сообщения: {e}")
                    # В случае ошибки сообщение будет возвращено в очередь
                    await message.reject(requeue=True)

        # Настраиваем получение сообщений из очереди
        await queue.consume(process_message)
        self._logger.info(f"Начато получение сообщений из очереди {queue_name}")
