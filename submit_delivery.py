import os
import smtplib
from email.mime.text import MIMEText
from astropy.time import Time
import sys
import glob
import shutil

# Observatory/Instrument constants
instruments = {'hst': ['STIS', 'COS', 'ACS', 'WFC3', 'NICMOS', 'WFPC2'],
               'jwst': ['FGS', 'MIRI', 'NIRCAM', 'NIRISS', 'NIRSPEC']}

# ======================================================================================================================


def recover_info():
    """Gets information about the delivery in order to create a delivery directory
    """
    # Interactively acquire the instrument, ops/test destination, email username and subject to make things simple
    instrument = input('Instrument: ').upper()
    if instrument not in instruments['hst'] and instrument not in instruments['jwst']:
        raise KeyError('INSTRUMENT DOES NOT EXIST\nor a typo may have occurred..\nplease try again')

    ops_or_test = input('Is the deliery going to CRDS OPS or CRDS TEST (ops/test): ')
    if ops_or_test not in ['ops', 'test']:
        raise TypeError('Must specify if the delivery is going to CRDS OPS or CRDS TEST')

    username = input('Email Username: ').lower()
    subject = input('Subject line for ReDCaT email (please refer to the delivery instructions): ')

    # Today's date for constructing the delivery directory of INSTRUMENT_YYYY_MM_DD
    today = Time.now().datetime

    return instrument, ops_or_test, username, today, subject

# ======================================================================================================================


def send_email(email_username, subject):
    """Constructs the email to be sent to the redcat team upon submission of the files to be delivered
    """

    # Check that the delivery form exists
    try:
        with open('delivery_form.txt') as df:
            message = MIMEText(df.read())

    except OSError:
        print('\nMissing delivery form\n\tPlease include the delivery form with the reference files to be submitted')
        print('\t(delivery_form.txt)')
        sys.exit()

    # Build the email
    message['Subject'] = subject
    message['From'] = '{}@stsci.edu'.format(email_username)
    message['To'] = 'redcat@stsci.edu'

    # Send it!
    s = smtplib.SMTP('smtp.stsci.edu')
    s.send_message(message)
    s.quit()

# ======================================================================================================================


def date_to_string(date):
    """Converts the month or day into a string that's formatted to ReDCaT standard for delivery area
    """
    if date < 10:
        date_string = '0' + str(date)
    else:
        date_string = str(date)

    return date_string

# ======================================================================================================================


def send_to_staging(delivery_instrument, date, staging_location):
    """Given the instrument string and the current date, create a delivery directory in /grp/redcat/staging/[ops/test]/
    """
    staging_directory = '/grp/redcat/staging/'
    staging_directory += '{}/'.format(staging_location)

    year = str(date.year)
    month = date_to_string(date.month)
    day = date_to_string(date.day)

    directory_name = '{}_{}_{}_{}'.format(delivery_instrument, year, month, day)

    destination = os.path.join(staging_directory, directory_name)
    print('\nDESTINATION: {}'.format(destination))

    os.mkdir(destination)
    os.chmod(destination, 777)

    current_dr = os.getcwd()
    fits_files = os.path.join(current_dr, '*fits')
    json_files = os.path.join(current_dr, '*json')
    asdf_files = os.path.join(current_dr, '*asdf')
    delivery_form = os.path.join(current_dr, 'delivery_form.txt')

    files_to_deliver = glob.glob(fits_files) + glob.glob(json_files) + glob.glob(asdf_files) + glob.glob(delivery_form)
    print('\nItems to be moved to staging area:\n')
    for f in files_to_deliver:
        print('\t{}'.format(f))

    print('\nMoving files...')
    for i, f in enumerate(files_to_deliver):
        print('{} out of {}'.format(i+1, len(files_to_deliver)))
        shutil.copy(f, destination)
    os.chmod(os.path.join(destination, '*'), 777)

    print('\nDone!')

# ======================================================================================================================


def submit_to_redcat():
    """Submit reference files to the ReDCaT Team
    """
    instrument, ops_or_test, username, today, subject = recover_info()

    send_to_staging(instrument, today, ops_or_test)

    send_email(username, subject)

# ======================================================================================================================


if __name__ == '__main__':
    submit_to_redcat()