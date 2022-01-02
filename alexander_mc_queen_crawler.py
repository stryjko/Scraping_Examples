from urllib.parse import urlparse

import scrapy

from app.spiders.base import BaseSpider
from app.utils import strip_product_id


class AlexanderMcQueenSpider(BaseSpider):
    name = 'alexander_mc_queen'
    start_urls = ('https://www.alexandermcqueen.com/en-us', )
    base_url = 'https://www.alexandermcqueen.com'
    skip_cat = ['world of mcqueen']
    skip_cat_2 = ['collections']

    def parse(self, response):
        for index, cat in enumerate(response.css('ul.c-nav__level1 > li[data-ref=item]')):
            cat_tag = cat.css('button::text') or cat.css('a::text')
            main_cat_name = cat_tag.extract_first().strip()
            if main_cat_name.lower() in self.skip_cat:
                continue

            main_category = self._make_category(name=main_cat_name,
                                                index=index,
                                                url=None)
            yield main_category
            yield from self._get_2_level_categories(cat.css('ul.c-nav__level2'), main_category)

    def _get_2_level_categories(self, cats_2, main_category):
        for index, cat_2 in enumerate(cats_2.css('li[data-ref=group]')):
            cat_tag = cat_2.css('button::text') or cat_2.css('a::text')
            cat_2_name = cat_tag.extract_first().strip()
            if cat_2_name.lower() in self.skip_cat_2:
                continue

            cat_2_category = self._make_category(name=cat_2_name,
                                                 index=index,
                                                 url=None,
                                                 parent_id=main_category['id'])
            yield cat_2_category
            yield from self._get_3_level_categories(cat_2.css('ul.c-nav__level3'), cat_2_category)

    def _get_3_level_categories(self, cats_3, cat_2_category):
        for index, cat_3 in enumerate(cats_3.css('li > a')):
            cat_3_name = cat_3.css('::text').extract_first().strip()
            cat_3_url = cat_3.css('::attr(href)').extract_first()
            cat_3_category = self._make_category(name=cat_3_name,
                                                 index=index,
                                                 url=self.check_url(cat_3_url.strip()),
                                                 parent_id=cat_2_category['id'])
            yield scrapy.Request(cat_3_category['url'],
                                 self.parse_products,
                                 meta={'category': cat_3_category},
                                 dont_filter=True)

    def parse_products(self, response):
        category = response.meta['category']
        category['product_urls'].extend(self._extract_products(response))
        next_prod_url = response.css('button.c-loadmore__btn')

        if next_prod_url:
            yield scrapy.Request(next_prod_url.css('::attr(data-url)').extract_first(),
                                 self.parse_products,
                                 meta={'category': category},
                                 dont_filter=True)
        else:
            yield category

    def _extract_products(self, response):
        products = []
        for product in response.css('li.l-productgrid__item > article.c-product'):
            url = product.css('a[itemprop=url]::attr(href)')
            if url:
                prod_url = self.check_url(url.extract_first())
                prod_id = '_'.join(urlparse(prod_url).path.split('/')[-1].split('-')[:-1]).replace('%', '_')
                products.append({
                    'id': strip_product_id(prod_id),
                    'url': self.check_url(url.extract_first()),
                })
        return products
