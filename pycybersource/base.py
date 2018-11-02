import collections
from decimal import Decimal as D

from zeep.exceptions import Fault
from zeep import Client
from zeep.wsse.username import UsernameToken

from pycybersource.config import CyberSourceConfig
from pycybersource.response import CyberSourceResponse


class CyberSourceError(Exception):
    def __init__(self, original_exception=None):
        self._original_exception = original_exception
        super(CyberSourceError, self).__init__()

    def __str__(self):
        return str(self._original_exception)


class CyberSource(object):
    """
    Light zeep wrapper around the with the Cybersource SOAP API
    """

    def __init__(self, config):
        self.config = self.init_config(config)
        self.client = self.init_client()

    def init_config(self, config):
        if isinstance(config, CyberSourceConfig):
            return config
        elif isinstance(config, collections.Mapping):
            return CyberSourceConfig(**config)
        else:
            raise ValueError(
                "config must be a CyberSourceConfig instance or a dict")

    def init_client(self):
        # Add wsse security
        token = UsernameToken(
            username=self.config.merchant_id, password=self.config.api_key)
        return Client(self.config.wsdl_url, wsse=token)

    def _build_service_data(self, serviceType, **kwargs):
        """
        Because each service can have differnt options, we delegate building
        the options to methods for each service type.
        """
        try:
            method = getattr(self, '_build_{0}'.format(serviceType))
            return method(**kwargs)
        except AttributeError:
            raise ValueError("{0} is not a valid service".format(serviceType))

    def _build_ccAuthService(self, **kwargs):
        # service
        ccAuthService = {'run': 'true'}

        # payment error
        payment = self._build_payment(**kwargs['payment'])

        # card error
        card = self._build_card(**kwargs['card'])

        # billing
        billTo = self._build_bill_to(**kwargs['billTo'])

        # businessRules = {'ignoreAVSResult': 'true'}
        if 'authService' in kwargs:
            for key, value in kwargs['authService'].items():
                setattr(ccAuthService, key, value)
        ret = {
            'ccAuthService': ccAuthService,
            'purchaseTotals': payment,
            'card': card,
            'billTo': billTo,
            # 'businessRules': businessRules,
        }

        for node_name in ['EncryptedPayment', 'UCAF', 'PaymentNetworkToken']:
            if node_name in kwargs:
                node = {}
                for key, value in kwargs[node_name].items():
                    setattr(node, key, value)
                ret.update({node_name: node})

        if 'paymentSolution' in kwargs:
            ret.update({'paymentSolution': kwargs['paymentSolution']})

        return ret

    def _build_ccCaptureService(self, **kwargs):
        # payment error
        payment = self._build_payment(**kwargs['payment'])
        return {
            'ccCaptureService': {
                'authRequestID': kwargs['authRequestID'],
                'run': 'true'
            },
            'purchaseTotals': payment,
        }

    def _build_ccAuthReversalService(self, **kwargs):
        # payment error
        payment = self._build_payment(**kwargs['payment'])
        return {
            'ccAuthReversalService': {
                'authRequestID': kwargs['authRequestID'],
                'run': 'true'
            },
            'purchaseTotals': payment,
        }

    def _build_ccCreditService(self, **kwargs):
        # payment error
        payment = self._build_payment(**kwargs['payment'])
        return {
            'ccCreditService': {
                'captureRequestID': kwargs['captureRequestID'],
                'run': 'true'
            },
            'purchaseTotals': payment,
        }

    def _build_ccSaleService(self, **kwargs):
        options = {}
        # auth
        options.update(self._build_ccAuthService(**kwargs))
        # capture
        options.update({'ccCaptureService': {'run': 'true'}})
        return options

    def _build_ccVoidService(self, **kwargs):
        return {
            'voidService': {
                'voidRequestID': kwargs['requestId'],
                'run': 'true'
            }
        }

    def _build_payment(self, total, currency):
        """
        kwargs:
        total: the total payment amount
        currency: the payment currency (e.g. USD)
        """
        return {'currency': currency, 'grandTotalAmount': D(total)}

    def _build_card(self,
                    accountNumber=None,
                    expirationMonth=None,
                    expirationYear=None,
                    cvNumber=None,
                    cardType=None):
        card = {}
        if accountNumber:
            card.update({'accountNumber': accountNumber})
        if expirationMonth:
            card.update({'expirationMonth': expirationMonth})
        if expirationYear:
            card.update({'expirationYear': expirationYear})

        if cvNumber:
            card.update({'cvIndicator': 1, 'cvNumber': cvNumber})

        if cardType:
            card.update({'cardType': cardType})

        return card

    def _build_bill_to(self,
                       firstName,
                       lastName,
                       email,
                       country,
                       state,
                       city,
                       postalCode,
                       street1,
                       street2=None):
        return {
            'firstName': firstName,
            'lastName': lastName,
            'email': email,
            'country': country,
            'city': city,
            'state': state,
            'postalCode': postalCode,
            'street1': street1,
            'street2': street2
        }

    def run_transaction(self, serviceType, **kwargs):
        """
        Builds the SOAP transaction and returns a response.
        """
        # build request options
        options = {
            'merchantID': self.config.merchant_id,
            'merchantReferenceCode': kwargs['referenceCode'],
        }

        # Each service may have different options
        service_options = self._build_service_data(serviceType, **kwargs)
        options.update(service_options)

        try:
            response = self.client.service.runTransaction(**options)
        except Fault as e:
            raise CyberSourceError(e)

        return CyberSourceResponse(response)

    # SOAP API calls below
    def ccAuth(self, referenceCode, payment, card, billTo, **kwargs):
        """
        Do a credit card auth transaction. Use this to crate a card auth, which
        can later be captured to charge the card.
        """
        kwargs.update(
            dict(
                referenceCode=referenceCode,
                payment=payment,
                card=card,
                billTo=billTo))
        return self.run_transaction('ccAuthService', **kwargs)

    def ccCapture(self, referenceCode, authRequestID, payment, **kwargs):
        """
        Do a credit card capture, based on a previous auth.
        """
        kwargs.update(
            dict(
                referenceCode=referenceCode,
                authRequestID=authRequestID,
                payment=payment))
        return self.run_transaction('ccCaptureService', **kwargs)

    def ccCredit(self, referenceCode, captureRequestID, payment, **kwargs):
        """
        Do a refund back to credit card, based on a previous auth.
        """
        kwargs.update(
            dict(
                referenceCode=referenceCode,
                captureRequestID=captureRequestID,
                payment=payment))
        return self.run_transaction('ccCreditService', **kwargs)

    def ccSale(self, referenceCode, payment, card, billTo, **kwargs):
        """
        Do an auth and an immediate capture. Use this for an immediate charge.
        """
        kwargs.update(
            dict(
                referenceCode=referenceCode,
                payment=payment,
                card=card,
                billTo=billTo))
        return self.run_transaction('ccSaleService', **kwargs)

    def ccAuthReversal(self, referenceCode, authRequestID, payment, **kwargs):
        """
        Do an authorization reversal, based on a previous auth.
        """
        kwargs.update(
            dict(
                referenceCode=referenceCode,
                authRequestID=authRequestID,
                payment=payment))
        return self.run_transaction('ccAuthReversalService', **kwargs)

    def ccVoid(self, referenceCode, requestId, **kwargs):
        """
        Do a void, based on a previous capture or credit.
        """
        kwargs.update(dict(referenceCode=referenceCode, requestId=requestId))
        return self.run_transaction('ccVoidService', **kwargs)
