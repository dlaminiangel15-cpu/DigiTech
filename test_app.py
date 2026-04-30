from app import app
import unittest

class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_redirect(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/customer', response.location)

    def test_customer_view(self):
        response = self.app.get('/customer')
        self.assertEqual(response.status_code, 200)

    def test_book_view(self):
        response = self.app.get('/book')
        self.assertEqual(response.status_code, 200)

    def test_login_view(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
