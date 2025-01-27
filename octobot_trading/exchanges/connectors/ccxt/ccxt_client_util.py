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
import logging
import ccxt

import octobot_trading.constants as constants
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums


def create_client(exchange_class, exchange_name, exchange_manager, logger, 
                  options, headers, additional_config, 
                  should_authenticate, unauthenticated_exchange_fallback=None):
    """
    Exchange instance creation
    :return: the created ccxt (pro, async or sync) client
    """
    is_authenticated = False
    if not exchange_manager.exchange_only:
        # avoid logging version on temporary exchange_only exchanges
        logger.info(f"Creating {exchange_class.__name__} exchange with ccxt in version {ccxt.__version__}")
    if exchange_manager.ignore_config or exchange_manager.check_config(exchange_name):
        try:
            key, secret, password = exchange_manager.get_exchange_credentials(exchange_name)
            if not (key and secret) and not exchange_manager.is_simulated:
                logger.warning(f"No exchange API key set for {exchange_manager.exchange_name}. "
                               f"Enter your account details to enable real trading on this exchange.")
            if should_authenticate:
                client = exchange_class(_get_client_config(options, headers, additional_config,
                                                           key, secret, password))
                is_authenticated = True
                if exchange_manager.check_credentials:
                    client.checkRequiredCredentials()
            else:
                client = exchange_class(_get_client_config(options, headers, additional_config))
        except (ccxt.AuthenticationError, Exception) as e:
            if unauthenticated_exchange_fallback is None:
                return get_unauthenticated_exchange(
                    exchange_class, options, headers, additional_config
                ), False
            return unauthenticated_exchange_fallback(e), False
    else:
        client = get_unauthenticated_exchange(exchange_class, options, headers, additional_config)
        logger.error("configuration issue: missing login information !")
    client.logger.setLevel(logging.INFO)
    _use_http_proxy_if_necessary(client)
    return client, is_authenticated


def get_unauthenticated_exchange(exchange_class, options, headers, additional_config):
    client = exchange_class(_get_client_config(options, headers, additional_config))
    _use_http_proxy_if_necessary(client)
    return client


def set_sandbox_mode(client, is_sandboxed):
    client.setSandboxMode(is_sandboxed)


def get_ccxt_client_login_options(exchange_manager):
    """
    :return: ccxt client login option dict, can be overwritten to custom exchange login
    """
    if exchange_manager.is_future:
        return {'defaultType': 'future'}
    if exchange_manager.is_margin:
        return {'defaultType': 'margin'}
    return {'defaultType': 'spot'}


def get_symbols(client):
    try:
        return set(client.symbols)
    except (AttributeError, TypeError):
        # ccxt exchange load_markets failed
        return set()


def get_time_frames(client):
    try:
        return set(client.timeframes)
    except (AttributeError, TypeError):
        # ccxt exchange describe() is invalid
        return set()


def get_exchange_pair(client, pair) -> str:
    if pair in client.symbols:
        try:
            return client.market(pair)["id"]
        except KeyError:
            pass
    raise ValueError(f'{pair} is not supported')


def get_pair_cryptocurrency(client, pair) -> str:
    if pair in client.symbols:
        try:
            return client.market(pair)["base"]
        except KeyError:
            pass
    raise ValueError(f'{pair} is not supported')


def get_contract_size(client, pair) -> float:
    return client.markets[pair][ccxt_enums.ExchangeConstantsMarketStatusCCXTColumns.CONTRACT_SIZE.value]


def add_headers(client, headers_dict):
    """
    Add new headers to ccxt client
    :param headers_dict: the additional header keys and values as dict
    """
    for header_key, header_value in headers_dict.items():
        client.headers[header_key] = header_value


def add_options(client, options_dict):
    """
    Add new options to ccxt client
    :param options_dict: the additional option keys and values as dict
    """
    for option_key, option_value in options_dict.items():
        client.options[option_key] = option_value


def _use_http_proxy_if_necessary(client):
    client.aiohttp_trust_env = constants.ENABLE_EXCHANGE_HTTP_PROXY_FROM_ENV


def _get_client_config(options, headers, additional_config, api_key=None, secret=None, password=None):
    config = {
        'verbose': constants.ENABLE_CCXT_VERBOSE,
        'enableRateLimit': constants.ENABLE_CCXT_RATE_LIMIT,
        'timeout': constants.DEFAULT_REQUEST_TIMEOUT,
        'options': options,
        'headers': headers
    }
    if api_key is not None:
        config['apiKey'] = api_key
    if secret is not None:
        config['secret'] = secret
    if password is not None:
        config['password'] = password
    config.update(additional_config or {})
    return config
