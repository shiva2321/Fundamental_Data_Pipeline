import re
from datetime import datetime
from typing import Optional
import xml.etree.ElementTree as ET

class SECFormParser:
    """Base parser for SEC forms with common functionality"""

    @staticmethod
    def parse_xml_from_text(text: str) -> Optional[ET.Element]:
        """Extract and parse XML from SEC document text"""
        try:
            # Find XML content between <XML> and </XML> tags
            xml_match = re.search(r'<XML>(.*?)</XML>', text, re.DOTALL)
            if xml_match:
                xml_content = xml_match.group(1).strip()
                # Remove <?xml declaration if present
                xml_content = re.sub(r'<\?xml[^>]*\?>', '', xml_content).strip()
                return ET.fromstring(xml_content)
            return None
        except Exception as e:
            print(f"Error parsing XML: {e}")
            return None

    @staticmethod
    def get_text(element: Optional[ET.Element], path: str, default: str = "") -> str:
        """Safely get text from XML element"""
        if element is None:
            return default
        found = element.find(path)
        return found.text if found is not None and found.text else default

    @staticmethod
    def format_date(date_str: str) -> str:
        """Format date string to readable format"""
        if not date_str or len(date_str) < 8:
            return date_str
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.strftime('%B %d, %Y')
        except:
            return date_str
