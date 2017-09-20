import os
import glob
import shutil


# Constants
instruments = {'hst': ['STIS', 'COS', 'ACS', 'WFC3', 'NICMOS', 'WFPC2'],
               'jwst': ['FGS', 'MIRI', 'NIRCAM', 'NIRISS', 'NIRSPEC']}

# ----------------------------------------------------------------------------------------------------------------------


def parse_directory_name(name):
    """ Take the name of a delivery directory of the form INSTRUMENT_YYYY_MM_DD
        and retrieves delivery information from it
    """
    # Split the name into pieces
    pieces = name.split('_')
    instrument = pieces[0].upper()
    date_str = '_'.join(pieces[1:])  # Removes instrument from directory name. Works for n deliveries > 1 in a day

    if instrument not in instruments['hst'] and instrument not in instruments['jwst']:
        raise NameError('Directory name does not comply with INSTR_YYYY_MM_DD or invalid INSTRUMENT')

    return instrument, date_str

# ----------------------------------------------------------------------------------------------------------------------


def move_results(directory, obs_instruments):
    """ Move all .log and .txt files to the appropriate directory on /ifs/....
        This should include the following:

            1. rename.log: contains the results of uniqname
            2. delivery_form.txt: contains a plain-text version of the delivery
                form
            3. certify_errored_files.txt
            4. delivery.log: contains the results of the actual delivery
    """
    # Grab the logs and txts
    results = glob.glob(os.path.join(directory, '*.log'))
    results += glob.glob(os.path.join(directory, '*.txt'))

    # Grab the delivery info
    delivery = directory.split('/')[-1]
    instrument, date_str = parse_directory_name(delivery)
    print('-'*50)
    print('\n\t{} DELIVERY\n\t{}'.format(instrument, date_str))
    print('-'*50)
    date_dir = date_str

    # Construct Destination
    if 'test' in directory:
        if instrument in obs_instruments['hst']:
            destination = '/ifs/redcat/hst/cdbstest/{}/'.format(instrument)
        elif instrument in obs_instruments['jwst']:
            destination = '/ifs/redcat/jwst/cdbstest/{}/'.format(instrument)
        else:
            raise Exception(
                'Unknown Instrument or Observatory/Delivery Area Incorrectly Formatted')
    elif 'ops' in directory:
        if instrument in obs_instruments['hst']:
            destination = '/ifs/redcat/hst/srefpipe/{}/'.format(instrument)
        elif instrument in obs_instruments['jwst']:
            destination = '/ifs/redcat/jwst/srefpipe/{}/'.format(instrument)
        else:
            raise Exception(
                'Unknown Instrument or Observatory/Delivery Area Incorrectly Formatted')
    elif 'etc' in directory:
        if instrument in obs_instruments['hst']:
            destination = '/ifs/redcat/hst/srefpipe/ETC/'
        elif instrument in obs_instruments['jwst']: # JWST ETC directories are lowercase on /ifs/redcat/ tree
            destination = '/ifs/redcat/jwst/srefpipe/ETC/deliveries/{}/'.format(instrument.lower())
        else:
            raise Exception(
                'Unknown Instrument or Observatory/Delivery Area Incorrectly Formatted')            
    else:
        raise Exception(
            'Cannot Identify Delivery Type/Delivery Is Not Located in Delivery Area')

    # Move the files
    complete_destination = os.path.join(destination, date_dir)  # full path
    os.mkdir(os.path.join(destination, date_dir))   # make the directory to deposit files
    for item in results:
        print('\nMOVING {} TO {}\n'.format(item, complete_destination))
        shutil.copy(item, complete_destination)

    # HST references should go to central store
    if instrument in obs_instruments['hst']:
        move_hst_references(instrument, directory)

    print('\n\tFILE MOVES COMPLETED\n')

# ----------------------------------------------------------------------------------------------------------------------


def move_hst_references(instrument, directory):
    """ Move HST reference files to the appropriate ..ref directory on central store
    """
    print('\n\tMOVING HST REFERENCES TO CENTRAL STORE')
    central_store_path = '/grp/hst/cdbs/'
    central_store_names = {'COS': 'lref',
                           'STIS': 'oref',
                           'ACS': 'jref',
                           'WFC3': 'iref',
                           'WFPC2': 'uref',
                           'NICMOS': 'nref'}

    # Grab the reference files
    reference_files = glob.glob(os.path.join(directory, '*fits'))

    # Construct the path
    central_store = os.path.join(central_store_path, central_store_names[instrument])

    # Move the files
    for ref in reference_files:
        print('\nCOPYING {} TO {}'.format(os.path.split(ref)[-1], central_store_names[instrument]))
        shutil.copy(ref, central_store)

# ----------------------------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    delivery_directory = os.getcwd()
    move_results(delivery_directory, instruments)
