# Create comprehensive parsers for Form 8-A12B, 8-K, and 8-K/A
"""
SEC Form 8 Parser Library
=========================
Comprehensive parsers for SEC Forms 8-A12B, 8-K, and 8-K/A

Form 8-A12B: Registration of certain classes of securities
Form 8-K: Current report of material events or corporate changes
Form 8-K/A: Amendment to Form 8-K

Author: Generated for SEC Filing Analysis
Date: December 2025
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from html.parser import HTMLParser
from html import unescape


class SECForm8Parser:
    """Base parser for SEC Form 8 series with common functionality"""

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
    def parse_header(document_text: str) -> Dict[str, Any]:
        """Parse SEC document header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        # Extract basic filing information
        result = {
            "accession_number": SECForm8Parser._extract_field(header, r'ACCESSION NUMBER:\\s*(\\S+)'),
            "submission_type": SECForm8Parser._extract_field(header, r'CONFORMED SUBMISSION TYPE:\\s*(\\S+)'),
            "public_document_count": SECForm8Parser._extract_field(header, r'PUBLIC DOCUMENT COUNT:\\s*(\\d+)'),
            "filed_as_of_date": SECForm8Parser.format_date(
                SECForm8Parser._extract_field(header, r'FILED AS OF DATE:\\s*(\\d+)')
            ),
            "date_as_of_change": SECForm8Parser.format_date(
                SECForm8Parser._extract_field(header, r'DATE AS OF CHANGE:\\s*(\\d+)')
            )
        }

        # Extract period of report if present (8-K specific)
        period = SECForm8Parser._extract_field(header, r'CONFORMED PERIOD OF REPORT:\\s*(\\d+)')
        if period:
            result["period_of_report"] = SECForm8Parser.format_date(period)

        # Extract item information if present (8-K specific)
        item_info = SECForm8Parser._extract_field(header, r'ITEM INFORMATION:\\s*(.+?)(?:\\n|$)')
        if item_info:
            result["item_information"] = item_info.strip()

        # Extract filer/company information
        result["filer"] = SECForm8Parser._parse_filer_info(header)

        return result

    @staticmethod
    def _extract_field(text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_filer_info(header: str) -> Dict[str, Any]:
        """Parse filer/company information from header"""
        filer_match = re.search(r'FILER:(.*?)(?=FILER:|ISSUER:|$)', header, re.DOTALL)
        if not filer_match:
            return {}

        filer_section = filer_match.group(1)

        result = {
            "company_data": {
                "name": SECForm8Parser._extract_field(filer_section, r'COMPANY CONFORMED NAME:\\s*(.+?)(?:\\n|$)'),
                "cik": SECForm8Parser._extract_field(filer_section, r'CENTRAL INDEX KEY:\\s*(\\d+)'),
                "sic": SECForm8Parser._extract_field(filer_section, r'STANDARD INDUSTRIAL CLASSIFICATION:\\s*(.+?)\\[?(\\d+)?\\]?(?:\\n|$)'),
                "irs_number": SECForm8Parser._extract_field(filer_section, r'IRS NUMBER:\\s*(\\S+)'),
                "state_of_incorporation": SECForm8Parser._extract_field(filer_section, r'STATE OF INCORPORATION:\\s*(\\S+)'),
                "fiscal_year_end": SECForm8Parser._extract_field(filer_section, r'FISCAL YEAR END:\\s*(\\d+)')
            }
        }

        # Parse business address
        business_addr = re.search(r'BUSINESS ADDRESS:(.*?)(?=MAIL ADDRESS:|FORMER COMPANY:|$)', filer_section, re.DOTALL)
        if business_addr:
            addr_text = business_addr.group(1)
            result["business_address"] = {
                "street1": SECForm8Parser._extract_field(addr_text, r'STREET 1:\\s*(.+?)(?:\\n|$)'),
                "street2": SECForm8Parser._extract_field(addr_text, r'STREET 2:\\s*(.+?)(?:\\n|$)'),
                "city": SECForm8Parser._extract_field(addr_text, r'CITY:\\s*(.+?)(?:\\n|$)'),
                "state": SECForm8Parser._extract_field(addr_text, r'STATE:\\s*(\\S+)'),
                "zip": SECForm8Parser._extract_field(addr_text, r'ZIP:\\s*(\\S+)'),
                "phone": SECForm8Parser._extract_field(addr_text, r'BUSINESS PHONE:\\s*(.+?)(?:\\n|$)')
            }

        # Parse mail address
        mail_addr = re.search(r'MAIL ADDRESS:(.*?)(?=FORMER COMPANY:|$)', filer_section, re.DOTALL)
        if mail_addr:
            addr_text = mail_addr.group(1)
            result["mail_address"] = {
                "street1": SECForm8Parser._extract_field(addr_text, r'STREET 1:\\s*(.+?)(?:\\n|$)'),
                "street2": SECForm8Parser._extract_field(addr_text, r'STREET 2:\\s*(.+?)(?:\\n|$)'),
                "city": SECForm8Parser._extract_field(addr_text, r'CITY:\\s*(.+?)(?:\\n|$)'),
                "state": SECForm8Parser._extract_field(addr_text, r'STATE:\\s*(\\S+)'),
                "zip": SECForm8Parser._extract_field(addr_text, r'ZIP:\\s*(\\S+)')
            }

        # Parse former company names
        former_companies = []
        for match in re.finditer(r'FORMER COMPANY:(.*?)(?=FORMER COMPANY:|</SEC-HEADER>|FILER:|$)', filer_section, re.DOTALL):
            former_text = match.group(1)
            former_name = SECForm8Parser._extract_field(former_text, r'FORMER CONFORMED NAME:\\s*(.+?)(?:\\n|$)')
            date_change = SECForm8Parser._extract_field(former_text, r'DATE OF NAME CHANGE:\\s*(\\d+)')
            if former_name:
                former_companies.append({
                    "name": former_name,
                    "date_of_change": SECForm8Parser.format_date(date_change) if date_change else ""
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
                "type": SECForm8Parser._extract_field(doc_content, r'<TYPE>([^<\\n]+)'),
                "sequence": SECForm8Parser._extract_field(doc_content, r'<SEQUENCE>(\\d+)'),
                "filename": SECForm8Parser._extract_field(doc_content, r'<FILENAME>([^<\\n]+)'),
                "description": SECForm8Parser._extract_field(doc_content, r'<DESCRIPTION>([^<\\n]+)')
            }

            # Extract text content (remove HTML/XML tags for summary)
            text_match = re.search(r'<TEXT>(.*?)</TEXT>', doc_content, re.DOTALL)
            if text_match:
                text_content = text_match.group(1)

                # Check if it's HTML/XBRL
                if '<HTML>' in text_content.upper() or '<html>' in text_content:
                    doc_info["content_type"] = "HTML"
                    doc_info["has_xbrl"] = 'xbrli:' in text_content or '<XBRL>' in text_content

                    # Extract key information from HTML
                    doc_info["summary"] = SECForm8Parser._extract_html_summary(text_content)
                elif text_content.strip().startswith('<?xml'):
                    doc_info["content_type"] = "XML"
                else:
                    doc_info["content_type"] = "TEXT"

                # Store first 500 chars as preview
                clean_text = re.sub(r'<[^>]+>', '', text_content)
                clean_text = re.sub(r'\\s+', ' ', clean_text).strip()
                doc_info["preview"] = clean_text[:500] + "..." if len(clean_text) > 500 else clean_text

            documents.append(doc_info)

        return documents

    @staticmethod
    def _extract_html_summary(html_content: str) -> Dict[str, Any]:
        """Extract key information from HTML content"""
        summary = {}

        # Extract XBRL facts if present
        if 'ix:nonNumeric' in html_content:
            # Extract document type
            doc_type = re.search(r'<ix:nonNumeric[^>]*name="dei:DocumentType"[^>]*>([^<]+)</ix:nonNumeric>', html_content)
            if doc_type:
                summary["document_type"] = doc_type.group(1).strip()

            # Extract entity name
            entity_name = re.search(r'<ix:nonNumeric[^>]*name="dei:EntityRegistrantName"[^>]*>([^<]+)</ix:nonNumeric>', html_content)
            if entity_name:
                summary["entity_name"] = entity_name.group(1).strip()

            # Extract CIK
            cik = re.search(r'<ix:nonNumeric[^>]*name="dei:EntityCentralIndexKey"[^>]*>([^<]+)</ix:nonNumeric>', html_content)
            if cik:
                summary["cik"] = cik.group(1).strip()

        # Extract Item sections (for 8-K)
        items = []
        for match in re.finditer(r'Item\\s+(\\d+\\.\\d+)[.:\\s]*([^<\\n]+)', html_content, re.IGNORECASE):
            items.append({
                "item_number": match.group(1),
                "item_title": match.group(2).strip()
            })

        if items:
            summary["items_reported"] = items

        return summary


class Form8A12BParser(SECForm8Parser):
    """
    Parser for SEC Form 8-A12B

    Form 8-A12B is used to register a class of securities under Section 12(b)
    of the Securities Exchange Act of 1934. This form is typically filed when
    a company wants to list its securities on a national securities exchange.
    """

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 8-A12B document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "Form 8-A12B - Registration of Securities",
            "filing_info": self.parse_header(document_text),
            "documents": self.parse_documents(document_text),
            "securities_info": self._parse_securities_info(document_text)
        }

        return result

    def _parse_securities_info(self, document_text: str) -> Dict[str, Any]:
        """Extract securities registration information"""
        info = {}

        # Look for securities class information in the main document
        main_doc = re.search(r'<TYPE>8-A12B.*?<TEXT>(.*?)</TEXT>', document_text, re.DOTALL | re.IGNORECASE)
        if main_doc:
            content = main_doc.group(1)

            # Extract title of securities
            title_match = re.search(r'Title of each class.*?(?:to be registered|being registered)[:\\s]*([^<\\n]+)', content, re.IGNORECASE)
            if title_match:
                info["title_of_securities"] = title_match.group(1).strip()

            # Extract trading symbol
            symbol_match = re.search(r'Trading [Ss]ymbol[:\\s]*([A-Z]+)', content)
            if symbol_match:
                info["trading_symbol"] = symbol_match.group(1)

            # Extract exchange
            exchange_match = re.search(r'Name of each exchange.*?registered[:\\s]*([^<\\n]+)', content, re.IGNORECASE)
            if exchange_match:
                info["exchange"] = exchange_match.group(1).strip()

        return info


class Form8KParser(SECForm8Parser):
    """
    Parser for SEC Form 8-K

    Form 8-K is a "current report" used to notify investors of significant
    events that shareholders should know about. Must be filed within 4 business
    days of the event.

    Common reportable events:
    - Item 1.01: Entry into Material Agreement
    - Item 1.02: Termination of Material Agreement
    - Item 2.01: Completion of Acquisition or Disposition
    - Item 2.02: Results of Operations and Financial Condition
    - Item 5.02: Departure/Election of Directors or Officers
    - Item 7.01: Regulation FD Disclosure
    - Item 8.01: Other Events
    - Item 9.01: Financial Statements and Exhibits
    """

    # Item number to description mapping
    ITEM_DESCRIPTIONS = {
        "1.01": "Entry into a Material Definitive Agreement",
        "1.02": "Termination of a Material Definitive Agreement",
        "1.03": "Bankruptcy or Receivership",
        "1.04": "Mine Safety - Reporting of Shutdowns and Patterns of Violations",
        "1.05": "Material Cybersecurity Incidents",
        "2.01": "Completion of Acquisition or Disposition of Assets",
        "2.02": "Results of Operations and Financial Condition",
        "2.03": "Creation of a Direct Financial Obligation",
        "2.04": "Triggering Events That Accelerate or Increase a Direct Financial Obligation",
        "2.05": "Costs Associated with Exit or Disposal Activities",
        "2.06": "Material Impairments",
        "3.01": "Notice of Delisting or Failure to Satisfy Listing Rule",
        "3.02": "Unregistered Sales of Equity Securities",
        "3.03": "Material Modification to Rights of Security Holders",
        "4.01": "Changes in Registrant's Certifying Accountant",
        "4.02": "Non-Reliance on Previously Issued Financial Statements",
        "5.01": "Changes in Control of Registrant",
        "5.02": "Departure of Directors or Officers; Election of Directors; Appointment of Officers",
        "5.03": "Amendments to Articles of Incorporation or Bylaws",
        "5.04": "Temporary Suspension of Trading Under Registrant's Employee Benefit Plans",
        "5.05": "Amendment to Registrant's Code of Ethics",
        "5.06": "Change in Shell Company Status",
        "5.07": "Submission of Matters to a Vote of Security Holders",
        "5.08": "Shareholder Nominations Pursuant to Exchange Act Rule 14a-11",
        "6.01": "ABS Informational and Computational Material",
        "6.02": "Change of Servicer or Trustee",
        "6.03": "Change in Credit Enhancement or Other External Support",
        "6.04": "Failure to Make a Required Distribution",
        "6.05": "Securities Act Updating Disclosure",
        "7.01": "Regulation FD Disclosure",
        "8.01": "Other Events",
        "9.01": "Financial Statements and Exhibits"
    }

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 8-K document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        filing_info = self.parse_header(document_text)

        result = {
            "form_type": "Form 8-K - Current Report",
            "filing_info": filing_info,
            "items_reported": self._parse_items(document_text, filing_info),
            "documents": self.parse_documents(document_text),
            "exhibits": self._parse_exhibits(document_text)
        }

        return result

    def _parse_items(self, document_text: str, filing_info: Dict) -> List[Dict[str, str]]:
        """Parse reported items from 8-K"""
        items = []

        # First check header for item information
        if "item_information" in filing_info:
            item_text = filing_info["item_information"]
            # Parse item numbers from header
            for item_num in re.findall(r'(\\d+\\.\\d+)', item_text):
                items.append({
                    "item_number": item_num,
                    "item_description": self.ITEM_DESCRIPTIONS.get(item_num, ""),
                    "source": "header"
                })

        # Also parse from document body
        main_doc = re.search(r'<TYPE>8-K.*?<TEXT>(.*?)</TEXT>', document_text, re.DOTALL | re.IGNORECASE)
        if main_doc:
            content = main_doc.group(1)

            # Find Item sections in the document
            for match in re.finditer(r'Item\\s+(\\d+\\.\\d+)[.:\\s]*([^<\\n]{0,200})', content, re.IGNORECASE):
                item_num = match.group(1)
                item_context = match.group(2).strip()

                # Check if already added from header
                if not any(item["item_number"] == item_num for item in items):
                    items.append({
                        "item_number": item_num,
                        "item_description": self.ITEM_DESCRIPTIONS.get(item_num, ""),
                        "context": item_context[:200] if item_context else "",
                        "source": "document"
                    })

        # Sort by item number
        items.sort(key=lambda x: x["item_number"])

        return items

    def _parse_exhibits(self, document_text: str) -> List[Dict[str, str]]:
        """Parse exhibit list from 8-K"""
        exhibits = []

        # Look for exhibit index/list
        exhibit_section = re.search(r'(Exhibit|EXHIBIT)\\s+(Index|LIST|No\\.)(.*?)(?=<DOCUMENT>|</TEXT>|$)',
                                   document_text, re.DOTALL | re.IGNORECASE)

        if exhibit_section:
            content = exhibit_section.group(3)

            # Parse exhibit entries
            for match in re.finditer(r'(\\d+(?:\\.\\d+)?)[\\s\\-]+([^\\n]+)', content):
                exhibit_num = match.group(1).strip()
                description = match.group(2).strip()

                # Clean up description
                description = re.sub(r'\\s+', ' ', description)

                exhibits.append({
                    "exhibit_number": exhibit_num,
                    "description": description
                })

        # Also check documents for exhibit types
        for doc in self.parse_documents(document_text):
            if doc["type"].startswith("EX-"):
                exhibit_num = doc["type"].replace("EX-", "")
                if not any(ex["exhibit_number"] == exhibit_num for ex in exhibits):
                    exhibits.append({
                        "exhibit_number": exhibit_num,
                        "description": doc.get("description", ""),
                        "filename": doc.get("filename", "")
                    })

        return exhibits


class Form8KAParser(Form8KParser):
    """
    Parser for SEC Form 8-K/A

    Form 8-K/A is an amendment to a previously filed Form 8-K.
    Used to correct errors or provide additional information.
    """

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form 8-K/A document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = super().parse(document_text)
        result["form_type"] = "Form 8-K/A - Amendment to Current Report"

        # Add amendment-specific information
        result["amendment_info"] = self._parse_amendment_info(document_text)

        return result

    def _parse_amendment_info(self, document_text: str) -> Dict[str, Any]:
        """Parse amendment-specific information"""
        info = {}

        main_doc = re.search(r'<TYPE>8-K/A.*?<TEXT>(.*?)</TEXT>', document_text, re.DOTALL | re.IGNORECASE)
        if main_doc:
            content = main_doc.group(1)

            # Look for explanatory note
            explan_note = re.search(r'(Explanatory Note|EXPLANATORY NOTE)(.*?)(?=Item|ITEM|<)',
                                   content, re.DOTALL | re.IGNORECASE)
            if explan_note:
                note_text = explan_note.group(2).strip()
                # Clean HTML tags
                note_text = re.sub(r'<[^>]+>', '', note_text)
                note_text = re.sub(r'\\s+', ' ', note_text).strip()
                info["explanatory_note"] = note_text[:1000]  # First 1000 chars

            # Look for reference to original filing
            orig_filing = re.search(r'originally filed on\\s+([A-Z][a-z]+\\s+\\d+,\\s+\\d{4})', content, re.IGNORECASE)
            if orig_filing:
                info["original_filing_date"] = orig_filing.group(1)

        return info


# Utility function to auto-detect and parse any Form 8 type
def parse_sec_form8(document_text: str) -> Dict[str, Any]:
    """
    Auto-detect Form 8 type and parse accordingly

    Args:
        document_text: Raw SEC document text

    Returns:
        Dictionary containing parsed form data
    """
    # Detect form type from header
    if 'SUBMISSION TYPE:\\t8-K/A' in document_text or 'CONFORMED SUBMISSION TYPE:\\t8-K/A' in document_text:
        parser = Form8KAParser()
    elif 'SUBMISSION TYPE:\\t8-K' in document_text or 'CONFORMED SUBMISSION TYPE:\\t8-K' in document_text:
        parser = Form8KParser()
    elif 'SUBMISSION TYPE:\\t8-A12B' in document_text or 'CONFORMED SUBMISSION TYPE:\\t8-A12B' in document_text:
        parser = Form8A12BParser()
    else:
        # Try to detect from content
        if '8-K/A' in document_text[:5000]:
            parser = Form8KAParser()
        elif '8-K' in document_text[:5000]:
            parser = Form8KParser()
        elif '8-A12B' in document_text[:5000]:
            parser = Form8A12BParser()
        else:
            return {"error": "Unknown Form 8 type"}

    return parser.parse(document_text)


# Example usage
if __name__ == "__main__":
    # Example: Parse a Form 8-K
    with open('sec_filings/AAPL/sample_forms/8-A12B/0001193125-19-292825.txt', 'r') as f:
        form8k_text = f.read()

    result = parse_sec_form8(form8k_text)
    print(json.dumps(result, indent=2))


