import os
import sys
from move_files import parse_directory_name

"""
-------------!!!! NOTE !!!!--------------

This tool requires that the files that are being delivered reside in the
"official" redcat delivery staging area: /grp/redcat/staging/[ops/test]/.
This is to determine easily whether or not the file being delivered is
going to TEST or OPS, becuase setup is different for the delivery tool
depending on where the files are going. The ReDCaT member must also be logged
into dmsinsvm.
"""


# Constants
instruments= {'hst': ['STIS', 'COS', 'ACS', 'WFC3', 'NICMOS', 'WFPC2'],
              'jwst': ['FGS', 'MIRI', 'NIRCAM', 'NIRISS', 'NIRSPEC']}

#-------------------------------------------------------------------------------
def setup():
    """ This sets up the user's environment to enable the command line delivery
        tool to be run.
    """

    username= input('\nPlease provide CRDS username: ')
    password= input('\nPlease provide CRDS password: ')

    # Create an init file that stores the user's username and password
    # to be used with the command line tool
    f= open('$HOME/.crds.ini', 'w')
    f.write('[authentication]\nCRDS_USERNAME = {}\nCRDS_PASSWORD = {}'.format(
        username, password))
    f.close()

    # set the permissions of the file
    os.system('chmod 600 $HOME/.crds.ini')

#-------------------------------------------------------------------------------
def execute_delivery(delivery_directory):
    """ Delivers reference files to the appropriate system given that it resides
        in a directory located in /grp/redcat/staging/[ops/test]/ and of the
        form INSTRUMENT_YYYY_MM_DD
    """
    description= parse_delivery_form(os.path.join(delivery_directory,
        'delivery_form.txt'))

    # Grab delivery info based on the delivery directory name
    delivery_name= delivery_directory.split('/')[-1]
    delivery_info= parse_directory_name(delivery_name)
    intrument= delivery_info[0]

    # Deliver the files
    deliver= 'python -m crds.submit --files @files --monitor --wait --wipe --log-time --stats --creator "{}" --description "{}” | tee delivery.log'.format(
        instrument, description)

    activate_crds= 'source activate crds-file-submission'
    set_path= 'export PATH="/grp/crds/code/crds_stacks/anaconda3/bin:$PATH"'
    set_python= 'export PYTHONPATH="$PYTHONPATH:/grp/redcat/code"'

    if instrument in instruments['hst'] and 'test' in delivery_directory:
        crds_url= 'export CRDS_SERVER_URL="https://hst-crds-test.stsci.edu"'
        crds_path= 'export CRDS_PATH="$HOME/crds_cache_test”'

    elif instrument in instruments['hst'] and 'ops' in delivery_directory:
        crds_url= 'export CRDS_SERVER_URL="https://hst-crds.stsci.edu"'
        crds_path= 'export CRDS_PATH="$HOME/crds_cache_ops”'

    elif instrument in instruments['jwst'] and 'test' in delivery_directory:
        crds_url= 'export CRDS_SERVER_URL="https://jwst-crds-test.stsci.edu"'
        crds_path= 'export CRDS_PATH="$HOME/crds_cache_test”'

    elif instrument in instruments['jwst'] and 'ops' in delivery_directory:
        crds_url= 'export CRDS_SERVER_URL="https://jwst-crds.stsci.edu"'
        crds_path= 'export CRDS_PATH="$HOME/crds_cache_ops”'

    os.system('{}\n{}\n{}\n{}\n{}\n{}'.format(
        set_path, activate_crds, set_python, crds_url, crds_path, deliver))

#-------------------------------------------------------------------------------
def parse_delivery_form(form):
    """ This goes and finds the 'reason for delivery' in the delivery form to
        provide to the command line tool
    """

    f= open(form, 'r')

    lines= f.readlines()
    description= ''
    for line in line:
        if '16.' in line:
            if '17.' not in line:
                description += line
            else:
                break
        else:
            continue

    description_sans_number= description.split('16.')[-1]

    return description_sans_number

#-------------------------------------------------------------------------------

if __name__ == '__main__':

    delivery_directory= os.getcwd()
    if '/grp/redcat/staging/' not in delivery_directory:
        sys.exit('\n\tERROR\n\tDELIVERIES MUST BE EXECUTED FROM THE REDCAT STAGING AREA')

    setup()
    execute_delivery(delivery_directory)
