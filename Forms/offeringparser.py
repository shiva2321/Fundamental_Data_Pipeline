"""
SEC Alternative Offering Forms Parsers
========================================
Parsers for Regulation A, Regulation D, and Crowdfunding offerings

FORM D: Private placements (Regulation D)
FORM 1-A: Regulation A offerings (up to $75M)
FORM C: Crowdfunding offerings
S-1: IPO registration

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, List, Any
from Forms.baseParser import SECFormParser


class FormDParser(SECFormParser):
    """Parser for Form D - Notice of Exempt Offering (Private Placements)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form D document"""
        result = {
            "form_type": "Form D - Notice of Exempt Offering (Regulation D)",
            "filing_info": self._parse_header(document_text),
            "issuer_information": {},
            "offering_information": {},
            "related_persons": [],
            "regulation_d_exemption": {}
        }

        result["issuer_information"] = self._parse_issuer_info(document_text)
        result["offering_information"] = self._parse_offering_info(document_text)
        result["regulation_d_exemption"] = self._parse_exemption(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse SEC document header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_issuer_info(self, document_text: str) -> Dict[str, Any]:
        """Parse issuer information"""
        root = self.parse_xml_from_text(document_text)
        if root is None:
            return {}

        issuer_elem = root.find('.//issuer')
        if issuer_elem is None:
            return {}

        return {
            "name": self.get_text(issuer_elem, 'issuerName'),
            "cik": self.get_text(issuer_elem, 'issuerCik'),
            "entity_type": self.get_text(issuer_elem, 'entityType'),
            "jurisdiction": self.get_text(issuer_elem, 'jurisdictionOfInc'),
            "year_of_incorporation": self.get_text(issuer_elem, 'yearOfInc')
        }

    def _parse_offering_info(self, document_text: str) -> Dict[str, Any]:
        """Parse offering information"""
        root = self.parse_xml_from_text(document_text)
        if root is None:
            return {}

        offering_elem = root.find('.//offeringData')
        if offering_elem is None:
            return {}

        return {
            "industry_group": self.get_text(offering_elem, 'industryGroupType'),
            "offering_type": self.get_text(offering_elem, 'typeOfOffering'),
            "total_offering_amount": self.get_text(offering_elem, 'totalOfferingAmount'),
            "total_amount_sold": self.get_text(offering_elem, 'totalAmountSold'),
            "total_remaining": self.get_text(offering_elem, 'totalRemaining'),
            "is_equity_offering": self.get_text(offering_elem, 'isEquityType'),
            "is_debt_offering": self.get_text(offering_elem, 'isDebtType')
        }

    def _parse_exemption(self, document_text: str) -> Dict[str, str]:
        """Parse Regulation D exemption information"""
        exemptions = {}
        
        # Check for Rule 506(b) or 506(c)
        if re.search(r'Rule\s+506\(b\)', document_text, re.IGNORECASE):
            exemptions["rule_506b"] = "true"
        if re.search(r'Rule\s+506\(c\)', document_text, re.IGNORECASE):
            exemptions["rule_506c"] = "true"
        if re.search(r'Rule\s+504', document_text, re.IGNORECASE):
            exemptions["rule_504"] = "true"

        return exemptions


class Form1AParser(SECFormParser):
    """Parser for Form 1-A - Offering Statement (Regulation A)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 1-A document"""
        result = {
            "form_type": "Form 1-A - Offering Statement (Regulation A)",
            "filing_info": self._parse_header(document_text),
            "offering_information": {},
            "tier": "",
            "use_of_proceeds": ""
        }

        result["tier"] = self._parse_tier(document_text)
        result["offering_information"] = self._parse_offering_info(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_tier(self, document_text: str) -> str:
        """Parse Regulation A tier"""
        if re.search(r'Tier\s+2', document_text, re.IGNORECASE):
            return "Tier 2"
        elif re.search(r'Tier\s+1', document_text, re.IGNORECASE):
            return "Tier 1"
        return ""

    def _parse_offering_info(self, document_text: str) -> Dict[str, str]:
        """Parse offering information"""
        return {
            "max_offering_amount": self._extract_field(
                document_text, r'Maximum\s+Offering.*?\$\s*([\d,]+)'
            )
        }


class FormCParser(SECFormParser):
    """Parser for Form C - Offering Statement (Crowdfunding)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form C document"""
        result = {
            "form_type": "Form C - Offering Statement (Crowdfunding)",
            "filing_info": self._parse_header(document_text),
            "issuer_information": {},
            "offering_information": {},
            "target_amount": "",
            "deadline": ""
        }

        result["offering_information"] = self._parse_offering_info(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_offering_info(self, document_text: str) -> Dict[str, str]:
        """Parse offering information"""
        return {
            "target_offering_amount": self._extract_field(
                document_text, r'Target\s+Offering.*?\$\s*([\d,]+)'
            ),
            "maximum_offering_amount": self._extract_field(
                document_text, r'Maximum\s+Offering.*?\$\s*([\d,]+)'
            )
        }


class S1Parser(SECFormParser):
    """Parser for Form S-1 - General Registration Statement (IPOs)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form S-1 document"""
        result = {
            "form_type": "S-1 - Registration Statement (IPO)",
            "filing_info": self._parse_header(document_text),
            "offering_information": {},
            "use_of_proceeds": "",
            "risk_factors": [],
            "business_description": "",
            "underwriters": []
        }

        result["offering_information"] = self._parse_offering_info(document_text)
        result["use_of_proceeds"] = self._parse_use_of_proceeds(document_text)
        result["risk_factors"] = self._parse_risk_factors(document_text)
        result["underwriters"] = self._parse_underwriters(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_offering_info(self, document_text: str) -> Dict[str, str]:
        """Parse offering information"""
        return {
            "proposed_maximum_aggregate_offering": self._extract_field(
                document_text, r'Proposed maximum aggregate offering price.*?\$\s*([\d,]+)'
            )
        }

    def _parse_use_of_proceeds(self, document_text: str) -> str:
        """Parse use of proceeds"""
        use_match = re.search(
            r'Use of Proceeds(.{0,1000}?)(?:Dividend|Capitalization|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if use_match:
            text = re.sub(r'<[^>]+>', '', use_match.group(1))
            return text.strip()[:1000]
        return ""

    def _parse_risk_factors(self, document_text: str) -> List[str]:
        """Parse risk factors"""
        risks = []
        risk_section = re.search(
            r'Risk Factors(.{0,3000}?)(?:Use of Proceeds|Forward|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if risk_section:
            risk_items = re.findall(r'[•\-]\s*(.{30,300}?)(?:\n|$)', risk_section.group(1))
            risks.extend([r.strip() for r in risk_items[:10]])
        return risks

    def _parse_underwriters(self, document_text: str) -> List[str]:
        """Parse underwriters"""
        underwriters = []
        underwriter_section = re.search(
            r'Underwriting(.{0,2000}?)(?:Legal Matters|Experts|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if underwriter_section:
            names = re.findall(
                r'([A-Z][A-Za-z\s&,\.]+(?:LLC|L\.P\.|Inc\.|Securities))',
                underwriter_section.group(1)
            )
            underwriters.extend(list(set(names))[:10])
        return underwriters
