"""Sets up snomed-squasher.

This scipt sets up the snomed-squasher by:
 1. Extracting the SNOMED definitions and copying relevant files to the specified directory.
 2. Setting the SNOMED_DEFINITIONS environment variable to the destination directory.

If you already have a SNOMED Definitions directory, you can simply set the 
 SNOMED_DEFINITIONS environment variable to the path of the directory.
"""
import argparse
import os
import shutil
import tempfile
import zipfile

import dotenv


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
    """Extracts a SNOMED zip file, keeping only files relevant to finding/disease ontology.

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
            files_to_keep = get_relevant_files(temp_dir)
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for file in files:
                    fullfile = os.path.join(root, file)
                    if fullfile not in files_to_keep:
                        os.remove(fullfile)
                for d in dirs:
                    full_dir = os.path.join(root, d)
                    if not os.listdir(full_dir):
                        os.rmdir(full_dir)

            if destination:
                shutil.copytree(temp_dir, destination)
               
            return [os.path.split(f)[1] for f in files_to_keep]

def extract_all_files(source: str, destination: str | None = None) -> list[str]:
    """Extracts all files from a SNOMED zip file.

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
            if destination:
                shutil.copytree(temp_dir, destination)
            files = [file for _, _, files in os.walk(temp_dir) for file in files]
            return files

def main():
    """Main setup script"""
    parser = argparse.ArgumentParser(description='''Extract and copy relevant SNOMED CT files.
                            If no destination is specified, will use zip file name as destination.

                            By default, only the relevant files for finding/disease ontology are copied [to create a CDR directory].
                            Use the --full-snomed flag to extract all files from the SNOMED archive.

                            Use the --set-env flag to set the SNOMED_DEFINITIONS environment variable to the destination directory.         
                                     
                            ''')
    parser.add_argument('source', type=str, 
                        help='The path to the zip file to extract')
    parser.add_argument('destination', type=str, nargs='?', 
                        help='The path to the directory to copy (only the necessary) SNOMED files to (optional)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Do not copy files, only print the relevant files for inspection')
    parser.add_argument('--full-snomed', action='store_true',
                        help='Extract all files from the SNOMED archive, not just the relevant ones [CDR]')
    parser.add_argument('--set-env', action='store_true', 
                        help='Set the SNOMED_DEFINITIONS environment variable to the destination directory')
    args = parser.parse_args()

    if args.dry_run:
        destination = None
    else:
        destination = args.destination if args.destination else os.path.splitext(args.source)[0]

    if args.full_snomed:
        files_to_copy = extract_all_files(args.source, destination)
    else:
        files_to_copy = extract_and_copy_relevant_files(args.source, destination)
    
    if args.dry_run:
        print("Dry run: Files not copied.")
        print("Files that would be copied: ")
        for f in files_to_copy:
            print(f'\t{f}')
        print(f"Would be copied to: {args.destination if args.destination else os.path.splitext(args.source)[0]}")
        return
    
    print(f"Files copied to {destination}")
    if args.set_env:
        dotenv.load_dotenv()
        dotenv.set_key('.env', 'SNOMED_DEFINITIONS', destination)
    
    print('Setup complete.')
if __name__ == '__main__':
    main()
