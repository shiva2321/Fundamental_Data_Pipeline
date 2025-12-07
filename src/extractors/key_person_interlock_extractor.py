"""
Key Person Interlock Extractor

Cross-references key persons across multiple companies to identify
board interlocks, executive transfers, and potential conflicts of interest.
"""
import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class KeyPersonInterlockExtractor:
    """
    Identify interlocks where same person holds positions at multiple companies.

    Detects:
    - Board interlocks (director on multiple boards)
    - Executive transfers (CEO/CFO at multiple companies)
    - Potential conflicts of interest
    """

    def __init__(self):
        """Initialize the interlock extractor"""
        self.person_index = defaultdict(list)  # person_name -> [(cik, title, company_name), ...]
        logger.info("KeyPersonInterlockExtractor initialized")

    def build_person_index(self, all_profiles: List[Dict]) -> None:
        """
        Build global index of persons and their affiliations across all companies.

        Args:
            all_profiles: List of all company profiles
        """
        self.person_index.clear()

        for profile in all_profiles:
            cik = profile.get('cik')
            company_name = profile.get('company_info', {}).get('name', 'Unknown')

            # Add executives
            key_persons = profile.get('key_persons', {})

            for executive in key_persons.get('executives', []):
                person_name = self._normalize_name(executive.get('name', ''))
                if person_name:
                    title = executive.get('title', 'Executive')
                    self.person_index[person_name].append({
                        'cik': cik,
                        'company_name': company_name,
                        'title': title,
                        'role_type': 'executive',
                        'tenure': executive.get('tenure')
                    })

            # Add board members
            for board_member in key_persons.get('board_members', []):
                person_name = self._normalize_name(board_member.get('name', ''))
                if person_name:
                    title = board_member.get('title', 'Board Member')
                    self.person_index[person_name].append({
                        'cik': cik,
                        'company_name': company_name,
                        'title': title,
                        'role_type': 'board_member',
                        'tenure': board_member.get('tenure')
                    })

        logger.info(f"Built person index with {len(self.person_index)} unique persons")

    def find_interlocks(self) -> List[Dict]:
        """
        Find all board interlocks where same person serves on multiple boards.

        Returns:
            List of interlock records
        """
        interlocks = []

        for person_name, affiliations in self.person_index.items():
            if len(affiliations) > 1:
                # Person holds multiple positions
                for i, aff1 in enumerate(affiliations):
                    for aff2 in affiliations[i+1:]:
                        if aff1['cik'] != aff2['cik']:
                            interlock = {
                                'person_name': person_name,
                                'company1_cik': aff1['cik'],
                                'company1_name': aff1['company_name'],
                                'company1_title': aff1['title'],
                                'company2_cik': aff2['cik'],
                                'company2_name': aff2['company_name'],
                                'company2_title': aff2['title'],
                                'interlock_type': self._determine_interlock_type(aff1, aff2),
                                'conflict_level': self._assess_conflict_level(aff1, aff2)
                            }
                            interlocks.append(interlock)

        logger.info(f"Found {len(interlocks)} board interlocks")
        return interlocks

    def find_executive_transfers(self, min_gap_years: int = 1) -> List[Dict]:
        """
        Find executives who moved between companies.

        Args:
            min_gap_years: Minimum years gap to consider as separate position

        Returns:
            List of executive transfer records
        """
        transfers = []

        for person_name, affiliations in self.person_index.items():
            executives = [a for a in affiliations if a['role_type'] == 'executive']

            if len(executives) > 1:
                # Person held executive positions at multiple companies
                for i, exec1 in enumerate(executives):
                    for exec2 in executives[i+1:]:
                        transfer = {
                            'person_name': person_name,
                            'from_company_cik': exec1['cik'],
                            'from_company_name': exec1['company_name'],
                            'from_title': exec1['title'],
                            'to_company_cik': exec2['cik'],
                            'to_company_name': exec2['company_name'],
                            'to_title': exec2['title'],
                            'transfer_type': self._determine_transfer_type(exec1['title'], exec2['title'])
                        }
                        transfers.append(transfer)

        logger.info(f"Found {len(transfers)} executive transfers")
        return transfers

    def find_conflict_of_interest(self, company_relationships: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Identify potential conflicts of interest based on interlocks
        and company relationships.

        Args:
            company_relationships: Optional list of company relationships

        Returns:
            List of potential conflicts
        """
        conflicts = []
        interlocks = self.find_interlocks()

        for interlock in interlocks:
            conflict_severity = self._assess_conflict_level(
                {'title': interlock['company1_title'], 'cik': interlock['company1_cik']},
                {'title': interlock['company2_title'], 'cik': interlock['company2_cik']}
            )

            if conflict_severity in ['SEVERE', 'MODERATE']:
                conflicts.append({
                    'person_name': interlock['person_name'],
                    'company1_cik': interlock['company1_cik'],
                    'company1_name': interlock['company1_name'],
                    'company1_title': interlock['company1_title'],
                    'company2_cik': interlock['company2_cik'],
                    'company2_name': interlock['company2_name'],
                    'company2_title': interlock['company2_title'],
                    'conflict_type': self._determine_conflict_type(
                        interlock['company1_title'],
                        interlock['company2_title']
                    ),
                    'severity': conflict_severity,
                    'description': self._describe_conflict(interlock)
                })

        logger.info(f"Found {len(conflicts)} potential conflicts of interest")
        return conflicts

    def _normalize_name(self, name: str) -> str:
        """Normalize person name for matching"""
        return name.strip().lower() if name else ''

    def _determine_interlock_type(self, aff1: Dict, aff2: Dict) -> str:
        """Determine type of interlock"""
        if aff1['role_type'] == 'board_member' and aff2['role_type'] == 'board_member':
            return 'dual_board_member'
        elif aff1['role_type'] == 'executive' and aff2['role_type'] == 'board_member':
            return 'executive_and_board'
        elif aff1['role_type'] == 'board_member' and aff2['role_type'] == 'executive':
            return 'board_and_executive'
        elif aff1['role_type'] == 'executive' and aff2['role_type'] == 'executive':
            return 'dual_executive'
        else:
            return 'other'

    def _determine_transfer_type(self, title1: str, title2: str) -> str:
        """Determine type of executive transfer"""
        roles = {title1.lower(), title2.lower()}

        if any('ceo' in r for r in roles):
            return 'ceo_transfer'
        elif any('cfo' in r for r in roles):
            return 'cfo_transfer'
        elif any('coo' in r for r in roles):
            return 'coo_transfer'
        else:
            return 'executive_transfer'

    def _determine_conflict_type(self, title1: str, title2: str) -> str:
        """Determine type of conflict"""
        title1_lower = title1.lower()
        title2_lower = title2.lower()

        if 'ceo' in title1_lower or 'ceo' in title2_lower:
            return 'executive_conflict'
        elif 'director' in title1_lower and 'director' in title2_lower:
            return 'dual_director'
        else:
            return 'board_interlock'

    def _assess_conflict_level(self, aff1: Dict, aff2: Dict) -> str:
        """Assess severity of conflict"""
        title1 = aff1.get('title', '').lower()
        title2 = aff2.get('title', '').lower()

        # Check for executive positions
        executive_keywords = {'ceo', 'cfo', 'coo', 'cto', 'president'}
        is_exec1 = any(kw in title1 for kw in executive_keywords)
        is_exec2 = any(kw in title2 for kw in executive_keywords)

        if is_exec1 and is_exec2:
            return 'SEVERE'
        elif is_exec1 or is_exec2:
            return 'MODERATE'
        else:
            return 'LOW'

    def _describe_conflict(self, interlock: Dict) -> str:
        """Generate description of conflict"""
        person = interlock['person_name'].title()
        company1 = interlock['company1_name']
        title1 = interlock['company1_title']
        company2 = interlock['company2_name']
        title2 = interlock['company2_title']

        return (f"{person} holds {title1} position at {company1} and {title2} position at {company2}. "
                f"Potential conflict of interest due to dual affiliation.")

    def get_person_affiliations(self, person_name: str) -> List[Dict]:
        """Get all affiliations for a specific person"""
        normalized = self._normalize_name(person_name)
        return self.person_index.get(normalized, [])

    def get_statistics(self) -> Dict:
        """Get overall interlock statistics"""
        interlocks = self.find_interlocks()
        transfers = self.find_executive_transfers()
        conflicts = self.find_conflict_of_interest()

        return {
            'total_persons': len(self.person_index),
            'persons_with_interlocks': len([p for p in self.person_index if len(self.person_index[p]) > 1]),
            'total_interlocks': len(interlocks),
            'executive_transfers': len(transfers),
            'conflicts_of_interest': len(conflicts),
            'severe_conflicts': len([c for c in conflicts if c['severity'] == 'SEVERE']),
            'moderate_conflicts': len([c for c in conflicts if c['severity'] == 'MODERATE']),
        }

