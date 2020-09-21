# cython: language_level=3
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
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.


""" Order class will represent an open order in the specified exchange
In simulation it will also define rules to be filled / canceled
It is also use to store creation & fill values of the order """
from octobot_trading.portfolios.portfolio_manager cimport PortfolioManager
from octobot_trading.portfolios.portfolio_value_holder cimport PortfolioValueHolder

cdef class PortfolioProfitability:
    cdef object logger

    cdef PortfolioManager portfolio_manager
    cdef PortfolioValueHolder value_manager

    cdef public double profitability
    cdef public double profitability_percent
    cdef public double profitability_diff
    cdef public double market_profitability_percent
    cdef public double initial_portfolio_current_profitability

    cdef set traded_currencies_without_market_specific
    cdef public set traded_currencies

    cdef double _calculate_average_market_profitability(self)
    cdef void _reset_before_profitability_calculation(self)
    cdef void _update_profitability_calculation(self)
    cdef void _update_portfolio_delta(self)
    cdef dict _only_symbol_currency_filter(self, dict currency_dict)
    # cdef void _init_traded_currencies_without_market_specific(self) can't be cythonized for now