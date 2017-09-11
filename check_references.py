"""Tool for handling delivery of HST/JWST pipeline reference files
Authors
-------
    - Varun Bajaj, James White July 2017
Use
---
    This script is intended to be run from the comand line, and has optional arguments:
    ::
        python check_references.py
"""


import argparse
import glob
import os
import subprocess
import warnings
import shlex
from astropy.io import fits

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

    files_help = 'Name of files or path to files.  Wildcards accepted Default is *.fits'
    context_help = 'Context filename to use/check against.  Default is most recent (NOT ALWAYS OPERATIONAL).'
    observatory_help = 'Observatory: either \'hst\' or \'jwst\''

    parser = argparse.ArgumentParser()

    parser.add_argument('o',
                        type=str,
                        help=observatory_help,
                        action='store',
                        nargs='?',
                        default=None)

    parser.add_argument('-f',
                        type=str,
                        help=files_help,
                        action='store',
                        required=False,
                        default=None)

    parser.add_argument('-c',
                        type=str,
                        help=context_help,
                        action='store',
                        required=False,
                        default=None)

    arguments = parser.parse_args()
    return arguments

# ----------------------------------------------------------------------------------------------------------------------


def get_context(observatory, context):
    """ Get context file for certification
    """
    cont_dir = '/grp/crds/{}/mappings/{}'.format(observatory, observatory)

    if context is not None:
        # Check if context is in current directory/user specified path
        cont_path = context

        if not os.path.exists(cont_path):
            # Check to see if context is in mappings directory
            cont_path = '{}/{}'.format(cont_dir,context)

        assert os.path.exists(cont_path), 'No context {} found at specified path or {}'.format(context, cont_dir)
    else:
        # Find highest numbered pmap in appropriate mapping directory
        cont_path = sorted(glob.glob('{}/*pmap'.format(cont_dir)))[-1]

    return cont_path

# ----------------------------------------------------------------------------------------------------------------------


def get_observatory(pending_files):
    """ Retrieves the observatory info from the delivery staging directory
    """
    # Instruments for each observatory
    hst_inst = ['ACS', 'WFC3', 'COS', 'STIS', 'NICMOS', 'WFPC2']
    jwst_inst = ['FGS', 'MIRI', 'NIRCAM', 'NIRISS', 'NIRSPEC']

    if options.o is not None:
        return options.o.lower()
    else:
        directory = os.path.split(os.getcwd())[-1]
        instrument = directory.split('_')[0]

        if instrument in hst_inst:
            return 'hst'
        elif instrument in jwst_inst:
            return 'jwst'
        else:
            for f in pending_files:
                if '.fits' in f:
                    try:
                        instrument = fits.getval(f, 'INSTRUME').upper()
                        if instrument in hst_inst:
                            return 'hst'
                        elif instrument in jwst_inst:
                            return 'jwst'
                        else:
                            raise ValueError('Cannot match {} to an observatory'.format(instrument))
                    except KeyError:
                        raise KeyError('INSTRUME not found in fits header, so observatory cannot be determined')

    # If if can't determine instrument, raise exception
    raise ValueError('Cannot match files to an observatory')

# ----------------------------------------------------------------------------------------------------------------------


def print_extra_help():
    print('If experiencing errors, ensure you are using astroconda with the following packages are installed:')

    # Try importing these packages to see if they work?
    print('\tjwst')
    print('\tasdf')
    print('\tasdf-standard')
    print('\tgwcs\n\n')
    print('To ensure packages are installed use command \'conda list\'.\n\n')
    print('If not use command \'conda install <package_name>\'')
    print(('If you already use these packages and do not wish to alter installed packages,' 
           ' use command \'conda create -n <new_environment_name_here>\''))

# ----------------------------------------------------------------------------------------------------------------------


def verify_files(fits_files):
    """ Check files conform to fits standard and update verification keyword
    """
    print('----------------------------------------------------------------')
    print('--------------------------VERIFYING-----------------------------')
    print('----------------------------------------------------------------')

    for f in fits_files:
        if '.json' in f or '.asdf' in f:
            print('{} is not a fits file, skipping verification'.format(f))
            continue

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


def check_certify_results(certified_files):
    """ Check files passed certify and update certification keyword
    """
    # Get list of files that failed certify (parses output file)
    bad_files = [os.path.split(x.strip())[-1] for x in open('certify_errored_files.txt').readlines()]
    for f in certified_files:
        if '.json' in f or '.asdf' in f:
            continue

            # This should be okay, as only HST references get checked
            # for VERIFYD/CERTIFYD keywords (because thats only checked in
            # rename_files.py) and json/asdf are only jwst.

        hdu = fits.open(f, mode='update')
        if f in bad_files:
            hdu[0].header['CERTIFYD'] = 'FAILED'
            print(f, 'FAILED CERTIFICATION')
        else:
            hdu[0].header['CERTIFYD'] = 'PASSED'
            print(f, 'PASSED CERTIFICATION')

        hdu.close(output_verify='ignore')
        print('----------------------------------------------------------------')

# ----------------------------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    options = parse_args()
    if options.f:
        files = glob.glob(options.f)
    else:
        files = glob.glob('*.fits') + glob.glob('*.json') + glob.glob('*.asdf')

    abs_paths = [os.path.abspath(f) for f in files]

    # Check if there are files?  Call to certify will handle this
    assert len(files) != 0, 'No files matched'
    observatory = get_observatory(files)
    assert observatory == 'hst' or observatory == 'jwst', 'Invalid observatory, specify either \'hst\' or \'jwst\''
    context = get_context(observatory, options.c)

    for f in files:
        print(f)

    verify_files(files)
    print('----------------------------------------------------------------')
    print('--------------------------CERTIFYING----------------------------')
    print('----------------------------------------------------------------')

    certify_command = ("crds certify --verbose -p --unique-errors-file "
                       "certify_errored_files.txt --comparison-context={} {}").format(context, ' '.join(abs_paths))

    shell_cmd = shlex.split(certify_command)    # Split the commmand string into a subprocess-friendly list
    print(shell_cmd, '\n')                            # of "tokenized" arguments

    # Open a subprocess and make sure to recover standard output and standard error
    with subprocess.Popen(shell_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        out_dat, out_err = p.communicate()    # the output of communicate is a tuple (stdout_data, stderr_data)

    print('{}\n{}'.format(out_dat.decode('utf-8'), out_err.decode('utf-8')))

    with open('certify_results.txt', mode='w+') as cert:
        print('\n{}\n{}'.format(out_dat.decode('utf-8'), out_err.decode('utf-8')), file=cert)

    check_certify_results(files)
