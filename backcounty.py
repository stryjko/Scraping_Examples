import sys
from enum import Enum
from urllib.parse import (
    urlparse,
    parse_qsl,
)

from edc_an_feeds_parsers.affiliates.openers import CsvOpener
from edc_an_feeds_parsers.affiliates.parsers import FeedParser
from edc_an_feeds_parsers.affiliates.utils import (
    unique,
    clean_urls,

)
from ew_models.products import Price
from ew_models.products.feed import (
    FeedProduct,
    FeedVariant,
)


class BackcountryFeed:
    @staticmethod
    def get_parser():
        return BackcountryParser()


class BackcountryParser(FeedParser):
    CUSTOM_HEADER = 'parent_id'
    IN_STOCK = 'in stock'

    class FieldsIndices(Enum):
        PRODUCT_ID = 0
        ID = 1
        NAME = 2
        BRAND = 3
        DESCRIPTION = 4
        AVAILABILITY = 5
        PRICE = 6
        SALE_PRICE = 7
        CURRENCY = 8
        LINK = 9
        IMAGE_LINK = 10
        GENDER = 11
        AGE = 12
        CATEGORY = 13
        COLOR = 14
        SIZE = 15
        GTIN = 16
        ADDITIONAL_IMAGE_LINK = 17
        MATERIAL = 18

    def __init__(self):
        super().__init__(CsvOpener('excel', 20))

    def is_new_item(self, feed_entity):
        return True

    def _affiliate_network_parse(self, row):
        if self.CUSTOM_HEADER in row.values():
            return None

        return self._merchant_parse(row)

    def _merchant_parse(self, row):
        return self._common_parse(row)

    def _common_parse(self, row):
        product_url = row[self.FieldsIndices.LINK.value]
        return FeedProduct({
            'id': row[self.FieldsIndices.ID.value],
            'name': row[self.FieldsIndices.NAME.value],
            'brand': row[self.FieldsIndices.BRAND.value],
            'description': row[self.FieldsIndices.DESCRIPTION.value],
            'url': self.extract_canonical_url(product_url),
            'affiliate_url': product_url,
            'images': list(self.get_images(row)),
            'categories': [row.get(self.FieldsIndices.CATEGORY.value)] or [],
            'variant': self._create_variant(row),
            'attributes': self._create_attributes(row),
        })

    @staticmethod
    def extract_canonical_url(affiliate_url):
        parsed_url = urlparse(affiliate_url)
        parsed_qs = dict(parse_qsl(parsed_url.query))
        return clean_urls(parsed_qs['mr:targetUrl'])

    def get_images(self, row):
        images = [row[self.FieldsIndices.IMAGE_LINK.value]]
        add_images_data = row[self.FieldsIndices.ADDITIONAL_IMAGE_LINK.value]
        if add_images_data:
            add_images = [clean_urls(url=add, custom_sheme='http') for add in add_images_data.split('http://') if add]
            images.extend(add_images)
        for img in unique(images):
            if img:
                yield {'url': clean_urls(img).replace('/large/', '/1200/')}

    def _create_variant(self, row):
        is_available = row[self.FieldsIndices.AVAILABILITY.value] == self.IN_STOCK
        price = row[self.FieldsIndices.PRICE.value]
        return FeedVariant({
            'variant_id': row[self.FieldsIndices.PRODUCT_ID.value],
            'stock_quantity': sys.maxsize if is_available else 0,
            'upc': row[self.FieldsIndices.GTIN.value],
            'price': Price({
                'value': row[self.FieldsIndices.SALE_PRICE.value] or price,
                'fmp': price,
                'currency': row[self.FieldsIndices.CURRENCY.value],
            }),
        })

    def _create_attributes(self, row):
        attributes = {
            'Color': row[self.FieldsIndices.COLOR.value],
            'Size': row[self.FieldsIndices.SIZE.value],
            'Material': row[self.FieldsIndices.MATERIAL.value],
            'Gender': row[self.FieldsIndices.GENDER.value],
            'Age': row[self.FieldsIndices.AGE.value],
        }
        return {key: val for key, val in attributes.items() if val}
