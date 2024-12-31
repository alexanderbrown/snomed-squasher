# SNOMED SQUASHER

## Introduction
This package is designed to amlgamate SNOMED diagnosis / finding codes in to higher-level groupings. 
This can be used for:
* Analysis / Machine learning - reducing the number of classes
* Annonymising data - removing rare / idiosyncratic diagnoses

Definitions are obtained from a SNOMED directory. This needs to be downloaded separately from [NHS TRUD](https://isd.digital.nhs.uk/trud/)

Optionally, a `CDR Directory`, a subset of the full SNOMED data, can be used for definitions. This contains only the files needed for this package.

## CDR directory
A `CDR` is a directory containing a subset of SNOMED CT files. These are only the *Concept*, *Definition*, and *Relationship* files. These files are the minimal set needed to define the ontology tree containing Findings/Diagnoses. 

`snomed-squasher` uses only the `Snapshot` data from SNOMED, as the full history of SNOMED definitions is unnecessary. 

A `CDR Directory` is created by default in the setup script. However, you can extract the whole zip file, or just use an existing definitions directory. 

## Installation
1. Clone this repo
1. Setup a `venv`, `conda` instance, or similar.
1. `pip install -r requirements.txt`
1. Obtain a zipfile of the relevant SNOMED CT Ontology: `SNOMED CT UK Clinical Edition, RF2: Full, Snapshot & Delta`, available from [NHS TRUD](https://isd.digital.nhs.uk/trud/)
1. Run `setup.py`, specifying the location of the zipfile, and the destination directory to copy the CDR files to. 
    - If you already have a CDR built, or a SNOMED CT directory, you can skip the setup script. Instead, just set the `SNOMED_DEFINITIONS` variable in a `.env` file to your existing CDR directory.
    - You also don't need to run setup; instead the path to the Definitions can be manually specified when creating a `Snomed` object.  

## Usage Notes
* Concept name resolution is currently implemented as being case insensitive. This may cause issues in certain cases, e.g. blood group haplotypes. (see [Snomed Guidance on Case Significance](https://confluence.ihtsdotools.org/display/DOCEG/Case+Significance)). It is not a problem for my use case, so I haven't fixed it. 

## Example Usage

### Import code and create `snomed` object
```python
from snomed import Snomed
snomed = Snomed()
```

### Find a cui, by name
Find the `cui` for a concept, from its name
```python
snomed.find_cui('Asthma')
```
> 195967001

`find_cui` will try to find a single exact match. If it cannot, it will return `None`:
```python
snomed.find_cui('Asth')
```
> \<None\>

If you need partial matches, use `find_concepts`, which returns a `DataFrame` of zero or more matches. This will still *try* to find a single exact match, but will return multiple partial matches if it cannot find a perfect match. 

### Get concepts 
Find all concepts with a given `cui`:
```python
snomed.get_concepts(195967001)
```


> |cui	|name	|name_status	|release	|description_type_ids |
> |-------|-------|---------------|-----------|---------------------|
> |195967001	|Airway hyperreactivity             |A|	InternationalRF2	||
>    |195967001	|Asthmatic 	                        |A|	InternationalRF2	||
>	|195967001	|Bronchial asthma	                |A|	InternationalRF2	||
>	|195967001	|Bronchial hyperreactivity	        |A|	InternationalRF2	||
>	|195967001	|BHR - Bronchial hyperreactivity	|A|	InternationalRF2	||
>	|195967001	|Bronchial hyperresponsiveness	    |A|	InternationalRF2	||
>	|195967001	|Bronchial hypersensitivity	        |A|	InternationalRF2	||
>	|195967001	|Asthma                             |A|	InternationalRF2	||
>	|195967001	|Asthma (disorder)	                |P|	InternationalRF2	|disorder|
>	|195967001	|Hyperreactive airway disease	    |A|	InternationalRF2	||

Find the single Primary concept associated with a `cui`:
```python
snomed.get_primary_concept(195967001)
```
> |cui	|name	|name_status	|release	|description_type_ids |
> |-------|-------|---------------|-----------|---------------------|
>	|195967001	|Asthma (disorder)	                |P|	InternationalRF2	|disorder|


### Get children of a concept
Children are the first-order descendents of a concept
```python
snomed.get_children(195967001) 
snomed.get_children_by_name('asthma') # alternative, using name rather than CUI
```
> |cui	|name	|name_status	|release	|description_type_ids |
> |-------|-------|---------------|-----------|---------------------|
> |31387002|	Exercise-induced asthma (disorder)	            |P|	InternationalRF2	|disorder|
> |55570000|	Asthma without status asthmaticus (disorder)	|P|	InternationalRF2	|disorder|
> |57607007|	Occupational asthma (disorder)	                |P|	InternationalRF2	|disorder|
> |...     |    ...                                            |...| ...                |...     |                    

### Find parents of a concept
Parents are the first-order ancestors of a concept
```python
snomed.get_parents(195967001) 
snomed.get_parents_by_name('asthma') # alternative, using name rather than CUI 
```
> |cui	|name	|name_status	|release	|description_type_ids |
> |-------|-------|---------------|-----------|---------------------|
> |114155	|50043002|	Disorder of respiratory system (disorder)|	P	|InternationalRF2|	|disorder|

### Get ancestors of a concept
You can also get *all* ancestors of a concept. This can be a bit slow (on the order of tens-hundreds of ms per query), so may not be suitable for using at scale. 
```python
snomed.get_ancestors(195967001) 
snomed.get_ancestors_by_name('asthma') # alternative, using name rather than CUI
```
> |cui	|name	|name_status	|release	|description_type_ids | level |
> |-------|-------|---------------|-----------|---------------------|-----|
>|	50043002	|Disorder of respiratory system (disorder)	|P|	InternationalRF2|	disorder	    |1|
>|	106048009	|Respiratory finding (finding)	            |P|	InternationalRF2|	finding	        |2|
>|	362965005	|Disorder of body system (disorder)	        |P|	InternationalRF2|	disorder	    |2|
>|	64572001	|Disease (disorder)     	                |P|	InternationalRF2|	disorder	    |3|
>|	404684003	|Clinical finding (finding) 	            |P|	InternationalRF2|	finding	        |3|
>|	138875005	|SNOMED CT Concept (SNOMED RT+CTV3)	        |P|	InternationalRF2|	SNOMED RT+CTV3	|4|

Note that an additional column, `level` is added. This is the *minimum* number of steps required to reach a given ancestor from the input concept (`cui` or name). There may be more than one path up through the ontology, only the smallest path is returned. 

Note also that ancestors with level 1 are equivalent to the output of `get_parents`