import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

FIXTURE = '''
import streamlit as st
import pandas as pd
from ui import render
def search(query, count):
    return [{'title': 'Travel Affiliate Program', 'snippet': 'Join our affiliate program and earn commission', 'link': 'https://brand.co.uk/affiliate'},
            {'title': 'Travel Affiliate Program', 'snippet': 'Join and earn commission', 'link': 'https://partners.brand.co.uk/affiliate'}]
def detect(url):
    return {'affiliate': True, 'ads': [], 'checked': True, 'final_url': url}
def info(item):
    return {'Domain': 'brand.co.uk', 'Tiêu đề': item['title'], 'Mô tả': item['snippet'], 'Thời gian ra mắt': 'Không rõ', 'Link thông tin dự án': item['link'], 'Link đăng ký': item['link'], 'PageSpeed Metrics': None}
render(st, pd, search, detect, info, lambda url: url.split('/')[2])
'''


class DashboardTests(unittest.TestCase):
    def test_suffix_filter_and_reset(self):
        app = AppTest.from_string(FIXTURE).run()
        app.multiselect[0].set_value(['.ai'])
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['ket_qua_loc'], [])
        app.multiselect[0].set_value(['.co.uk'])
        app.button[1].click().run()
        self.assertEqual(len(app.session_state['ket_qua_loc']), 1)
        app.button[0].click().run()
        self.assertEqual(app.multiselect[0].value, [])

    def test_suffix_checked_after_redirect(self):
        fixture = FIXTURE.replace("'final_url': url", "'final_url': 'https://elsewhere.net/affiliate'")
        app = AppTest.from_string(fixture).run()
        app.multiselect[0].set_value(['.co.uk'])
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['ket_qua_loc'], [])

    def test_real_app_loads(self):
        app = AppTest.from_file(str(Path(__file__).with_name('ads.py')), default_timeout=30).run()
        self.assertFalse(app.exception)

    def test_diversity_evidence_and_strict_filter(self):
        app = AppTest.from_string(FIXTURE).run()
        app.selectbox[0].set_value('Travel')
        app.button[1].click().run()
        self.assertFalse(app.exception)
        rows = app.session_state['ket_qua_loc']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Domain'], 'brand.co.uk')
        self.assertEqual(rows[0]['Google Ads'], 'Không thấy mã Ads')
        self.assertTrue(rows[0]['Bằng chứng'])
        self.assertEqual(len(app.dataframe), 1)
        app.checkbox[1].set_value(True)
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['ket_qua_loc'], [])
        app.button[0].click().run()
        self.assertFalse(app.checkbox[1].value)
        self.assertEqual(app.session_state['discovery_stats'], {})

    def test_failure_preserves_previous_results(self):
        fixture = FIXTURE.replace("def search(query, count):", "def search(query, count):\n    if st.session_state.get('force_error'):\n        from search_api import SearchError\n        raise SearchError('No credits')")
        app = AppTest.from_string(fixture).run()
        app.button[1].click().run()
        old_rows = app.session_state['ket_qua_loc']
        app.session_state['force_error'] = True
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['ket_qua_loc'], old_rows)
        self.assertTrue(app.error)

    def test_traffic_filter_requires_source_before_search(self):
        fixture = FIXTURE.replace('def search(query, count):', "def search(query, count):\n    st.session_state['called_search'] = True")
        app = AppTest.from_string(fixture).run()
        app.number_input[0].set_value(10000)
        app.button[1].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertNotIn('called_search', app.session_state.filtered_state)
        app.button[0].click().run()
        self.assertEqual(app.number_input[0].value, 0)


if __name__ == '__main__':
    unittest.main()
