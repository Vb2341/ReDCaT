import argparse
import glob
import os
import subprocess
import warnings
import shlex
import sys

from astropy.io import fits
from astropy.io.fits.verify import VerifyError
from crds import jwst

def parse_args():
    """Parse command line arguments.

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

    parser.add_argument('o',type=str,help=observatory_help,action='store')
    parser.add_argument('-f',type=str,help=files_help,action='store',
        required=False,default='*.fits')
    parser.add_argument('-c', type=str, help=context_help,action='store',
        required=False,default=None)
    arguments = parser.parse_args()
    return arguments

def get_context(observatory, context):
    '''Get context file for certification'''
    cont_dir = '/grp/crds/{}/mappings/{}'.format(observatory,observatory)
    if context != None:
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


def print_extra_help():
    print('If experiencing errors, ensure you are using astroconda with the following packages are installed:')
    # Try importing these packages to see if they work?
    print('\tjwst')
    print('\tasdf')
    print('\tasdf-standard')
    print('\tgwcs\n\n')
    print('To ensure packages are installed use command \'conda list\'.\n\n')
    print('If not use command \'conda install <package_name>\'')
    print('If you already use these packages and do not wish to alter installed packages, use command \'conda create -n <new_environment_name_here>\'')

def verify_files(files):
    '''Check files conform to fits standard and update verification keyword'''
    print('----------------------------------------------------------------')
    print('--------------------------VERIFYING-----------------------------')
    print('----------------------------------------------------------------')
    for f in files:
        print('Verifying {}'.format(f))
        with warnings.catch_warnings(record=True) as w: # Workaround for astropy verify issues
            warnings.simplefilter("always") # Catch all warnings
            hdu = fits.open(f, mode='update') # Catches the 'fixable violations'
            hdu.verify('warn') # Catches the unfixable ones
            if len(w) == 0: # Check number of warnings, if =0 then file is good
                print(f, 'PASSED VERIFICATION')
                hdu[0].header['VERIFIED'] = 'PASSED'
            else:
                print(f, 'FAILED VERIFICATION')
                hdu[0].header['VERIFIED'] = 'FAILED'
                for warn in w:
                    print(warn.message)
            hdu.close(output_verify='ignore')
        print('----------------------------------------------------------------')

def check_certify_results(files):
    '''Check files passed certify and update certification keyword'''
    # Get list of files that failed certify (parses output file)
    bad_files = [os.path.split(x.strip())[-1] for x in open('certify_errored_files.txt').readlines()]
    for f in files:
        hdu = fits.open(f, mode='update')
        if f in bad_files:
            hdu[0].header['CERTIFYD'] = 'FAILED'
            print(f, 'FAILED CERTIFICATION')
        else:
            hdu[0].header['CERTIFYD'] = 'PASSED'
            print(f, 'PASSED CERTIFICATION')
        hdu.close(output_verify='ignore')
        print('----------------------------------------------------------------')

if __name__ == '__main__':
    options = parse_args()

    # Grab the files and make a string-list. Avoids issues becuase
    # doing it this way includes the paths of the files
    files = glob.glob(options.f)
    input_files = ' '.join(files)
    print(input_files)
        # Check if there are files?  Call to certify will handle this
    assert len(files) != 0, 'No files matched'
    assert options.o == 'hst' or options.o == 'jwst', 'Invalid observatory, specify either \'hst\' or \'jwst\''
    context = get_context(options.o, options.c)
    for f in files: print(f)
    verify_files(files)
    print('----------------------------------------------------------------')
    print('--------------------------CERTIFYING----------------------------')
    print('----------------------------------------------------------------')

    certify_command = ("crds certify --unique-errors-file"
                       " certify_errored_files.txt --comparison-context={} {}").format(context, input_files)

    shell_cmd = shlex.split(certify_command)

    try:
        output = subprocess.check_output(shell_cmd)
        print(output)
        with open('certify_results.txt', mode= 'w+') as cert:
            print(output, file= cert)
    except subprocess.CalledProcessError as err:
        print(err.returncode, err.output)
        sys.exit()

    check_certify_results(files)
