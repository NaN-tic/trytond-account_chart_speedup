#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


__all__ = ['AccountTemplate', 'CreateChart', 'TaxTemplate', 'UpdateChart']


__metaclass__ = PoolMeta


class AccountTemplate:
    __name__ = 'account.account.template'

    def save_account(self, accounts):
        def get_parent(created_accounts, code):
            for acc in created_accounts:
                if acc.code == code:
                    return acc

        Account = Pool().get('account.account')

        childs = {}
        for account in accounts:
            childs[account] = account.childs
            account.childs = []

        vals = [x._save_values for x in accounts]

        created_accounts = Account.create(vals)
        new_accounts = []
        for account, childs2 in childs.iteritems():
            for child in childs2:
                child.parent = get_parent(created_accounts, account.code)
            new_accounts += childs2

        if new_accounts:
            self.save_account(new_accounts)

    def create_account(self, company_id, template2account=None,
            template2type=None, parent=None):

        if self.id not in template2account:
            account = self.create_account_tree(company_id, template2account,
                template2type, parent)

            # Algorithm to create accounts in batch
            self.save_account([account])

            # Make coorelation template 2 account needed for tax creation
            Account = Pool().get('account.account')
            accounts = Account.search([
                    ('company', '=', company_id),
                    ('template', '!=', None),
                    ])
            for acc in accounts:
                template2account[acc.template.id] = acc.id
        else:
            for child in self.childs:
                child.create_account(company_id,
                    template2account=template2account,
                    template2type=template2type, parent=self)

    def create_account_tree(self, company_id, template2account=None,
            template2type=None, parent=None):
        pool = Pool()
        Account = pool.get('account.account')

        if template2type is None:
            template2type = {}

        if template2account is None:
            template2account = {}

        nacc = self._get_account_value()
        nacc['company'] = company_id
        nacc['type'] = (template2type.get(self.type.id) if self.type
            else None)
        nacc['parent'] = (template2account.get(parent.id) if parent else None)

        new_account = Account()
        for key, value in nacc.iteritems():
            setattr(new_account, key, value)

        new_account.childs = []
        for child in self.childs:
            new_account.childs.append(child.create_account_tree(company_id,
                template2type=template2type,
                    template2account=template2account))

        return new_account


class TaxTemplate:

    __name__ = 'account.tax.template'

    @classmethod
    def save_tax(self, taxes):

        def get_parent(created_taxes, template):
            for t in created_taxes:
                if t.template.id == template:
                    return t

        Tax = Pool().get('account.tax')

        childs = {}
        for tax in taxes:
            childs[tax['template']] = tax['childs']
            tax['childs'] = []

        created_taxes = Tax.create(taxes)
        new_taxes = []
        for tax, childs2 in childs.iteritems():
            for child in childs2:
                child['parent'] = get_parent(created_taxes, tax)
            new_taxes += childs2

        if new_taxes:
            self.save_tax(new_taxes)

    @classmethod
    def create_batch(cls, templates, company_id, template2tax_code,
                template2account, template2tax=None, parent_id=None):

        taxes = []
        for tax_template in templates:
            tax = tax_template.create_tax_tree(company_id,
                template2tax_code=template2tax_code,
                template2account=template2account,
                template2tax=template2tax)

            taxes.append(tax)

        cls.save_tax(taxes)

        Tax = Pool().get('account.tax')
        taxes = Tax.search([])
        for t in taxes:
            template2tax[t.template.id] = t.id

    def create_tax_tree(self, company_id, template2tax_code, template2account,
            template2tax=None, parent_id=None):

        if template2tax is None:
            template2tax = {}

        if not template2tax.get(self.id):
            vals = self._get_tax_value()
            vals['company'] = company_id

            if self.invoice_account:
                vals['invoice_account'] = \
                    template2account[self.invoice_account.id]
            else:
                vals['invoice_account'] = None
            if self.credit_note_account:
                vals['credit_note_account'] = \
                    template2account[self.credit_note_account.id]
            else:
                vals['credit_note_account'] = None
            if self.invoice_base_code:
                vals['invoice_base_code'] = \
                    template2tax_code[self.invoice_base_code.id]
            else:
                vals['invoice_base_code'] = None
            if self.invoice_tax_code:
                vals['invoice_tax_code'] = \
                    template2tax_code[self.invoice_tax_code.id]
            else:
                vals['invoice_tax_code'] = None
            if self.credit_note_base_code:
                vals['credit_note_base_code'] = \
                    template2tax_code[self.credit_note_base_code.id]
            else:
                vals['credit_note_base_code'] = None
            if self.credit_note_tax_code:
                vals['credit_note_tax_code'] = \
                    template2tax_code[self.credit_note_tax_code.id]
            else:
                vals['credit_note_tax_code'] = None

            new_tax = vals
            template2tax[self.id] = new_tax

        else:
            new_tax = template2tax[self.id]

        new_tax['template'] = self.id
        new_tax['childs'] = []
        for child in self.childs:
            new_tax['childs'].append(child.create_tax_tree(company_id,
                    template2tax_code, template2account,
                    template2tax=template2tax, parent_id=None))
        return new_tax


class CreateChart:

    __name__ = 'account.create_chart'

    def transition_create_account(self):

        Account = Pool().get('account.account')

        Account.parent.left = None
        Account.parent.right = None

        res = super(CreateChart, self).transition_create_account()

        Account.parent.left = 'left'
        Account.parent.right = 'right'
        Account._rebuild_tree('parent', None, 0)
        return res


class UpdateChart:

    __name__ = 'account.update_chart'


    def transition_update(self):

        def _rebuild_tree():
            cr = Transaction().connection.cursor()
            table = 'account_account'
            field = 'parent'

            def browse_rec(root, pos=0):
                where = field + '=' + str(root) + 'AND company = ' + company

                if not root:
                    where = parent_field + 'IS NULL'

                cr.execute('SELECT id FROM %s WHERE %s \
                    ORDER BY %s' % (table, where, field))
                pos2 = pos + 1
                childs = cr.fetchall()
                for id in childs:
                    pos2 = browse_rec(id[0], pos2)
                cr.execute('update %s set "left"=%s, "right"=%s\
                    where id=%s' % (table, pos, pos2, root))
                return pos2 + 1


            where = field + 'IS NULL AND company = ' + company
            query = 'SELECT id FROM %s WHERE %s IS NULL order by %s' % (
                table, field, field)
            pos = 0
            cr.execute(query)
            for (root,) in cr.fetchall():
                pos = browse_rec(root, pos)
            return True

        Account = Pool().get('account.account')

        Account.parent.left = None
        Account.parent.right = None

        res = super(UpdateChart, self).transition_update()

        Account.parent.left = 'left'
        Account.parent.right = 'right'

        company = str(Transaction().context.get('company'))
        _rebuild_tree()
        return res
