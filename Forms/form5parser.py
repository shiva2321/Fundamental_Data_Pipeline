from typing import Dict, Any, List
import xml.etree.ElementTree as ET
from Forms.baseParser import SECFormParser


class Form5Parser(SECFormParser):
    """
    Parser for SEC Form 5 - Annual Statement of Changes in Beneficial Ownership

    Form 5 is an annual filing for transactions that were exempt from
    reporting on Form 4 or were not reported earlier.
    """

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 5 document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        root = self.parse_xml_from_text(document_text)
        if root is None:
            return {"error": "Failed to parse XML"}

        result = {
            "form_type": "Form 5 - Annual Statement of Changes in Beneficial Ownership",
            "filing_info": self._parse_filing_info(root),
            "issuer": self._parse_issuer(root),
            "reporting_owner": self._parse_reporting_owner(root),
            "transactions": self._parse_transactions(root),
            "holdings": self._parse_holdings(root),
            "footnotes": self._parse_footnotes(root),
            "remarks": self.get_text(root, 'remarks'),
            "signature": self._parse_signature(root)
        }

        return result

    def _parse_filing_info(self, root: ET.Element) -> Dict[str, Any]:
        """Parse filing information"""
        return {
            "schema_version": self.get_text(root, 'schemaVersion'),
            "document_type": self.get_text(root, 'documentType'),
            "period_of_report": self.format_date(self.get_text(root, 'periodOfReport')),
            "not_subject_to_section_16": self.get_text(root, 'notSubjectToSection16') == "1",
            "form3_holdings_reported": self.get_text(root, 'form3HoldingsReported') == "1",
            "form4_transactions_reported": self.get_text(root, 'form4TransactionsReported') == "1"
        }

    def _parse_issuer(self, root: ET.Element) -> Dict[str, str]:
        """Parse issuer information"""
        issuer = root.find('issuer')
        if issuer is None:
            return {}

        return {
            "cik": self.get_text(issuer, 'issuerCik'),
            "name": self.get_text(issuer, 'issuerName'),
            "trading_symbol": self.get_text(issuer, 'issuerTradingSymbol')
        }

    def _parse_reporting_owner(self, root: ET.Element) -> Dict[str, Any]:
        """Parse reporting owner information"""
        owner = root.find('reportingOwner')
        if owner is None:
            return {}

        owner_id = owner.find('reportingOwnerId')
        address = owner.find('reportingOwnerAddress')
        relationship = owner.find('reportingOwnerRelationship')

        result = {
            "identity": {
                "cik": self.get_text(owner_id, 'rptOwnerCik'),
                "name": self.get_text(owner_id, 'rptOwnerName')
            },
            "address": {
                "street1": self.get_text(address, 'rptOwnerStreet1'),
                "street2": self.get_text(address, 'rptOwnerStreet2'),
                "city": self.get_text(address, 'rptOwnerCity'),
                "state": self.get_text(address, 'rptOwnerState'),
                "zip_code": self.get_text(address, 'rptOwnerZipCode')
            },
            "relationship": {
                "is_director": self.get_text(relationship, 'isDirector') == "1",
                "is_officer": self.get_text(relationship, 'isOfficer') == "1",
                "is_ten_percent_owner": self.get_text(relationship, 'isTenPercentOwner') == "1",
                "is_other": self.get_text(relationship, 'isOther') == "1",
                "officer_title": self.get_text(relationship, 'officerTitle')
            }
        }

        return result

    def _parse_transactions(self, root: ET.Element) -> Dict[str, List[Dict]]:
        """Parse transaction information"""
        result = {
            "non_derivative_transactions": [],
            "derivative_transactions": []
        }

        # Parse non-derivative transactions
        non_deriv_table = root.find('nonDerivativeTable')
        if non_deriv_table is not None:
            for trans in non_deriv_table.findall('nonDerivativeTransaction'):
                result["non_derivative_transactions"].append(
                    self._parse_non_derivative_transaction(trans)
                )

        # Parse derivative transactions
        deriv_table = root.find('derivativeTable')
        if deriv_table is not None:
            for trans in deriv_table.findall('derivativeTransaction'):
                result["derivative_transactions"].append(
                    self._parse_derivative_transaction(trans)
                )

        return result

    def _parse_holdings(self, root: ET.Element) -> Dict[str, List[Dict]]:
        """Parse holdings information"""
        result = {
            "non_derivative_holdings": [],
            "derivative_holdings": []
        }

        # Parse non-derivative holdings
        non_deriv_table = root.find('nonDerivativeTable')
        if non_deriv_table is not None:
            for holding in non_deriv_table.findall('nonDerivativeHolding'):
                result["non_derivative_holdings"].append(
                    self._parse_non_derivative_holding(holding)
                )

        # Parse derivative holdings
        deriv_table = root.find('derivativeTable')
        if deriv_table is not None:
            for holding in deriv_table.findall('derivativeHolding'):
                result["derivative_holdings"].append(
                    self._parse_derivative_holding(holding)
                )

        return result

    def _parse_non_derivative_transaction(self, trans: ET.Element) -> Dict[str, Any]:
        """Parse non-derivative transaction"""
        trans_amounts = trans.find('transactionAmounts')
        post_trans = trans.find('postTransactionAmounts')
        ownership = trans.find('ownershipNature')

        return {
            "security_title": self.get_text(trans, 'securityTitle/value'),
            "transaction_date": self.format_date(self.get_text(trans, 'transactionDate/value')),
            "deemed_execution_date": self.format_date(self.get_text(trans, 'deemedExecutionDate/value')),
            "transaction_coding": {
                "form_type": self.get_text(trans, 'transactionCoding/transactionFormType'),
                "code": self.get_text(trans, 'transactionCoding/transactionCode'),
                "equity_swap": self.get_text(trans, 'transactionCoding/equitySwapInvolved') == "1"
            },
            "transaction_amounts": {
                "shares": self.get_text(trans_amounts, 'transactionShares/value'),
                "price_per_share": self.get_text(trans_amounts, 'transactionPricePerShare/value'),
                "acquired_disposed": self.get_text(trans_amounts, 'transactionAcquiredDisposedCode/value')
            },
            "shares_owned_following": self.get_text(post_trans, 'sharesOwnedFollowingTransaction/value'),
            "ownership_type": self.get_text(ownership, 'directOrIndirectOwnership/value')
        }

    def _parse_derivative_transaction(self, trans: ET.Element) -> Dict[str, Any]:
        """Parse derivative transaction"""
        trans_amounts = trans.find('transactionAmounts')
        underlying = trans.find('underlyingSecurity')
        post_trans = trans.find('postTransactionAmounts')
        ownership = trans.find('ownershipNature')

        result = {
            "security_title": self.get_text(trans, 'securityTitle/value'),
            "conversion_price": self.get_text(trans, 'conversionOrExercisePrice/value'),
            "transaction_date": self.format_date(self.get_text(trans, 'transactionDate/value')),
            "deemed_execution_date": self.format_date(self.get_text(trans, 'deemedExecutionDate/value')),
            "transaction_coding": {
                "form_type": self.get_text(trans, 'transactionCoding/transactionFormType'),
                "code": self.get_text(trans, 'transactionCoding/transactionCode'),
                "equity_swap": self.get_text(trans, 'transactionCoding/equitySwapInvolved') == "1"
            }
        }

        if trans_amounts is not None:
            result["transaction_amounts"] = {
                "shares": self.get_text(trans_amounts, 'transactionShares/value'),
                "price_per_share": self.get_text(trans_amounts, 'transactionPricePerShare/value'),
                "acquired_disposed": self.get_text(trans_amounts, 'transactionAcquiredDisposedCode/value')
            }

        if underlying is not None:
            result["underlying_security"] = {
                "title": self.get_text(underlying, 'underlyingSecurityTitle/value'),
                "shares": self.get_text(underlying, 'underlyingSecurityShares/value')
            }

        if post_trans is not None:
            result["shares_owned_following"] = self.get_text(post_trans, 'sharesOwnedFollowingTransaction/value')

        result["ownership_type"] = self.get_text(ownership, 'directOrIndirectOwnership/value')

        return result

    def _parse_non_derivative_holding(self, holding: ET.Element) -> Dict[str, Any]:
        """Parse non-derivative holding"""
        ownership = holding.find('ownershipNature')

        return {
            "security_title": self.get_text(holding, 'securityTitle/value'),
            "shares_owned": self.get_text(holding, 'postTransactionAmounts/sharesOwnedFollowingTransaction/value'),
            "ownership_type": self.get_text(ownership, 'directOrIndirectOwnership/value'),
            "nature_of_ownership": self.get_text(ownership, 'natureOfOwnership/value')
        }

    def _parse_derivative_holding(self, holding: ET.Element) -> Dict[str, Any]:
        """Parse derivative holding"""
        underlying = holding.find('underlyingSecurity')
        ownership = holding.find('ownershipNature')

        return {
            "security_title": self.get_text(holding, 'securityTitle/value'),
            "exercise_date": self.format_date(self.get_text(holding, 'exerciseDate/value')),
            "expiration_date": self.format_date(self.get_text(holding, 'expirationDate/value')),
            "underlying_security": {
                "title": self.get_text(underlying, 'underlyingSecurityTitle/value'),
                "shares": self.get_text(underlying, 'underlyingSecurityShares/value')
            },
            "ownership_type": self.get_text(ownership, 'directOrIndirectOwnership/value')
        }

    def _parse_footnotes(self, root: ET.Element) -> Dict[str, str]:
        """Parse footnotes"""
        footnotes_elem = root.find('footnotes')
        if footnotes_elem is None:
            return {}

        result = {}
        for footnote in footnotes_elem.findall('footnote'):
            footnote_id = footnote.get('id')
            if footnote_id:
                result[footnote_id] = footnote.text or ""

        return result

    def _parse_signature(self, root: ET.Element) -> Dict[str, str]:
        """Parse signature"""
        sig = root.find('ownerSignature')
        if sig is None:
            return {}

        return {
            "name": self.get_text(sig, 'signatureName'),
            "date": self.format_date(self.get_text(sig, 'signatureDate'))
        }