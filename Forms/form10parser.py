"""
SEC Form 10 Parser Library
==========================
Comprehensive parsers for SEC Forms 10-K and 10-Q

Form 10-K: Annual report with audited financial statements
Form 10-Q: Quarterly report with unaudited financial statements

Author: Generated for SEC Filing Analysis
Date: December 2025
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from html.parser import HTMLParser


class SECForm10Parser:
    """Base parser for SEC Form 10 series with common functionality"""

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
            return date_str
        except:
            return date_str

    @staticmethod
    def format_fiscal_year_end(mmdd: str) -> str:
        """Format fiscal year end MMDD to readable format"""
        if not mmdd or len(mmdd) != 4:
            return mmdd
        try:
            month = int(mmdd[:2])
            day = int(mmdd[2:])
            months = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
            return f"{months[month]} {day}"
        except:
            return mmdd

    @staticmethod
    def parse_header(document_text: str) -> Dict[str, Any]:
        """Parse SEC document header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        # Extract basic filing information
        result = {
            "accession_number": SECForm10Parser._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": SECForm10Parser._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(\S+)'),
            "public_document_count": SECForm10Parser._extract_field(header, r'PUBLIC DOCUMENT COUNT:\s*(\d+)'),
            "conformed_period_of_report": SECForm10Parser.format_date(
                SECForm10Parser._extract_field(header, r'CONFORMED PERIOD OF REPORT:\s*(\d+)')
            ),
            "filed_as_of_date": SECForm10Parser.format_date(
                SECForm10Parser._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "date_as_of_change": SECForm10Parser.format_date(
                SECForm10Parser._extract_field(header, r'DATE AS OF CHANGE:\s*(\d+)')
            )
        }

        # Extract filer/company information
        result["filer"] = SECForm10Parser._parse_filer_info(header)

        return result

    @staticmethod
    def _extract_field(text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_filer_info(header: str) -> Dict[str, Any]:
        """Parse filer/company information from header"""
        filer_match = re.search(r'FILER:(.*?)(?=</SEC-HEADER>|$)', header, re.DOTALL)
        if not filer_match:
            return {}

        filer_section = filer_match.group(1)

        fiscal_year_end = SECForm10Parser._extract_field(filer_section, r'FISCAL YEAR END:\s*(\d+)')

        result = {
            "company_data": {
                "name": SECForm10Parser._extract_field(filer_section, r'COMPANY CONFORMED NAME:\s*(.+?)(?:\n|$)'),
                "cik": SECForm10Parser._extract_field(filer_section, r'CENTRAL INDEX KEY:\s*(\d+)'),
                "sic": SECForm10Parser._extract_field(filer_section,
                                                      r'STANDARD INDUSTRIAL CLASSIFICATION:\s*(.+?)\[?(\d+)?\]?(?:\n|$)'),
                "irs_number": SECForm10Parser._extract_field(filer_section, r'IRS NUMBER:\s*(\S+)'),
                "ein": SECForm10Parser._extract_field(filer_section, r'EIN:\s*(\S+)'),
                "state_of_incorporation": SECForm10Parser._extract_field(filer_section,
                                                                         r'STATE OF INCORPORATION:\s*(\S+)'),
                "fiscal_year_end": SECForm10Parser.format_fiscal_year_end(fiscal_year_end),
                "fiscal_year_end_raw": fiscal_year_end
            },
            "filing_values": {
                "form_type": SECForm10Parser._extract_field(filer_section, r'FORM TYPE:\s*(\S+)'),
                "sec_act": SECForm10Parser._extract_field(filer_section, r'SEC ACT:\s*(.+?)(?:\n|$)'),
                "sec_file_number": SECForm10Parser._extract_field(filer_section, r'SEC FILE NUMBER:\s*(\S+)'),
                "film_number": SECForm10Parser._extract_field(filer_section, r'FILM NUMBER:\s*(\S+)')
            }
        }

        # Parse business address
        business_addr = re.search(r'BUSINESS ADDRESS:(.*?)(?=MAIL ADDRESS:|FORMER COMPANY:|$)', filer_section,
                                  re.DOTALL)
        if business_addr:
            addr_text = business_addr.group(1)
            result["business_address"] = {
                "street1": SECForm10Parser._extract_field(addr_text, r'STREET 1:\s*(.+?)(?:\n|$)'),
                "street2": SECForm10Parser._extract_field(addr_text, r'STREET 2:\s*(.+?)(?:\n|$)'),
                "city": SECForm10Parser._extract_field(addr_text, r'CITY:\s*(.+?)(?:\n|$)'),
                "state": SECForm10Parser._extract_field(addr_text, r'STATE:\s*(\S+)'),
                "zip": SECForm10Parser._extract_field(addr_text, r'ZIP:\s*(\S+)'),
                "phone": SECForm10Parser._extract_field(addr_text, r'BUSINESS PHONE:\s*(.+?)(?:\n|$)')
            }

        # Parse mail address
        mail_addr = re.search(r'MAIL ADDRESS:(.*?)(?=FORMER COMPANY:|$)', filer_section, re.DOTALL)
        if mail_addr:
            addr_text = mail_addr.group(1)
            result["mail_address"] = {
                "street1": SECForm10Parser._extract_field(addr_text, r'STREET 1:\s*(.+?)(?:\n|$)'),
                "street2": SECForm10Parser._extract_field(addr_text, r'STREET 2:\s*(.+?)(?:\n|$)'),
                "city": SECForm10Parser._extract_field(addr_text, r'CITY:\s*(.+?)(?:\n|$)'),
                "state": SECForm10Parser._extract_field(addr_text, r'STATE:\s*(\S+)'),
                "zip": SECForm10Parser._extract_field(addr_text, r'ZIP:\s*(\S+)')
            }

        # Parse former company names
        former_companies = []
        for match in re.finditer(r'FORMER COMPANY:(.*?)(?=FORMER COMPANY:|</SEC-HEADER>|$)', filer_section, re.DOTALL):
            former_text = match.group(1)
            former_name = SECForm10Parser._extract_field(former_text, r'FORMER CONFORMED NAME:\s*(.+?)(?:\n|$)')
            date_change = SECForm10Parser._extract_field(former_text, r'DATE OF NAME CHANGE:\s*(\d+)')
            if former_name:
                former_companies.append({
                    "name": former_name,
                    "date_of_change": SECForm10Parser.format_date(date_change) if date_change else ""
                })

        if former_companies:
            result["former_companies"] = former_companies

        return result

    @staticmethod
    def parse_documents(document_text: str) -> List[Dict[str, Any]]:
        """Parse all embedded documents in the filing"""
        documents = []

        # Find all document sections
        doc_pattern = r'<DOCUMENT>(.*?)</DOCUMENT>'
        for match in re.finditer(doc_pattern, document_text, re.DOTALL):
            doc_content = match.group(1)

            doc_info = {
                "type": SECForm10Parser._extract_field(doc_content, r'<TYPE>([^<\n]+)'),
                "sequence": SECForm10Parser._extract_field(doc_content, r'<SEQUENCE>(\d+)'),
                "filename": SECForm10Parser._extract_field(doc_content, r'<FILENAME>([^<\n]+)'),
                "description": SECForm10Parser._extract_field(doc_content, r'<DESCRIPTION>([^<\n]+)')
            }

            # Categorize document type
            doc_type = doc_info["type"].upper()
            if doc_type in ['10-K', '10-Q', '10-K/A', '10-Q/A']:
                doc_info["category"] = "Main Filing"
            elif doc_type.startswith('EX-'):
                doc_info["category"] = "Exhibit"
                doc_info["exhibit_number"] = doc_type.replace('EX-', '')
            elif 'GRAPHIC' in doc_type or doc_info["filename"].endswith(('.jpg', '.gif', '.png')):
                doc_info["category"] = "Graphic"
            elif 'XML' in doc_type or doc_info["filename"].endswith('.xml'):
                doc_info["category"] = "XBRL/XML"
            elif 'EXCEL' in doc_type or doc_info["filename"].endswith(('.xls', '.xlsx')):
                doc_info["category"] = "Excel"
            else:
                doc_info["category"] = "Other"

            # Extract text content info
            text_match = re.search(r'<TEXT>(.*?)</TEXT>', doc_content, re.DOTALL)
            if text_match:
                text_content = text_match.group(1)

                # Check content type
                if '<HTML>' in text_content.upper() or '<html>' in text_content:
                    doc_info["content_type"] = "HTML"
                    doc_info["has_xbrl"] = 'xbrli:' in text_content or '<XBRL>' in text_content or 'ix:' in text_content
                elif text_content.strip().startswith('<?xml'):
                    doc_info["content_type"] = "XML"
                elif text_content.strip().startswith('begin '):
                    doc_info["content_type"] = "Binary (uuencoded)"
                else:
                    doc_info["content_type"] = "TEXT"

                # Get size estimate
                doc_info["size_bytes"] = len(text_content)
                doc_info["size_kb"] = round(len(text_content) / 1024, 2)

            documents.append(doc_info)

        return documents

    @staticmethod
    def extract_xbrl_facts(document_text: str, fact_names: List[str]) -> Dict[str, Any]:
        """Extract specific XBRL facts from inline XBRL"""
        facts = {}

        for fact_name in fact_names:
            # Look for inline XBRL tags
            pattern = rf'<ix:nonNumeric[^>]*name="{re.escape(fact_name)}"[^>]*>([^<]+)</ix:nonNumeric>'
            match = re.search(pattern, document_text)
            if match:
                facts[fact_name] = match.group(1).strip()
            else:
                # Try without namespace prefix
                simple_name = fact_name.split(':')[-1]
                pattern = rf'<ix:nonNumeric[^>]*name="[^:]*:{re.escape(simple_name)}"[^>]*>([^<]+)</ix:nonNumeric>'
                match = re.search(pattern, document_text)
                if match:
                    facts[fact_name] = match.group(1).strip()

        return facts

    @staticmethod
    def parse_document_sections(document_text: str) -> Dict[str, List[str]]:
        """Parse major sections from the main document (Part I, Part II, etc.)"""
        sections = {}

        # Find the main 10-K or 10-Q document
        main_doc = re.search(r'<TYPE>10-[KQ].*?<TEXT>(.*?)</TEXT>', document_text, re.DOTALL | re.IGNORECASE)
        if not main_doc:
            return sections

        content = main_doc.group(1)

        # Look for Part headers
        part_pattern = r'(?:PART\s+([IVX]+)|Item\s+(\d+[A-Z]?\.?))\s*[:\-\.]*\s*([^<\n]{5,200})'

        for match in re.finditer(part_pattern, content, re.IGNORECASE):
            part_num = match.group(1) or match.group(2)
            title = match.group(3).strip()

            if part_num:
                section_key = f"Part {part_num}" if match.group(1) else f"Item {part_num}"
                if section_key not in sections:
                    sections[section_key] = []
                sections[section_key].append(title)

        return sections


class Form10KParser(SECForm10Parser):
    """
    Parser for SEC Form 10-K

    Form 10-K is a comprehensive annual report that provides a detailed overview
    of a company's business and financial condition. It includes audited financial
    statements and must be filed within 60-90 days after fiscal year end.

    Major Sections:
    - Part I: Business, Risk Factors, Properties
    - Part II: Financial Data, MD&A
    - Part III: Directors, Executive Compensation, Security Ownership
    - Part IV: Exhibits, Financial Statement Schedules
    """

    # Standard 10-K sections
    STANDARD_ITEMS = {
        "1": "Business",
        "1A": "Risk Factors",
        "1B": "Unresolved Staff Comments",
        "1C": "Cybersecurity",
        "2": "Properties",
        "3": "Legal Proceedings",
        "4": "Mine Safety Disclosures",
        "5": "Market for Registrant's Common Equity",
        "6": "Reserved",
        "7": "Management's Discussion and Analysis (MD&A)",
        "7A": "Quantitative and Qualitative Disclosures About Market Risk",
        "8": "Financial Statements and Supplementary Data",
        "9": "Changes in and Disagreements with Accountants",
        "9A": "Controls and Procedures",
        "9B": "Other Information",
        "9C": "Disclosure Regarding Foreign Jurisdictions",
        "10": "Directors, Executive Officers and Corporate Governance",
        "11": "Executive Compensation",
        "12": "Security Ownership and Stockholder Matters",
        "13": "Certain Relationships and Related Transactions",
        "14": "Principal Accounting Fees and Services",
        "15": "Exhibits and Financial Statement Schedules",
        "16": "Form 10-K Summary"
    }

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 10-K document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        filing_info = self.parse_header(document_text)

        # Extract key XBRL facts
        xbrl_facts = self.extract_xbrl_facts(document_text, [
            'dei:DocumentFiscalYearFocus',
            'dei:DocumentFiscalPeriodFocus',
            'dei:EntityRegistrantName',
            'dei:EntityCentralIndexKey',
            'dei:CurrentFiscalYearEndDate',
            'dei:DocumentType',
            'dei:AmendmentFlag'
        ])

        result = {
            "form_type": "Form 10-K - Annual Report",
            "filing_info": filing_info,
            "fiscal_info": {
                "fiscal_year": xbrl_facts.get('dei:DocumentFiscalYearFocus', ''),
                "fiscal_period": xbrl_facts.get('dei:DocumentFiscalPeriodFocus', 'FY'),
                "fiscal_year_end": xbrl_facts.get('dei:CurrentFiscalYearEndDate', ''),
                "period_end_date": filing_info.get('conformed_period_of_report', '')
            },
            "document_info": {
                "is_amendment": xbrl_facts.get('dei:AmendmentFlag', 'false') == 'true',
                "document_count": filing_info.get('public_document_count', '0')
            },
            "sections": self.parse_document_sections(document_text),
            "documents": self.parse_documents(document_text),
            "exhibits": self._parse_exhibits(document_text),
            "financial_statements": self._identify_financial_statements(document_text)
        }

        return result

    def _parse_exhibits(self, document_text: str) -> List[Dict[str, str]]:
        """Parse exhibit list from 10-K"""
        exhibits = []

        # Look for exhibit index
        exhibit_section = re.search(
            r'(EXHIBIT\s+INDEX|Item\s+15[^\n]{0,100}Exhibits)(.*?)(?=<DOCUMENT>|</TEXT>|SIGNATURES|$)',
            document_text, re.DOTALL | re.IGNORECASE
        )

        if exhibit_section:
            content = exhibit_section.group(2)

            # Parse exhibit entries - common format: "3.1  Description"
            for match in re.finditer(r'(\d+(?:\.\d+)?(?:\([a-z]\))?)[\s\-]+([^\n]+)', content):
                exhibit_num = match.group(1).strip()
                description = match.group(2).strip()

                # Clean up description
                description = re.sub(r'\s+', ' ', description)
                description = re.sub(r'\*+', '', description)

                if len(description) > 5:  # Filter out noise
                    exhibits.append({
                        "exhibit_number": exhibit_num,
                        "description": description[:500]  # Limit length
                    })

        # Also check documents for exhibit types
        for doc in self.parse_documents(document_text):
            if doc.get("category") == "Exhibit":
                exhibit_num = doc.get("exhibit_number", "")
                if exhibit_num and not any(ex["exhibit_number"] == exhibit_num for ex in exhibits):
                    exhibits.append({
                        "exhibit_number": exhibit_num,
                        "description": doc.get("description", ""),
                        "filename": doc.get("filename", "")
                    })

        # Sort by exhibit number
        try:
            exhibits.sort(key=lambda x: float(re.sub(r'[^0-9.]', '', x["exhibit_number"])))
        except:
            pass

        return exhibits

    def _identify_financial_statements(self, document_text: str) -> Dict[str, bool]:
        """Identify which financial statements are present"""
        statements = {
            "balance_sheet": False,
            "income_statement": False,
            "cash_flow_statement": False,
            "stockholders_equity": False,
            "notes_to_financial_statements": False
        }

        # Search for financial statement indicators
        content_lower = document_text.lower()

        if any(term in content_lower for term in
               ['balance sheet', 'statement of financial position', 'consolidated balance']):
            statements["balance_sheet"] = True

        if any(term in content_lower for term in
               ['income statement', 'statement of operations', 'statement of earnings',
                'consolidated statements of operations']):
            statements["income_statement"] = True

        if any(term in content_lower for term in
               ['cash flow', 'statement of cash flows', 'consolidated statements of cash']):
            statements["cash_flow_statement"] = True

        if any(term in content_lower for term in
               ['stockholders\' equity', 'shareholders\' equity', 'statement of equity']):
            statements["stockholders_equity"] = True

        if any(term in content_lower for term in
               ['notes to consolidated financial statements', 'notes to financial statements']):
            statements["notes_to_financial_statements"] = True

        return statements


class Form10QParser(SECForm10Parser):
    """
    Parser for SEC Form 10-Q

    Form 10-Q is a quarterly report that provides a continuing view of a company's
    financial position during the year. It includes unaudited financial statements
    and must be filed within 40-45 days after quarter end.

    Major Sections:
    - Part I: Financial Information (unaudited)
    - Part II: Other Information
    """

    # Standard 10-Q sections
    STANDARD_ITEMS = {
        "1": "Financial Statements (unaudited)",
        "2": "Management's Discussion and Analysis (MD&A)",
        "3": "Quantitative and Qualitative Disclosures About Market Risk",
        "4": "Controls and Procedures",
        "1A": "Risk Factors",
        "2": "Unregistered Sales of Equity Securities",
        "3": "Defaults Upon Senior Securities",
        "4": "Mine Safety Disclosures",
        "5": "Other Information",
        "6": "Exhibits"
    }

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 10-Q document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        filing_info = self.parse_header(document_text)

        # Extract key XBRL facts
        xbrl_facts = self.extract_xbrl_facts(document_text, [
            'dei:DocumentFiscalYearFocus',
            'dei:DocumentFiscalPeriodFocus',
            'dei:EntityRegistrantName',
            'dei:EntityCentralIndexKey',
            'dei:CurrentFiscalYearEndDate',
            'dei:DocumentType',
            'dei:AmendmentFlag'
        ])

        # Determine quarter
        fiscal_period = xbrl_facts.get('dei:DocumentFiscalPeriodFocus', '')
        quarter_map = {'Q1': 'First Quarter', 'Q2': 'Second Quarter', 'Q3': 'Third Quarter', 'Q4': 'Fourth Quarter'}
        quarter_name = quarter_map.get(fiscal_period, fiscal_period)

        result = {
            "form_type": "Form 10-Q - Quarterly Report",
            "filing_info": filing_info,
            "fiscal_info": {
                "fiscal_year": xbrl_facts.get('dei:DocumentFiscalYearFocus', ''),
                "fiscal_period": fiscal_period,
                "quarter": quarter_name,
                "fiscal_year_end": xbrl_facts.get('dei:CurrentFiscalYearEndDate', ''),
                "period_end_date": filing_info.get('conformed_period_of_report', '')
            },
            "document_info": {
                "is_amendment": xbrl_facts.get('dei:AmendmentFlag', 'false') == 'true',
                "document_count": filing_info.get('public_document_count', '0')
            },
            "sections": self.parse_document_sections(document_text),
            "documents": self.parse_documents(document_text),
            "exhibits": self._parse_exhibits(document_text),
            "financial_statements": self._identify_financial_statements(document_text)
        }

        return result

    def _parse_exhibits(self, document_text: str) -> List[Dict[str, str]]:
        """Parse exhibit list from 10-Q"""
        exhibits = []

        # Look for exhibit index
        exhibit_section = re.search(
            r'(EXHIBIT\s+INDEX|Item\s+6[^\n]{0,100}Exhibits|Part\s+II[^\n]{0,100}Item\s+6)(.*?)(?=<DOCUMENT>|</TEXT>|SIGNATURES|$)',
            document_text, re.DOTALL | re.IGNORECASE
        )

        if exhibit_section:
            content = exhibit_section.group(2)

            # Parse exhibit entries
            for match in re.finditer(r'(\d+(?:\.\d+)?(?:\([a-z]\))?)[\s\-]+([^\n]+)', content):
                exhibit_num = match.group(1).strip()
                description = match.group(2).strip()

                # Clean up description
                description = re.sub(r'\s+', ' ', description)
                description = re.sub(r'\*+', '', description)

                if len(description) > 5:
                    exhibits.append({
                        "exhibit_number": exhibit_num,
                        "description": description[:500]
                    })

        # Also check documents for exhibit types
        for doc in self.parse_documents(document_text):
            if doc.get("category") == "Exhibit":
                exhibit_num = doc.get("exhibit_number", "")
                if exhibit_num and not any(ex["exhibit_number"] == exhibit_num for ex in exhibits):
                    exhibits.append({
                        "exhibit_number": exhibit_num,
                        "description": doc.get("description", ""),
                        "filename": doc.get("filename", "")
                    })

        # Sort by exhibit number
        try:
            exhibits.sort(key=lambda x: float(re.sub(r'[^0-9.]', '', x["exhibit_number"])))
        except:
            pass

        return exhibits

    def _identify_financial_statements(self, document_text: str) -> Dict[str, bool]:
        """Identify which financial statements are present"""
        statements = {
            "condensed_balance_sheet": False,
            "condensed_income_statement": False,
            "condensed_cash_flow_statement": False,
            "condensed_stockholders_equity": False,
            "notes_to_financial_statements": False
        }

        # Search for financial statement indicators
        content_lower = document_text.lower()

        if any(term in content_lower for term in ['condensed consolidated balance sheet', 'condensed balance sheet']):
            statements["condensed_balance_sheet"] = True

        if any(term in content_lower for term in
               ['condensed consolidated statements of operations', 'condensed income statement',
                'condensed statement of operations']):
            statements["condensed_income_statement"] = True

        if any(term in content_lower for term in
               ['condensed consolidated statements of cash flows', 'condensed cash flow']):
            statements["condensed_cash_flow_statement"] = True

        if any(term in content_lower for term in
               ['condensed consolidated statements of shareholders\' equity', 'condensed statement of equity']):
            statements["condensed_stockholders_equity"] = True

        if any(term in content_lower for term in
               ['notes to condensed consolidated financial statements', 'notes to financial statements']):
            statements["notes_to_financial_statements"] = True

        return statements


# Utility function to auto-detect and parse any Form 10 type
def parse_sec_form10(document_text: str) -> Dict[str, Any]:
    """
    Auto-detect Form 10 type and parse accordingly

    Args:
        document_text: Raw SEC document text

    Returns:
        Dictionary containing parsed form data
    """
    # Detect form type from header
    if 'SUBMISSION TYPE:\t10-K' in document_text or 'CONFORMED SUBMISSION TYPE:\t10-K' in document_text:
        parser = Form10KParser()
    elif 'SUBMISSION TYPE:\t10-Q' in document_text or 'CONFORMED SUBMISSION TYPE:\t10-Q' in document_text:
        parser = Form10QParser()
    else:
        # Try to detect from content
        if '10-K' in document_text[:5000]:
            parser = Form10KParser()
        elif '10-Q' in document_text[:5000]:
            parser = Form10QParser()
        else:
            return {"error": "Unknown Form 10 type"}

    return parser.parse(document_text)


# Example usage
if __name__ == "__main__":
    # Example: Parse a Form 10-K
    with open('form10k_sample.txt', 'r') as f:
        form10k_text = f.read()

    result = parse_sec_form10(form10k_text)
    print(json.dumps(result, indent=2))