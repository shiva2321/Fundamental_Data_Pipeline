"""
SEC Registration Statement Parsers
===================================
Parsers for SEC Registration Statements (S-forms)

S-3ASR: Automatic Shelf Registration Statement
S-8: Registration Statement for Employee Stock Plans
S-8 POS: Post-Effective Amendment to S-8

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from Forms.baseParser import SECFormParser


class S3ASRParser(SECFormParser):
    """Parser for SEC Form S-3ASR - Automatic Shelf Registration Statement"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form S-3ASR document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "S-3ASR - Automatic Shelf Registration Statement",
            "filing_info": self._parse_header(document_text),
            "registration_info": {},
            "securities_registered": [],
            "risk_factors": [],
            "use_of_proceeds": "",
            "plan_of_distribution": ""
        }

        # Parse registration information
        result["registration_info"] = self._parse_registration_info(document_text)
        
        # Parse securities being registered
        result["securities_registered"] = self._parse_securities_registered(document_text)
        
        # Parse risk factors
        result["risk_factors"] = self._parse_risk_factors(document_text)
        
        # Parse use of proceeds
        result["use_of_proceeds"] = self._parse_use_of_proceeds(document_text)
        
        # Parse plan of distribution
        result["plan_of_distribution"] = self._parse_plan_of_distribution(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse SEC document header information"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "public_document_count": self._extract_field(header, r'PUBLIC DOCUMENT COUNT:\s*(\d+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "effectiveness_date": self.format_date(
                self._extract_field(header, r'EFFECTIVENESS DATE:\s*(\d+)')
            ) if 'EFFECTIVENESS DATE:' in header else "",
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "sec_file_number": self._extract_field(header, r'SEC FILE NUMBER:\s*(.+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_registration_info(self, document_text: str) -> Dict[str, Any]:
        """Parse registration information"""
        reg_info = {}

        # Extract registration number
        reg_match = re.search(
            r'Registration\s+(?:Statement\s+)?No\.\s*([\d-]+)',
            document_text[:2000],
            re.IGNORECASE
        )
        if reg_match:
            reg_info["registration_number"] = reg_match.group(1)

        # Check if automatic shelf registration
        if 'S-3ASR' in document_text[:2000] or 'Automatic Shelf' in document_text[:2000]:
            reg_info["registration_type"] = "Automatic Shelf"

        # Extract well-known seasoned issuer status
        if re.search(r'Well[- ]Known Seasoned Issuer', document_text[:5000], re.IGNORECASE):
            reg_info["well_known_seasoned_issuer"] = True

        return reg_info

    def _parse_securities_registered(self, document_text: str) -> List[Dict[str, str]]:
        """Parse securities being registered"""
        securities = []

        # Look for securities description in the registration statement
        security_patterns = [
            r'(?:Debt Securities|Notes)',
            r'(?:Common Stock|Preferred Stock)',
            r'(?:Warrants|Rights)',
            r'(?:Purchase Contracts|Units)'
        ]

        for pattern in security_patterns:
            if re.search(pattern, document_text[:10000], re.IGNORECASE):
                securities.append({
                    "security_type": re.search(pattern, document_text[:10000], re.IGNORECASE).group(0)
                })

        return securities[:10]

    def _parse_risk_factors(self, document_text: str) -> List[str]:
        """Parse risk factors"""
        risk_factors = []

        # Look for risk factors section
        risk_section = re.search(
            r'Risk Factors(.{0,3000}?)(?:Use of Proceeds|Description|Forward)',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if risk_section:
            section_text = risk_section.group(1)
            
            # Extract individual risk factors
            factor_patterns = [
                r'(?:^|\n)([A-Z][^\.]{30,300}?\.)\s*(?:\n|$)'
            ]

            for pattern in factor_patterns:
                matches = re.findall(pattern, section_text, re.MULTILINE)
                for factor in matches[:5]:
                    clean_factor = re.sub(r'<[^>]+>', '', factor).strip()
                    if len(clean_factor) > 30:
                        risk_factors.append(clean_factor[:300])

        return risk_factors

    def _parse_use_of_proceeds(self, document_text: str) -> str:
        """Parse use of proceeds section"""
        use_match = re.search(
            r'Use of Proceeds(.{0,800}?)(?:\n\n|(?:Risk Factors|Description|Ratio))',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if use_match:
            use_text = re.sub(r'<[^>]+>', '', use_match.group(1)).strip()
            use_text = re.sub(r'\s+', ' ', use_text)
            return use_text[:800]

        return ""

    def _parse_plan_of_distribution(self, document_text: str) -> str:
        """Parse plan of distribution section"""
        plan_match = re.search(
            r'Plan of Distribution(.{0,800}?)(?:\n\n|(?:Legal|Experts|Validity))',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if plan_match:
            plan_text = re.sub(r'<[^>]+>', '', plan_match.group(1)).strip()
            plan_text = re.sub(r'\s+', ' ', plan_text)
            return plan_text[:800]

        return ""


class S8Parser(SECFormParser):
    """Parser for SEC Form S-8 - Registration Statement for Employee Stock Plans"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form S-8 document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "S-8 - Registration Statement for Employee Stock Plans",
            "filing_info": self._parse_header(document_text),
            "plan_information": {},
            "securities_registered": {},
            "incorporation_by_reference": []
        }

        # Parse plan information
        result["plan_information"] = self._parse_plan_information(document_text)
        
        # Parse securities being registered
        result["securities_registered"] = self._parse_securities_info(document_text)
        
        # Parse incorporation by reference
        result["incorporation_by_reference"] = self._parse_incorporation(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse SEC document header information"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "public_document_count": self._extract_field(header, r'PUBLIC DOCUMENT COUNT:\s*(\d+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "effectiveness_date": self.format_date(
                self._extract_field(header, r'EFFECTIVENESS DATE:\s*(\d+)')
            ) if 'EFFECTIVENESS DATE:' in header else "",
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "sec_file_number": self._extract_field(header, r'SEC FILE NUMBER:\s*(.+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_plan_information(self, document_text: str) -> Dict[str, str]:
        """Parse employee stock plan information"""
        plan_info = {}

        # Extract plan name
        plan_patterns = [
            r'([A-Za-z0-9\s]+(?:Stock|Equity|Incentive|Employee|Purchase)\s+Plan)',
            r'Plan Name.*?:\s*(.+?)(?:\n|<)',
            r'(?:the|The)\s+([A-Za-z0-9\s]+Plan)\s+\('
        ]

        for pattern in plan_patterns:
            match = re.search(pattern, document_text[:5000], re.IGNORECASE)
            if match:
                plan_info["plan_name"] = match.group(1).strip()
                break

        # Extract plan adoption date
        date_match = re.search(
            r'(?:adopted|effective|established)\s+(?:on|as of)?\s*([A-Za-z]+\s+\d+,\s*\d{4})',
            document_text[:5000],
            re.IGNORECASE
        )
        if date_match:
            plan_info["plan_adoption_date"] = date_match.group(1)

        return plan_info

    def _parse_securities_info(self, document_text: str) -> Dict[str, str]:
        """Parse information about securities being registered"""
        securities_info = {}

        # Extract number of shares
        shares_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s+shares',
            r'shares.*?(\d{1,3}(?:,\d{3})*)',
            r'Amount to be [Rr]egistered.*?(\d{1,3}(?:,\d{3})*)'
        ]

        for pattern in shares_patterns:
            match = re.search(pattern, document_text[:3000], re.IGNORECASE)
            if match:
                securities_info["shares_registered"] = match.group(1)
                break

        # Extract security type
        if re.search(r'Common Stock', document_text[:3000], re.IGNORECASE):
            securities_info["security_type"] = "Common Stock"
        elif re.search(r'Preferred Stock', document_text[:3000], re.IGNORECASE):
            securities_info["security_type"] = "Preferred Stock"

        return securities_info

    def _parse_incorporation(self, document_text: str) -> List[str]:
        """Parse documents incorporated by reference"""
        incorporated_docs = []

        # Look for incorporation by reference section
        inc_section = re.search(
            r'Incorporation(?:s)?\s+(?:of|by)\s+Reference(.{0,2000}?)(?:Indemnification|Exhibits|$)',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if inc_section:
            section_text = inc_section.group(1)
            
            # Extract references to Form 10-K, 10-Q, etc.
            form_matches = re.findall(
                r'Form\s+(10-K|10-Q|8-K|DEF 14A).*?(?:filed|for the).*?(\w+\s+\d+,\s*\d{4})',
                section_text,
                re.IGNORECASE
            )

            for form_type, date in form_matches:
                incorporated_docs.append(f"{form_type} for {date}")

        return incorporated_docs[:10]


class S8POSParser(S8Parser):
    """Parser for SEC Form S-8 POS - Post-Effective Amendment to S-8"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form S-8 POS document"""
        result = super().parse(document_text)
        result["form_type"] = "S-8 POS - Post-Effective Amendment to S-8"
        
        # Add amendment information
        result["amendment_info"] = {
            "amendment_type": "Post-Effective",
            "original_file_number": self._extract_field(
                document_text,
                r'(?:amends|relates to)\s+(?:File|Registration)\s+No\.\s*([\d-]+)'
            )
        }
        
        return result
