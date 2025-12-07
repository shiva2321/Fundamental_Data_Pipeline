from typing import Dict, Any, List

import xml.etree.ElementTree as ET
from Forms.baseParser import SECFormParser

class Form3Parser(SECFormParser):
    """
    Parser for SEC Form 3 - Initial Statement of Beneficial Ownership

    Form 3 is filed by insiders when they first become an officer, director,
    or beneficial owner of more than 10% of a class of equity securities.
    """

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 3 document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        root = self.parse_xml_from_text(document_text)
        if root is None:
            return {"error": "Failed to parse XML"}

        result = {
            "form_type": "Form 3 - Initial Statement of Beneficial Ownership",
            "filing_info": self._parse_filing_info(root),
            "issuer": self._parse_issuer(root),
            "reporting_owner": self._parse_reporting_owner(root),
            "securities_owned": self._parse_securities(root),
            "footnotes": self._parse_footnotes(root),
            "remarks": self.get_text(root, 'remarks'),
            "signature": self._parse_signature(root)
        }

        return result

    def _parse_filing_info(self, root: ET.Element) -> Dict[str, str]:
        """Parse filing information"""
        return {
            "schema_version": self.get_text(root, 'schemaVersion'),
            "document_type": self.get_text(root, 'documentType'),
            "period_of_report": self.format_date(self.get_text(root, 'periodOfReport')),
            "no_securities_owned": self.get_text(root, 'noSecuritiesOwned') == "1"
        }

    def _parse_issuer(self, root: ET.Element) -> Dict[str, str]:
        """Parse issuer (company) information"""
        issuer = root.find('issuer')
        if issuer is None:
            return {}

        return {
            "cik": self.get_text(issuer, 'issuerCik'),
            "name": self.get_text(issuer, 'issuerName'),
            "trading_symbol": self.get_text(issuer, 'issuerTradingSymbol')
        }

    def _parse_reporting_owner(self, root: ET.Element) -> Dict[str, Any]:
        """Parse reporting owner (insider) information"""
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

    def _parse_securities(self, root: ET.Element) -> Dict[str, List[Dict]]:
        """Parse securities ownership"""
        result = {
            "non_derivative_holdings": [],
            "derivative_holdings": []
        }

        # Parse non-derivative holdings (e.g., common stock)
        non_deriv_table = root.find('nonDerivativeTable')
        if non_deriv_table is not None:
            for holding in non_deriv_table.findall('nonDerivativeHolding'):
                result["non_derivative_holdings"].append(
                    self._parse_non_derivative_holding(holding)
                )

        # Parse derivative holdings (e.g., options, RSUs)
        deriv_table = root.find('derivativeTable')
        if deriv_table is not None:
            for holding in deriv_table.findall('derivativeHolding'):
                result["derivative_holdings"].append(
                    self._parse_derivative_holding(holding)
                )

        return result

    def _parse_non_derivative_holding(self, holding: ET.Element) -> Dict[str, Any]:
        """Parse non-derivative security holding"""
        ownership = holding.find('ownershipNature')

        return {
            "security_title": self.get_text(holding, 'securityTitle/value'),
            "shares_owned": self.get_text(holding, 'postTransactionAmounts/sharesOwnedFollowingTransaction/value'),
            "ownership_type": self.get_text(ownership, 'directOrIndirectOwnership/value'),
            "nature_of_ownership": self.get_text(ownership, 'natureOfOwnership/value')
        }

    def _parse_derivative_holding(self, holding: ET.Element) -> Dict[str, Any]:
        """Parse derivative security holding"""
        underlying = holding.find('underlyingSecurity')
        ownership = holding.find('ownershipNature')

        # Get footnote references
        conversion_footnote = holding.find('conversionOrExercisePrice/footnoteId')
        exercise_footnote = holding.find('exerciseDate/footnoteId')
        expiration_footnote = holding.find('expirationDate/footnoteId')

        return {
            "security_title": self.get_text(holding, 'securityTitle/value'),
            "conversion_price_footnote": conversion_footnote.get('id') if conversion_footnote is not None else None,
            "exercise_date_footnote": exercise_footnote.get('id') if exercise_footnote is not None else None,
            "expiration_date_footnote": expiration_footnote.get('id') if expiration_footnote is not None else None,
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
        """Parse signature information"""
        sig = root.find('ownerSignature')
        if sig is None:
            return {}

        return {
            "name": self.get_text(sig, 'signatureName'),
            "date": self.format_date(self.get_text(sig, 'signatureDate'))
        }


class Form3AParser(Form3Parser):
    """
    Parser for SEC Form 3/A - Amendment to Form 3

    Form 3/A is used to amend a previously filed Form 3.
    """

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 3/A document"""
        result = super().parse(document_text)
        result["form_type"] = "Form 3/A - Amendment to Initial Statement of Beneficial Ownership"
        return result

