from collections import OrderedDict


class API_Vars(object):
    '''
    Holds the definition and values of a list of variables.
    Allows the defs and values to be interchanged with a query string
    or a dictionary.
    Support different types of variables:
        * multi-select (multi)
        * single-select (single)
        * interval of numbers (range)
    '''

    def __init__(self, vars=None):
        self.vars = OrderedDict()
        if vars:
            for var in vars:
                self.add(var)

    def add(self, var):
        # complete and transform the dictionary

        options_selected = var.get('selected', [])
        options_default = var.get('default', [])

        if 'options' in var:
            if var['options']:
                is_dict = isinstance(var['options'], dict)
                options = []
                for option_key in var['options']:
                    options.append({
                        'key': option_key,
                        'name': var['options'][option_key] if is_dict
                        else get_name_from_key(option_key),
                        'selected': option_key in options_selected,
                        'default': option_key in options_default,
                    })

                var['options'] = options

        assert(var.get('key'))
        assert(var.get('name'))
        assert(var.get('type'))

        # add it to our list of vars

        self.vars[var['key']] = var

    def _set_selected(self):
        # Help vue.js to manage radio button
        # by placing a single selected value directly under the var.
        # Also helps javascript to quickly access selected values.
        for var in self.vars.values():
            var['selected'] = self.get(var['key'], var['type'] == 'single')

    def get_query_string(self):
        '''returns the vars as a query string'''
        import urllib
        ret = '&'.join([
            ('%s=%s' % (
                urllib.parse.quote(akey, ','),
                urllib.parse.quote(self.get_str(akey), ',')
            ))
            for akey
            in self.vars
        ])
        return ret

    def get_dict(self):
        '''returns the vars as a dict'''
        self._set_selected()
        return dict(self.vars)

    def get_list(self):
        '''returns the vars as a list'''
        self._set_selected()
        ret = [var for var in self.vars.values()]
        return ret

    def reset_vars_from_request(self, request):
        '''selected value(s) from the request'''
        for var in self.vars.values():
            values = request.GET.get(var['key'], None)

            self.set(var['key'], values)

    def set(self, akey, values=None):
        '''selected value(s) for the given var key'''
        '''
        values = ['option1_key', 'option3_key']
        values = 'option1_key,option3_key'
        values = 'all'
        values = None => reset to default
        values = []
        '''

        if 'options' in self.vars[akey]:
            if hasattr(values, 'split'):
                values = values.split(',')

            if values:
                values = [v.strip() for v in values]

            for option in self.vars[akey]['options']:
                if values is None:
                    option['selected'] = option['default']
                    continue
                option['selected'] = ('all' in values)\
                    or (option['key'] in values)
        else:
            value = values
            if value in ['', None]:
                value = self.vars[akey]['default']
            if self.vars[akey]['type'] == 'int':
                value = int(value)
            self.vars[akey]['value'] = value

    def get_all_options(self, akey):
        var = self.vars.get(akey, {})

        return var.get('options', [])

    def get(self, akey, first=False, prop='key'):
        '''return the selected value(s) for the given var key'''
        var = self.vars[akey]
        if 'options' in var:
            ret = [
                option.get(prop)
                for option
                in var['options']
                if option.get('selected')
            ]

            if first:
                ret = ret[0]
        else:
            ret = var['value']
            if var['type'] == 'int':
                ret = int(ret)
            if var['type'] == 'str':
                ret = str(ret)

        return ret

    def get_str(self, akey, first=False):
        ret = self.get(akey, first)

        if isinstance(ret, list):
            ret = ','.join(ret)

        return '%s' % ret


def get_name_from_key(akey):
    import re
    return re.sub(r'[_]', r' ', akey.title()).strip()
