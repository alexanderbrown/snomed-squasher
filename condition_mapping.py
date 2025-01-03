'''Module to manage the mapping of freetext conditions to SNOMED codes'''
import glob
import json
import os

from IPython.display import clear_output, display, HTML
import pandas as pd

from snomed import Snomed

class ConditionMapper():
    '''Class to manage SNOMED mapping from an input text file - a list of freetext diagnoses.

    1. Identification of SNOMED `conditions` from freetext `strings`
    2. Grouping of identified `conditions` in to `groupings`. The `groupings` are also SNOMED codes.
    
    This class provides a variety of methods to interactively carry out these two mapping tasks, 
     as well as to non-destructively save and load mapping data, 
     and properties to access the mapping data in various formats.

    Note that the terminology used here is as follows:

    - `string` refers to a freetext condition name
    - `condition` refers to a SNOMED code, and has a pd.Series representation
    - `grouping` also refers to a SNOMED code, and has a pd.Series representation

    For `condition` and `grouping`, `cui` is the unique identifier for the SNOMED code, and has type int.

    Attributes:
        input_file: str
        output_location: str
        unknown_strings: list[str]
        string_to_condition_cui: dict[str, int]
        condition_to_grouping: dict[int, int]
        snomed: Snomed | None

    
    '''
    unknown_strings: list[str]
    string_to_condition_cui: dict[str, int]
    condition_cui_to_grouping_cui: dict[int, int]
    snomed: Snomed | None
    def __init__(self, input_file: str, file_number: int = 0, snomed: Snomed | None = None):
        '''Create a new ConditionMapper object
        
        Args:
            input_file: The path to the file containing the list of conditions to map
            file_number: The number of the saved mapping file to load (optional)
                            If 0, the input file is loaded and no mapping is loaded
                            If -1, the most recent saved mapping file is loaded
                            Otherwise, the mapping file with the specified number is loaded
            snomed: A Snomed object to use for mapping conditions to SNOMED-CT (optional)
        '''
        self.input_file = input_file
        if not os.path.exists(self.input_file):
            raise FileNotFoundError(f'File not found: {self.input_file}')
        self.output_location = os.path.splitext(self.input_file)[0]

        if file_number == 0:
            self.unknown_strings = _load_data(self.input_file)
            self.string_to_condition_cui = {}
            self.condition_cui_to_grouping_cui = {}
        elif file_number == -1:
            self.load_from_most_recent_mapping_file()
        else:
            self.load_from_mapping_file(file_number)
        if snomed:
            self.snomed = snomed
        else:
            self.snomed = None
        
    def __repr__(self):
        return f'ConditionMapper(input_file={self.input_file})'
    
    def __str__(self):
        return f'''ConditionMapper for {self.input_file} with:
        \t{len(self.unknown_strings)} unknown conditions,
        \tand {len(self.string_to_condition_cui)} known conditions'''

    def mapping_file_path(self, n: int) -> str:
        '''Return the path to the saved mapping file with the given number'''
        return f'{self.output_location}_mapped_{n}.json'
    
    @property
    def most_recent_mapping_file(self) -> int:
        '''Return the number of the most recent saved mapping file'''
        existing_output_files = glob.glob(f'{self.output_location}_mapped_*.json')
        if existing_output_files:
            return max(int(f.split('_')[-1].replace('.json', '')) for f in existing_output_files)
        return 0
    
    def save_mapping(self):
        '''Save the current mapping to a new file'''
        last_mapping_file_number = self.most_recent_mapping_file
        output_file = self.mapping_file_path(last_mapping_file_number + 1) 

        print(f'Saving mapping to {output_file}... ', end='')
        with open(output_file, 'w', encoding='utf-8') as file:
            data = {'unknown_strings': self.unknown_strings,
                    'string_to_condition_cui': self.string_to_condition_cui,
                    'condition_cui_to_grouping_cui': self.condition_cui_to_grouping_cui}
            json.dump(data, file, indent=4)
        print('Done')

    def load_from_mapping_file(self, n: int):
        '''Load a mapping from a specified saved file'''
        mapping_file = self.mapping_file_path(n)
        print(f'Loading mapping file {mapping_file}... ', end='')
        with open(mapping_file, 'r', encoding='utf-8') as file:
            mapping = json.load(file)
        print('Done')
        self.unknown_strings = mapping.get('unknown_strings', [])
        self.string_to_condition_cui = mapping.get('string_to_condition_cui', {})

        # As this is a dictionary, the keys are stored as strings:
        condition_to_grouping = mapping.get('condition_cui_to_grouping_cui', {})
        # Convert them back to integers:
        self.condition_cui_to_grouping_cui = {int(k): v for k,v in condition_to_grouping.items()}
    
    def load_from_most_recent_mapping_file(self):
        '''Load a mapping from the most recent saved file'''
        last_mapping_file_number = self.most_recent_mapping_file
        if last_mapping_file_number:
            self.load_from_mapping_file(last_mapping_file_number)
        else:
            raise FileNotFoundError('No mapping files found')
        
    def clear_mapping_files(self):
        '''Clear all saved mapping files'''
        response = input('Are you sure you want to clear all mapping files? (y/N) ')
        if response.lower() == 'y':
            existing_output_files = glob.glob(f'{self.output_location}_mapped_*.json')
            for f in existing_output_files:
                os.remove(f)
            print(f'{len(existing_output_files)} mapping files removed')

# ---------------------- Interactive mapping functions (string -> CUI) ----------------------

    def automatically_map_conditions(self):
        '''Automatically maps conditions to SNOMED-CT
        
        If an exact match is found, it is added to the string_to_condition dictionary'''

        if not self.snomed:
            raise ValueError('No SNOMED object provided')
        
        if len(self.unknown_strings) == 0:
            print('All conditions already mapped to SNOMED-CT')
            return

        print('Automatically mapping conditions to SNOMED-CT...')
        for condition_name in self.unknown_strings:
            cui = self.snomed.find_cui(condition_name)
            if cui:
                self.string_to_condition_cui[condition_name] = int(cui)
                concept = self.snomed.get_primary_concept(cui)
                print(f'\t{condition_name} mapped to {concept["name"]}')

        self.unknown_strings = [condition for condition in self.unknown_strings 
                                   if condition not in self.string_to_condition_cui]
        if self.unknown_strings:
            print(len(self.string_to_condition_cui), 'conditions mapped to SNOMED-CT.')
            print(len(self.unknown_strings), 'conditions not mapped to SNOMED-CT:')
            for condition in self.unknown_strings:
                print(f'\t{condition}')
        else:
            print(f'All {len(self.string_to_condition_cui)} conditions mapped to SNOMED-CT')

    def get_user_input_cuis(self):
        '''Gets manually entered CUIs for conditions. Useful after automatic mapping has been attempted.'''

        def get_user_input_cui(condition_name: str):
            if not self.snomed:
                raise ValueError('No SNOMED object provided')
            print(f'\nSearching for partial matches for {condition_name}...')
            matches = self.snomed.find_concepts(condition_name)
            if len(matches):
                with pd.option_context("display.max_rows", None):
                    df = matches[matches.name_status=='P'].set_index('cui')
                    
                    display(HTML("<div style='max-height: 400px; overflow: auto; width: 700px'>" +
                                df[['name']].style.to_html() +
                                "</div>"), clear=True)
            else:
                print(f'\tNo partial matches found for {condition_name}')

            return input(f'Enter the CUI for {condition_name}. Suggested options shown below, ' + 
                          'but you can enter any CUI. Press Enter to skip. ')

        if not self.snomed:
            raise ValueError('No SNOMED object provided')
        
        if len(self.unknown_strings) == 0:
            print('All conditions already mapped to SNOMED-CT')
            return

        cuis = {}
        for condition_name in self.unknown_strings:
            cuis[condition_name] = get_user_input_cui(condition_name)

        display(f'Manually mapped {len([v for v in cuis.values() if v])} conditions to SNOMED-CT:', clear=True)
        for raw_name, manual_cui in cuis.items():
            if manual_cui:
                try:
                    cui = int(manual_cui)
                except ValueError:
                    print(f'\t{manual_cui} is not a valid CUI. Skipping {raw_name}')
                    continue

                concept = self.snomed.get_primary_concept(cui)
                print(f'\t{raw_name} mapped to {concept["name"]} ({cui})')
                self.unknown_strings.remove(raw_name)
                self.string_to_condition_cui[raw_name] = int(cui)

        print(f'{len([v for v in cuis.values() if not v])} conditions skipped:')
        for raw_name,manual_cui in cuis.items():
            if not manual_cui:
                print(f'\t{raw_name}')

# ---------------------- Interactive mapping functions (CUI -> grouping) ----------------------

    def interactive_condition_group_selection(self, cui: int):
        '''Groups a condition interactively.
        
        Args:
            cui: The CUI of the condition to group

        Returns the CUI of the grouping, or None if no grouping is selected.
        '''
        if not self.snomed:
            raise ValueError('ConditionMapper must be initialized with a Snomed object to group conditions.')

        # 1. If the condition itself is already a known grouping, use that.
        if cui in self.known_grouping_cuis:
            return cui
        
        # Get condition and ancestors
        condition = self.snomed.get_primary_concept(cui)
        ancestors = self.snomed.get_ancestors(cui)

        # 2. If the condition has a one or more ancestors that are known groupings, suggest those to the user
        # We don't just assume that an ancestor is a grouping because it is a known grouping. 
        # For example, 'Lower Respiratory Tract Infection' is an ancestor of 'Bronchiolitis', but the 
        # user may wish to group 'Bronchiolitis' on its own.
        known_ancestors = ancestors[ancestors['cui'].isin(self.known_grouping_cuis)].reset_index(drop=True)
        if len(known_ancestors)>0:
            clear_output()
            print(f'Select grouping for {condition["name"]}. Ancestors already used as groupings:')
            display(known_ancestors[['name', 'cui', 'level']])
            idx = input(f'''The following are ancestors of {condition["name"]} that are already used as groupings.
                        Are any of these suitable? If so, please enter the index.
                        Otherwise, press escape or enter to see all ancestors.''')
            if idx:
                return known_ancestors.loc[int(idx)]['cui'].item()

        # 3. Ask if any of the ancestors are appropriate as new groupings (including the condition itself)
        clear_output()
        print(f'Select grouping for {condition["name"]}. All ancestors:') 
        display(ancestors[['name', 'cui', 'level']])
        idx = input(f'''Please enter the index of the most suitable ancestor for {condition["name"]}
                    This can be zero for the concept itself.
                    If none are suitable, press escape or enter to enter a CUI manually.''')
        if idx:
            return ancestors.loc[int(idx)]['cui'].item()
        
        # 4. Ask the user if any of the known groupings are appropriate. Presumably, 
        # these won't be ancestors of the condition, as if they were they would have been selected in step 2.
        # It is possible that a user may wish to break out of the SNOMED hierarchy and group a condition manually.
        clear_output()
        print(f'Select grouping for {condition["name"]}. All existing groupings:') 
        display(self.known_groupings)
        idx = input(f'''Please enter the index of the most suitable known grouping for {condition["name"]} 
                    If none are suitable, press escape or enter to enter a CUI manually.''')
        if idx:
            return self.known_groupings.loc[int(idx)]['cui'].item()

        # 5. If none of the above, ask for a manual entry of a new grouping. 
        # Again, this is likely to be a break from the SNOMED hierarchy.
        clear_output()
        print(f'Manual grouping entry for {condition["name"]}')
        response = input('Please enter a grouping CUI.')
        if response:
            return int(cui)
        
        return None
    
    def group_conditions(self):
        '''Groups conditions not yet grouped into existing or new groupings.'''
        n_new_grouping_mappings = 0
        n_groupings_start = len(self.known_grouping_cuis)
        for condition_cui in set(self.known_condition_cuis):
            if condition_cui in self.condition_cui_to_grouping_cui:
                continue

            grouping_cui = self.interactive_condition_group_selection(condition_cui)
            if grouping_cui:
                self.condition_cui_to_grouping_cui[condition_cui] = grouping_cui
                n_new_grouping_mappings += 1
            else:
                abort = input('Abort Grouping? (y/N)')
                if abort.lower() == 'y':
                    break

        clear_output()
        n_groupings_end = len(self.known_grouping_cuis)
        print(f'{n_groupings_end - n_groupings_start} new groupings created.')
        print(f'{n_new_grouping_mappings} new condition -> grouping mappings created.')

# ---------------------- Properties - manipuation of data structures ----------------------

    @property
    def known_condition_cuis(self) -> list[int]:
        '''Returns a list of all CUIs for all known conditions'''
        return list(set(self.string_to_condition_cui.values()))
    
    @property
    def known_conditions(self):
        '''Returns a DataFrame of all known conditions'''
        if not self.snomed:
            raise ValueError('No SNOMED object provided')
        df = pd.DataFrame([self.snomed.get_primary_concept(cui) for cui in self.known_condition_cuis])
        return df.reset_index(drop=True)

    @property
    def known_grouping_cuis(self) -> list[int]:
        '''Returns a list of all CUIs for all known groupings'''
        return list(set(self.condition_cui_to_grouping_cui.values()))
    
    @property
    def known_groupings(self) -> pd.DataFrame:
        '''Returns a DataFrame of all conditions that have been grouped'''
        if not self.snomed:
            raise ValueError('No SNOMED object provided')
        df = pd.DataFrame([self.snomed.get_primary_concept(cui) for cui in self.known_grouping_cuis])
        if len(df) == 0:
            return pd.DataFrame(columns=['cui', 'name', 'name_status', 'release', 'description_type_ids'])
        return df.reset_index(drop=True)
    
    @property 
    def condition_cui_to_strings(self) -> dict[int, list[str]]:
        '''Returns a dictionary mapping CUIs to lists of strings'''
        cui_to_strings = {}
        for condition, cui in self.string_to_condition_cui.items():
            cui_to_strings.setdefault(cui, []).append(condition)
        return cui_to_strings
    
    @property
    def grouping_cui_to_condition_cuis(self) -> dict[int, list[int]]:
        '''Returns a dictionary mapping groupings to lists of condition CUIs'''
        grouping_to_cuis = {}
        for cui, grouping in self.condition_cui_to_grouping_cui.items():
            grouping_to_cuis.setdefault(grouping, []).append(cui)
        return grouping_to_cuis
    
    @property
    def grouping_cui_to_strings(self) -> dict[int, list[str]]:
        '''Returns a dictionary mapping groupings to lists of condition strings'''
        grouping_to_strings = {}
        for grouping, cuis in self.grouping_cui_to_condition_cuis.items():
            for cui in cuis:
                grouping_to_strings.setdefault(grouping, []).extend(self.condition_cui_to_strings[cui])
        return grouping_to_strings
    
    @property
    def string_to_grouping_cui(self) -> dict[str, int]:
        '''Returns a dictionary mapping condition strings to groupings'''
        string_to_grouping = {}
        for condition, cui in self.string_to_condition_cui.items():
            string_to_grouping[condition] = self.condition_cui_to_grouping_cui.get(cui, -1)
        return string_to_grouping

    @property
    def groupings_table(self):
        '''Returns a DataFrame of all strings, conditions, and groupings. 
        
        This can be used to display the mapping in a tabular format, to save to a file, or for further analysis.
        
        For example, you can get a dict of all grouping names -> list of strings as:
        
        (CM.groupings_table
            .reset_index()
            .groupby('grouping_name')['string']
            .apply(lambda x: x.tolist())
            .to_dict()
        )
        '''


        # Initialise DataFrame with string -> condition mapping
        df = pd.DataFrame({'string': self.string_to_condition_cui.keys(),
                           'condition_cui': self.string_to_condition_cui.values()})
        
        # Add in unknown strings
        df_unknown = pd.DataFrame({'string': self.unknown_strings, 'condition_cui': -1})
        df = pd.concat([df, df_unknown], sort=False)

        # Add in condition names
        df_condition_names = (self.known_conditions
                         .set_index('cui')[['name']]
                         .rename(columns={'name': 'condition_name'})
                        )
        df = df.join(df_condition_names, on='condition_cui', how='left')
        df = df.fillna('Unknown')

        # Add in grouping CUIs
        df_grouping_cuis = pd.DataFrame({'grouping_cui': self.condition_cui_to_grouping_cui.values()}, 
                    index=list(self.condition_cui_to_grouping_cui.keys()))
        df = df.join(df_grouping_cuis, on='condition_cui', how='left')
        df = df.fillna(-1)
        df['grouping_cui'] = df['grouping_cui'].astype(int)

        # Add in grouping names
        df_grouping_names = (self.known_groupings
                        .set_index('cui')[['name']]
                        .rename(columns={'name': 'grouping_name'})
                        )
        df = df.join(df_grouping_names, on='grouping_cui', how='left')
        df = df.fillna('Unknown')

        return df.set_index('string')


def _load_data(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = file.read().splitlines()
    return data
