======================
Analytic Work Scenario
======================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install stock_reservation Module::

    >>> Module = Model.get('ir.module.module')
    >>> modules = Module.find([
    ...     ('name', 'in', ['analytic_work'])])
    >>> Module.install([x.id for x in modules], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

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
    ...     currency = Currency(name='US Dollar', symbol='$', code='USD',
    ...     rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...     mon_decimal_point='.')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...     rate=Decimal('1.0'), currency=currency).save()
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
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
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
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> account_tax, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('company', '=', company.id),
    ...         ('name', '=', 'Main Tax'),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')


Create analytic accounts::

    >>> AnalyticAccount = Model.get('analytic_account.account')
    >>> root = AnalyticAccount(type='root', name='Root')
    >>> root.save()
    >>> analytic_account = AnalyticAccount(root=root, parent=root,
    ...     name='Analytic')
    >>> analytic_account.save()

Create Employee::

    >>> Employee = Model.get('company.employee')
    >>> employee_party = Party(name='Employee')
    >>> employee_party.save()
    >>> employee = Employee(company=company, party=employee_party)
    >>> cost = employee.cost_prices.new()
    >>> cost.date = today
    >>> cost.cost_price = Decimal('10.0')
    >>> employee.save()

Create timesheet work::

    >>> Work = Model.get('timesheet.work')
    >>> work = Work(name='Work')
    >>> work.account = analytic_account
    >>> work.save()
    >>> work.save()

Create a timesheet line and check analytic account::

    >>> Line = Model.get('timesheet.line')
    >>> line = Line()
    >>> line.employee = employee
    >>> line.work = work
    >>> line.hours = 2.0
    >>> line.save()
    >>> analytic_account.reload()
    >>> analytic_account.debit
    Decimal('0.00')
    >>> analytic_account.credit
    Decimal('20.00')

If we modify the timesheet line the amount should be updated on analytic::

    >>> line.hours = 4.0
    >>> line.save()
    >>> analytic_account.reload()
    >>> analytic_account.debit
    Decimal('0.00')
    >>> analytic_account.credit
    Decimal('40.00')
