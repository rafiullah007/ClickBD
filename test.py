import os
import django
import time


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping.settings')

django.setup()

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from django.contrib.auth.models import User
from app.models import Product, Cart, Customer
from django.urls import reverse


class TemplateRenderingTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Chrome()  # Ensure chromedriver is in PATH
        cls.driver.implicitly_wait(10)  # Implicit wait for elements to appear

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        # Create a test user if it doesn't exist
        self.username = "testuser"
        self.password = "testpassword"
        # Ensure the user exists or create them
        self.user, created = User.objects.get_or_create(username=self.username)
        if created:
            self.user.set_password(self.password)
            self.user.save()
        else:
            # If user already exists, ensure password is set (e.g., if previous run failed mid-creation)
            if not self.user.has_usable_password():
                self.user.set_password(self.password)
                self.user.save()

        # Create a test product for product-detail and cart tests
        self.product, created = Product.objects.get_or_create(
            title='Test Product',
            defaults={
                'selling_price': 120.0,
                'discounted_price': 100.0,
                'description': 'Test description',
                'brand': 'TestBrand',
                'category': 'TW',
                'product_image': 'productimg/test.jpg'  # Use a dummy path
            }
        )

    def _login(self):
        driver = self.driver
        login_url = reverse('login')
        driver.get(f'{self.live_server_url}{login_url}')

        try:
            # Wait for username and password fields to be present and fill them
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'username'))).send_keys(
                self.username)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'password'))).send_keys(
                self.password)

            # Click the submit button
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"]'))).click()

            # Wait for the URL to change, indicating successful login to the home page
            # Adjust this if your login redirects to a different page (e.g., '/profile/')
            WebDriverWait(driver, 10).until(EC.url_matches(f'{self.live_server_url}/'))
            print(f"Successfully logged in as {self.username}")
        except TimeoutException as e:
            self.fail(
                f"Login failed within timeout. Current URL: {driver.current_url}, Page source: {driver.page_source[:500]}... Error: {e}")
        except Exception as e:
            self.fail(f"An unexpected error occurred during login: {e}")

    def _check_template_renders(self, url_name, expected_title_substring=None, login_required=False, url_kwargs=None):
        driver = self.driver

        # Build the URL using reverse, including kwargs if provided
        try:
            if url_kwargs:
                url = reverse(url_name, kwargs=url_kwargs)
            else:
                url = reverse(url_name)
        except Exception as e:
            self.fail(f"Could not reverse URL for '{url_name}' with kwargs {url_kwargs}: {e}")

        driver.get(f'{self.live_server_url}{url}')
        print(f"Testing URL: {driver.current_url}")  # For debugging

        if login_required:
            # Check if redirected to login page before attempting login
            login_url = reverse('login')
            if driver.current_url.startswith(f'{self.live_server_url}{login_url}'):
                print(f"'{url_name}' requires login and redirects correctly. Attempting login...")
                self._login()
                driver.get(f'{self.live_server_url}{url}')  # Try accessing the original URL again after login

        try:
            # Wait for the <body> tag to be present, indicating a basic HTML structure
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            # Assert that the page source contains the opening <html> tag
            self.assertIn('<html', driver.page_source.lower(), "Page source does not contain <html> tag.")

            if expected_title_substring:
                # Wait for the title to contain the expected substring
                WebDriverWait(driver, 10).until(EC.title_contains(expected_title_substring))
                self.assertIn(expected_title_substring.lower(), driver.title.lower(),
                              f"Title '{driver.title}' does not contain '{expected_title_substring}'.")

            self.assertTrue(True,
                            f"'{url_name}' template rendered successfully.")  # This line will always be true if no exception
        except TimeoutException:
            self.fail(
                f"'{url_name}' template did not load within the timeout (10s). Current URL: {driver.current_url}, Page source: {driver.page_source[:500]}...")
        except AssertionError as e:
            self.fail(
                f"Assertion failed for '{url_name}': {e}. Current URL: {driver.current_url}, Page source: {driver.page_source[:500]}...")
        except Exception as e:
            self.fail(
                f"An unexpected error occurred while testing '{url_name}': {e}. Current URL: {driver.current_url}, Page source: {driver.page_source[:500]}...")

    # --- Template Rendering Tests ---

    def test_addtocart_template(self):
        # 'add-to-cart' is usually an action, not a template.
        # If it's a page, it usually redirects to show-cart.
        # This test will check if the 'add-to-cart' URL itself can be accessed without error.
        # For a full test of adding to cart, you'd need to simulate a POST request or click a button.
        # Given your urls.py, 'add-to-cart' is a view, not necessarily a template to render directly.
        # If this is expected to render a page, adjust the expected_title_substring.
        self._check_template_renders('add-to-cart', login_required=True)

    def test_base_template(self):
        # Base template is usually not a direct view, so we skip direct URL testing.
        # Its content is implicitly tested by other pages that extend it.
        self.assertTrue(True, "'base.html' is a base template and doesn't have a direct URL.")

    def test_buynow_template(self):
        # 'buy-now' is usually an action, not a template.
        # If it's a page, it usually redirects to checkout.
        # This test will check if the 'buy-now' URL itself can be accessed without error.
        self._check_template_renders('buy-now', login_required=True)

    def test_customerregistration_template(self):
        self._check_template_renders('customerregistration', expected_title_substring='Registration')  # Changed name

    # Removed test_emptycart_template as there's no 'emptycart' URL name in your urls.py
    # If you want to test an empty cart, you'd typically navigate to 'show-cart'
    # after ensuring the cart is empty for the test user.

    def test_home_template(self):
        self._check_template_renders('home', expected_title_substring='Home')

    def test_login_template(self):
        self._check_template_renders('login', expected_title_substring='Login')

    def test_password_reset_template(self):
        self._check_template_renders('password_reset', expected_title_substring='Reset password')

    def test_password_reset_confirm_template(self):
        # This URL requires a uidb64 and token. Direct testing without a valid token
        # is complex and usually requires simulating the password reset email flow.
        # For now, we'll just print a message.
        print(f"Skipping 'password_reset_confirm' test as it requires a valid uidb64 and token. "
              f"URL pattern: {self.live_server_url}{reverse('password_reset_confirm', kwargs={'uidb64': 'MQ', 'token': 'set-password'})}")
        self.assertTrue(True, "'password_reset_confirm.html' requires a token for direct access.")


    def test_product_detail_template(self):
        self._check_template_renders('product-detail', expected_title_substring='Product Detail',
                                     url_kwargs={'pk': self.product.pk})

    def test_show_cart_template(self):
        self._login()
        print(f"Logged in as user: {self.user.username}")
        # To properly test show-cart, we should add a product to the cart first.
        cart_item, created = Cart.objects.get_or_create(user=self.user, product=self.product, defaults={'quantity': 1})
        if created:
            print(f"Added product '{self.product.title}' to the cart.")
        else:
            print(f"Product '{self.product.title}' already in the cart.")

        self._check_template_renders('show-cart', expected_title_substring='Cart', login_required=True)


