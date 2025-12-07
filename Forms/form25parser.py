"""
SEC Form 25 Parser Library
==========================
Comprehensive parsers for SEC Forms 25 and 25-NSE

Form 25: Notification of Removal from Listing and/or Registration
Form 25-NSE: Notification filed by national securities exchange

These forms are filed when a class of securities is removed from listing
and/or registration on a securities exchange.

Author: Generated for SEC Filing Analysis
Date: December 2025
"""

import re
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Any


class SECForm25Parser:
    """Base parser for SEC Form 25 series with common functionality"""

    @staticmethod
    def format_date(date_str: str) -> str:
        """Format date string to readable format"""
        if not date_str or len(date_str) < 8:
            return date_str
        try:
            # Handle YYYYMMDD format
            if len(date_str) == 8 and date_str.isdigit():
                dt = datetime.strptime(date_str, '%Y%m%d')
                return dt.strftime('%B %d, %Y')
            # Handle YYYY-MM-DD format
            elif '-' in date_str:
                dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
                return dt.strftime('%B %d, %Y')
            # Handle MM/DD/YYYY format
            elif '/' in date_str:
                dt = datetime.strptime(date_str, '%m/%d/%Y')
                return dt.strftime('%B %d, %Y')
            return date_str
        except:
            return date_str

    @staticmethod
    def parse_header(document_text: str) -> Dict[str, Any]:
        """Parse SEC document header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        # Extract basic filing information
        result = {
            "accession_number": SECForm25Parser._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": SECForm25Parser._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(\S+)'),
            "public_document_count": SECForm25Parser._extract_field(header, r'PUBLIC DOCUMENT COUNT:\s*(\d+)'),
            "filed_as_of_date": SECForm25Parser.format_date(
                SECForm25Parser._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "date_as_of_change": SECForm25Parser.format_date(
                SECForm25Parser._extract_field(header, r'DATE AS OF CHANGE:\s*(\d+)')
            ),
            "effectiveness_date": SECForm25Parser.format_date(
                SECForm25Parser._extract_field(header, r'EFFECTIVENESS DATE:\s*(\d+)')
            )
        }

        return result

    @staticmethod
    def _extract_field(text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_company_section(section: str, section_name: str) -> Dict[str, Any]:
        """Parse company information section (FILER, SUBJECT COMPANY, FILED BY)"""
        result = {
            "company_data": {
                "name": SECForm25Parser._extract_field(section, r'COMPANY CONFORMED NAME:\s*(.+?)(?:\n|$)'),
                "cik": SECForm25Parser._extract_field(section, r'CENTRAL INDEX KEY:\s*(\d+)'),
                "sic": SECForm25Parser._extract_field(section,
                                                      r'STANDARD INDUSTRIAL CLASSIFICATION:\s*(.+?)\[?(\d+)?\]?(?:\n|$)'),
                "ein": SECForm25Parser._extract_field(section, r'(?:IRS NUMBER|EIN):\s*(\S+)'),
                "state_of_incorporation": SECForm25Parser._extract_field(section, r'STATE OF INCORPORATION:\s*(\S+)'),
                "fiscal_year_end": SECForm25Parser._extract_field(section, r'FISCAL YEAR END:\s*(\d+)')
            },
            "filing_values": {
                "form_type": SECForm25Parser._extract_field(section, r'FORM TYPE:\s*(\S+)'),
                "sec_act": SECForm25Parser._extract_field(section, r'SEC ACT:\s*(.+?)(?:\n|$)'),
                "sec_file_number": SECForm25Parser._extract_field(section, r'SEC FILE NUMBER:\s*(\S+)'),
                "film_number": SECForm25Parser._extract_field(section, r'FILM NUMBER:\s*(\S+)')
            }
        }

        # Parse business address
        business_addr = re.search(r'BUSINESS ADDRESS:(.*?)(?=MAIL ADDRESS:|FORMER COMPANY:|FILED BY:|</SEC-HEADER>|$)',
                                  section, re.DOTALL)
        if business_addr:
            addr_text = business_addr.group(1)
            result["business_address"] = {
                "street1": SECForm25Parser._extract_field(addr_text, r'STREET 1:\s*(.+?)(?:\n|$)'),
                "street2": SECForm25Parser._extract_field(addr_text, r'STREET 2:\s*(.+?)(?:\n|$)'),
                "city": SECForm25Parser._extract_field(addr_text, r'CITY:\s*(.+?)(?:\n|$)'),
                "state": SECForm25Parser._extract_field(addr_text, r'STATE:\s*(\S+)'),
                "zip": SECForm25Parser._extract_field(addr_text, r'ZIP:\s*(\S+)'),
                "phone": SECForm25Parser._extract_field(addr_text, r'BUSINESS PHONE:\s*(.+?)(?:\n|$)')
            }

        # Parse mail address
        mail_addr = re.search(r'MAIL ADDRESS:(.*?)(?=FORMER COMPANY:|FILED BY:|</SEC-HEADER>|$)',
                              section, re.DOTALL)
        if mail_addr:
            addr_text = mail_addr.group(1)
            result["mail_address"] = {
                "street1": SECForm25Parser._extract_field(addr_text, r'STREET 1:\s*(.+?)(?:\n|$)'),
                "street2": SECForm25Parser._extract_field(addr_text, r'STREET 2:\s*(.+?)(?:\n|$)'),
                "city": SECForm25Parser._extract_field(addr_text, r'CITY:\s*(.+?)(?:\n|$)'),
                "state": SECForm25Parser._extract_field(addr_text, r'STATE:\s*(\S+)'),
                "zip": SECForm25Parser._extract_field(addr_text, r'ZIP:\s*(\S+)')
            }

        # Parse former company names
        former_companies = []
        for match in re.finditer(
                r'FORMER COMPANY:(.*?)(?=FORMER COMPANY:|</SEC-HEADER>|FILED BY:|FILER:|SUBJECT COMPANY:|$)',
                section, re.DOTALL):
            former_text = match.group(1)
            former_name = SECForm25Parser._extract_field(former_text, r'FORMER CONFORMED NAME:\s*(.+?)(?:\n|$)')
            date_change = SECForm25Parser._extract_field(former_text, r'DATE OF NAME CHANGE:\s*(\d+)')
            if former_name:
                former_companies.append({
                    "name": former_name,
                    "date_of_change": SECForm25Parser.format_date(date_change) if date_change else ""
                })

        if former_companies:
            result["former_companies"] = former_companies

        return result


class Form25Parser(SECForm25Parser):
    """
    Parser for SEC Form 25

    Form 25 is filed to notify the SEC of the removal of a class of securities
    from listing and/or registration under Section 12(b) of the Securities
    Exchange Act of 1934.

    Common reasons for filing:
    - Voluntary delisting by the issuer
    - Securities redeemed or cancelled
    - Merger or acquisition
    - Transfer to another exchange
    - Bankruptcy
    """

    # CFR Rule provisions
    CFR_RULES = {
        "240.12d2-2(a)(1)": "Issuer has complied with exchange rules for delisting",
        "240.12d2-2(a)(2)": "Entire class of securities has been redeemed or paid at maturity",
        "240.12d2-2(a)(3)": "Entire class has been called for redemption and funds deposited",
        "240.12d2-2(a)(4)": "Entire class has been converted into another class",
        "240.12d2-2(b)": "Exchange has complied with its rules to strike the class",
        "240.12d2-2(c)": "Issuer has voluntarily withdrawn the class from listing"
    }

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 25 document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        header = self.parse_header(document_text)

        # Parse filer information
        filer_match = re.search(r'FILER:(.*?)(?=</SEC-HEADER>|$)', document_text, re.DOTALL)
        filer_info = {}
        if filer_match:
            filer_info = self._parse_company_section(filer_match.group(1), "FILER")

        result = {
            "form_type": "Form 25 - Notification of Removal from Listing and/or Registration",
            "filing_info": header,
            "issuer": filer_info,
            "exchange_info": self._parse_exchange_info(document_text),
            "securities": self._parse_securities(document_text),
            "cfr_provision": self._parse_cfr_provision(document_text),
            "signature": self._parse_signature(document_text)
        }

        return result

    def _parse_exchange_info(self, document_text: str) -> Dict[str, str]:
        """Parse exchange information from the document"""
        info = {}

        # Look for exchange name in the title or body
        exchange_match = re.search(r'Apple Inc\. / (.+?)(?:\n|</)', document_text, re.IGNORECASE)
        if exchange_match:
            info["exchange_name"] = exchange_match.group(1).strip()

        # Look for commission file number
        file_num = self._extract_field(document_text, r'Commission File Number:\s*([\d-]+)')
        if file_num:
            info["commission_file_number"] = file_num

        return info

    def _parse_securities(self, document_text: str) -> List[str]:
        """Parse list of securities being delisted"""
        securities = []

        # Look for securities listed in the document body
        # Pattern: percentage followed by "Notes due" and year
        for match in re.finditer(r'([\d.]+%\s+Notes\s+due\s+\d{4})', document_text, re.IGNORECASE):
            security = match.group(1).strip()
            if security not in securities:
                securities.append(security)

        # Also look for other security types
        for match in re.finditer(r'(Common Stock|Preferred Stock|Warrants?|Rights?)', document_text, re.IGNORECASE):
            security = match.group(1).strip()
            if security not in securities and len(securities) < 20:  # Reasonable limit
                securities.append(security)

        return securities

    def _parse_cfr_provision(self, document_text: str) -> Dict[str, Any]:
        """Parse the CFR rule provision relied upon"""
        result = {
            "rule": None,
            "description": None,
            "checked": False
        }

        # Look for checked boxes (■ or ☑ or X in box)
        for rule_code, description in self.CFR_RULES.items():
            # Pattern for checked box followed by rule
            pattern = r'[■☑✓Xx].*?' + re.escape(rule_code)
            if re.search(pattern, document_text, re.DOTALL | re.IGNORECASE):
                result["rule"] = rule_code
                result["description"] = description
                result["checked"] = True
                break

        # If no checked box found, look for any mentioned rule
        if not result["rule"]:
            for rule_code, description in self.CFR_RULES.items():
                if rule_code in document_text:
                    result["rule"] = rule_code
                    result["description"] = description
                    break

        return result

    def _parse_signature(self, document_text: str) -> Dict[str, str]:
        """Parse signature information"""
        sig_info = {}

        # Look for signature date
        date_match = re.search(r'Date:\s*([A-Z][a-z]+\s+\d+,\s+\d{4})', document_text)
        if date_match:
            sig_info["date"] = date_match.group(1)

        # Look for signatory name and title
        name_match = re.search(r'By:\s*/s/\s*(.+?)(?:\n|$)', document_text)
        if name_match:
            sig_info["name"] = name_match.group(1).strip()

        title_match = re.search(r'Title:\s*(.+?)(?:\n|$)', document_text)
        if title_match:
            sig_info["title"] = title_match.group(1).strip()

        return sig_info


class Form25NSEParser(SECForm25Parser):
    """
    Parser for SEC Form 25-NSE

    Form 25-NSE is filed by a national securities exchange to notify the SEC
    of the removal of a class of securities from listing and/or registration.

    This form is typically filed by the exchange (not the issuer) when:
    - Securities have been redeemed or cancelled
    - Issuer has failed to meet listing requirements
    - Issuer has requested delisting
    - Merger or acquisition has occurred
    """

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 25-NSE document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        header = self.parse_header(document_text)

        # Parse subject company (the company being delisted)
        subject_match = re.search(r'SUBJECT COMPANY:(.*?)(?=FILED BY:|</SEC-HEADER>|$)',
                                  document_text, re.DOTALL)
        subject_company = {}
        if subject_match:
            subject_company = self._parse_company_section(subject_match.group(1), "SUBJECT COMPANY")

        # Parse filed by (the exchange)
        filed_by_match = re.search(r'FILED BY:(.*?)(?=</SEC-HEADER>|$)', document_text, re.DOTALL)
        filed_by = {}
        if filed_by_match:
            filed_by = self._parse_company_section(filed_by_match.group(1), "FILED BY")

        result = {
            "form_type": "Form 25-NSE - Notification of Removal from Listing (Filed by Exchange)",
            "filing_info": header,
            "subject_company": subject_company,
            "exchange": filed_by,
            "removal_details": self._parse_xml_details(document_text)
        }

        return result

    def _parse_xml_details(self, document_text: str) -> Dict[str, Any]:
        """Parse XML document containing removal details"""
        xml_match = re.search(r'<XML>(.*?)</XML>', document_text, re.DOTALL)
        if not xml_match:
            return {}

        xml_content = xml_match.group(1).strip()

        try:
            root = ET.fromstring(xml_content)

            result = {
                "schema_version": self._get_xml_text(root, 'schemaVersion')
            }

            # Parse exchange info
            exchange_elem = root.find('exchange')
            if exchange_elem is not None:
                result["exchange_info"] = {
                    "cik": self._get_xml_text(exchange_elem, 'cik'),
                    "name": self._get_xml_text(exchange_elem, 'entityName')
                }

            # Parse issuer info
            issuer_elem = root.find('issuer')
            if issuer_elem is not None:
                issuer_info = {
                    "cik": self._get_xml_text(issuer_elem, 'cik'),
                    "name": self._get_xml_text(issuer_elem, 'entityName'),
                    "file_number": self._get_xml_text(issuer_elem, 'fileNumber')
                }

                # Parse address
                address_elem = issuer_elem.find('address')
                if address_elem is not None:
                    issuer_info["address"] = {
                        "street1": self._get_xml_text(address_elem, 'street1'),
                        "street2": self._get_xml_text(address_elem, 'street2'),
                        "city": self._get_xml_text(address_elem, 'city'),
                        "state": self._get_xml_text(address_elem, 'stateOrCountryCode'),
                        "state_name": self._get_xml_text(address_elem, 'stateOrCountry'),
                        "zip_code": self._get_xml_text(address_elem, 'zipCode'),
                        "phone": self._get_xml_text(address_elem, 'phoneNumber')
                    }

                result["issuer"] = issuer_info

            # Parse class of securities
            securities_elem = root.find('classOfSecurities')
            if securities_elem is not None:
                result["class_of_securities"] = {
                    "title": self._get_xml_text(securities_elem, 'title'),
                    "cusip": self._get_xml_text(securities_elem, 'cusip'),
                    "trading_symbol": self._get_xml_text(securities_elem, 'tradingSymbol')
                }

            # Parse removal details
            result["removal_date"] = self.format_date(self._get_xml_text(root, 'removalDate'))
            result["removal_reason"] = self._get_xml_text(root, 'removalReason')

            return result

        except ET.ParseError as e:
            return {"error": f"Failed to parse XML: {str(e)}"}

    @staticmethod
    def _get_xml_text(element: ET.Element, tag: str, default: str = "") -> str:
        """Safely get text from XML element"""
        found = element.find(tag)
        return found.text if found is not None and found.text else default


# Utility function to auto-detect and parse any Form 25 type
def parse_sec_form25(document_text: str) -> Dict[str, Any]:
    """
    Auto-detect Form 25 type and parse accordingly

    Args:
        document_text: Raw SEC document text

    Returns:
        Dictionary containing parsed form data
    """
    # Detect form type from header
    if 'SUBMISSION TYPE:\t25-NSE' in document_text or 'CONFORMED SUBMISSION TYPE:\t25-NSE' in document_text:
        parser = Form25NSEParser()
    elif 'SUBMISSION TYPE:\t25' in document_text or 'CONFORMED SUBMISSION TYPE:\t25' in document_text:
        parser = Form25Parser()
    elif 'SUBJECT COMPANY:' in document_text and 'FILED BY:' in document_text:
        parser = Form25NSEParser()
    else:
        # Default to Form 25
        parser = Form25Parser()

    return parser.parse(document_text)


# Example usage
if __name__ == "__main__":
    # Example: Parse a Form 25
    with open('form25_sample.txt', 'r') as f:
        form25_text = f.read()

    result = parse_sec_form25(form25_text)
    print(json.dumps(result, indent=2))