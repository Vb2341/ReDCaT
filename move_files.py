import os       # os.mkdir(); os.getcwd()
import glob
import shutil   # shutil.copy()


# Constants
instruments= {'hst': ['STIS', 'COS', 'ACS', 'WFC3', 'NICMOS', 'WFPC2']
              'jwst': ['MIRI', 'NIRCAM', 'NIRISS', 'NIRSPEC']}

#-------------------------------------------------------------------------------
def parse_directory_name(name):
    """ Takes the name of a delivery directory of the form INSTRUMENT_YYYY_MM_DD
        and moves it to the appropriate directory in /ifs/redcat...
    """
    pieces= name.split('_')
    instrument, year, month, day= pieces[0].upper(), pieces[1], pieces[2]

    if instrument not in instruments['hst'] and instrument not in instruments['jwst']:
        raise NameError('Directory name does not comply with INSTR_YYYY_MM_DD or invalid INSTRUMENT')

    return instrument, year, month, day

#-------------------------------------------------------------------------------
def move_results(dir, obs_instruments):
    """ Moves all .log and .txt files to the appropriate directory.
        This should include the following:

            1. delivery.log: contains the results of uniqname
            2. delivery_form.txt: contains a plain-text version of the delivery
                form
            3. certify_errored_files.txt
    """
    # Grab the logs and txts
    results= glob.glob(os.path.join(dir, '*.log'))
    results += glob.glob(os.path.join(dir, '*.txt'))

    # Grab the delivery info
    delivery= dir.split('/')[-1]
    instrument, year, month, day= parse_directory_name(dir)
    print('-'*50)
    print('\n\t {} DELIVERY\n\t{} {} {}'.format(instrument, year, month, day))
    print('-'*50)
    date_dir= year + '_' + month + '_' + day

    # Construct Destination
    if instrument in obs_instruments['hst'] and 'ops' in dir:
        destination= '/ifs/redcat/hst/srefpipe/{}/'.format(instrument)

    elif instrument in obs_instruments['jwst'] and 'ops' in dir:
        destination= '/ifs/redcat/jwst/srefpipe/{}/'.format(instrument)

    elif instrument in obs_instruments['hst'] and 'test' in dir:
        destination= '/ifs/redcat/hst/cdbstest/{}/'.format(instrument)
        
    elif instrument in obs_instruments['jwst'] and 'test' in dir:
        raise IOError('\n\tJWST DELIVERIES SHOULD NOT BE IN TEST STAGING AREA\n')

    # Move the files
    complete_destination= os.path.join(destination, date_dir)
    os.mkdir(os.path.join(destination, date_dir))
    for item in results:
        print('\nMOVING {} TO {}\n'.format(item, complete_destination))
        shutil.copy(item, complete_destination)

    print('\n\tFILE MOVES COMPLETED')

#-------------------------------------------------------------------------------
def arrrg_pirate():
  import argparse
  
  parser= argparse.ArgumentParser(
      description= 'Moves the results from the delivery directory to /ifs..')
  
  parser.add_argument('-dr',
                      '--delivery_directory',
                      default= os.getcwd(),
                      action= 'store',
                      help= 'Delivery directory of the form INSTRUMENT_YYYY_MM_DD')
  
  return parser.parse_args()

#-------------------------------------------------------------------------------

if __name__ == '__main__':

    args= arrrg_pirate()
    
    move_results(args.delivery_directory, instruments)
    
    
    
