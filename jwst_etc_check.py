"""Tool for handling delivery of JWST ETC files
Authors
-------
    - Varun Bajaj, Brian Brooks August 2017
Use
---
    This script is intended to be run from the comand line:
    ::
        python jwst_etc_check.py [-d <destination> -f <files> -i <instrument> -u -m]
    -d <destination> - Path to current Pandeia directory (where files will be placed)
    -f <files> - Files to check/update/move, accepts wildcards
    -i <instrument> - Instrument the files are used for
    -u - Switch to update the JSON file with the new filenames
    -m - Switch to move files into the Pandeia directory.
"""

import argparse
import datetime
import glob
import json
import os
import shlex
import shutil
import subprocess
import time
import warnings

from astropy.io import fits
from collections import OrderedDict
from move_files import move_results

# ----------------------------------------------------------------------------------------------------------------------


def parse_args():
    """ Parse command line arguments.

    Parameters:
        Nothing

    Returns:
        arguments: argparse.Namespace object
            An object containing all of the added arguments.

    Outputs:
        Nothing
    """

    files_help = 'Name of files or path to files.  Wildcards accepted Default is *.fits + *.json'
    instrument_help = 'Instrument these files are for.  Default: auto detect from json filename.'
    destination_help = 'Path to directory structure of pandeia directories. Default is /ifs/redcat/jwst/srefpipe/ETC/pandeia/pandeia_jwst_release_1.1dev UPDATE THIS AS NEW RELEASES ARE MADE'
    update_json_help = 'Actually update the JSON file?  Default: False'
    move_help = 'Actually replace the files in destination?  Default: False'

    parser = argparse.ArgumentParser()

    parser.add_argument('-d',
                        type=str,
                        help=destination_help,
                        action='store',
                        required=False,
                        default='/ifs/redcat/jwst/srefpipe/ETC/pandeia/pandeia_jwst_release_1.1dev')
    parser.add_argument('-f',
                        type=str,
                        help=files_help,
                        action='store',
                        required=False,
                        default=None)
    parser.add_argument('-i',
                        type=str,
                        help=instrument_help,
                        action='store',
                        required=False,
                        default=None)
    parser.add_argument('-m',
                        help=move_help,
                        action='store_true',
                        required=False)
    parser.add_argument('-u',
                        help=update_json_help,
                        action='store_true',
                        required=False)

    arguments = parser.parse_args()
    return arguments
# ----------------------------------------------------------------------------------------------------------------------

def add_timestamps(files, local_time, instrument):
    new_filenames = []
    l = open('rename.log', 'w')  # log file containing renaming history
    timestamp = time.strftime('%Y%m%d%H%M%S', local_time.timetuple())
    for f in files:
        name, extension = os.path.splitext(f)
        last = name.split('_')[-1]
        if all(c.isdigit() for c in last) and len(last) == 14:
            name = '_'.join(name.split('_')[:-1]) # To check if a timestamp is already there
        new_name = '{}_{}{}'.format(name,timestamp,extension)
        if 'json' in extension:
            if '_shutters' not in name and '_cr' not in name: # check to make sure its a configuration file
                new_name = 'jwst_{}_configuration_{}.json'.format(instrument,timestamp)
        os.rename(f,new_name)
        new_filenames.append(new_name)
        print('Renaming {} to {}'.format(f, new_name))
        l.write('{} ----> {}\n'.format(f, new_name))
    l.close()
    return new_filenames

# ----------------------------------------------------------------------------------------------------------------------

def check_single_section(json_block, section_name):
    """ Check a block of json (i.e. data['meta'] or data['paths']['meta']) for
        all required subsections and lengths of subsections
    """
    passed = True
    second_keys = ['author','litref','history','pedigree']
    third_key_lists = []
    for sk in second_keys:
        if sk not in json_block.keys():
            '{} NOT FOUND under {}'.format(sk, section_name)
            passed = False
        s_data = json_block[sk]
        # Only check subsections of meta for description entry
        if section_name == 'meta' and 'description' not in s_data.keys():
            'Description NOT FOUND under {}/{}'.format(section_name,sk)
            passed = False
        third_key_lists.append(s_data.keys())

    lengths = [len(keys) for keys in third_key_lists]
    if len(set(lengths)) != 1: # Check to see all subsections have same number of entries
        'Sections {}/{} have differing numbers of entries: {}'.format(section_name,second_keys,lengths)
        passed = False
    for i, keys in enumerate(third_key_lists):
        if third_key_lists[0] != keys:
            print('{}/{} ({} entries) does not have matching entries compared to {}'.format(section_name,second_keys[i],lengths[i],second_keys[0]))
            passed = False
    return passed


def check_json_sections(json_files, instrument):
    """ Check a json file for required top level sections, wrap subsection
        checking.
    """
    template = '/user/mcmaster/CRDS/for_matt/templates/{}.json'.format(instrument)
    template_data = json.load(open(template))
    template_version = template_data['-delivered-for-version-']
    for f in json_files:
        statuses = []
        print('Checking {}'.format(f))
        with open(f) as json_data:
            data = json.load(json_data)
            version = data['-delivered-for-version-']
            if version != template_version:
                print('WARNING: Version of file submitted ({}) does not match template version ({})'.format(version, template_version))
                statuses.append(False)
            first_keys = ['meta', 'paths']
            for fk in first_keys:
                section_name = fk
                assert fk in data.keys(), '{} NOT FOUND'.format(fk)
                json_block = data[fk]
                if fk == 'paths':
                    json_block = json_block['meta']
                    section_name = '{}/meta'.format(fk)
                status = check_single_section(json_block, section_name)
                statuses.append(status)
        if all(statuses):
            print('{} PASSED JSON CHECK'.format(f))
        else:
            print('{} FAILED JSON CHECK'.format(f))
        print('----------------------------------------------------------------\n')

def check_fits_files(fits_files):
    ''' This checks the fits files for required keywords.  It works, but this
        has been harvested from old code and should really be updated to be
        more pythonic and have real handling of errors, currently just prints,
        but fits files are likely lower priority/issue prone.
    '''
    out_file = open('fits_header_out.txt', 'w')
    keys = ['TELESCOP','SYSTEM','INSTRUME','FILETYPE','REFTYPE','COMPNAME','PEDIGREE','LITREF','DESCRIP','AUTHOR','HISTORY']
    print('keys are :', keys)
    for f in fits_files:
        hdu = fits.open(f)
        if len(keys) > 0:
            result = '['
            resultk = '\n File: '+f+' KEYWORD in EXT [0]:\n ['
            for i in xrange(len(keys)):
                matches = [x for x in hdu[0].header if x == keys[i]]
                if len(matches) > 0:
                  read_key=hdu[0].header[keys[i]]
                  resultk += keys[i]+', '
                  result +=  '\''+str(read_key)+'\','
                  if  keys[i] =='TELESCOP':
                      if read_key != 'JWST':
                        print(read_key, 'IS NOT A VALID ENTRY for:', keys[i])

                  if  keys[i] =='SYSTEM':
                      if read_key != 'MODELING':
                        print(read_key, 'IS NOT A VALID ENTRY for:', keys[i])


                  if  keys[i] =='INSTRUME':
                      if read_key not in ['NIRCAM', 'MIRI','NIRSPEC', 'NIRISS', 'TELESCOPE']:
                        print(read_key, 'IS NOT A VALID ENTRY for:', keys[i])

                  if  keys[i] =='FILETYPE':
                      if read_key not in ['THROUGHPUT_TABLE', 'IMAGE', 'CORR_MATRIX', 'DATA_TABLE']:
                        print(read_key, 'IS NOT A VALID ENTRY for:', keys[i])

                  if  keys[i] =='PEDIGREE':
                      if read_key not in  ['INFLIGHT YYYY-MM-DD YYYY-MM-DD', 'GROUND','PLACEHOLDER', 'DUMMY']:
                        print(read_key, 'IS NOT A VALID ENTRY for:', keys[i])

                else:
                    print('Keyword ',keys[i],' not found')
                    result += '============Keyword '+keys[i]+' not found\n'
            resultk += ']\n'
            result += ']\n'
            resultall = resultk + result
            print(resultall)
            print('----------------------------------------------------------------')
            out_file.write(resultall)
    out_file.close()

# ----------------------------------------------------------------------------------------------------------------------

def find_old_file(filename, target_dir):
    ''' This function uses the filename to determine what the corresponding
        old file is.  THIS BREAKS IF NEW FILES NOT IN THE PANDEIA DESTINATION
        DIRECTORY.  This can be an enhancement later
    '''
    ext = os.path.splitext(filename)
    filetype = '_'.join(filename.split('_')[:-1])
    matched = glob.glob('{}{}*'.format(target_dir,filetype))
    if len(matched) != 1:
        print('WARNING Too many or no files matched for {}'.format(filename))
        return ''
    old_file = matched[0]
    full_path = os.path.abspath(old_file)
    return full_path

def move_to_pandeia(files, instrument, destination):
    ''' This function figures out which subdirectory each of the delivered files
        goes into, figures out the corresponding OLD file, deletes it (if one exists), 
        and moves the new one into its correct place.
    '''
    # Take care when editing this dictionary, since the files are matched to their directory
    # based on the presence the dictionaries keys in the filenames.  For instance, 'trans'
    # would get matched to filters, but would return a positive match for a file containing
    # the name 'trans_modmean'

    # This dictionary maps the part of the filename to the directory
    ext_to_dir = OrderedDict([
                ('_disp', '/dispersion/'),
                ('_blaze', '/blaze/'),
                ('_optical', '/optical/'),
                ('_dich', '/optical/'),
                ('_ge_ar1_trans', '/optical/'),
                ('_ge_ar2_trans', '/optical/'),
                ('_trans_modmean', '/optical/'),
                ('_substrate_trans', '/optical/'),
                ('_trans', '/filters/'),
                ('_psf', '/psfs/'),
                ('_r.', '/resolving_power/'),
                ('_ldwave', '/wavecal/'),
                ('_specef', '/blaze/'),
                ('_ipc', '/detector/'),
                ('_qe', '/qe/'),
                ('_throughput', '/optical/'),
                ('_telescope', '/'),
                ('_configuration', '/'),
                ('_shutters', '/'),
                ('_internaloptics', '/optical/'),
                ('_lyot', '/optical/'),
                ('_substrate', '/optical/'),
                ('_dbs_', '/optical/'),
                ('_trace', '/wavepix/'),
                ('_wl', '/optical/')])

    new_to_old = {}
    l = open('replacement.log', 'w')
    l.write('#REPLACEMENT ONLY PERFORMED IF -m FLAG IS GIVEN\n')
    l.write('#However, this log is created regardless.\n')
    for f in files:
        for ext in ext_to_dir.keys():
            if ext in f:
                subdir = ext_to_dir[ext]
                break
        final_dir = '{}/{}/{}'.format(destination,instrument,subdir)
        old_file = find_old_file(f,final_dir)
        new_to_old[f] = old_file
        print('Replacing {} with {}'.format(old_file,f))
        l.write('Replacing {} with {} in {}\n'.format(old_file,f,final_dir))
        if options.m: # Explicit control for replacing the files
            shutil.copy(f,final_dir)
            if old_file:
                os.remove(old_file)
    l.close()


def update_json_file(config_file, files, destination, instrument):
    ''' This updates the new JSON file (the paths sections) by first getting
        the paths from the previous corresponding JSON file, and the accordingly
        Updating the paths for each new fits file in the delivery directory.
        This was a bear of a function.
    '''
    old_config = glob.glob('{}/{}/*configuration*.json'.format(destination,instrument))[0]
    print('OLD CONFIG: {}'.format(old_config))
    old_data = json.loads(open(old_config, 'r').read(),object_pairs_hook=OrderedDict)

    new_data = json.loads(open(config_file, 'r').read(),object_pairs_hook=OrderedDict)

    # first update with old paths:
    for key in old_data['paths'].keys():
        if 'meta' in key:
            continue
        new_data['paths'][key] = old_data['paths'][key]
        print('First setting {} to old value: {}'.format(key, old_data['paths'][key]))


    for f in files:
        if '.fits' not in f: continue
        print('Attempting to update json file with {}'.format(f))
        filetype = '_'.join(f.split('_')[:-1])
        for key in new_data['paths'].keys():
            if 'meta' in key:
                continue
            elif filetype in new_data['paths'][key]:
                prefix = os.path.split(new_data['paths'][key])[0]
                new_entry = '{}/{}'.format(prefix, f)
                print('Changing {} to {}'.format(new_data['paths'][key], new_entry))
                new_data['paths'][key] = new_entry
        print('--------------------------------------')

    if options.u: # only write updated JSON file if supplied in commandline flag:
        with open(config_file, 'w') as tmp:
            json.dump(new_data, tmp, indent=4)

# ----------------------------------------------------------------------------------------------------------------------

def verify_json_files(json_files):
    """ Check files conform to fits standard and update verification keyword
        NOTE: This function is loosely derived from
        /grp/redcat/SCRIPTS/verification-tools/Is_Valid_JSON/is_valid_json.py,
        so the only checks being performed come from that script.
    """
    for f in json_files:

        print('Verifying {}'.format(f))
        fname = os.path.abspath(f)
        try:
            tmp = open(fname, 'r')
            buf = tmp.read()
            tmp.close()
            obj = json.loads(buf)
            key_str = str(' '.join(obj.keys()))
            print('{} appears valid with keys: {}'.format(f, key_str))
        except Exception as e:
           print('Trouble with file: {}'.format(fname))
           print(e)
           raise e
        print('----------------------------------------------------------------\n')
# ----------------------------------------------------------------------------------------------------------------------


def verify_fits_files(fits_files):
    """ Check files conform to fits standard and update verification keyword
    """
    for f in fits_files:

        print('Verifying {}'.format(f))
        with warnings.catch_warnings(record=True) as w:  # Workaround for astropy verify issues
            warnings.simplefilter("always")  # Catch all warnings
            hdu = fits.open(f, mode='update')  # Catches the 'fixable violations'
            hdu.verify('warn')  # Catches the unfixable ones

            if len(w) == 0:  # Check number of warnings, if =0 then file is good
                print(f, 'PASSED VERIFICATION')
                hdu[0].header['VERIFIED'] = 'PASSED'
            else:
                print(f, 'FAILED VERIFICATION')
                hdu[0].header['VERIFIED'] = 'FAILED'
                for warn in w:
                    print(warn.message)

            hdu.close(output_verify='ignore')

        print('----------------------------------------------------------------')

# ----------------------------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    options = parse_args()
    if options.f:
        files = glob.glob(options.f)
    else:
        files = glob.glob('*.fits') + glob.glob('*.json')

    assert len(files) != 0, 'No files matched'

    # Split files up by extension
    fits_files = [f for f in files if '.fits' in f]
    json_files = [f for f in files if '.json' in f]

    instrument = options.i
    instruments = ['miri', 'nirspec', 'nircam', 'niriss', 'telescope']
    if not instrument:
        for inst in instruments:
            if inst in json_files[0]:
                instrument = inst
                break
    assert instrument in instruments, 'Cannot match instrument to one of: {}'.format(' '.join(instruments))

    # Verify both file types
    print('----------------------------------------------------------------')
    print('--------------------------VERIFYING-----------------------------')
    print('----------------------------------------------------------------')
    verify_fits_files(fits_files)
    verify_json_files(json_files)

    # Check the header keywords
    print('----------------------------------------------------------------')
    print('--------------------------CHECK VALUES--------------------------')
    print('----------------------------------------------------------------')
    check_fits_files(fits_files)
    check_json_sections(json_files, instrument)

    # !!Check to make sure all files passed, otherwise do not allow moving/updating
    print('----------------------------------------------------------------')
    print('--------------------------RENAMING------------------------------')
    print('----------------------------------------------------------------')
    local_time = datetime.datetime.now()
    files = add_timestamps(files, local_time, instrument)


    print('----------------------------------------------------------------')
    print('--------------------------UPDATING JSON-------------------------')
    print('----------------------------------------------------------------')
    config_file = ''
    for f in files:
        if '.json' in f and 'configuration' in f:
            config_file = f
    assert config_file != '', 'NO CONFIGURATION FILE'

    destination = options.d
    update_json_file(config_file, files, destination, instrument)

    print('----------------------------------------------------------------')
    print('--------------------------MOVING FILES--------------------------')
    print('----------------------------------------------------------------')
    move_to_pandeia(files, instrument, destination)
    if options.m:
        obs_instruments = {'hst': ['STIS', 'COS', 'ACS', 'WFC3', 'NICMOS', 'WFPC2'],
               'jwst': ['FGS', 'MIRI', 'NIRCAM', 'NIRISS', 'NIRSPEC', 'TELESCOPE']}
        delivery_directory = os.getcwd()
        move_results(delivery_directory, obs_instruments)
