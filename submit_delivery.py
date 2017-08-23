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

    which_staging = input('Is the deliery going to CRDS OPS, CRDS TEST or ETC (ops/test/etc): ').lower()
    if which_staging not in ['ops', 'test', 'etc']:
        raise TypeError('Must specify if the delivery is going to CRDS OPS, CRDS TEST or ETC')

    username = input('Email Username : ').lower().split('@')[0]
    subject = input('Subject of delivery request: ')

    # Today's date for constructing the delivery directory of INSTRUMENT_YYYY_MM_DD
    today = Time.now().datetime

    return instrument, which_staging, username, today, subject

# ======================================================================================================================


def send_email(email_username, subject):
    """Constructs the email to be sent to the redcat team upon submission of the files to be delivered
    """

    # Check that the delivery form exists
    try:
        with open('delivery_form.txt', encoding='utf-8') as df:
            message = MIMEText(df.read())

    except OSError:
        print('\nMissing delivery form\n\tPlease include the delivery form with the reference files to be submitted')
        print('\t(delivery_form.txt)')
        sys.exit()

    # Build the email
    deliverer = '{}@stsci.edu'.format(email_username)
    message['Subject'] = subject
    message['From'] = deliverer
    message['To'] = 'redcat@stsci.edu'
    message['CC'] = deliverer

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


def update_delivery_form(path_to_delivery_form, files_being_delivered, file_destination):
    """Update the delivery form to reflect the location and names of the files being delivered
    """
    form_path = os.path.split(path_to_delivery_form)[0]
    temp_file = os.path.join(form_path, 'temp.txt')
    
    with open(temp_file, mode='w+', encoding='utf-8') as out, open(path_to_delivery_form, encoding='utf-8') as old:
        for line in old:
            if "16. Disk location and name of files:" in line:
                f_list = '{}\n'.format(file_destination)
                for f in files_being_delivered:
                    name = os.path.split(f)[-1]
                    f_list += '{}\n'.format(name)
                line += f_list
            out.write(line)

    shutil.copy(temp_file, path_to_delivery_form)

# ======================================================================================================================


def send_to_staging(delivery_instrument, date, staging_location):
    """Given the instrument string and the current date, create a delivery directory in /grp/redcat/staging/[ops/test]/
    """
    staging_directory = '/grp/redcat/staging/'
    staging_directory += '{}/'.format(staging_location)

    year = str(date.year)
    month = date_to_string(date.month)
    day = date_to_string(date.day)

    directory_name = '{}_{}_{}_{}_0'.format(delivery_instrument, year, month, day)

    # Check to see if the destination alreading exists in the staging area
    pending_deliveries = os.listdir(staging_directory)
    if directory_name in pending_deliveries:
        while (directory_name in pending_deliveries) is True:
            directory_pieces = directory_name.split('_')

            directory_name_core = '_'.join(directory_pieces[:-1])
            delivery_number = int(directory_pieces[-1])

            delivery_number += 1

            directory_name = directory_name_core + '_' + str(delivery_number)

    destination = os.path.join(staging_directory, directory_name)
    print('\nDESTINATION: {}'.format(destination))

    os.mkdir(destination)
    os.chmod(destination, 0o777)

    current_dr = os.getcwd()
    fits_files = os.path.join(current_dr, '*fits')
    json_files = os.path.join(current_dr, '*json')
    asdf_files = os.path.join(current_dr, '*asdf')
    delivery_form = os.path.join(current_dr, 'delivery_form.txt')

    files_to_deliver = glob.glob(fits_files) + glob.glob(json_files) + glob.glob(asdf_files) + glob.glob(delivery_form)
    print('\nItems to be moved to staging area:\n')
    for f in files_to_deliver:
        print('\t{}'.format(f))

    print('\nUpdating delivery form... adding destination and filenames')
    update_delivery_form(delivery_form, files_to_deliver, destination)

    print('\nMoving files...')
    for i, f in enumerate(files_to_deliver):
        print('{} out of {}'.format(i+1, len(files_to_deliver)))
        shutil.copy(f, destination)

        filename = os.path.split(f)[-1]  # isolate the filenames for use below
        os.chmod(os.path.join(destination, filename), 0o777)  # os.chmod can only be used on one file at a time

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
