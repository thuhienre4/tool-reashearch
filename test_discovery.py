import unittest
from discovery import root_domain, canonical_url, rank_candidate, discover, build_queries, inspect_html, matches_suffix


def item(url, title='Travel Affiliate Program', snippet='Join our affiliate program and earn commission'):
    return {'link': url, 'title': title, 'snippet': snippet}


class DiscoveryTests(unittest.TestCase):
    def test_suffix_boundaries(self):
        self.assertTrue(matches_suffix('https://PARTNER.EXAMPLE.IO./affiliate', ['.com', '.io']))
        self.assertFalse(matches_suffix('https://example.com.vn', ['.com']))
        self.assertTrue(matches_suffix('https://example.com.vn', ['.vn']))
        self.assertFalse(matches_suffix('https://example.ai.evil.org/com?next=example.com', ['.com', '.ai']))
        self.assertTrue(matches_suffix('https://example.net', []))

    def test_suffix_discovery_and_query(self):
        calls = []
        def search(query, count):
            calls.append(query)
            return [item('https://brand.com/affiliate'), item('https://brand.ai/affiliate'), item('https://brand.net/affiliate')]
        rows, _ = discover(search, 'Travel', '', [], 20, suffixes=['.com', '.ai'])
        self.assertEqual({row['root_domain'] for row in rows}, {'brand.com', 'brand.ai'})
        self.assertTrue(all('(site:com OR site:ai)' in query for query in calls))

    def test_registered_domains(self):
        self.assertEqual(root_domain('https://partners.example.co.uk/a'), 'example.co.uk')
        self.assertEqual(root_domain('https://www.example.co.uk/b'), 'example.co.uk')
        self.assertNotEqual(root_domain('https://alice.blogspot.com'), root_domain('https://bob.blogspot.com'))

    def test_tracking_duplicates(self):
        self.assertEqual(canonical_url('https://example.com/affiliate?utm_source=google#top'), canonical_url('https://example.com/affiliate'))

    def test_roundup_below_program(self):
        official = rank_candidate(item('https://brand.com/affiliate'))
        roundup = rank_candidate(item('https://blog.com/best-travel', 'My Top 20 Travel Affiliate Programs That Pay'))
        self.assertGreater(official['rank_score'], roundup['rank_score'])
        self.assertTrue(roundup['roundup'])

    def test_discovery_diversity_and_filter(self):
        calls = []
        def search(query, count):
            calls.append((query, count))
            return [item('https://brand.co.uk/affiliate'), item('https://partners.brand.co.uk/affiliate'),
                    item('https://other.com/affiliate'), item('https://blog.com/list', 'Top 20 Travel Affiliate Programs')]
        rows, stats = discover(search, 'Travel', '', [], 20)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(calls), 6)
        self.assertEqual(stats['max_requests'], 6)
        rows, _ = discover(search, 'Travel', '', ['brand.co.uk'], 20)
        self.assertEqual([r['root_domain'] for r in rows], ['brand.co.uk'])
        self.assertIn('site:brand.co.uk', calls[-1][0])

    def test_queries_keep_keyword(self):
        queries = build_queries('Travel', 'luxury', ['example.com'])
        self.assertTrue(all('luxury' in q and 'site:example.com' in q for q in queries))
        self.assertTrue(any('insurance' in q for q in queries))

    def test_generic_tracking_is_not_ads(self):
        evidence = inspect_html('<p>Join our affiliate program and earn commission</p> pixel fbclid gclid utm_source GTM-123 G-123')
        self.assertTrue(evidence['affiliate'])
        self.assertEqual(evidence['ads'], [])
        self.assertFalse(inspect_html('<script>affiliate program commission</script>')['affiliate'])
        self.assertTrue(inspect_html('<script>gtag("config", "AW-123456789")</script>')['ads'])

    def test_error_does_not_become_success(self):
        from search_api import SearchError
        def fail(query, count):
            raise SearchError('No credits')
        with self.assertRaises(SearchError):
            discover(fail, 'Travel', '', [], 20)


if __name__ == '__main__':
    unittest.main()
