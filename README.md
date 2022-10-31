# Homework Bot
- [Введение](#введение)
- [Функционал проекта](#функционал-проекта)
- [Используемые технологии](#используемые-технологии)
- [Переменные окружения](#переменные-окружения)
- [Запуск приложения](#запуск-приложения)

## Введение
Проект homework_bot представляет из себя телеграм-бот для парсинга статуса проверки домашних работ в Яндекс.Практикуме.

## Функционал проекта:
Бот получает от апи Яндекс.Практикума статусы проверки домашних работ обучающихся и при изменении статуса отправляет оповещение в Телеграм пользователя. 

## Используемые технологии
При создании и разворачивании приложения использовались следующие технологии:
- ```python 3.7```
- ```python-telegram-bot 13.7```
- ```requests 2.26.0```
- ```docker```

## Переменные окружения
В директории infra репозитория находится файл ```all.env```, содержащий следующие переменные окружения:\
```TELEGRAM_TOKEN``` - секретный токен для телеграм-канала\
```PRACTICUM_TOKEN``` - секретный токен для авторизации в апи "Яндекс.Практикум"\
```TELEGRAM_CHAT_ID``` - ID УЗ в Телеграм, которой присылаются сообщения\
```DEBUG_LEVEL``` - уровень логирования

## Запуск приложения
Для запуска приложения перейдите в директорию infra и введите 
```
docker-compose up
```
