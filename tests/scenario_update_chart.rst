=====================
Update Chart Scenario
=====================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install account::

    >>> Module = Model.get('ir.module')
    >>> modules = Module.find([
    ...         ('name', 'in', ['account', 'account_chart_speedup']),
    ...         ])
    >>> Module.install([x.id for x in modules], config.context)
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='U.S. Dollar', symbol='$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point='.', mon_thousands_sep=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> account_template, = AccountTemplate.find([('parent', '=', None),
    ...         ('name', '=', 'Minimal Account Chart')])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')

Update a tax with childs::

    >>> Tax = Model.get('account.tax')
    >>> TaxTemplate = Model.get('account.tax.template')
    >>> Account = Model.get('account.account')
    >>> AccountTemplate = Model.get('account.account.template')
    >>> IrModel = Model.get('ir.model')
    >>> Access = Model.get('ir.model.access')

    >>> model, = IrModel.find([('model','=','account.tax.template')])
    >>> access, = Access.find([('model', '=', model.id)])
    >>> access.perm_create = True
    >>> access.perm_write = True
    >>> access.save()

    >>> cash_template, = AccountTemplate.find([('name', '=', 'Main Cash')])
    >>> account, = Account.find([('name', '=', 'Minimal Account Chart')])

    >>> ttemplate = TaxTemplate()
    >>> ttemplate.name = 'Tax 1'
    >>> ttemplate.description = 'Tax 1'
    >>> ttemplate.amount = Decimal('10')
    >>> ttemplate.type = 'fixed'
    >>> ttemplate.invoice_account = cash_template
    >>> ttemplate.credit_note_account = cash_template
    >>> ttemplate.account = account_template
    >>> ttemplate.save()

    >>> update_chart = Wizard('account.update_chart')
    >>> update_chart.form.account = account
    >>> update_chart.execute('update')

    >>> ttemplate2 = TaxTemplate()
    >>> ttemplate2.parent = ttemplate
    >>> ttemplate2.name = 'Tax 1A'
    >>> ttemplate2.description = 'Tax 1A'
    >>> ttemplate2.amount = Decimal('10')
    >>> ttemplate2.type = 'fixed'
    >>> ttemplate2.invoice_account = cash_template
    >>> ttemplate2.credit_note_account = cash_template
    >>> ttemplate2.account = account_template
    >>> ttemplate2.save()

    >>> ttemplate3 = TaxTemplate()
    >>> ttemplate3.parent = ttemplate
    >>> ttemplate3.name = 'Tax 1B'
    >>> ttemplate3.description = 'Tax 1B'
    >>> ttemplate3.amount = Decimal('10')
    >>> ttemplate3.type = 'fixed'
    >>> ttemplate3.invoice_account = cash_template
    >>> ttemplate3.credit_note_account = cash_template
    >>> ttemplate3.account = account_template
    >>> ttemplate3.save()

    >>> update_chart = Wizard('account.update_chart')
    >>> update_chart.form.account = account
    >>> update_chart.execute('update')

    >>> taxes = Tax.find([])
    >>> len(taxes[0].childs)
    2
