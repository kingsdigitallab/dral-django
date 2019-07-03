from django.shortcuts import render
from collections import OrderedDict
from dral_wagtail.api_vars import API_Vars
from dral_text.models import Chapter, Text
from django.conf import settings
from django.template.defaultfilters import slugify


class Visualisation(object):

    def __init__(self):
        self.chapter_slugs = OrderedDict(list(
            Chapter.objects.values_list('slug', 'id').order_by('display_order')
        ))
        self.text_codes = list(
            Text.objects.values_list(
                'code', flat=True
            ).exclude(code__iexact=settings.DRAL_REFERENCE_LANGUAGE)
            .order_by('code')
        )

    def process_request(self, visualisation_code, context, request):
        self.context = context
        self.request = request

        ret = self.view_visualisation()

        return ret

    def get_config(self):
        ret = API_Vars(self.get_config_schema())

        ret.reset_vars_from_request(self.request)

        return ret

    def get_visualisations_list(self):
        return API_Vars(self.get_config_schema()).get_all_options('viz')

    def get_config_schema(self):

        ret = [
            {
                'key': 'viz',
                'default': 'relative_omission',
                'options': [
                    'relative_omission',
                    'relative_omission_gn',
                    'relative_omission_calendar',
                    'variants_progression',
                    'proof_read'
                ],
                'name': 'Visualisation',
                'type': 'single',
            },
            {
                'key': 'chapter',
                'default': list(self.chapter_slugs.keys()),
                'options': list(self.chapter_slugs.keys()),
                'name': 'Chapter',
                'type': 'multi',
            },
            {
                'key': 'sort',
                'default': 'frequency',
                'options': ['frequency', 'name', 'omission'],
                'name': 'Sort by',
                'type': 'single',
            },
            {
                'key': 'freq-min',
                'default': 0,
                'name': 'Minimum frequency',
                'type': 'int',
            },
            {
                'key': 'lemma',
                'default': 'SAY',
                'name': 'Lemma',
                'type': 'str',
            },
            {
                'key': 'text',
                'default': [
                    c for c in self.text_codes[:]
                    if c in ['ru', 'pol', 'lt']
                ],
                'options': self.text_codes[:],
                'name': 'Text',
                'type': 'multi',
            },
        ]

        return ret

    def view_visualisation(self):

        config = self.config = self.get_config()
        self.context['config'] = config.get_list()

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
            self.context['text_infos'] = self.get_text_infos()
            return render(
                self.context['request'],
                'dral_wagtail/visualisation_page.html',
                self.context
            )

    def get_text_infos(self):
        ret = {}

        for text in Text.objects.all():
            ret[text.code] = {
                'code': text.code,
                'reference': text.reference,
                'language': text.language,
                'pointer': text.pointer,
                'label': text.get_label(),
            }

        return ret

    def visualisation_variants_progression(self):
        query = r'''
            SELECT ch.slug as ch,
                oc.sentence_index as sidx,
                oc.string as word,
                oc.lemma_group as grp,
                oc.zero as omitted,
                oc.paraphrase as para,
                oc.replace as repl
            FROM dral_text_occurence oc
                join dral_text_text te
                on (oc.text_id = te.id)
                join dral_text_lemma le
                on (oc.lemma_id = le.id)
                join dral_text_chapter ch
                on (oc.chapter_id = ch.id)
            WHERE te.code = %s
                and le.string = %s
                and ch.slug = ANY(%s)
            ORDER by array_position(%s, ch.slug::text),
                sentence_index
            ;
        '''

        lemma = self.config.get('lemma', 'DOORS')
        chapters = self.config.get('chapter')
        _, text_codes = self.get_chap_text_from_config()

        data = OrderedDict()

        for lg in text_codes:
            variants = {}
            # fetch all the occurrences
            words = get_rows_from_query(
                query,
                [lg, lemma, chapters, chapters],
                rounding=3
            )

            # build variants table
            word_count = 0
            for word in words:
                if word['omitted']:
                    continue
                word_count += 1
                k = word['ch'] + '-' + str(word['grp'])
                variants[k] = variants.get(k, 0) + 1

            # TODO: find a way to unify lemma across chapters!
            sum = word_count
            variants_data = OrderedDict()
            for k, c in sorted(variants.items(), key=lambda v: -v[1]):
                variants_data[k] = {
                    'count': c,
                    'color': round(sum / word_count, 4)
                }
                sum -= c

            # print(variants_data)

            language_data = {
                'words': words,
                'variants': variants_data,
            }
            data[lg] = language_data

        self.context['vis_data'] = data

    def visualisation_proof_read(self):
        lemma = self.config.get('lemma', 'DOORS')
        chapters = self.config.get('chapter')

        _, text_codes = self.get_chap_text_from_config()

        sort_by = self.config.get('sort', True)
#         if sort_by == 'name':
#             lemma_order = 'lemma_string'
#         elif sort_by == 'omission':
#             lemma_order = 'name'
#         else:
#             lemma_order = ''

        from dral_text.models import Occurence

        data_chapters = []

        for chapter in chapters:
            blocks = []
            block = {}

            occurrences = Occurence.objects.filter(
                chapter__slug=chapter,
                text__code__in=['en'] + text_codes,
            ).select_related(
                'lemma', 'text'
            )

            occurrences = occurrences.order_by(
                'lemma__string', 'lemma_id', 'text_id', 'cell_col'
            )

            last_lemma = None
            last_text = None
            for occ in occurrences:
                text = occ.text
                lemma = occ.lemma

                if lemma != last_lemma:
                    if block:
                        blocks.append(block)
                    block = {
                        'keyword': lemma,
                        'texts': [],
                        'sidxs': [],
                        'freq': 0,
                        'omissions': 0,
                    }

                if text != last_text:
                    strings = []
                    row = {
                        'name': occ.text.code,
                        'strings': strings,
                        'omissions': 0,
                        # number of ? or ??
                        'unknowns': 0,
                    }
                    block['texts'].append(row)

                if text.code == settings.DRAL_REFERENCE_LANGUAGE:
                    block['sidxs'].append(occ.sentence_index)
                    if occ.string:
                        block['freq'] += 1

                strings.append(occ)
                if occ.string is None:
                    block['omissions'] += 1
                    row['omissions'] += 1
                if occ.string in ['?', '??']:
                    row['unknowns'] += 1

                last_text = text
                last_lemma = lemma

            # add last block
            if block and blocks and blocks[-1] != block:
                blocks.append(block)

            if sort_by == 'frequency':
                blocks = sorted(blocks, key=lambda b: -b['freq'])
            if sort_by == 'omission':
                blocks = sorted(blocks, key=lambda b: -b['omissions'])

            data_chapter = {
                'name': chapter,
                'blocks': blocks
            }
            data_chapters.append(data_chapter)

        self.context['vis_data'] = {
            'chapters': data_chapters
        }

    def visualisation_relative_omission(self):
        '''
        For each unique (lemma, lg) pair we get:
            * the frequency (sc.qt)
            * the number of ommissions (zc.qt)
        '''
        query = r'''
            select
                le.string as lemma, te.code as code, sc.qt as freq,
                coalesce(zc.qt::float, 0.0) omitted,
                coalesce(zc.qt::float, 0.0) / (sc.qt::float) as ratio_omitted
            from
                (
                    select lemma_id, text_id, count(*) qt
                    from dral_text_occurence oc
                    where chapter_id = ANY (%s)
                    group by lemma_id, text_id
                ) as sc
                left join
                (
                    select lemma_id, text_id, count(*) qt
                    from dral_text_occurence oc
                    where chapter_id = ANY(%s)
                    and zero is true
                    group by lemma_id, text_id
                ) as zc
                on (
                    sc.text_id = zc.text_id
                    and sc.lemma_id = zc.lemma_id
                ),
                dral_text_text te,
                dral_text_lemma le
            where sc.text_id = te.id
            and sc.qt >= %s
            and sc.lemma_id = le.id
            and te.code = %s
        '''

        sort_by = self.config.get('sort', True)
        if sort_by == 'name':
            query += '''
                order by lemma
            '''
        elif sort_by == 'omission':
            query += '''
                order by ratio_omitted desc
            '''
        else:
            query += '''
                order by sc.qt desc
            '''

        chapter_ids, text_codes = self.get_chap_text_from_config()

        freq_min = self.config.get('freq-min', 0)

        data = [
            (code, get_rows_from_query(
                query,
                [chapter_ids, chapter_ids, freq_min, code],
                rounding=3
            )[0:])
            for code
            in text_codes
        ]
        self.context['vis_data'] = OrderedDict(data)

    def visualisation_relative_omission_gn(self):
        '''
        For each unique (lemma, lg) pair we get:
            * the frequency (sc.qt)
            * the number of ommissions (zc.qt)
                le.string as lemma, la.code as language, sc.qt as freq,
        '''
        query = r'''
            select
                le.string as lemma,
                count(*) as freq,
                sum(case when oct.zero then 1 else 0 end) as omitted
            from
                dral_text_occurence oce
                join dral_text_text tee on (oce.text_id = tee.id)
                join dral_text_lemma le on (oce.lemma_id = le.id)
                join dral_text_text tet on (tet.code = %s)
                left join dral_text_occurence oct on (
                    oce.lemma_id = oct.lemma_id
                    and oce.cell_col = oct.cell_col
                    and oct.text_id = tet.id
                    and oce.chapter_id = oct.chapter_id
                    and oct.zero is true
                )
            where
                oce.chapter_id = ANY(%s)
                and tee.code = 'en'
                and oce.zero is false
            group by le.string
        '''

        sort_key = None
        sort_by = self.config.get('sort', True)
        if sort_by == 'name':
            query += '''
                order by lemma
            '''
        elif sort_by == 'omission':
            def sort_key_omission(r):
                return -(1.0 * r['omitted']) / r['freq']
            sort_key = sort_key_omission
        else:
            query += '''
                order by freq desc, lemma
            '''

        chapter_ids, text_codes = self.get_chap_text_from_config()

        # freq_min = self.config.get('freq-min', 0)

        data = [
            (text_code, get_rows_from_query(
                query,
                # [chapter_ids, chapter_ids, freq_min, lg],
                [text_code, chapter_ids],
                sort_key=sort_key
            )[0:])
            for text_code
            in text_codes
        ]
        self.context['vis_data'] = OrderedDict(data)

    def visualisation_relative_omission_calendar(self):
        ret = self.visualisation_relative_omission()
        return ret

    def get_chap_text_from_config(self):
        chapter_ids = [self.chapter_slugs[slug]
                       for slug in self.config.get('chapter')]
        text_codes = [slugify(c) for c in self.config.get('text')]

        return chapter_ids, text_codes


def get_rows_from_query(query, params, rounding=None, sort_key=None):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        ret = dictfetchall(cursor)

    if rounding:
        for row in ret:
            for k, v in row.items():
                if isinstance(v, float):
                    row[k] = round(v, 3)

    if sort_key:
        ret = sorted(ret, key=sort_key)

    return ret


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]
