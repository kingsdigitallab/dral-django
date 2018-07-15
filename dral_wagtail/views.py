from django.shortcuts import render
from collections import OrderedDict
from dral_wagtail.api_vars import API_Vars


class Visualisation(object):

    def process_request(self, visualisation_code, context, request):
        self.visualisation_code = visualisation_code
        self.context = context
        self.request = request

        ret = self.view_visualisation()

        return ret

    def get_config(self):
        ret = API_Vars(self.get_config_schema())

        ret.reset_vars_from_request(self.request)

        return ret

    def get_config_schema(self, alignment_data=None):
        # cache = caches['kiln']

        ret = [
            {
                'key': 'viz',
                'default': 'relative_omission',
                'options': ['relative_omission', 'relative_omission_calendar'],
                'name': 'Visualisation',
                'type': 'single',
            },
            {
                'key': 'chapters',
                'default': ['benjy', 'quentin', 'jason', 'dilsey'],
                'options': ['benjy', 'quentin', 'jason', 'dilsey'],
                'name': 'Chapters',
                'type': 'multi',
            },
            {
                'key': 'sort',
                'default': 'frequency',
                'options': ['frequency', 'alphabetically'],
                'name': 'Sort lemmas by',
                'type': 'single',
            },
        ]

        # cache.set('alignment_config_options', ret)
        return ret

    def view_visualisation(self):

        config = self.config = self.get_config()
        self.context['config'] = config.get_list()

        # code = self.visualisation_code.replace('-', '_')
        code = config.get('viz', 1)

        method = getattr(self, 'visualisation_{}'.format(code))
        method()

        template_path = 'dral_visualisations/{}.html'.format(code)

        from django.template.loader import get_template
        template = get_template(template_path)

        if self.request.GET.get('js', '') == '1':
            # template_path = 'text_alignment/views/%s.html' % selected_view
            json_res = {
                'config': config.get_list(),
                'html': template.render(self.context),
                'qs': config.get_query_string(),
                'page_title': code,
            }

            from django.http import JsonResponse
            return JsonResponse(json_res)
        else:
            return render(
                self.context['request'],
                'dral_wagtail/visualisation_page.html',
                self.context
            )

    def visualisation_relative_omission(self):

        query = r'''
            select
                le.string as lemma, la.name as language, sc.qt as freq,
                coalesce(zc.qt::float, 0.0) omitted,
                coalesce(zc.qt::float, 0.0) / (sc.qt::float) as ratio_omitted
            from
                (
                    select lemma_id, language_id, count(*) qt
                    from dral_text_occurence oc
                    where chapter = ANY(%s)
                    group by lemma_id, language_id
                ) as sc
                left join
                (
                    select lemma_id, language_id, count(*) qt
                    from dral_text_occurence oc
                    where zero is true
                    group by lemma_id, language_id
                ) as zc
                on (
                    sc.language_id = zc.language_id
                    and sc.lemma_id = zc.lemma_id
                ),
                dral_text_language la,
                dral_text_lemma le
            where sc.language_id = la.id
            and sc.lemma_id = le.id
            and la.name = %s
        '''

        sort_by = self.config.get('sort', True)
        if sort_by == 'alphabetically':
            query += '''
                order by lemma
            '''
        else:
            query += '''
                order by sc.qt desc
            '''

        chapters = [c.upper() for c in self.config.get('chapters')]

        data = [
            (lg, get_rows_from_query(query, [chapters, lg], rounding=3)[0:])
            for lg
            in ['LT', 'RU', 'POL']
        ]
        self.context['vis_data'] = OrderedDict(data)

    def visualisation_relative_omission_calendar(self):
        ret = self.visualisation_relative_omission()
        return ret


def get_rows_from_query(query, params, rounding=None):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        ret = dictfetchall(cursor)

    if rounding:
        for row in ret:
            for k, v in row.items():
                if isinstance(v, float):
                    row[k] = round(v, 3)

    return ret


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]
