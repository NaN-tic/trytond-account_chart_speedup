# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .account import *


def register():
    Pool.register(
        AccountTemplate,
        TaxTemplate,
        module='account_chart_speedup', type_='model')
    Pool.register(
        CreateChart,
        module='account_chart_speedup', type_='wizard')
