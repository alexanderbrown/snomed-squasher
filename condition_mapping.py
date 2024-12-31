'''Module to manage the mapping of freetext conditions to SNOMED codes'''
import glob
import json
import os

from IPython.display import display, HTML
import pandas as pd

from snomed import Snomed

class ConditionMapper():
    '''Class to manage the mapping of freetext conditions to SNOMED codes'''
    def __init__(self, input_file: str, file_number: int = 0):
        '''Create a new ConditionMapper object
        
        Args:
            input_file: The path to the file containing the list of conditions to map
            file_number: The number of the saved mapping file to load (optional)
                            If 0, the input file is loaded and no mapping is loaded
                            If -1, the most recent saved mapping file is loaded
                            Otherwise, the mapping file with the specified number is loaded
        '''
        self.input_file = input_file
        self.output_location = os.path.splitext(self.input_file)[0]

        if file_number == 0:
            self.unknown_conditions = _load_data(self.input_file)
            self.known_conditions = {}
        elif file_number == -1:
            self.known_conditions, self.unknown_conditions = self.load_most_recent_mapping_file()
        else:
            self.known_conditions, self.unknown_conditions = self.load_from_mapping_file(file_number)

    def __repr__(self):
        return f'ConditionMapper(input_file={self.input_file})'
    
    def __str__(self):
        return f'''ConditionMapper for {self.input_file} with:
        \t{len(self.unknown_conditions)} unknown conditions,
        \tand {len(self.known_conditions)} known conditions'''

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
            json.dump({'known': self.known_conditions, 'unknown': self.unknown_conditions}, file, indent=4)
        print('Done')

    def load_from_mapping_file(self, n: int):
        '''Load a mapping from a specified saved file'''
        mapping_file = self.mapping_file_path(n)
        print(f'Loading mapping file {mapping_file}... ', end='')
        with open(mapping_file, 'r', encoding='utf-8') as file:
            mapping = json.load(file)
        print('Done')
        return mapping['known'], mapping['unknown']
    
    def load_most_recent_mapping_file(self):
        '''Load a mapping from the most recent saved file'''
        last_mapping_file_number = self.most_recent_mapping_file
        if last_mapping_file_number:
            return self.load_from_mapping_file(last_mapping_file_number)
        return None, None
        
    def clear_mapping_files(self):
        '''Clear all saved mapping files'''
        response = input('Are you sure you want to clear all mapping files? (y/N) ')
        if response.lower() == 'y':
            existing_output_files = glob.glob(f'{self.output_location}_mapped_*.json')
            for f in existing_output_files:
                os.remove(f)
            print(f'{len(existing_output_files)} mapping files removed')


    def automatically_map_conditions(self, snomed: Snomed):
        '''Automatically maps conditions to SNOMED-CT
        
        If an exact match is found, it is added to the known_conditions dictionary'''

        if len(self.unknown_conditions) == 0:
            print('All conditions already mapped to SNOMED-CT')
            return

        print('Automatically mapping conditions to SNOMED-CT...')
        for condition_name in self.unknown_conditions:
            cui = snomed.find_cui(condition_name)
            if cui:
                self.known_conditions[condition_name] = int(cui)
                concept = snomed.get_primary_concept(cui)
                print(f'\t{condition_name} mapped to {concept['name']}')

        self.unknown_conditions = [condition for condition in self.unknown_conditions 
                                   if condition not in self.known_conditions]
        if self.unknown_conditions:
            print(len(self.known_conditions), 'conditions mapped to SNOMED-CT.')
            print(len(self.unknown_conditions), 'conditions not mapped to SNOMED-CT:')
            for condition in self.unknown_conditions:
                print(f'\t{condition}')
        else:
            print(f'All {len(self.known_conditions)} conditions mapped to SNOMED-CT')

    def get_user_input_cuis(self, snomed: Snomed):
        '''Gets manually entered CUIs for conditions. Useful after automatic mapping has been attempted.'''
        def get_user_input_cui(condition_name: str, snomed: Snomed):
            print(f'\nSearching for partial matches for {condition_name}...')
            matches = snomed.find_concepts(condition_name)
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
        
        if len(self.unknown_conditions) == 0:
            print('All conditions already mapped to SNOMED-CT')
            return

        cuis = {}
        for condition_name in self.unknown_conditions:
            cuis[condition_name] = get_user_input_cui(condition_name, snomed)

        display(f'Manually mapped {len([v for v in cuis.values() if v])} conditions to SNOMED-CT:', clear=True)
        for raw_name, manual_cui in cuis.items():
            if manual_cui:
                try:
                    cui = int(manual_cui)
                except ValueError:
                    print(f'\t{manual_cui} is not a valid CUI. Skipping {raw_name}')
                    continue

                concept = snomed.get_primary_concept(cui)
                print(f'\t{raw_name} mapped to {concept['name']} ({cui})')
                self.unknown_conditions.remove(raw_name)
                self.known_conditions[raw_name] = int(cui)

        print(f'{len([v for v in cuis.values() if not v])} conditions skipped:')
        for raw_name,manual_cui in cuis.items():
            if not manual_cui:
                print(f'\t{raw_name}')
    
def _load_data(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = file.read().splitlines()
    return data
