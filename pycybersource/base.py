import collections
from decimal import Decimal as D
from suds.client import Client
from suds.wsse import Security, UsernameToken
from suds import WebFault

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
    Light suds wrapper around the with the Cybersource SOAP API
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
        client = Client(self.config.wsdl_url)

        # Add wsse security
        security = Security()
        token = UsernameToken(username=self.config.merchant_id,
                              password=self.config.api_key)
        security.tokens.append(token)
        client.set_options(wsse=security)
        return client

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
        ccAuthService = self.client.factory.create(
                                    'ns0:ccAuthService')
        ccAuthService._run = 'true'

        # payment info
        payment = self._build_payment(**kwargs['payment'])

        # card info
        card = self._build_card(**kwargs['card'])

        # billing
        billTo = self._build_bill_to(**kwargs['billTo'])

        # business rules
        # businessRules = self.client.factory.create('ns0:businessRules')
        # businessRules.ignoreAVSResult = 'true'

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

        for node_name in ['encryptedPayment', 'ucaf', 'paymentNetworkToken']:
            if node_name in kwargs:
                node = self.client.factory.create(
                                    'ns0:{}'.format(node_name))
                for key, value in kwargs[node_name].items():
                    setattr(node, key, value)
                ret.update({node_name: node})

        if 'encryptedPayment' in kwargs:
            encryptedPayment = self.client.factory.create(
                                    'ns0:encryptedPayment')
            for key, value in kwargs['encryptedPayment'].items():
                setattr(encryptedPayment, key, value)
            ret.update({'encryptedPayment': encryptedPayment})

        if 'ucaf' in kwargs:
            ucaf = self.client.factory.create(
                                    'ns0:ucaf')
            for key, value in kwargs['ucaf'].items():
                setattr(ucaf, key, value)
            ret.update({'ucaf': ucaf})

        if 'paymentNetworkToken' in kwargs:
            paymentNetworkToken = self.client.factory.create(
                                    'ns0:paymentNetworkToken')
            for key, value in kwargs['paymentNetworkToken'].items():
                setattr(paymentNetworkToken, key, value)
            ret.update({'paymentNetworkToken': paymentNetworkToken})

        if 'paymentSolution' in kwargs:
            ret.update({'paymentSolution': kwargs['paymentSolution']})

        return ret

    def _build_ccCaptureService(self, **kwargs):
        # service
        ccCaptureService = self.client.factory.create(
                                    'ns0:ccCaptureService')
        ccCaptureService.authRequestID = kwargs['authRequestID']
        ccCaptureService._run = 'true'

        # payment info
        payment = self._build_payment(**kwargs['payment'])

        return {
            'ccCaptureService': ccCaptureService,
            'purchaseTotals': payment,
        }

    def _build_ccAuthReversalService(self, **kwargs):
        ccAuthReversalService = self.client.factory.create(
                                            'ns0:ccAuthReversalService')
        ccAuthReversalService.authRequestID = kwargs['authRequestID']
        ccAuthReversalService._run = 'true'

        # payment info
        payment = self._build_payment(**kwargs['payment'])
        return {
            'ccAuthReversalService': ccAuthReversalService,
            'purchaseTotals': payment,
        }

    def _build_ccCreditService(self, **kwargs):
        ccCreditService = self.client.factory.create(
                                            'ns0:ccCreditService')
        ccCreditService.captureRequestID = kwargs['captureRequestID']
        ccCreditService._run = 'true'

        # payment info
        payment = self._build_payment(**kwargs['payment'])
        return {
            'ccCreditService': ccCreditService,
            'purchaseTotals': payment,
        }

    def _build_ccSaleService(self, **kwargs):
        # auth
        ccAuthServiceOptions = self._build_ccAuthService(**kwargs)
        # capture
        ccCaptureService = self.client.factory.create(
                                    'ns0:ccCaptureService')
        ccCaptureService._run = 'true'

        options = {}
        options.update(ccAuthServiceOptions)
        options.update({
            'ccCaptureService': ccCaptureService
        })
        return options

    def _build_ccVoidService(self, **kwargs):
        voidService = self.client.factory.create(
                                            'ns0:VoidService')
        voidService.voidRequestID = kwargs['requestId']
        voidService._run = 'true'

        return {
            'voidService': voidService,
        }

    def _build_payment(self, total, currency):
        """
        kwargs:
        total: the total payment amount
        currency: the payment currency (e.g. USD)
        """
        payment = self.client.factory.create('ns0:PurchaseTotals')
        payment.currency = currency
        payment.grandTotalAmount = D(total)
        return payment

    def _build_card(self,
                    accountNumber=None,
                    expirationMonth=None,
                    expirationYear=None,
                    cvNumber=None,
                    cardType=None):

        card = self.client.factory.create('ns0:Card')
        if accountNumber:
            card.accountNumber = accountNumber
        if expirationMonth:
            card.expirationMonth = expirationMonth
        if expirationYear:
            card.expirationYear = expirationYear

        if cvNumber:
            card.cvIndicator = 1
            card.cvNumber = cvNumber

        if cardType:
            card.cardType = cardType

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
        billTo = self.client.factory.create('ns0:BillTo')
        billTo.firstName = firstName
        billTo.lastName = lastName
        billTo.email = email
        billTo.country = country
        billTo.city = city
        billTo.state = state
        billTo.postalCode = postalCode
        billTo.street1 = street1
        billTo.street2 = street2

        return billTo

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
        except WebFault as e:
            raise CyberSourceError(e)

        return CyberSourceResponse(response)

    # SOAP API calls below
    def ccAuth(self, referenceCode, payment, card, billTo, **kwargs):
        """
        Do a credit card auth transaction. Use this to crate a card auth, which
        can later be captured to charge the card.
        """
        kwargs.update(dict(
            referenceCode=referenceCode,
            payment=payment,
            card=card,
            billTo=billTo))
        return self.run_transaction('ccAuthService', **kwargs)

    def ccCapture(self, referenceCode, authRequestID, payment, **kwargs):
        """
        Do a credit card capture, based on a previous auth.
        """
        kwargs.update(dict(
            referenceCode=referenceCode,
            authRequestID=authRequestID,
            payment=payment))
        return self.run_transaction('ccCaptureService', **kwargs)

    def ccCredit(self, referenceCode, captureRequestID, payment, **kwargs):
        """
        Do a refund back to credit card, based on a previous auth.
        """
        kwargs.update(dict(
            referenceCode=referenceCode,
            captureRequestID=captureRequestID,
            payment=payment))
        return self.run_transaction('ccCreditService', **kwargs)

    def ccSale(self, referenceCode, payment, card, billTo, **kwargs):
        """
        Do an auth and an immediate capture. Use this for an immediate charge.
        """
        kwargs.update(dict(
            referenceCode=referenceCode,
            payment=payment,
            card=card,
            billTo=billTo))
        return self.run_transaction('ccSaleService', **kwargs)

    def ccAuthReversal(self, referenceCode, authRequestID, payment, **kwargs):
        """
        Do an authorization reversal, based on a previous auth.
        """
        kwargs.update(dict(
            referenceCode=referenceCode,
            authRequestID=authRequestID,
            payment=payment))
        return self.run_transaction('ccAuthReversalService', **kwargs)

    def ccVoid(self, referenceCode, requestId, **kwargs):
        """
        Do a void, based on a previous capture or credit.
        """
        kwargs.update(dict(
            referenceCode=referenceCode,
            requestId=requestId))
        return self.run_transaction('ccVoidService', **kwargs)
