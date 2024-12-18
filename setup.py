"""Sets up snomed-squasher.

This scipt sets up the snomed-squasher by:
 1. Extracting the SNOMED definitions and copying relevant files to the specified directory.
 2. Setting the EXISTING_SNOMED_CDR environment variable to the destination directory.

If you already have a SNOMED CDR directory, you can simply set the 
 EXISTING_SNOMED_CDR environment variable to the path of the directory.
"""
import dotenv


from build_cdr import main as build_cdr_main

def main():
    """Main setup script"""
    dotenv.load_dotenv()

    destination = build_cdr_main()
    if destination:
        dotenv.set_key('.env', 'EXISTING_SNOMED_CDR', destination)
    else:
        print('Warning: No destination directory specified. Files not copied.')
        return 
    
    print('Setup complete.')
if __name__ == '__main__':
    main()
