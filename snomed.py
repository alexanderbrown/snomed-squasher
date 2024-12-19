"""Module to parse SNOMED definitions."""
import glob
import os

import dotenv
import pandas as pd

dotenv.load_dotenv()

def parse_file(file_path: str, drop_inactive=True) -> pd.DataFrame:
    """Reads in a SNOMED file and returns a DataFrame."""

    # Explicitly tell pandas to read the 'term' column as a string. 
    # This prevents a bug where the string 'None' or 'N/A' is read as NaN
    converters = {'term': str} 

    df = pd.read_csv(file_path, sep='\t', converters=converters)
    if drop_inactive:
        df = df[df.active == 1]
        df.drop(columns=['active'], inplace=True)
    return df

class Snomed():
    """Class to parse SNOMED definitions.
    
    Parameters:
        cdr_path (str, optional): Path to the SNOMED CDR. 
                                  If not provided, will check for an environment variable called EXISTING_SNOMED_CDR.
    
    Attributes:
        cdr_path (str): Path to the SNOMED CDR.
        source_file (str): The source file for the SNOMED CDR.
        releases (list): List of available releases in the CDR.
        concepts (DataFrame): DataFrame of all concepts in the CDR.
        relationships (DataFrame): DataFrame of all relationships in the CDR.

    Methods:
        find_concept(name: str) -> int | None: 
            Finds a concept by name, returning the CUI if found, otherwise None.
        find_concepts(name: str) -> pd.DataFrame: 
            Finds a concept by name. Returns ideally one perfect match, 
                otherwise multiple partial matches, or an empty DataFrame.
        get_concepts(cui: int) -> pd.DataFrame: 
            Returns all concepts with the specified CUI.
        get_primary_concept(cui: int) -> pd.DataFrame: 
            Returns the primary concept with the specified CUI.
        get_parents(cui: int, primary_only: bool = True) -> pd.DataFrame: 
            Returns the parent concept(s) of the specified CUI.
        get_parents_by_name(name: str, primary_only: bool = True) -> pd.DataFrame: 
            Returns the parent concept(s) of the specified name.
        get_children(cui: int, primary_only: bool = True) -> pd.DataFrame:
            Returns the child concept(s) of the specified CUI.
        get_children_by_name(name: str, primary_only: bool = True) -> pd.DataFrame:
            Returns the child concept(s) of the specified name.
        get_ancestors(cui: int) -> pd.DataFrame:
            Returns all ancestor concepts of the specified CUI.
        
    
    """
    def __init__(self, cdr_path: str | None = None):
        self.cdr_path = _get_cdr_path(cdr_path)
        self.source_file = _get_source_file(self.cdr_path)

        self.releases = self._list_available_releases()
        self.concepts = self._load_all_concept_definitions()
        self.relationships = self._load_all_hierarchy_definitions()

    def find_concept(self, name: str) -> int | None:
        """Wrapper for find_concepts, but returns a single concept, or None if not found / multiple found.
        
        Parameters:
            name (str): The name to search for

        Returns the CUI of the concept if found, otherwise None.
        
        """

        matches = self.find_concepts(name)

        if len(matches) == 1:
            return matches.cui.values[0]

        return None
        
    def find_concepts(self, name: str) -> pd.DataFrame:
        """Finds a concept by name.
        
        First tries to find a full exact matches for the name. 
        
        If no matches, will try to find exact matches with a ' (disorder)' or ' (finding)' suffix.

        If no matches, will try to find partial matches.

        Parameters:
            name (str): The name to search for
        
        Returns a DataFrame containing the matching concepts. May be empty.
        
        """

        # Try full match first
        match = self.concepts.loc[self.concepts.name.str.fullmatch(name, case=False)]

        if match.empty:
            # Get all full matches, optionally with ' (disorder)' or ' (finding)' suffix
            regex = name +  r'(?: \(disorder\)| \(finding\))'
            match = self.concepts.loc[self.concepts.name.str.fullmatch(regex, case=False)]
        
        if match.empty:
            # Try partial match
            match = self.concepts.loc[self.concepts.name.str.contains(name, case=False)]
        
        return match
    
    def get_concepts(self, cui: int) -> pd.DataFrame:
        """Returns all concepts with the specified CUI.
        
        Parameters:
            cui (int): The CUI to search for

        Returns a DataFrame containing the matching concepts.
        """
        return self.concepts[self.concepts.cui == cui]
    
    def get_primary_concept(self, cui: int) -> pd.DataFrame:
        """Returns the primary concept with the specified CUI.
        
        Parameters:
            cui (int): The CUI to search for

        Returns a DataFrame containing the matching primary concept as a single row.
        """
        concepts = self.get_concepts(cui)
        primary_concept = concepts[concepts.name_status == 'P']
        if primary_concept.empty:
            raise ValueError(f"No primary concept found for CUI {cui}")
        if len(primary_concept) > 1:
            raise ValueError(f"Multiple primary concepts found for CUI {cui}")
        return primary_concept

    def get_parents(self, cui: int, primary_only: bool = True) -> pd.DataFrame:
        """Returns the parent concept(s) [first-order ancestors] of the specified CUI.
        
        Parameters:
            cui (int): The CUI to search for
            primary_only (bool): If True, will only return primary concepts

        Returns a DataFrame containing the parent concepts.
        """
        parent_ids = self.relationships[self.relationships.sourceId == cui].destinationId
        parents = self.concepts[self.concepts.cui.isin(parent_ids)]
        if primary_only:
            parents = parents[parents.name_status == 'P']
        return parents
    
    def get_parents_by_name(self, name: str, primary_only: bool = True) -> pd.DataFrame:
        """Returns the parent concept(s) [first-order ancestors] of the specified name.
        
        Parameters:
            name (str): The name to search for
            primary_only (bool): If True, will only return primary concepts

        Returns a DataFrame containing the parent concepts.
        """
        cui = self.find_concept(name)
        if cui is None:
            raise ValueError(f"No concept found with name {name}")
        return self.get_parents(cui, primary_only)
    
    def get_children(self, cui: int, primary_only: bool = True) -> pd.DataFrame:
        """Returns the child concept(s) [first-order descendants] of the specified CUI.
        
        Parameters:
            cui (int): The CUI to search for
            primary_only (bool): If True, will only return primary concepts

        Returns a DataFrame containing the child concepts.
        """
        child_ids = self.relationships[self.relationships.destinationId == cui].sourceId
        children = self.concepts[self.concepts.cui.isin(child_ids)]
        if primary_only:
            children = children[children.name_status == 'P']
        return children

    def get_children_by_name(self, name: str, primary_only: bool = True) -> pd.DataFrame:
        """Returns the child concept(s) [first-order descendants] of the specified name.
        
        Parameters:
            name (str): The name to search for
            primary_only (bool): If True, will only return primary concepts

        Returns a DataFrame containing the child concepts.
        """
        cui = self.find_concept(name)
        if cui is None:
            raise ValueError(f"No concept found with name {name}")
        return self.get_children(cui, primary_only)

    def get_ancestors(self, cui: int) -> pd.DataFrame:
        """Returns all ancestor concepts of the specified CUI (primary only).

        Parameters:
            cui (int): The CUI to search for

        Returns a DataFrame containing the ancestor concepts, along with the level, 
         the minimum number of steps required to reach the concept from the specified CUI.
        """
        ancestor_cuis, ancestor_levels = self._get_ancestors(cui)
        
        df = self.concepts[(self.concepts.cui.isin(ancestor_cuis)) & (self.concepts.name_status == 'P')]
        df_levels = pd.DataFrame({'cui': ancestor_cuis, 'level': ancestor_levels})
        min_level = df_levels.groupby('cui')['level'].min()
        df = df.merge(min_level, on='cui', how='left')
        return df.sort_values('level').reset_index(drop=True)
    
    def get_ancestors_by_name(self, name: str) -> pd.DataFrame:
        """Returns all ancestor concepts of the specified name (primary only).

        Parameters:
            name (str): The name to search for

        Returns a DataFrame containing the ancestor concepts, along with the level, 
         the minimum number of steps required to reach the concept from the specified CUI.  
        """
        cui = self.find_concept(name)
        if cui is None:
            raise ValueError(f"No concept found with name {name}")
        return self.get_ancestors(cui)

    def _list_available_releases(self) -> list[str]:
        """Lists the available releases in the CDR."""
        return [f for f in os.listdir(self.cdr_path) if os.path.isdir(os.path.join(self.cdr_path, f))]
    
    def _load_all_concept_definitions(self):
        """Loads all releases and concatenates in to a single DataFrame of concepts."""
        concepts = pd.concat([self._load_concept_definition(r) for r in self.releases])
        concepts.reset_index(inplace=True)
        concepts = _extract_description_type(concepts)
        return concepts

    def _load_concept_definition(self, release: str):
        """Converts a release to a DataFrame of concepts."""
        if release not in self.releases:
            raise ValueError(f"Release {release} not found in {self.cdr_path}")
        
        # Find the concept and description files
        concept_file = glob.glob(os.path.join(self.cdr_path, release, '*Concept*.txt'))[0]
        description_file = glob.glob(os.path.join(self.cdr_path, release, '*Description*.txt'))[0]

        # Read in DataFrames, drop unnecessary columns, and merge
        concepts = parse_file(concept_file)
        concepts.drop(columns=['effectiveTime', 'moduleId', 'definitionStatusId'], inplace=True)
        concepts.set_index('id', drop=True, inplace=True)

        descriptions = parse_file(description_file)
        descriptions.set_index('conceptId', drop=True, inplace=True)
        descriptions.drop(columns=['moduleId', 'languageCode', 'effectiveTime', 'caseSignificanceId'], inplace=True)

        df = pd.merge(concepts, descriptions, left_index=True, right_index=True, how='inner')
        df.drop(columns=['id'], inplace=True)
        df.rename(columns={'term': 'name'}, inplace=True)
        df.index.name = 'cui'

        # Process and add columns
        df = _convert_type_id(df)
        df['release'] = release

        return df
    
    def _load_all_hierarchy_definitions(self) -> pd.DataFrame:
        """Loads all releases and concatenates in to a single DataFrame of hierarchy definitions."""
        relationships = pd.concat([self._load_hierarchy_definition(r) for r in self.releases])
        return relationships.reset_index(drop=True)

    def _load_hierarchy_definition(self, release: str) -> pd.DataFrame:
        """Loads the hierarchy definition (`is_a` relationships) for a release."""
        isa_id = 116680003 # 116680003 is the 'is a' relationship (child -> parent)

        if release not in self.releases:
            raise ValueError(f"Release {release} not found in {self.cdr_path}")
        
        # Find the relationship file
        relationship_file = glob.glob(os.path.join(self.cdr_path, release, '*Relationship*.txt'))[0]

        # Read in DataFrame and drop unnecessary columns
        df = parse_file(relationship_file)
        df = df[df.typeId == isa_id]
        df = df[['id', 'sourceId', 'destinationId']]
        df['release'] = release
        return df.reset_index(drop=True)

    def _get_ancestors(self, cui: int, level: int = 0) -> pd.DataFrame | tuple[list[int], list[int]]:
        """Internal recursive function to get all ancestors of a concept."""
        parents = self.get_parents(cui)
        ancestor_cuis = []
        ancestor_levels = []
        for parent in parents.cui.unique():
            ancestor_cuis.append(parent)
            ancestor_levels.append(level+1)

            a,l = self._get_ancestors(parent, level=level+1)
            ancestor_cuis += a
            ancestor_levels += l

        return ancestor_cuis, ancestor_levels
# ------------------------------ Utils ---------------------------------------

def _get_cdr_path(cdr_path: str | None) -> str:
    """Returns the path to the SNOMED CDR."""
    if cdr_path:
        return cdr_path
    if 'EXISTING_SNOMED_CDR' in os.environ:
        return os.environ.get('EXISTING_SNOMED_CDR')
    
    raise ValueError('No SNOMED definitions path specified')
    
def _get_source_file(cdr_path: str) -> str:
    """Returns the source file for the SNOMED CDR."""
    with open(os.path.join(cdr_path, 'cdr_notes.txt'), 'r', encoding='utf-8') as file:
        first_line = file.readline()
        return first_line.replace('Source file: ', '').replace('.zip:\n', '')

# ----------------------- Concept Definition Processing -----------------------

def _convert_type_id(df: pd.DataFrame) -> pd.DataFrame:
    """Converts the typeId column to a name_status column.
    
    Name statuses:
    P: Primary / Preferred
    A: Alternative / Synonym
    """
    name_statuses = {
            900000000000003001: 'P', # Primary / Preferred
            900000000000013009: 'A'  # Alternative / Synonym
        }

    df['name_status'] = df.typeId.apply(lambda x: name_statuses[x])
    df.drop(columns=['typeId'], inplace=True)
    return df

def _extract_description_type(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts the description type from the name column.
    
    Description types are in parentheses at the end of the name column, such as (finding) or (organism).
    These appear only in the primary concept descriptions.

    Extracted description types are stored in a new column called description_type_ids, and
    applied only to primary concept descriptions.

    Alternative / synonym entries receive an empty string in the description_type_ids column.
    """
    description_type_regex = r"\((\w+\s?.?\s?\w+.?\w+.?\w+.?)\)$"

    primary_concept_descriptions=df[df['name_status']=='P']['name'].str.extract(description_type_regex)
    primary_concept_descriptions.columns = ['description_type_ids']
    df2 = df.join(primary_concept_descriptions, how='left')
    df2.description_type_ids = df2.description_type_ids.fillna('')
    return df2
