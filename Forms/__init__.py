"""
SEC Forms Parser Package
=========================
Comprehensive collection of parsers for all major SEC form types

This package provides parsers for extracting structured data from SEC filings
"""

# Base parser
from Forms.baseParser import SECFormParser

# Trading forms
from Forms.form3parser import Form3Parser
from Forms.form4parser import Form4Parser
from Forms.form5parser import Form5Parser
from Forms.form144parser import Form144Parser, Form144AParser

# Periodic reports
from Forms.form10parser import Form10KParser, Form10QParser

# Current reports and events
from Forms.form8parser import SECForm8Parser, Form8KParser, Form8KAParser, Form8A12BParser

# Beneficial ownership
from Forms.schedule13Gparser import Schedule13GParser, Schedule13GAParser, SC13GParser, SC13GAParser

# Proxy statements
from Forms.proxyparser import DEF14AParser, DEFA14AParser, PX14A6GParser, PX14A6NParser

# Prospectus and offering documents
from Forms.prospectusparser import Form424B2Parser, FWPParser

# Registration statements
from Forms.registrationparser import S3ASRParser, S8Parser, S8POSParser

# Specialized disclosures
from Forms.formSDparser import FormSDParser

# Notifications and compliance
from Forms.form25parser import Form25Parser

# Miscellaneous forms
from Forms.miscparser import (
    CERTParser, CERTNYSParser, CORRESPParser,
    IRANNOTICEParser, NOACTParser, UPLOADParser
)

# Investment company forms (N-Series)
from Forms.investmentparser import (
    N1AParser, N2Parser, NCSRParser, NPORTParser,
    NPXParser, NCENParser
)

# Foreign issuer forms
from Forms.foreignparser import (
    Form20FParser, Form6KParser, F1Parser, F3Parser, Form40FParser
)

# Alternative offering forms
from Forms.offeringparser import (
    FormDParser, Form1AParser, FormCParser, S1Parser
)

# Administrative forms
from Forms.administrativeparser import (
    NT10KParser, NT10QParser, RWParser, EFFECTParser, Form12b25Parser
)

# Prospectus 424 variants
from Forms.prospectus424parser import (
    Form424B1Parser, Form424B3Parser, Form424B4Parser, Form424B5Parser,
    Form424AParser, Form424HParser
)

# Post-effective amendments
from Forms.posparser import (
    POSAMParser, POSEXParser, POS462BParser, POS462CParser, POSASRParser
)

# Schedule 13D and tender offers
from Forms.schedule13Dparser import (
    Schedule13DParser, Schedule13DAParser, SCTOParser,
    SCTO_IParser, SCTO_TParser, SC14D9Parser
)

# Additional registration forms
from Forms.additionalregistrationparser import (
    S3Parser, S4Parser, S11Parser, F2Parser, F4Parser, F6Parser, F8Parser, F10Parser
)

# Additional investment company forms
from Forms.additionalinvestmentparser import (
    N3Parser, N4Parser, N5Parser, N6Parser, N8AParser, N8B2Parser,
    N14Parser, N23C1Parser, NQParser
)

# Additional reporting forms
from Forms.additionalreportingparser import (
    Form11KParser, Form15Parser, Form15FParser, Form18KParser,
    ARSParser, PRE14AParser, DEF14CParser, DEFM14AParser, DEFR14AParser
)

__all__ = [
    # Base
    'SECFormParser',

    # Trading forms
    'Form3Parser',
    'Form4Parser',
    'Form5Parser',
    'Form144Parser',
    'Form144AParser',

    # Periodic reports
    'Form10KParser',
    'Form10QParser',

    # Current reports
    'SECForm8Parser',
    'Form8KParser',
    'Form8KAParser',
    'Form8A12BParser',

    # Beneficial ownership
    'Schedule13GParser',
    'Schedule13GAParser',
    'SC13GParser',
    'SC13GAParser',

    # Proxy statements
    'DEF14AParser',
    'DEFA14AParser',
    'PX14A6GParser',
    'PX14A6NParser',

    # Prospectus and offerings
    'Form424B2Parser',
    'FWPParser',

    # Registration statements
    'S3ASRParser',
    'S8Parser',
    'S8POSParser',

    # Specialized disclosures
    'FormSDParser',

    # Notifications
    'Form25Parser',

    # Miscellaneous
    'CERTParser',
    'CERTNYSParser',
    'CORRESPParser',
    'IRANNOTICEParser',
    'NOACTParser',
    'UPLOADParser',

    # Investment companies
    'N1AParser',
    'N2Parser',
    'NCSRParser',
    'NPORTParser',
    'NPXParser',
    'NCENParser',

    # Foreign issuers
    'Form20FParser',
    'Form6KParser',
    'F1Parser',
    'F3Parser',
    'Form40FParser',

    # Alternative offerings
    'FormDParser',
    'Form1AParser',
    'FormCParser',
    'S1Parser',

    # Administrative
    'NT10KParser',
    'NT10QParser',
    'RWParser',
    'EFFECTParser',
    'Form12b25Parser',
    
    # Prospectus 424 variants
    'Form424B1Parser',
    'Form424B3Parser',
    'Form424B4Parser',
    'Form424B5Parser',
    'Form424AParser',
    'Form424HParser',
    
    # Post-effective amendments
    'POSAMParser',
    'POSEXParser',
    'POS462BParser',
    'POS462CParser',
    'POSASRParser',
    
    # Schedule 13D and tender offers
    'Schedule13DParser',
    'Schedule13DAParser',
    'SCTOParser',
    'SCTO_IParser',
    'SCTO_TParser',
    'SC14D9Parser',
    
    # Additional registration
    'S3Parser',
    'S4Parser',
    'S11Parser',
    'F2Parser',
    'F4Parser',
    'F6Parser',
    'F8Parser',
    'F10Parser',
    
    # Additional investment company
    'N3Parser',
    'N4Parser',
    'N5Parser',
    'N6Parser',
    'N8AParser',
    'N8B2Parser',
    'N14Parser',
    'N23C1Parser',
    'NQParser',
    
    # Additional reporting
    'Form11KParser',
    'Form15Parser',
    'Form15FParser',
    'Form18KParser',
    'ARSParser',
    'PRE14AParser',
    'DEF14CParser',
    'DEFM14AParser',
    'DEFR14AParser',
]

# Mapping of form types to parser classes
FORM_PARSER_MAP = {
    # Trading forms
    '3': Form3Parser,
    '3/A': Form3Parser,
    '4': Form4Parser,
    '4/A': Form4Parser,
    '5': Form5Parser,
    '144': Form144Parser,
    '144/A': Form144AParser,

    # Periodic reports
    '10-K': Form10KParser,
    '10-Q': Form10QParser,
    '10-K/A': Form10KParser,
    '10-Q/A': Form10QParser,

    # Current reports
    '8-K': Form8KParser,
    '8-K/A': Form8KAParser,
    '8-A12B': Form8A12BParser,

    # Beneficial ownership
    'SC 13G': SC13GParser,
    'SC 13G/A': SC13GAParser,
    'SCHEDULE 13G/A': Schedule13GAParser,

    # Proxy statements
    'DEF 14A': DEF14AParser,
    'DEFA14A': DEFA14AParser,
    'PX14A6G': PX14A6GParser,
    'PX14A6N': PX14A6NParser,

    # Prospectus
    '424B2': Form424B2Parser,
    'FWP': FWPParser,

    # Registration
    'S-3ASR': S3ASRParser,
    'S-8': S8Parser,
    'S-8 POS': S8POSParser,

    # Specialized
    'SD': FormSDParser,
    '25': Form25Parser,
    '25-NSE': Form25Parser,

    # Miscellaneous
    'CERT': CERTParser,
    'CERTNYS': CERTNYSParser,
    'CORRESP': CORRESPParser,
    'IRANNOTICE': IRANNOTICEParser,
    'NO ACT': NOACTParser,
    'UPLOAD': UPLOADParser,

    # Investment Company Forms (N-Series)
    'N-1A': N1AParser,
    'N-2': N2Parser,
    'N-CSR': NCSRParser,
    'N-CSRS': NCSRParser,
    'N-PORT': NPORTParser,
    'N-PX': NPXParser,
    'N-CEN': NCENParser,

    # Foreign Issuer Forms
    '20-F': Form20FParser,
    '20-F/A': Form20FParser,
    '6-K': Form6KParser,
    '6-K/A': Form6KParser,
    'F-1': F1Parser,
    'F-1/A': F1Parser,
    'F-3': F3Parser,
    'F-3/A': F3Parser,
    '40-F': Form40FParser,
    '40-F/A': Form40FParser,

    # Alternative Offerings
    'D': FormDParser,
    'D/A': FormDParser,
    '1-A': Form1AParser,
    '1-A/A': Form1AParser,
    'C': FormCParser,
    'C/A': FormCParser,
    'S-1': S1Parser,
    'S-1/A': S1Parser,

    # Administrative Forms
    'NT 10-K': NT10KParser,
    'NT 10-Q': NT10QParser,
    'NT 10-K/A': NT10KParser,
    'NT 10-Q/A': NT10QParser,
    'RW': RWParser,
    'RW WD': RWParser,
    'EFFECT': EFFECTParser,
    '12b-25': Form12b25Parser,
    
    # Prospectus 424 Variants
    '424B1': Form424B1Parser,
    '424B3': Form424B3Parser,
    '424B4': Form424B4Parser,
    '424B5': Form424B5Parser,
    '424A': Form424AParser,
    '424H': Form424HParser,
    
    # Post-Effective Amendments
    'POS AM': POSAMParser,
    'POS EX': POSEXParser,
    'POS 462B': POS462BParser,
    'POS 462C': POS462CParser,
    'POSASR': POSASRParser,
    
    # Schedule 13D and Tender Offers
    'SC 13D': Schedule13DParser,
    'SC 13D/A': Schedule13DAParser,
    'SC TO': SCTOParser,
    'SC TO-I': SCTO_IParser,
    'SC TO-T': SCTO_TParser,
    'SC 14D9': SC14D9Parser,
    
    # Additional S-Forms
    'S-3': S3Parser,
    'S-3/A': S3Parser,
    'S-4': S4Parser,
    'S-4/A': S4Parser,
    'S-11': S11Parser,
    'S-11/A': S11Parser,
    
    # Additional F-Forms
    'F-2': F2Parser,
    'F-2/A': F2Parser,
    'F-4': F4Parser,
    'F-4/A': F4Parser,
    'F-6': F6Parser,
    'F-6/A': F6Parser,
    'F-8': F8Parser,
    'F-8/A': F8Parser,
    'F-10': F10Parser,
    'F-10/A': F10Parser,
    
    # Additional N-Forms
    'N-3': N3Parser,
    'N-3/A': N3Parser,
    'N-4': N4Parser,
    'N-4/A': N4Parser,
    'N-5': N5Parser,
    'N-6': N6Parser,
    'N-6/A': N6Parser,
    'N-8A': N8AParser,
    'N-8B-2': N8B2Parser,
    'N-14': N14Parser,
    'N-14/A': N14Parser,
    'N-23C-1': N23C1Parser,
    'N-Q': NQParser,
    
    # Additional Reporting Forms
    '11-K': Form11KParser,
    '11-K/A': Form11KParser,
    '15': Form15Parser,
    '15F': Form15FParser,
    '18-K': Form18KParser,
    'ARS': ARSParser,
    'PRE 14A': PRE14AParser,
    'DEF 14C': DEF14CParser,
    'DEFM14A': DEFM14AParser,
    'DEFR14A': DEFR14AParser,
}


def get_parser_for_form_type(form_type: str):
    """
    Get the appropriate parser class for a given form type

    Args:
        form_type: SEC form type (e.g., '10-K', '8-K', '144')

    Returns:
        Parser class or None if no parser available
    """
    return FORM_PARSER_MAP.get(form_type)


def parse_form(form_type: str, document_text: str):
    """
    Parse a SEC form document

    Args:
        form_type: SEC form type
        document_text: Raw document text

    Returns:
        Parsed data dictionary or None if no parser available
    """
    parser_class = get_parser_for_form_type(form_type)
    if parser_class:
        parser = parser_class()
        return parser.parse(document_text)
    return None

