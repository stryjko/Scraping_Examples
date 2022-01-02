import json
import re

from scrapers.base_scraper import BaseParser
from scrapers.custom_exception import (
    ProductUnavailableException,
    ProductErrorException,
)
from scrapers.utils import (
    fill_variant_selectors,
    generate_size_attribute,
)


class JourneysParser(BaseParser):
    RE_DATA = re.compile(r'maProductJson = (?P<prod_data>.*);')
    currency = 'USD'

    def _check_product_errors(self):
        error_tag = self.soup.select_one('div.panel-body')
        if error_tag and 'Product No Longer Available' in error_tag.text.strip():
            raise ProductUnavailableException

    async def scrape_availability(self):
        self.soup = await self.parse_document()
        self._check_product_errors()
        prod_data = self.get_product_data()
        return {'variants': self.get_variants(prod_data)}

    def get_variants(self, prod_data):
        variants = []
        for item in prod_data['SKUs']:
            variant = {
                'id': item['SKU'],
                'sku': item['SKU'],
                'cart': {},
                'mpn': prod_data['StyleID'],
                'upc': item['MasterUPC'],
                'price': self.get_price(item),
                'selection': {'size': item['Size1']},
                'stock': {'status': 'in_stock'},
            }
            variants.append(variant)
        if not variants:
            raise ProductUnavailableException

        return variants

    def get_price(self, product_data):
        fmp = self.check_price(product_data['ListPrice'], check_currency=False)
        regular = self.check_price(product_data['Price'], check_currency=False)
        if fmp < regular:
            fmp = regular
        price = {
            'currency': self.currency,
            'fmp': fmp,
            'regular': regular,
        }
        return price

    async def scrape_full(self):
        self.soup = await self.parse_document()
        self._check_product_errors()
        product_data = self.get_product_data()
        product_info = {
            'name': product_data['Name'],
            'description': product_data['LongDescription'],
            'category': self.get_category(),
            'attributes': self.get_attributes(product_data),
            'assets': self.get_assets(),
            'variantSelectors': [],
        }
        if product_data.get('VendorBrand'):
            product_info['brand'] = product_data['VendorBrand']
        return fill_variant_selectors(product_info)

    def get_product_data(self):
        script = self.soup.find('script', text=self.RE_DATA)
        if script:
            prod_data_re = self.RE_DATA.search(script.text).group('prod_data')
            return json.loads(prod_data_re)

        raise ProductErrorException('MAIN DATA WASN\'T FOUND')

    def get_category(self):
        breadcrumbs = self.soup.select('.breadcrumb a')
        return [item.text.strip() for item in breadcrumbs[1:]]

    @staticmethod
    def get_attributes(product_data):
        size_attr = generate_size_attribute()
        for size in product_data['RelatedSizes']:
            size_attr['values'].append({
                'name': size,
                'id': size,
            })
        return [size_attr]

    def get_assets(self):
        image_tags = self.soup.select('#detailAltViewsWrap a')
        return [{
            'images': [{'url': tag['href']} for tag in image_tags if '/noimage' not in tag['href']],
            'videos': [],
            'selector': {},
        }]
