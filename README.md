# SNOMED SQUASHER

## Introduction
This package is designed to amlgamate SNOMED diagnosis / finding codes in to higher-level groupings. 
This can be used for:
* Analysis / Machine learning - reducing the number of classes
* Annonymising data - removing rare / idiosyncratic diagnoses

## CDR directory
A `CDR` is a directory containing a subset of SNOMED CT files. These are only the *Concept*, *Definition*, and *Relationship* files. These files are the minimal set needed to define the ontology tree containing Findings/Diagnoses. 

`snomed-squasher` uses only the `Snapshot` data from SNOMED, as the full history of SNOMED definitions is unnecessary. 

## Installation
1. Obtain a zipfile of the relevant SNOMED CT Ontology: `SNOMED CT UK Clinical Edition, RF2: Full, Snapshot & Delta`, available from [NHS TRUD](https://isd.digital.nhs.uk/trud/)
1. Run `setup.py`, specifying the location of the zipfile, and the destination directory to copy the CDR files to. 
    - If you already have a CDR built, you can skip the setup script. Instead, just set the `EXISTING_SNOMED_CDR` variable in a `.env` file to your existing CDR directory. 