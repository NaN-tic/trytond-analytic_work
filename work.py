from trytond.model import fields, ModelSQL
from trytond.pool import Pool, PoolMeta
from decimal import Decimal

__metaclass__ = PoolMeta

__all__ = ['Line', 'TimesheetWork', 'AnalyticTimesheetRelation',
    'AnalyticLine']

_ZERO = Decimal('0.00')


class TimesheetWork:
    __name__ = 'timesheet.work'

    account = fields.Many2One('analytic_account.account', 'Analytic Account')


class AnalyticLine:
    __name__ = 'analytic_account.line'

    timesheet_line = fields.One2One(
        'analytic_account.line-timesheet.line',
        'analytic_line', 'timesheet_line', 'Timesheet Line')

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default.setdefault('timesheet_line', None)
        return super(AnalyticLine, cls).copy(lines, default=default)


class Line:
    __name__ = 'timesheet.line'

    analytic_line = fields.One2One(
        'analytic_account.line-timesheet.line',
        'timesheet_line', 'analytic_line', 'Analytic Line')

    def get_analytic_line_values(self):
        val = {
            'name': self.description or self.work.name,
            'debit': _ZERO,
            'credit': self.compute_cost(),
            'account': self.work.account.id,
            'date': self.date,
            'active': True,
            'timesheet_line': self.id,
        }
        return val

    def create_analytic_line(self):
        AnalyticLine = Pool().get('analytic_account.line')
        values = self.get_analytic_line_values()
        AnalyticLine.create([values])

    def check_analytic_line(self):
        if not self.work.account:
            return
        if self.analytic_line:
            self.update_analytic_line()
        else:
            self.create_analytic_line()

    def update_analytic_line(self):
        line = self.analytic_line
        line.credit = self.compute_cost()
        line.date = self.date
        line.save()

    @classmethod
    def create(cls, vlist):
        lines = super(Line, cls).create(vlist)
        for line in lines:
            line.check_analytic_line()
        return lines

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        args = []
        fields = ['hours', 'employee', 'date', 'company']
        update_records = []
        for records, values in zip(actions, actions):
            for field in fields:
                if values.get(field):
                    update_records += records
                    break
            args.extend((records, values))
        super(Line, cls).write(*args)

        for r in list(set(update_records)):
            r.check_analytic_line()

    @classmethod
    def delete(cls, lines):
        analytic_lines = [x.analytic_line for x in lines if x.analytic_line]
        AnalyticLine = Pool().get('analytic_account.line')
        AnalyticLine.delete(analytic_lines)
        super(Line, cls).delete(lines)

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        default.setdefault('analytic_line', None)
        return super(Line, cls).copy(lines, default=default)


class AnalyticTimesheetRelation(ModelSQL):
    'Analtyic Line - Timesheet Line'
    __name__ = 'analytic_account.line-timesheet.line'

    analytic_line = fields.Many2One('analytic_account.line',
         'Analytic Line', ondelete='CASCADE',
        required=True, select=True)
    timesheet_line = fields.Many2One('timesheet.line', 'Timesheet Line',
        ondelete='CASCADE', required=True, select=True)

    @classmethod
    def __setup__(cls):
        super(AnalyticTimesheetRelation, cls).__setup__()
        cls._sql_constraints += [
            ('analytic_line_unique', 'UNIQUE(analytic_line)',
                'The Analtyic Line must be unique.'),
            ('timesheet_line_unique', 'UNIQUE(timesheet_line)',
                'The Timesheet Line must be unique.'),
            ]
