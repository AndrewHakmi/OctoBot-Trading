# pylint: disable=E0611
#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import typing

import ccxt.async_support as ccxt
from octobot_commons import enums as common_enums

import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.exchanges.types as exchanges_types
import octobot_trading.exchanges.connectors as exchange_connectors
from octobot_trading.enums import ExchangeConstantsOrderColumns as ecoc


class SpotCCXTExchange(exchanges_types.SpotExchange):
    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.connector = exchange_connectors.CCXTExchange(config, exchange_manager)

    async def initialize_impl(self):
        await self.connector.initialize()
        self.symbols = self.connector.symbols
        self.time_frames = self.connector.time_frames

    async def stop(self) -> None:
        await self.connector.stop()
        self.exchange_manager = None

    @classmethod
    def is_supporting_exchange(cls, exchange_candidate_name) -> bool:
        return exchange_connectors.CCXTExchange.is_supporting_exchange(exchange_candidate_name)

    async def create_order(self, order_type: enums.TraderOrderType, symbol: str, quantity: float,
                           price: float = None, stop_price=None, **kwargs: dict) -> typing.Optional[dict]:
        try:
            created_order = await self._create_specific_order(order_type, symbol, quantity, price)
            # some exchanges are not returning the full order details on creation: fetch it if necessary
            if created_order and not SpotCCXTExchange._ensure_order_details_completeness(created_order):
                if ecoc.ID.value in created_order:
                    order_symbol = created_order[ecoc.SYMBOL.value] if ecoc.SYMBOL.value in created_order else None
                    created_order = await self.exchange_manager.exchange.get_order(created_order[ecoc.ID.value],
                                                                                   order_symbol, **kwargs)

            # on some exchange, market order are not not including price, add it manually to ensure uniformity
            if created_order[ecoc.PRICE.value] is None and price is not None:
                created_order[ecoc.PRICE.value] = price

            return self.clean_order(created_order)

        except ccxt.InsufficientFunds as e:
            self.logger.error(e, order_type, symbol, quantity, price, stop_price)
            self.logger.warning(str(e))
            raise errors.MissingFunds(e)
        except ccxt.NotSupported:
            raise errors.NotSupported
        except Exception as e:
            self.logger.error(e, order_type, symbol, quantity, price, stop_price)
            self.logger.error(e)
        return None

    async def _create_specific_order(self, order_type, symbol, quantity, price=None):
        created_order = None
        if order_type == enums.TraderOrderType.BUY_MARKET:
            created_order = await self.connector.client.create_market_buy_order(symbol, quantity)
        elif order_type == enums.TraderOrderType.BUY_LIMIT:
            created_order = await self.connector.client.create_limit_buy_order(symbol, quantity, price)
        elif order_type == enums.TraderOrderType.SELL_MARKET:
            created_order = await self.connector.client.create_market_sell_order(symbol, quantity)
        elif order_type == enums.TraderOrderType.SELL_LIMIT:
            created_order = await self.connector.client.create_limit_sell_order(symbol, quantity, price)
        elif order_type == enums.TraderOrderType.STOP_LOSS:
            created_order = None
        elif order_type == enums.TraderOrderType.STOP_LOSS_LIMIT:
            created_order = None
        elif order_type == enums.TraderOrderType.TAKE_PROFIT:
            created_order = None
        elif order_type == enums.TraderOrderType.TAKE_PROFIT_LIMIT:
            created_order = None
        elif order_type == enums.TraderOrderType.TRAILING_STOP:
            created_order = None
        elif order_type == enums.TraderOrderType.TRAILING_STOP_LIMIT:
            created_order = None
        return created_order

    @staticmethod
    def _ensure_order_details_completeness(order, order_required_fields=None):
        if order_required_fields is None:
            order_required_fields = [ecoc.ID.value, ecoc.TIMESTAMP.value, ecoc.SYMBOL.value, ecoc.TYPE.value,
                                     ecoc.SIDE.value, ecoc.PRICE.value, ecoc.AMOUNT.value, ecoc.REMAINING.value]
        return all(key in order for key in order_required_fields)

    def get_exchange_current_time(self):
        return self.connector.get_exchange_current_time()

    def get_uniform_timestamp(self, timestamp):
        return self.connector.get_uniform_timestamp(timestamp)

    def get_market_status(self, symbol, price_example=None, with_fixer=True):
        return self.connector.get_market_status(symbol, price_example=price_example, with_fixer=with_fixer)

    async def get_balance(self, **kwargs: dict):
        return await self.connector.get_balance(**kwargs)

    async def get_symbol_prices(self, symbol: str, time_frame: common_enums.TimeFrames, limit: int = None,
                                **kwargs: dict) -> typing.Optional[list]:
        return await self.connector.get_symbol_prices(symbol=symbol, time_frame=time_frame, limit=limit, **kwargs)

    async def get_kline_price(self, symbol: str, time_frame: common_enums.TimeFrames, **kwargs: dict) -> typing.Optional[list]:
        return await self.connector.get_kline_price(symbol=symbol, time_frame=time_frame, **kwargs)

    async def get_order_book(self, symbol: str, limit: int = 5, **kwargs: dict) -> typing.Optional[dict]:
        return await self.connector.get_order_book(symbol=symbol, limit=limit, **kwargs)

    async def get_recent_trades(self, symbol: str, limit: int = 50, **kwargs: dict) -> typing.Optional[list]:
        return await self.connector.get_recent_trades(symbol=symbol, limit=limit, **kwargs)

    async def get_price_ticker(self, symbol: str, **kwargs: dict) -> typing.Optional[dict]:
        return await self.connector.get_price_ticker(symbol=symbol, **kwargs)

    async def get_all_currencies_price_ticker(self, **kwargs: dict) -> typing.Optional[list]:
        return await self.connector.get_all_currencies_price_ticker(**kwargs)

    async def get_order(self, order_id: str, symbol: str = None, **kwargs: dict) -> dict:
        return await self.connector.get_order(symbol=symbol, order_id=order_id, **kwargs)

    async def get_all_orders(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_all_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    async def get_open_orders(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_open_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    async def get_closed_orders(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_closed_orders(symbol=symbol, since=since, limit=limit, **kwargs)

    async def get_my_recent_trades(self, symbol: str = None, since: int = None, limit: int = None, **kwargs: dict) -> list:
        return await self.connector.get_my_recent_trades(symbol=symbol, since=since, limit=limit, **kwargs)

    async def cancel_order(self, order_id: str, symbol: str = None, **kwargs: dict) -> bool:
        return await self.connector.cancel_order(symbol=symbol, order_id=order_id, **kwargs)

    def get_trade_fee(self, symbol, order_type, quantity, price, taker_or_maker):
        return self.connector.get_trade_fee(symbol, order_type, quantity, price, taker_or_maker)

    def get_fees(self, symbol):
        return self.connector.get_fees(symbol)

    def get_pair_from_exchange(self, pair) -> str:
        return self.connector.get_pair_from_exchange(pair)

    def get_split_pair_from_exchange(self, pair) -> (str, str):
        return self.connector.get_split_pair_from_exchange(pair)

    def get_exchange_pair(self, pair) -> str:
        return self.connector.get_exchange_pair(pair)

    def get_pair_cryptocurrency(self, pair) -> str:
        return self.connector.get_pair_cryptocurrency(pair)

    def get_default_balance(self):
        return self.connector.get_default_balance()

    def get_rate_limit(self):
        return self.connector.get_rate_limit()

    async def switch_to_account(self, account_type: enums.AccountTypes):
        return await self.connector.switch_to_account(account_type=account_type)

    def parse_balance(self, balance):
        return self.connector.parse_balance(balance)

    def parse_trade(self, trade):
        return self.connector.parse_trade(trade)

    def parse_order(self, order):
        return self.connector.parse_order(order)

    def parse_ticker(self, ticker):
        return self.connector.parse_ticker(ticker)

    def parse_ohlcv(self, ohlcv):
        return self.connector.parse_ohlcv(ohlcv)

    def parse_order_book(self, order_book):
        return self.connector.parse_order_book(order_book)

    def parse_order_book_ticker(self, order_book_ticker):
        return self.connector.parse_order_book_ticker(order_book_ticker)

    def parse_timestamp(self, data_dict, timestamp_key, default_value=None, ms=False):
        return self.connector.parse_timestamp(data_dict, timestamp_key, default_value=default_value, ms=ms)

    def parse_currency(self, currency):
        return self.connector.parse_currency(currency)

    def parse_order_id(self, order):
        return self.connector.parse_order_id(order)

    def parse_order_symbol(self, order):
        return self.connector.parse_order_symbol(order)

    def parse_status(self, status):
        return self.connector.parse_status(status)

    def parse_side(self, side):
        return self.connector.parse_side(side)

    def parse_account(self, account):
        return self.connector.parse_account(account)

    def clean_recent_trade(self, recent_trade):
        return self.connector.clean_recent_trade(recent_trade)

    def clean_trade(self, trade):
        return self.connector.clean_trade(trade)

    def clean_order(self, order):
        return self.connector.clean_order(order)
