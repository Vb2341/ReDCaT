from astropy.io import fits
import glob
import subprocess
import shlex


# ----------------------------------------------------------------------------------------------------------------------


def rename_files(list_of_files):
    """ This checks that the files have been checked for compliance with fits standards as well as CRDS standards using
        check_references.py Should check the output of check_references.py **before** running this.
    """
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

            if verified != 'PASSED' or certified != 'PASSED':
                print('\n FILE NOT COMPLIANT \n \t {}'.format(item))
                break
            else:
                print('\n {} IS COMPLIANT'.format(item))

    string_list_of_files = ' '.join(list_of_files)

    # Run uniqname
    uniqname = 'crds uniqname --hst -s -a -r --files {}'.format(string_list_of_files)
    rename_cmd = shlex.split(uniqname)

    with subprocess.Popen(rename_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p, \
            open('rename.log', mode='w+') as log:

        while p.poll() is None:
            out = p.stderr.readline().decode('utf-8')
            if out == '' and p.poll() is not None:
                break
            if out:
                print(out)
                print(out, file=log)  # Document rename results in a log file

    print('DONE. FILES RENAMED')

# ----------------------------------------------------------------------------------------------------------------------


if __name__ == "__main__":

    files= glob.glob('*fits')
    rename_files(files)
