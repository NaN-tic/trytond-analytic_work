from trytond.model import fields, ModelSQL
from trytond.pool import Pool, PoolMeta
from decimal import Decimal

__metaclass__ = PoolMeta

__all__ = ['Line', 'TimesheetWork']

_ZERO = Decimal('0.00')


class TimesheetWork:
    __name__ = 'timesheet.work'

    account = fields.Many2One('analytic_account.account', 'Analytic Account')


class Line:
    __name__ = 'timesheet.line'

    analytic_line = fields.Many2One('analytic_account.line', 'Analytic Line',
        readonly=True)

    def get_analytic_line(self, line=None):
        pool = Pool()
        Journal = pool.get('account.journal')
        AnalyticLine = pool.get('analytic_account.line')
        if line is None:
            line = AnalyticLine()
            expense, = Journal.search([
                    ('type', '=', 'expense'),
                    ], limit=1)
            line.name = self.description or self.work.name
            line.journal = expense
            line.account = self.work.account
            line.debit = Decimal('0.0')
            line.active = True
        line.date = self.date
        line.credit = self.compute_cost()
        return line

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        AnalyticLine = pool.get('analytic_account.line')
        lines = super(Line, cls).create(vlist)
        analytic_lines, timesheet_lines = [], []
        for line in lines:
            analytic_line = line.get_analytic_line()
            if analytic_line:
                analytic_lines.append(analytic_line)
                timesheet_lines.append(line)
        if analytic_lines:
            analytic_lines = AnalyticLine.create([x._save_values
                    for x in analytic_lines])
            to_write = []
            for analytic, timesheet in zip(analytic_lines, timesheet_lines):
                to_write.extend(([timesheet], {
                            'analytic_line': analytic.id,
                            }))
            # Call super to avoid re-updating analytic_lines
            super(Line, cls).write(*to_write)
        return lines

    @classmethod
    def write(cls, *args):
        pool = Pool()
        AnalyticLine = pool.get('analytic_account.line')
        actions = iter(args)
        args = []
        fields = set(['hours', 'employee', 'date', 'company'])
        update_records = []
        for records, values in zip(actions, actions):
            if set(values) & fields:
                update_records += records
            args.extend((records, values))
        super(Line, cls).write(*args)

        to_write = []
        for r in list(set(update_records)):
            line = r.get_analytic_line(r.analytic_line)
            to_write.extend(([line], line._save_values))
        if to_write:
            AnalyticLine.write(*to_write)

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
