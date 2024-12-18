"""Test the extract module"""
import os

import dotenv

import extract

dotenv.load_dotenv()


def test_remove_date_from_filename():
    """Test the remove_date_from_filename function."""
    assert extract.remove_date_from_filename('sct2_Relationship_UKEDSnapshot_GB_20241120.txt') == \
        'sct2_Relationship_UKEDSnapshot_GB_.txt'
    assert extract.remove_date_from_filename('sct2_Relationship_UKEDSnapshot_GB_202410.txt') == \
        'sct2_Relationship_UKEDSnapshot_GB_.txt'

def test_extraction_matches():
    """Test that the extraction process matches the expected files.
        Will only work if available files are the same as the ones in the test
        Files are not included in the repository as they are too large and due to licensing restrictions
    """
    # Check files exist
    existing_snomed_cdr = os.environ.get('EXISTING_SNOMED_CDR') 
    new_zip_file='d:\\data\\SNOMED\\uk_sct2cl_39.2.0_20241120000001Z.zip'

    assert existing_snomed_cdr, 'EXISTING_SNOMED_CDR not set in .env file'
    assert new_zip_file, 'NEW_ZIP_FILE not specified in test'
    assert os.path.exists(existing_snomed_cdr), 'EXISTING_SNOMED_CDR does not exist'
    assert os.path.exists(new_zip_file), 'NEW_ZIP_FILE does not exist'
    
    # Known correct extraction
    existing_files = []
    for _, _, files in os.walk(existing_snomed_cdr):
        for file in files:
            existing_files.append(os.path.join(file))
    assert len(existing_files) == 12, 'Should have 12 files in the existing SNOMED CDR'

    existing_files_no_date = {extract.remove_date_from_filename(f)  for f in existing_files}
    assert len(existing_files_no_date) == 12, 'Should have 12 files in the existing SNOMED CDR'

    # Extract and compare
    files_to_copy = extract.extract_and_copy_relevant_files(new_zip_file)    
    assert len(files_to_copy) == 12, 'Should have 12 files in the new SNOMED CDR'

    files_to_copy_no_date = {extract.remove_date_from_filename(f) for f in files_to_copy}
    assert len(files_to_copy_no_date) == 12, 'Should have 12 files in the new SNOMED CDR'

    different_files = existing_files_no_date.symmetric_difference(files_to_copy_no_date)
    assert len(different_files) == 0, 'Extracted files should match existing files'

if __name__ == '__main__':
    test_extraction_matches()
    print('All tests passed')
