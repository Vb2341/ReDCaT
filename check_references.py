import argparse
import glob
import os
import subprocess

from astropy.io import fits
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
    print 'If experiencing errors, ensure you are using astroconda with the following packages are installed:'
    # Try importing these packages to see if they work?
    print '\tjwst'
    print '\tasdf'
    print '\tasdf-standard'
    print '\tgwcs\n\n'
    print 'To ensure packages are installed use command \'conda list\'.\n\n'
    print 'If not use command \'conda install <package_name>\''
    print 'If you already use these packages and do not wish to alter installed packages, use command \'conda create -n <new_environment_name_here>\''

def verify_files(files):
    for f in files:
        print 'Verifying {}'.format(f)
        hdu = fits.open(f)
        hdu.verify('warn')
        hdu.close(output_verify="exception")
        fits.setval(f, 'VERIFIED', ext=0, value='PASSED')

def check_certify_results(files):
    bad_files = [x.strip() for x in open('certify_errored_files.txt').readlines()]
    for f in files:
        if f in bad_files:
            fits.setval(f, 'CERTIFYD', ext=0, value='FAILED')
        else:
            fits.setval(f, 'CERTIFYD', ext=0, value='PASSED')

if __name__ == '__main__':
    options = parse_args()
    files = glob.glob(options.f)
    # Check if there are files?  Call to certify will handle this
    assert len(files) != 0, 'No files matched'
    assert options.o == 'hst' or options.o == 'jwst', 'Invalid observatory, specify either \'hst\' or \'jwst\''
    context = get_context(options.o, options.c)
    print files
    verify_files(files)
    print '-------------------------------'
    command = ' '.join(['python', '-m', 'crds.certify','--unique-errors-file', 'certify_errored_files.txt', '--comparison-context={}'.format(context), options.f, '>', 'certify_results.txt', '2>&1'])
    print command
    os.system(command)
    check_certify_results(files)
    # python -m crds.certify --comparison-context=<operational contextI> <files or path to files if they're not in the current directory>
