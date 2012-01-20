#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this :repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval, Bool
from trytond.pool import Pool
from decimal import Decimal

class ProductKitLine(ModelSQL, ModelView):
    '''Product Kit'''
    _name = 'product.kit.line'
    _description = __doc__

    parent = fields.Many2One('product.product', 'Parent Product', required=True,
            ondelete='CASCADE')
    product = fields.Many2One('product.product', 'Product', required=True,
            domain=[
                ('id', '!=', Eval('parent_parent')),
            ],
            ondelete='CASCADE')
    sequence = fields.Integer('sequence')
    quantity = fields.Float('Quantity', digits=(16, Eval('unit_digits', 2)),
            required=True, depends=['unit_digits'])
    unit = fields.Many2One('product.uom', 'Unit', required=True,
            domain=[
                ('category', '=',
                (Eval('product'), 'product.default_uom.category')),
            ],
            context={
                'category': (Eval('product'), 'product.default_uom.category'),
            },
            on_change_with=['product'],
            depends=['product'])
    unit_digits = fields.Function(fields.Integer('Unit Digits',
            on_change_with=['unit']), 'get_unit_digits')

    def get_unit_digits(self, ids, name):
        res = {}
        for line in self.browse(ids):
            if line.unit:
                res[line.id] = line.unit.digits
            else:
                res[line.id] = 2
        return res

    def on_change_with_unit(self, vals):
        product_obj = Pool().get('product.product')
        if vals.get('product'):
            product = product_obj.browse(vals['product'])
            return product.sale_uom.id

    def on_change_with_unit_digits(self, vals):
        uom_obj = ().get('product.uom')
        if vals.get('unit'):
            uom = uom_obj.browse(vals['unit'])
            return uom.digits
        return 2

    def __init__(self):
        super(ProductKitLine, self).__init__()
        self._order.insert(0, ('sequence', 'ASC'))

        self._constraints += [
            ('check_recursion', 'recursive_kits'),
        ]
        self._error_messages.update({
            'recursive_kits': 'You can not create recursive kits!',
        })

ProductKitLine()

STATES = {
    'readonly': ~Eval('active', True),
}
DEPENDS = ['active']

class Product(ModelSQL, ModelView):
    _name = "product.product"

    kit = fields.Boolean('Kit?')
    kit_lines = fields.One2Many('product.kit.line', 'parent', 
            'Components', states={
                    'readonly': Bool(~Eval('kit')),
                    }, depends=['kit'])
    kit_fixed_list_price = fields.Boolean('Fixed List Price', help='Mark this '
            'field if the list price of the kit should be fixed. Do not mark '
            'it if the price should be calculated from the sum of the prices '
            'of the products in the pack.'),


    def explode_kit(self, product_id, quantity, unit, depth=1):
        """
        Walks through the Kit tree in depth-first order and returns
        a sorted list with all the components of the product.
        """
        uom_obj = pool.get('product.uom')
        result = []
        for line in self.browse(product_id).kit_lines:
            qty = quantity * uom_obj.compute_qty(line.unit, line.quantity, unit)
            result.append({
                    'product_id': line.product.id,
                    'quantity': qty,
                    'unit': line.unit.id,
                    'unit_price': Decimal('0.00'),
                    'depth': depth,
                    })
            result += self.explode_kit(line.product.id, quantity,
                    line.unit, depth+1)
        return result

Product()
