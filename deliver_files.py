import os
import sys
import glob
import subprocess
import shlex
import getpass
from move_files import parse_directory_name

# Constants
instruments= {'hst': ['STIS', 'COS', 'ACS', 'WFC3', 'NICMOS', 'WFPC2'],
              'jwst': ['FGS', 'MIRI', 'NIRCAM', 'NIRISS', 'NIRSPEC']}

#-------------------------------------------------------------------------------
def setup(delivery_directory):
    """ Set up the user's environment to enable the command line delivery
        tool to be run.
    """
    # Get username and password
    username= getpass.getuser()
    password= getpass.getpass(prompt= 'CRDS Webpage Password:')

    # Create an init file that stores the user's username and password
    # to be used with the command line tool
    init_file= os.path.join(os.environ['HOME'], '.crds.ini')
    with open(init_file, mode= 'w+') as f:
        print('[authentication]\nCRDS_USERNAME = {}\nCRDS_PASSWORD = {}'.format(
            username, password), file= f)

    # set the permissions of the file
    os.chmod(init_file, 0o600)

    # Grab delivery info based on the delivery directory name
    delivery_name= delivery_directory.split('/')[-1]
    delivery_info= parse_directory_name(delivery_name)  # returns (instrument, year, month, day)
    instrument= delivery_info[0]

    # Set the appropriate environment variables to operate the command line tool
    if 'test' in delivery_directory:
        os.environ['CRDS_PATH'] = "{}/crds_cache_test".format(os.environ['HOME'])
        if instrument in instruments['hst']:
            os.environ['CRDS_SERVER_URL'] = 'https://hst-crds-test.stsci.edu'
        elif instrument in instruments['jwst']:
            os.environ['CRDS_SERVER_URL'] = 'https://jwst-crds-test.stsci.edu'
        else:
            raise Exception(
                'Unknown Isntrument or Observatory/Delivery Area Incorrectly Formatted')

    elif 'ops' in delivery_directory:
        os.environ['CRDS_PATH'] = "{}/crds_cache_ops".format(os.environ['HOME'])
        if instrument in instruments['hst']:
            os.environ['CRDS_SERVER_URL'] = 'https://hst-crds.stsci.edu'
        elif instrument in instruments['jwst']:
            os.environ['CRDS_SERVER_URL'] = 'https://jwst-crds.stsci.edu'
        else:
            raise Exception(
                'Unknown Isntrument or Observatory/Delivery Area Incorrectly Formatted')

    else:
        raise Exception(
            'Cannot Identify Delivery Type/Delivery Is Not Located in Delivery Area')


    return delivery_info
#-------------------------------------------------------------------------------
def execute_delivery(delivery_directory, delivery_type):
    """ Deliver reference files to the appropriate system given that it resides
        in a directory located in /grp/redcat/staging/[ops/test]/ and of the
        form INSTRUMENT_YYYY_MM_DD
    """
    instrument= delivery_type[0]
    
    # Get the "reason for delivery" from the delivery form
    description= parse_delivery_form(os.path.join(delivery_directory,
        'delivery_form.txt'))

    # Create a string-list of files that the command line can use
    files= glob.glob(os.path.join(delivery_directory, '*fits*')) + \
           glob.glob(os.path.join(delivery_directory, '*json*'))
    
    submit_files= ' '.join(files)
    print('\nFILES BEING SUBMITTED:\n{}'.format(submit_files))

    # Deliver the files
    deliver= ("crds submit "
              "--files {} --monitor --wait --wipe --log-time "
              "--stats --creator '{} Team' --description '{}'").format(
        submit_files,
        instrument,
        description)
    
    # Split up the command string into a "command list" to be used by 
    # subprocess
    deliver_cmd = shlex.split(deliver)
    print(deliver_cmd)
    
    # run crds submit
    output = subprocess.check_output(deliver_cmd)
    print(output)     # so the user can see the output

    # write the output to a delivery log
    with open('delivery.log', mode= 'w+') as log:
        print(output, file= log)
    
    # Clean up the environment variables
    del os.environ['CRDS_PATH']
    del os.environ['CRDS_SERVER_URL']

#-------------------------------------------------------------------------------
def parse_delivery_form(form):
    """ Find the 'reason for delivery' in the delivery form to
        provide to the command line tool
    """
    # Open the form and read in the lines to a list
    f = open(form, 'r')
    lines = f.readlines()
    
    # Find the first line of the description
    start = None
    for i,line in enumerate(lines):
        if 'Reason for delivery:' in line:
            start = i
        else:
            continue
    
    # Grab all the line after the first; 
    # The reason for delivery is the last question of the form
    description = ''
    for line in lines[start:]:
        description += line
    
    # Get rid of the number and question; leaves only the description
    description_sans_number= description.split('17. Reason for delivery: ')[-1]
    
    # Get rid of '\n' characters in case they exist
    if '\n' in description_sans_number:
        no_newline = [piece for piece in description_sans_number.split('\n') if '\n' not in piece]
        final_description = ' '.join(no_newline)
    else:
        final_description = description_sans_number

    print('\nReason for Delivery: {}'.format(final_description))
    return final_description

#-------------------------------------------------------------------------------
if __name__ == '__main__':
    
    # Force this to be run in a delivery directory that's properly formatted
    delivery_directory = os.getcwd()
    if '/grp/redcat/staging/' not in delivery_directory:
        sys.exit('\nERROR: DELIVERIES MUST BE EXECUTED FROM THE REDCAT STAGING AREA')

    delivery_type = setup(delivery_directory)
    execute_delivery(delivery_directory, delivery_type)
