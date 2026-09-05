import unittest
from unittest.mock import Mock
import requests
from search_api import SearchError, search_serper


def response(data, status=200):
    result = Mock(status_code=status)
    result.json.return_value = data
    return result


class SearchTests(unittest.TestCase):
    def test_missing_key(self):
        session = Mock()
        with self.assertRaises(SearchError):
            search_serper(session, 'plugin', 20, '')
        session.post.assert_not_called()

    def test_pagination_and_mapping(self):
        session = Mock()
        rows = [{'title': 'Example', 'link': f'https://example.com/{i}', 'snippet': 'Info', 'date': '2026-01-01'} for i in range(20)]
        session.post.side_effect = [response({'organic': rows[:10]}), response({'organic': rows[10:]})]
        result = search_serper(session, 'site:example.com plugin', 12, ' secret ')
        self.assertEqual(len(result), 12)
        self.assertEqual(result[0]['date'], '2026-01-01')
        self.assertEqual(session.post.call_args.kwargs['headers'], {'X-API-KEY': 'secret'})
        self.assertEqual(session.post.call_args.kwargs['json'], {'q': 'site:example.com plugin', 'num': 10, 'page': 2})

    def test_empty_and_duplicate_results(self):
        session = Mock()
        session.post.return_value = response({'organic': []})
        self.assertEqual(search_serper(session, 'test', 20, 'key'), [])
        session.post.return_value = response({'organic': [{'link': 'https://example.com'}] * 2})
        self.assertEqual(len(search_serper(session, 'test', 20, 'key')), 1)

    def test_http_errors_do_not_leak_keys(self):
        for status in (400, 401, 402, 403, 429, 500):
            with self.subTest(status=status):
                session = Mock()
                session.post.return_value = response({'message': 'secret'}, status)
                with self.assertRaises(SearchError) as error:
                    search_serper(session, 'test', 20, 'secret')
                self.assertIn(str(status), str(error.exception))
                self.assertNotIn('secret', str(error.exception))

    def test_network_and_malformed_errors(self):
        session = Mock()
        session.post.side_effect = requests.Timeout('secret')
        with self.assertRaises(SearchError) as error:
            search_serper(session, 'test', 20, 'secret')
        self.assertNotIn('secret', str(error.exception))
        session.post.side_effect = None
        for data in ({}, {'organic': 'invalid'}, {'organic': [None]}):
            session.post.return_value = response(data)
            with self.assertRaises(SearchError):
                search_serper(session, 'test', 20, 'secret')

    def test_page_failure_is_not_partial_success(self):
        session = Mock()
        session.post.side_effect = [response({'organic': [{'link': f'https://example.com/{i}'} for i in range(10)]}), response({}, 402)]
        with self.assertRaises(SearchError):
            search_serper(session, 'test', 20, 'key')


if __name__ == '__main__':
    unittest.main()
