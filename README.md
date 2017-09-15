# ReDCaT #
*Repository for tools used by the STScI ReDCaT Team*

---
 
## Code ##
*The following tools are intended to be run from the command line and with Python 3.5 or higher*
 
#### check_references.py ####

**Purpose:** Checks references files intended for delivery to the CRDS system for compliance with CRDS standards and requirements\
**Use:** `python check_references.py [<jwst>/<hst> -f <files> -c <context path>]`\
**Options/Arguments:**
> ###### Options
> 'o': manually specify the observatory for the files. Either 'jwst' or 'hst'
> ###### Arguments
> '-f': manually specify the names or paths to target files\
> '-c': name of the context to be used for certification

#### deliver_files.py ####

**Purpose:** Delivers reference files to CRDS by using crds.submit. Automatically configure users' environments to run crds.submit for JWST or HST deliveries\
**Use:** `python deliver_files.py`\
**Options/Arguments:**
> N/a

 #### jwst_etc_check.py ####
 
 **Purpose:** Verifies JWST ETC reference files are compliant with standards, adds a timestamp to the name of the files, and delivers the files to the JWST ETC area\
 **Use:** `python jwst_etc_check.py [ -d <destination> -f <files> -i <instrument> -u -m]`\
 **Options/Arguments:**
 > ###### Arguments
 > '-d': path to the current Pandeia directory (delivery location)\
 > '-f': files to be checked, updated, and moved. Wildcards are accepted\
 > '-i': instrument that the files are for
 > '-u': switch for updating JSON file names with a timestamp and adding the updated path to the file. JSON files will not be updated without this argument
 > '-m': switch for moving the files into the Paindeia directory. Files will not be moved without this argument
 
 #### move_files.py ####
 
 **Purpose:** Move the results of certification, delivery and renaming (for HST) to the record keeping area, `/ifs/redcat/..`. For HST, reference files are moved to their cache locations:
 * COS: lref
 * STIS: oref
 * ACS: jref
 * WFC3: iref
 * WFPC2: uref
 * NICMOS: nref
 **Use:** `python move_files.py`\
 **Options/Arguments:**
 > N/A
 
 #### rename_files.py ####
 
 **Purpose:** Rename HST reference files to CRDS standard using crds.uniqname\
 **Use:** `python rename_files.py`\
 **Options/Arguments:**
 >N/A
 
 #### submit_delivery.py ####
 
 **Purpose:** For use by instrument teams for submitting a delivery request to the ReDCaT Team. Consructs the appropriate staging area under `/grp/redcat/staging` depending on the type of delivery and which instrument the files are supporting, updaes the delivery form with the location and names of the files to be delivered, constructs and sends the request email to ReDCaT, and moves the files to the staging area\
 **User:**`python submit_delivery.py` The user will need to provide answers to interactive questions\
 **Options/Arguments:**
 >N/A
 
 ---
 
 ## Forms ##
 
 #### delivery_form.txt ####
 
 **Description:** Delivery request form in plain-text. This file is required for instrument teams to submit a delivery request to the ReDCaT Team. Provides important information about the reference files being delivered which is used in the delivery tools
 
 
 
