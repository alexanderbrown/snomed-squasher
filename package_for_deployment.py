'''This script packages the code in to a zip file, 
for deployment in to a Trusted Research Environment (TRE) or similar, 
where git / external package installation is not readily available.
'''
import zipfile

import git

repo = git.Repo('.')
all_files = repo.git.execute(['git', 'ls-files'])
files_to_exclude = ['.gitignore', 'package_for_deployment.py', '.pylintrc', 'README.md', 'LICENSE', 'requirements.txt']

files_to_package = [f for f in all_files.split('\n') if f not in files_to_exclude]

# Use current git tag as zip file name
tag = repo.tags[-1]
output_filename = f'snomed_squasher_{tag.name.replace('.', '_')}.zip'

with zipfile.ZipFile(output_filename, 'w') as z:
    for f in files_to_package:
        z.write(f)
