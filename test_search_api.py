import unittest
from unittest.mock import Mock
import requests
from search_api import SearchError, search_google


class SearchTests(unittest.TestCase):
    def test_missing_configuration(self):
        session = Mock()
        with self.assertRaises(SearchError):
            search_google(session, 'plugin', 20, '', '')
        session.get.assert_not_called()

    def test_invalid_key_does_not_leak_secret(self):
        session = Mock()
        session.get.return_value = Mock(status_code=400)
        session.get.return_value.json.return_value = {'error': {'message': 'API key not valid. secret-key'}}
        with self.assertRaises(SearchError) as error:
            search_google(session, 'plugin', 20, 'secret-key', 'engine')
        self.assertIn('GOOGLE_API_KEY', str(error.exception))
        self.assertNotIn('secret-key', str(error.exception))

    def test_pagination_and_trim(self):
        session = Mock()
        first = Mock(status_code=200)
        first.json.return_value = {'items': list(range(10)), 'queries': {'nextPage': [{}]}}
        last = Mock(status_code=200)
        last.json.return_value = {'items': [10, 11]}
        session.get.side_effect = [first, last]
        self.assertEqual(search_google(session, 'plugin', 12, ' key ', ' engine '), list(range(12)))
        self.assertEqual(session.get.call_args.kwargs['params']['num'], 2)
        self.assertEqual(session.get.call_args.kwargs['params']['start'], 11)
        self.assertEqual(session.get.call_args.kwargs['params']['key'], 'key')

    def test_network_error_is_safe(self):
        session = Mock()
        session.get.side_effect = requests.ConnectionError('https://googleapis.com?key=secret-key')
        with self.assertRaises(SearchError) as error:
            search_google(session, 'plugin', 20, 'secret-key', 'engine')
        self.assertNotIn('secret-key', str(error.exception))

    def test_second_page_error_is_not_partial_success(self):
        session = Mock()
        first = Mock(status_code=200)
        first.json.return_value = {'items': [1], 'queries': {'nextPage': [{}]}}
        last = Mock(status_code=400)
        last.json.return_value = {'error': {'message': 'Invalid argument'}}
        session.get.side_effect = [first, last]
        with self.assertRaises(SearchError):
            search_google(session, 'plugin', 20, 'key', 'engine')


if __name__ == '__main__':
    unittest.main()
