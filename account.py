#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta


__all__ = ['AccountTemplate', 'CreateChart']


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

        account = self.create_account_tree(company_id, template2account,
            template2type, parent)

        # Algorithm to create accounts in batch
        self.save_account([account])

        # Make coorelation template 2 account needed for tax creation
        Account = Pool().get('account.account')
        accounts = Account.search([])
        for acc in accounts:
            template2account[acc.template.id] = acc.id

    def create_account_tree(self, company_id, template2account=None,
            template2type=None, parent=None):

        if template2type is None:
            template2type = {}

        if template2account is None:
            template2account = {}

        nacc = self._get_account_value()
        nacc['company'] = company_id
        nacc['type'] = (template2type.get(self.type.id) if self.type
            else None)

        Account = Pool().get('account.account')
        new_account = Account()
        for key, value in nacc.iteritems():
            setattr(new_account, key, value)

        new_account.childs = []
        for child in self.childs:
            new_account['childs'].append(child.create_account_tree(company_id,
                template2type=template2type, template2account=template2account,
                parent=new_account))

        return new_account


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
