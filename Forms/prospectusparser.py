"""
SEC Prospectus and Offering Document Parsers
=============================================
Parsers for SEC prospectus and offering documents

424B2: Prospectus filed pursuant to Rule 424(b)(2)
FWP: Free Writing Prospectus

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from Forms.baseParser import SECFormParser


class Form424B2Parser(SECFormParser):
    """Parser for SEC Form 424B2 - Prospectus"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 424B2 document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "424B2 - Prospectus",
            "filing_info": self._parse_header(document_text),
            "offering_info": {},
            "securities_offered": [],
            "underwriters": [],
            "use_of_proceeds": "",
            "risk_factors": []
        }

        # Parse offering information
        result["offering_info"] = self._parse_offering_info(document_text)
        
        # Parse securities being offered
        result["securities_offered"] = self._parse_securities_offered(document_text)
        
        # Parse underwriters
        result["underwriters"] = self._parse_underwriters(document_text)
        
        # Parse use of proceeds
        result["use_of_proceeds"] = self._parse_use_of_proceeds(document_text)
        
        # Parse risk factors
        result["risk_factors"] = self._parse_risk_factors(document_text)

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
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "sec_act": self._extract_field(header, r'SEC ACT:\s*(.+)'),
            "sec_file_number": self._extract_field(header, r'SEC FILE NUMBER:\s*(.+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_offering_info(self, document_text: str) -> Dict[str, Any]:
        """Parse offering information"""
        offering_info = {}

        # Extract total offering amount
        amount_patterns = [
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion)?.*?(?:aggregate|total|offering)',
            r'(?:Aggregate|Total).*?\$\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion)?'
        ]

        for pattern in amount_patterns:
            match = re.search(pattern, document_text[:5000], re.IGNORECASE | re.DOTALL)
            if match:
                offering_info["aggregate_offering_amount"] = "$" + match.group(1)
                break

        # Extract registration number
        reg_match = re.search(
            r'Registration\s+No\.\s*([\d-]+)',
            document_text[:5000],
            re.IGNORECASE
        )
        if reg_match:
            offering_info["registration_number"] = reg_match.group(1)

        # Extract prospectus date
        date_match = re.search(
            r'(?:Prospectus Supplement|Prospectus).*?dated\s+([A-Za-z]+\s+\d+,\s*\d{4})',
            document_text[:5000],
            re.IGNORECASE | re.DOTALL
        )
        if date_match:
            offering_info["prospectus_date"] = date_match.group(1)

        return offering_info

    def _parse_securities_offered(self, document_text: str) -> List[Dict[str, str]]:
        """Parse securities being offered"""
        securities = []

        # Look for notes, bonds, or other securities descriptions
        security_patterns = [
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:of|aggregate principal amount of)\s+(.+?Notes due \d{4})',
            r'([\d,]+)\s+shares of\s+(.+?stock)',
            r'\$\s*([\d,]+(?:\.\d+)?)\s+(.+?%\s+Notes due \d{4})'
        ]

        for pattern in security_patterns:
            matches = re.finditer(pattern, document_text[:10000], re.IGNORECASE)
            for match in matches:
                securities.append({
                    "amount": match.group(1),
                    "description": re.sub(r'<[^>]+>', '', match.group(2)).strip()[:200]
                })

        return securities[:10]  # Limit to first 10

    def _parse_underwriters(self, document_text: str) -> List[str]:
        """Parse underwriters"""
        underwriters = []

        # Look for underwriters section or joint book-running managers
        underwriter_section = re.search(
            r'(?:Joint Book-Running Managers|Underwriters)(.{0,2000}?)(?:Co-Managers|Table of Contents|$)',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if underwriter_section:
            section_text = underwriter_section.group(1)
            
            # Extract company names (simplified - looks for patterns like "Bank Name LLC" or "Bank & Co.")
            name_patterns = [
                r'([A-Z][A-Za-z\s&,\.]+(?:LLC|L\.P\.|Inc\.|Securities|Capital))',
                r'([A-Z][A-Za-z]+\s+(?:Securities|Capital|Bank))'
            ]

            for pattern in name_patterns:
                matches = re.findall(pattern, section_text)
                for name in matches:
                    clean_name = name.strip()
                    if len(clean_name) > 5 and clean_name not in underwriters:
                        underwriters.append(clean_name)

        return underwriters[:20]  # Limit to first 20

    def _parse_use_of_proceeds(self, document_text: str) -> str:
        """Parse use of proceeds section"""
        use_match = re.search(
            r'Use of Proceeds(.{0,500}?)(?:\n\n|(?:Risk Factors|Description))',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if use_match:
            use_text = re.sub(r'<[^>]+>', '', use_match.group(1)).strip()
            use_text = re.sub(r'\s+', ' ', use_text)
            return use_text[:500]

        return ""

    def _parse_risk_factors(self, document_text: str) -> List[str]:
        """Parse risk factors"""
        risk_factors = []

        # Look for risk factors section
        risk_section = re.search(
            r'Risk Factors(.{0,5000}?)(?:Use of Proceeds|Description|Underwriting)',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if risk_section:
            section_text = risk_section.group(1)
            
            # Extract individual risk factors (typically italicized or bulleted)
            factor_patterns = [
                r'•\s*(.{20,200}?)\.',
                r'<li>(.{20,200}?)</li>',
                r'(?:^|\n)([A-Z][^\.]{20,200}?\.)\s*(?:\n|$)'
            ]

            for pattern in factor_patterns:
                matches = re.findall(pattern, section_text, re.MULTILINE)
                for factor in matches:
                    clean_factor = re.sub(r'<[^>]+>', '', factor).strip()
                    clean_factor = re.sub(r'\s+', ' ', clean_factor)
                    if len(clean_factor) > 20:
                        risk_factors.append(clean_factor[:200])

        return risk_factors[:10]  # Limit to first 10


class FWPParser(SECFormParser):
    """Parser for SEC FWP - Free Writing Prospectus"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse FWP document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "FWP - Free Writing Prospectus",
            "filing_info": self._parse_header(document_text),
            "related_filing": "",
            "subject_matter": "",
            "issuer_information": {}
        }

        # Extract related registration statement
        result["related_filing"] = self._extract_related_filing(document_text)
        
        # Extract subject matter
        result["subject_matter"] = self._extract_subject_matter(document_text)
        
        # Extract issuer information
        result["issuer_information"] = self._extract_issuer_info(document_text)

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
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _extract_related_filing(self, document_text: str) -> str:
        """Extract related registration statement or filing"""
        reg_patterns = [
            r'Registration\s+(?:Statement\s+)?No\.\s*([\d-]+)',
            r'Filed pursuant to Rule 433.*?Registration Statement No\.\s*([\d-]+)',
            r'Relates to Registration Statement\s+No\.\s*([\d-]+)'
        ]

        for pattern in reg_patterns:
            match = re.search(pattern, document_text[:2000], re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)

        return ""

    def _extract_subject_matter(self, document_text: str) -> str:
        """Extract subject matter of the free writing prospectus"""
        # Try to get title or main subject
        title_match = re.search(
            r'<title>(.{0,200}?)</title>',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if title_match:
            return re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

        # Look for main heading
        heading_match = re.search(
            r'<h1[^>]*>(.{0,200}?)</h1>',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if heading_match:
            return re.sub(r'<[^>]+>', '', heading_match.group(1)).strip()

        return ""

    def _extract_issuer_info(self, document_text: str) -> Dict[str, str]:
        """Extract issuer information"""
        issuer_info = {}

        # Extract from header
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if header_match:
            header = header_match.group(1)
            issuer_info["name"] = self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)')
            issuer_info["cik"] = self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')

        return issuer_info
