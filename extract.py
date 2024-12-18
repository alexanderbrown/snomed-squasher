"""Extracts a SNOMED CT release archive into a directory structure for the purposes of consolidating findings/diseases.

Deletes all files not relevant to finding/disease ontology.
"""

import argparse
import os
import re
import shutil
import tempfile
import zipfile

def remove_date_from_filename(filename: str) -> str:
    """Removes the date from the filename of a SNOMED CT release archive."""
    date_format=re.compile(r'2024[0-9]*')
    return date_format.sub('', filename)

def get_relevant_files(directory: str) -> list[str]:
    """Search a directory for files relevant to finding/disease ontology.
    Only concept, description, and relationship files are relevant; 
     furthermore we only need snapshots, as full releases cover the entire history of SNOMED CT.    
    """

    relevant_file_types = ['_Concept_', '_Description_', '_Relationship_']
    relevant_release_type = 'Snapshot'

    relevant_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            for file_type in relevant_file_types:
                if file_type in file and relevant_release_type in file:
                    relevant_files.append(os.path.join(root, file))
    return relevant_files

def extract_and_copy_relevant_files(source: str, destination: str | None = None) -> list[str]:
    """Extracts the zip file, and copies relevant files to a specified directory.

        Args:
            source: The path to the zip file to extract
            destination: The path to the directory to copy the files to (optional)
        
        Returns:
            A list of the paths to the relevant files in the archive

     If no directory is specified, the files are not copied, but the paths are still returned.
    """
    with zipfile.ZipFile(source, 'r') as archive:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive.extractall(temp_dir)
            files_to_copy = get_relevant_files(temp_dir)

            if destination:
                if not os.path.exists(destination):
                    os.makedirs(destination)
                else:
                    if os.listdir(destination):
                        raise FileExistsError(
                            f"""Destination directory {destination} is not empty.
                            Please specify an empty or non-existent directory.""")
                for file in files_to_copy:
                    shutil.copy(file, destination)

            return [os.path.split(f)[1] for f in files_to_copy]

def main():
    """Main function for the script."""
    os.system('cls' if os.name == 'nt' else 'clear')
    parser = argparse.ArgumentParser(description='''Extract and copy relevant SNOMED CT files.
                            If no destination is specified, the files are not copied, but the paths are displayed.''')
    parser.add_argument('source', type=str, 
                        help='The path to the zip file to extract')
    parser.add_argument('destination', type=str, nargs='?', 
                        help='The path to the directory to copy (only the necessary) SNOMED files to (optional)')
    args = parser.parse_args()
    files_to_copy = extract_and_copy_relevant_files(args.source, args.destination)
    print("Relevant files: ")
    for f in files_to_copy:
        print(f'\t{f}')

    if args.destination:
        print(f"Files copied to {args.destination}")

    return args.destination if args.destination else None
    
if __name__ == '__main__':
    main()
