"""
SEC Investment Company Forms Parsers (N-Series)
================================================
Parsers for investment company filings (mutual funds, ETFs, closed-end funds)

N-1A: Open-end management investment companies (mutual funds)
N-2: Closed-end management investment companies
N-CSR: Annual/semi-annual certified shareholder report
N-PORT: Monthly portfolio investments report
N-PX: Annual proxy voting record
N-CEN: Annual report for registered investment companies

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, List, Any
from Forms.baseParser import SECFormParser


class N1AParser(SECFormParser):
    """Parser for Form N-1A - Open-end Management Investment Company (Mutual Fund)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form N-1A document"""
        result = {
            "form_type": "N-1A - Mutual Fund Registration",
            "filing_info": self._parse_header(document_text),
            "fund_information": {},
            "investment_objectives": [],
            "fees_and_expenses": {},
            "principal_risks": [],
            "performance": {}
        }

        result["fund_information"] = self._parse_fund_info(document_text)
        result["investment_objectives"] = self._parse_investment_objectives(document_text)
        result["fees_and_expenses"] = self._parse_fees(document_text)
        result["principal_risks"] = self._parse_risks(document_text)
        result["performance"] = self._parse_performance(document_text)

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
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "file_number": self._extract_field(header, r'FILE NUMBER:\s*(.+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_fund_info(self, document_text: str) -> Dict[str, str]:
        """Parse fund information"""
        return {
            "fund_name": self._extract_field(document_text, r'Fund Name.*?:\s*(.+?)(?:\n|<)'),
            "fund_type": self._extract_field(document_text, r'Fund Type.*?:\s*(.+?)(?:\n|<)'),
            "investment_company_act_file_number": self._extract_field(
                document_text, r'Investment Company Act File Number.*?:\s*(.+?)(?:\n|<)'
            )
        }

    def _parse_investment_objectives(self, document_text: str) -> List[str]:
        """Parse investment objectives"""
        objectives = []
        obj_section = re.search(
            r'Investment Objective[s]?(.{0,1000}?)(?:Principal Investment|Fees|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if obj_section:
            text = re.sub(r'<[^>]+>', '', obj_section.group(1))
            objectives.append(text.strip()[:500])
        return objectives

    def _parse_fees(self, document_text: str) -> Dict[str, Any]:
        """Parse fees and expenses"""
        fees = {}
        
        # Management fee
        mgmt_fee = re.search(r'Management Fee[s]?.*?(\d+\.\d+)%', document_text, re.IGNORECASE)
        if mgmt_fee:
            fees["management_fee"] = mgmt_fee.group(1) + "%"
        
        # Expense ratio
        expense_ratio = re.search(r'(?:Total Annual|Expense Ratio).*?(\d+\.\d+)%', document_text, re.IGNORECASE)
        if expense_ratio:
            fees["expense_ratio"] = expense_ratio.group(1) + "%"
        
        return fees

    def _parse_risks(self, document_text: str) -> List[str]:
        """Parse principal risks"""
        risks = []
        risk_section = re.search(
            r'Principal Risk[s]?(.{0,2000}?)(?:Performance|Past Performance|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if risk_section:
            # Extract bullet points or paragraphs
            risk_items = re.findall(r'[•\-]\s*(.{20,200}?)(?:\n|$)', risk_section.group(1))
            risks.extend([r.strip() for r in risk_items[:10]])
        return risks

    def _parse_performance(self, document_text: str) -> Dict[str, str]:
        """Parse performance data"""
        performance = {}
        perf_section = re.search(
            r'Performance(.{0,1000}?)(?:Investment Adviser|Portfolio Manager|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if perf_section:
            performance["section_present"] = "true"
        return performance


class N2Parser(SECFormParser):
    """Parser for Form N-2 - Closed-end Investment Company"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form N-2 document"""
        result = {
            "form_type": "N-2 - Closed-end Investment Company Registration",
            "filing_info": self._parse_header(document_text),
            "fund_information": {},
            "use_of_proceeds": "",
            "investment_objectives": []
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class NCSRParser(SECFormParser):
    """Parser for Form N-CSR - Annual/Semi-annual Certified Shareholder Report"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form N-CSR document"""
        result = {
            "form_type": "N-CSR - Certified Shareholder Report",
            "filing_info": self._parse_header(document_text),
            "reporting_period": {},
            "fund_information": {},
            "portfolio_holdings": []
        }

        result["reporting_period"] = self._parse_reporting_period(document_text)
        result["fund_information"] = self._parse_fund_info(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            )
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_reporting_period(self, document_text: str) -> Dict[str, str]:
        """Parse reporting period"""
        period_match = re.search(
            r'Period.*?from\s+(.+?)\s+to\s+(.+?)(?:\n|<)',
            document_text, re.IGNORECASE
        )
        if period_match:
            return {
                "start_date": period_match.group(1),
                "end_date": period_match.group(2)
            }
        return {}

    def _parse_fund_info(self, document_text: str) -> Dict[str, str]:
        """Parse fund information"""
        return {
            "fund_name": self._extract_field(document_text, r'Fund Name.*?:\s*(.+?)(?:\n|<)')
        }


class NPORTParser(SECFormParser):
    """Parser for Form N-PORT - Monthly Portfolio Investments Report"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form N-PORT document"""
        result = {
            "form_type": "N-PORT - Monthly Portfolio Report",
            "filing_info": self._parse_header(document_text),
            "reporting_period": {},
            "portfolio_holdings": [],
            "summary_information": {}
        }

        result["reporting_period"] = self._parse_reporting_period(document_text)
        
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_reporting_period(self, document_text: str) -> Dict[str, str]:
        """Parse reporting period"""
        return {
            "period_end": self._extract_field(document_text, r'Report.*?Period.*?(\d{4}-\d{2}-\d{2})')
        }


class NPXParser(SECFormParser):
    """Parser for Form N-PX - Annual Proxy Voting Record"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form N-PX document"""
        result = {
            "form_type": "N-PX - Annual Proxy Voting Record",
            "filing_info": self._parse_header(document_text),
            "reporting_period": {},
            "proxy_votes": []
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class NCENParser(SECFormParser):
    """Parser for Form N-CEN - Annual Report for Registered Investment Companies"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form N-CEN document"""
        result = {
            "form_type": "N-CEN - Annual Report for Investment Companies",
            "filing_info": self._parse_header(document_text),
            "fund_information": {},
            "series_information": []
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""
