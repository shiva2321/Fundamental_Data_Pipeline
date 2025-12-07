"""
SEC Form 144 Parser
===================
Parser for SEC Form 144 - Notice of Proposed Sale of Securities

Form 144 is filed as notice of the proposed sale of restricted securities or securities held by 
an affiliate of the issuer. This form must be filed when the amount to be sold during any 
three-month period exceeds 5,000 shares or units or has an aggregate sales price greater than $50,000.

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET
from Forms.baseParser import SECFormParser


class Form144Parser(SECFormParser):
    """Parser for SEC Form 144 - Notice of Proposed Sale of Securities"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 144 document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "Form 144 - Notice of Proposed Sale of Securities",
            "filing_info": self._parse_header(document_text),
            "issuer": {},
            "securities_info": {},
            "securities_to_be_sold": {},
            "signature": {}
        }

        # Try to parse XML content
        root = self.parse_xml_from_text(document_text)
        if root is not None:
            result["issuer"] = self._parse_issuer_info(root)
            result["securities_info"] = self._parse_securities_information(root)
            result["securities_to_be_sold"] = self._parse_securities_to_be_sold(root)
            result["signature"] = self._parse_notice_signature(root)
        
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse SEC document header information"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(\S+)'),
            "public_document_count": self._extract_field(header, r'PUBLIC DOCUMENT COUNT:\s*(\d+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "date_as_of_change": self.format_date(
                self._extract_field(header, r'DATE AS OF CHANGE:\s*(\d+)')
            )
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _parse_issuer_info(self, root: ET.Element) -> Dict[str, Any]:
        """Parse issuer information"""
        issuer_elem = root.find('.//issuerInfo')
        if issuer_elem is None:
            return {}

        address_elem = issuer_elem.find('issuerAddress')
        
        return {
            "cik": self.get_text(issuer_elem, 'issuerCik'),
            "name": self.get_text(issuer_elem, 'issuerName'),
            "sec_file_number": self.get_text(issuer_elem, 'secFileNumber'),
            "address": {
                "street1": self.get_text(address_elem, 'ns2:street1') if address_elem is not None else "",
                "street2": self.get_text(address_elem, 'ns2:street2') if address_elem is not None else "",
                "city": self.get_text(address_elem, 'ns2:city') if address_elem is not None else "",
                "state": self.get_text(address_elem, 'ns2:stateOrCountry') if address_elem is not None else "",
                "zip_code": self.get_text(address_elem, 'ns2:zipCode') if address_elem is not None else ""
            },
            "contact_phone": self.get_text(issuer_elem, 'issuerContactPhone'),
            "person_selling_securities": self.get_text(issuer_elem, 'nameOfPersonForWhoseAccountTheSecuritiesAreToBeSold'),
            "relationship_to_issuer": self._parse_relationships(issuer_elem)
        }

    def _parse_relationships(self, issuer_elem: ET.Element) -> List[str]:
        """Parse relationship to issuer"""
        relationships = []
        rel_elem = issuer_elem.find('relationshipsToIssuer')
        if rel_elem is not None:
            for rel in rel_elem.findall('relationshipToIssuer'):
                if rel.text:
                    relationships.append(rel.text)
        return relationships

    def _parse_securities_information(self, root: ET.Element) -> Dict[str, Any]:
        """Parse securities information"""
        sec_info = root.find('.//securitiesInformation')
        if sec_info is None:
            return {}

        broker_elem = sec_info.find('brokerOrMarketmakerDetails')
        broker_addr = broker_elem.find('address') if broker_elem is not None else None

        return {
            "securities_class_title": self.get_text(sec_info, 'securitiesClassTitle'),
            "broker_or_marketmaker": {
                "name": self.get_text(broker_elem, 'name') if broker_elem is not None else "",
                "address": {
                    "street1": self.get_text(broker_addr, 'ns2:street1') if broker_addr is not None else "",
                    "street2": self.get_text(broker_addr, 'ns2:street2') if broker_addr is not None else "",
                    "city": self.get_text(broker_addr, 'ns2:city') if broker_addr is not None else "",
                    "state": self.get_text(broker_addr, 'ns2:stateOrCountry') if broker_addr is not None else "",
                    "zip_code": self.get_text(broker_addr, 'ns2:zipCode') if broker_addr is not None else ""
                }
            } if broker_elem is not None else {},
            "number_of_units_sold": self.get_text(sec_info, 'noOfUnitsSold'),
            "aggregate_market_value": self.get_text(sec_info, 'aggregateMarketValue'),
            "number_of_units_outstanding": self.get_text(sec_info, 'noOfUnitsOutstanding'),
            "approximate_sale_date": self.get_text(sec_info, 'approxSaleDate'),
            "securities_exchange_name": self.get_text(sec_info, 'securitiesExchangeName')
        }

    def _parse_securities_to_be_sold(self, root: ET.Element) -> Dict[str, Any]:
        """Parse securities to be sold information"""
        sec_sold = root.find('.//securitiesToBeSold')
        if sec_sold is None:
            return {}

        return {
            "securities_class_title": self.get_text(sec_sold, 'securitiesClassTitle'),
            "acquired_date": self.get_text(sec_sold, 'acquiredDate'),
            "nature_of_acquisition": self.get_text(sec_sold, 'natureOfAcquisitionTransaction'),
            "name_of_person_from_whom_acquired": self.get_text(sec_sold, 'nameOfPersonfromWhomAcquired'),
            "is_gift_transaction": self.get_text(sec_sold, 'isGiftTransaction'),
            "amount_of_securities_acquired": self.get_text(sec_sold, 'amountOfSecuritiesAcquired'),
            "payment_date": self.get_text(sec_sold, 'paymentDate'),
            "nature_of_payment": self.get_text(sec_sold, 'natureOfPayment')
        }

    def _parse_notice_signature(self, root: ET.Element) -> Dict[str, Any]:
        """Parse notice signature information"""
        sig_elem = root.find('.//noticeSignature')
        if sig_elem is None:
            return {}

        plan_dates = []
        plan_elem = sig_elem.find('planAdoptionDates')
        if plan_elem is not None:
            for date_elem in plan_elem.findall('planAdoptionDate'):
                if date_elem.text:
                    plan_dates.append(date_elem.text)

        return {
            "notice_date": self.get_text(sig_elem, 'noticeDate'),
            "plan_adoption_dates": plan_dates,
            "signature": self.get_text(sig_elem, 'signature')
        }


class Form144AParser(Form144Parser):
    """Parser for SEC Form 144/A - Amended Notice of Proposed Sale of Securities"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 144/A document"""
        result = super().parse(document_text)
        result["form_type"] = "Form 144/A - Amended Notice of Proposed Sale of Securities"
        return result
