import logging
import unittest
from random import randrange

from pycybersource.base import CyberSource, CyberSourceError
from pycybersource.config import get_config_from_file

# Set to logging.DEBUG or logging.INFO for more diagnostic messages
logging.basicConfig(level=logging.CRITICAL)

# logging.getLogger('suds.xsd.schema').setLevel(logging.DEBUG)


def create_processor(**kwargs):
    config = get_config_from_file(**kwargs)
    if config is None:
        raise RuntimeError(
            "Tests require config values for merchant_id and api_key. "
            "These can be read from .cybersource config file either in "
            "your home directory or the current run working directory.")
    return CyberSource(config)


class TestCyberSource(unittest.TestCase):
    def setUp(self):
        self.billTo = {
            'firstName': 'Bob',
            'lastName': 'Oblaw',
            'email': 'test@test.blah',
            'country': 'US',
            'state': 'CA',
            'city': 'Los Angeles',
            'postalCode': '90042',
            'street1': '555 Test St',
        }

        self.testCard = {
            'accountNumber': '4111111111111111',
            'expirationMonth': '05',
            'expirationYear': '2018',
            'cvNumber': '123',
        }

    def test_create_processor(self):
        create_processor()

    def test_cc_auth(self):
        api = create_processor()
        resp = api.ccAuth(
            referenceCode=randrange(0, 100000),
            payment={
                'currency': 'USD',
                'total': '99.99',
            },
            card=self.testCard,
            billTo=self.billTo)
        self.assertTrue(resp.success)
        self.assertEqual(resp.reasonCode, 100)
        self.assertEqual(resp.decision, 'ACCEPT')
        self.assertTrue(resp.ccAuthReply)
        self.assertTrue(resp.requestID)

        # test types
        self.assertIsInstance(resp.reasonCode, int)
        self.assertIsInstance(resp.requestID, str)
        self.assertIsInstance(resp.message, str)

    def test_auth_and_reversal(self):
        # Successful auth
        api = create_processor()
        auth_resp = api.ccAuth(
            referenceCode=randrange(0, 100000),
            payment={
                'currency': 'USD',
                'total': '99.99',
            },
            card=self.testCard,
            billTo=self.billTo)
        self.assertTrue(auth_resp.success)
        self.assertTrue(auth_resp.requestID)

        # Do auth reversal
        reverse_resp = api.ccAuthReversal(
            referenceCode=randrange(0, 100000),
            authRequestID=auth_resp.requestID,
            payment={
                'currency': 'USD',
                'total': '99.99',
            })
        self.assertTrue(reverse_resp.success)
        self.assertEqual(reverse_resp.reasonCode, 100)
        self.assertEqual(reverse_resp.decision, 'ACCEPT')

    def test_avs_fail_auth_and_reversal(self):
        payment = {
            'currency': 'USD',
            'total': '2836.00',  # trigger avs failure
        }

        # Auth failed avs
        api = create_processor()
        auth_resp = api.ccAuth(
            referenceCode=randrange(0, 100000),
            payment=payment,
            card=self.testCard,
            billTo=self.billTo)
        self.assertFalse(auth_resp.success)
        self.assertTrue(auth_resp.requestID)
        self.assertEqual(auth_resp.ccAuthReply.avsCode, 'N')
        self.assertTrue(auth_resp.is_soft_decline)

        # Still do reversal (issuing bank will still have the auth)
        reverse_resp = api.ccAuthReversal(
            referenceCode=randrange(0, 100000),
            authRequestID=auth_resp.requestID,
            payment=payment)
        self.assertTrue(reverse_resp.success)
        self.assertEqual(reverse_resp.reasonCode, 100)
        self.assertEqual(reverse_resp.decision, 'ACCEPT')

    def test_cc_capture(self):
        api = create_processor()
        referenceCode = randrange(0, 100000),
        resp = api.ccAuth(
            referenceCode=referenceCode,
            payment={
                'currency': 'USD',
                'total': '33.33',
            },
            card=self.testCard,
            billTo=self.billTo)
        self.assertTrue(resp.success)
        self.assertEqual(resp.reasonCode, 100)
        self.assertEqual(resp.decision, 'ACCEPT')

        resp = api.ccCapture(
            referenceCode=referenceCode,
            authRequestID=resp.requestID,
            payment={
                'currency': 'USD',
                'total': '33.33',
            })
        self.assertTrue(resp.success)
        self.assertEqual(resp.reasonCode, 100)
        self.assertEqual(resp.decision, 'ACCEPT')

    def test_cc_sale(self):
        api = create_processor()
        resp = api.ccSale(
            referenceCode=randrange(0, 100000),
            payment={
                'currency': 'USD',
                'total': '88.88',
            },
            card=self.testCard,
            billTo=self.billTo)
        self.assertTrue(resp.success)
        self.assertEqual(resp.reasonCode, 100)
        self.assertEqual(resp.decision, 'ACCEPT')
        self.assertTrue(resp.ccAuthReply)
        self.assertTrue(resp.requestID)

    def test_cc_credit(self):
        api = create_processor()
        referenceCode = randrange(0, 100000)
        sale_resp = api.ccSale(
            referenceCode=referenceCode,
            payment={
                'currency': 'USD',
                'total': '88.88',
            },
            card=self.testCard,
            billTo=self.billTo)
        api = create_processor()
        resp = api.ccCredit(
            referenceCode=referenceCode,
            captureRequestID=sale_resp.requestID,
            payment={
                'currency': 'USD',
                'total': '88.88',
            })
        self.assertTrue(resp.success)
        self.assertEqual(resp.reasonCode, 100)
        self.assertEqual(resp.ccCreditReply['amount'], '88.88')
        self.assertEqual(resp.decision, 'ACCEPT')

    def test_cc_credit_partial(self):
        api = create_processor()
        referenceCode = randrange(0, 100000)
        sale_resp = api.ccSale(
            referenceCode=referenceCode,
            payment={
                'currency': 'USD',
                'total': '88.88',
            },
            card=self.testCard,
            billTo=self.billTo)
        resp = api.ccCredit(
            referenceCode=referenceCode,
            captureRequestID=sale_resp.requestID,
            payment={
                'currency': 'USD',
                'total': '22.22',
            })
        self.assertTrue(resp.success)
        self.assertEqual(resp.reasonCode, 100)
        self.assertEqual(resp.ccCreditReply['amount'], '22.22')
        self.assertEqual(resp.decision, 'ACCEPT')

    def test_cc_capture_void(self):
        api = create_processor()
        referenceCode = randrange(0, 100000)
        sale_resp = api.ccSale(
            referenceCode=referenceCode,
            payment={
                'currency': 'USD',
                'total': '88.88',
            },
            card=self.testCard,
            billTo=self.billTo)
        resp = api.ccVoid(
            referenceCode=referenceCode,
            requestId=sale_resp.requestID,
        )
        self.assertTrue(resp.success)
        self.assertEqual(resp.reasonCode, 100)
        self.assertEqual(resp.decision, 'ACCEPT')

    def test_cc_bad_amount(self):
        api = create_processor()
        resp = api.ccAuth(
            referenceCode=randrange(0, 100000),
            payment={
                'currency': 'USD',
                'total': '-1',
            },
            card=self.testCard,
            billTo=self.billTo)
        self.assertFalse(resp.success)
        self.assertEqual(resp.reasonCode, 102)
        self.assertEqual(resp.decision, 'REJECT')
        self.assertTrue(resp.message)

    def test_bad_card_number(self):
        api = create_processor()
        card = self.testCard.copy()
        card['accountNumber'] = '4111111111111112 '
        resp = api.ccAuth(
            referenceCode=randrange(0, 100000),
            payment={
                'currency': 'USD',
                'total': '5',
            },
            card=card,
            billTo=self.billTo)
        self.assertFalse(resp.success)
        self.assertEqual(resp.reasonCode, 231)
        self.assertEqual(resp.decision, 'REJECT')
        self.assertTrue(resp.message)

    def test_bad_login_raises_error(self):
        api = create_processor()
        api.config.merchant_id = 'badid'
        try:
            api.ccAuth(
                referenceCode=randrange(0, 100000),
                payment={
                    'currency': 'USD',
                    'total': '5',
                },
                card=self.testCard,
                billTo=self.billTo)
        except CyberSourceError:
            pass


if __name__ == '__main__':
    unittest.main()
