import unittest
from datetime import date
from project_filters import read_metrics, passes_filters, months_ago, content_date
from discovery import discover

TODAY = date(2026, 9, 5)
HEADER = 'domain,monthly_visits,traffic_month,traffic_source,launched_at,launch_source\n'


class ProjectFiltersTests(unittest.TestCase):
    def test_valid_sources_and_unknown(self):
        rows = read_metrics((HEADER + 'example.com,50000,2026-08,Similarweb,2026-06-01,https://example.com/launch\nother.com,,,,,\n').encode(), TODAY)
        self.assertEqual(rows['example.com']['monthly_visits'], 50000)
        self.assertIsNone(rows['other.com']['monthly_visits'])

    def test_rejects_invalid_and_unsourced_metrics(self):
        for line in ('example.com,NaN,2026-08,report,,,',
                     'example.com,-1,2026-08,report,,,',
                     'example.com,10000,2026-08,,,,',
                     'example.com,10000,2026-09,report,,,',
                     'example.com,,,,2027-01-01,report',
                     'example.com,,,,2026-08-01,'):
            with self.subTest(line=line), self.assertRaises(ValueError):
                read_metrics((HEADER + line).encode(), TODAY)

    def test_rejects_duplicate_root_domains(self):
        with self.assertRaises(ValueError):
            read_metrics((HEADER + 'www.example.co.uk,,,,,\npartner.example.co.uk,,,,,').encode(), TODAY)

    def test_date_basis_is_not_conflated(self):
        item = {'rank_score': 85, 'date': '2026-08-01'}
        self.assertTrue(passes_filters(item, {}, 6, 'content', today=TODAY))
        self.assertFalse(passes_filters(item, {}, 6, 'launch', today=TODAY))
        self.assertFalse(passes_filters(item, {'launched_at': '2020-01-01'}, 6, 'launch', today=TODAY))
        self.assertFalse(passes_filters({'rank_score': 85, 'date': '2027-01-01'}, {}, 6, today=TODAY))

    def test_traffic_threshold_freshness_and_missing(self):
        item = {'rank_score': 85}
        for metrics in ({}, {'monthly_visits': 0, 'traffic_month': '2026-08'}, {'monthly_visits': 9000, 'traffic_month': '2026-08'}, {'monthly_visits': 90000, 'traffic_month': '2025-08'}):
            self.assertFalse(passes_filters(item, metrics, min_visits=10000, today=TODAY))
        self.assertTrue(passes_filters(item, {'monthly_visits': 10000, 'traffic_month': '2026-08'}, min_visits=10000, today=TODAY))

    def test_calendar_and_relative_date(self):
        self.assertEqual(months_ago(date(2024, 3, 31), 1), date(2024, 2, 29))
        self.assertEqual(content_date('2 months ago', TODAY), date(2026, 7, 5))

    def test_filter_before_limit(self):
        def search(query, count):
            return [{'title': 'Travel affiliate program', 'snippet': 'Join and earn commission', 'link': 'https://old.com/affiliate', 'date': '2020-01-01'},
                    {'title': 'Travel affiliate program', 'snippet': 'Join and earn commission', 'link': 'https://new.com/affiliate', 'date': '2026-08-01'}]
        rows, _ = discover(search, 'Travel', '', [], 1, candidate_filter=lambda row: passes_filters(row, {}, 6, today=TODAY))
        self.assertEqual(rows[0]['root_domain'], 'new.com')


if __name__ == '__main__':
    unittest.main()
