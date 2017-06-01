from astropy.io import fits
import glob
import subprocess


#-------------------------------------------------------------------------------
def rename_files(list_of_files):
    ''' This checks that the files have been checked for compliance with fits
        standards as well as CRDS standards using check_references.py
        Should check the output of check_references.py **before**
        running this.
    '''
    # Check that check_references.py has been run on the files.
    # If not, quit.
    # check_references.py creates keywords 'VERIFIED' and 'CERTIFYD'
    for item in list_of_files:
        with fits.open(item) as f:
            try:
                verified = f[0].header['VERIFIED']
                certified = f[0].header['CERTIFYD']
            except KeyError:
                print('VERIFICATION KEYWORDS NOT FOUND!!')
                break

            if verified != 'PASSED' and certified != 'PASSED':
                print('\n FILE NOT COMPLIANT \n \t {}'.format(item))
                break
            else:
                print('\n {} IS COMPLIANT'.format(item))
    
    # Run uniqname
    uniqname = 'crds uniqname -s -a -r --files *.fits'
    output = subprocess.check_output(command)
    print(output)
    
    # Document rename results in a log file
    with open('rename.log', mode= 'w+') as log:
        print(output, file= log)

    print('DONE. FILES RENAMED')

#-------------------------------------------------------------------------------
if __name__ == "__main__":

    files= glob.glob('*fits')
    rename_files(files)
