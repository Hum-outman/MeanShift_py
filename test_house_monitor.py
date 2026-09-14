import unittest

from house_monitor import COMMUNITY, parse_listings


class ListingParserTests(unittest.TestCase):
    def test_finds_only_target_building_and_resolves_link(self):
        page = '''<article class="house-card"><a href="/sale/1">天福元润国际 4号楼 精装</a><p>128 万 15600 元/㎡</p></article>
        <article class="house-card"><a href="/sale/2">天福元润国际 3号楼</a><p>100 万</p></article>'''
        listings = parse_listings(page, "https://example.com/search")
        self.assertEqual(1, len(listings))
        self.assertIn(COMMUNITY, listings[0].title)
        self.assertEqual(128.0, listings[0].price_wan)
        self.assertEqual(15600, listings[0].unit_price)
        self.assertEqual("https://example.com/sale/1", listings[0].url)


if __name__ == "__main__":
    unittest.main()
