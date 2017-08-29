import os
from astropy.io import fits
import numpy as np
import pysynphot as pysyn
from datetime import date
import glob
import dask
from dask.diagnostics import ProgressBar
import argparse
import pandas

# ----------------------------------------------------------------------------------------------------------------------


def find_models(model_directory):
    """ Find all models in a given directory"""
    print('\n\t==============')
    print('\n\tFinding models')
    print('\n\t==============')

    path = os.path.join(model_directory, 'lte*')
    models = glob.glob(path)
    print('\nTotal number of files found: {}'.format(len(models)))

    return models

# ----------------------------------------------------------------------------------------------------------------------


def sort_by_temp_metal(list_of_model_files):
    """ Given a list of models, sort them by temperature. The temperature is given as a part of the file naming
        convention
    """
    print('\n\t============================================')
    print('\n\tSorting files by Temperature and Metallicity')
    print('\n\t============================================\n')
    # Create a dictionary that will contain a list of files for each temperature keyword
    files_per_tempmetal = {}

    keys = []
    for f in list_of_model_files:
        name = os.path.split(f)[-1]

        temp = name[3:6]
        metal = name[10:14]
        if (temp, metal) not in keys:
            keys.append((temp, metal))
        else:
            continue

    for t, m in keys:
        key = '_'.join([t, m])
        files_per_tempmetal[key] = [model for model in list_of_model_files if (t in model and m in model)]
        print('Found {} models for {}\{} temperature\metallicity values'.format(len(files_per_tempmetal[key]), t, m))

    return files_per_tempmetal

# ----------------------------------------------------------------------------------------------------------------------


def generate_fits(temperature_metallicity_key):
    """ Generate a fits file name and primary header based on the key generated in sort_by_temp_metal
    """
    temperature, metallicity = temperature_metallicity_key.split('_')[0], temperature_metallicity_key.split('_')[1]
    print('\n\t=====================================================')
    print('\n\tCreating new file for {}/{} temperature/metallicity'.format(temperature, metallicity))
    print('\n\t=====================================================\n')

    if int(temperature[0]) == 0:
        temperature = temperature[1:] + '00'
    else:
        temperature += '00'

    # Metallicity sign
    if '-' in metallicity:
        sign = 'm'
    else:
        sign = 'p'

    # Construct filename and corresponding HDU object
    output_file = 'phoenix' + sign + metallicity[1:] + '_' + temperature + '.fits'

    today = date.today()
    date_string = '{}-{}-{}'.format(today.year, today.month, today.day)

    header = fits.Header()
    header['FILENAME'] = (output_file, 'Name of file')
    header['MAPKEY'] = ('phoenix', 'Mapping identifier for filetype')
    header['CONTACT'] = ('J. White/M. McMaster', 'ReDCaT Team Deputy/Lead')
    header['CREATED'] = (date_string, 'Date of file creation')
    header['DESCRIP'] = 'Phoenix Models BT-settl Allard et al. 03, 07, 09'
    header['FILE_TYP'] = ('Atmosphere Grid Model', 'Type of file')
    header['SYSTEMS'] = ('ETC, CDBS, PYSYNPHOT', 'Systems that will use this filetype')
    header['REASON'] = 'Delivered to support JWST'
    header['TEFF'] = (temperature, 'Effective temperature in K')
    header['LOG_Z'] = (metallicity, 'Log of stellar metallicity')
    header['FLUXUNT'] = ('Flambda', 'erg/cm^2/s/Angstrom')
    header['COMMENT'] = '= Files translated to CDBS format by J. White'

    pri_hdu = fits.PrimaryHDU(header=header)

    return pri_hdu, output_file

# ----------------------------------------------------------------------------------------------------------------------


def get_data(model_files):
    """ Recover information such as wavelength, flux and log(G) from the model file
    """
    expected_log_gs = ['0.0', '0.5', '1.0', '1.5', '2.0', '2.5', '3.0', '3.5', '4.0', '4.5', '5.0', '5.5']

    dfs = []
    loggs = []
    for model_file in model_files:
        model_path, model_name = os.path.split(model_file)

        log_g = model_name[7:10]  # log_g value is given in the naming converntion

        if log_g not in expected_log_gs:
            raise TypeError('Non-standard or mis-named file')
        else:
            loggs.append(log_g)

        print('Retrieving data for LogG = {}'.format(log_g))

        wave_flux_df = dask.delayed(pandas.read_table)(model_file, names=['wavelength', 'flux'], usecols=[0, 1],
                                                       delim_whitespace=True)
        dfs.append(wave_flux_df)

    with ProgressBar():
        data_results = dask.compute(*dfs)

    log_g_dat, wavelength_dat, flux_dat = clean_data(data_results, loggs)

    return log_g_dat, wavelength_dat, flux_dat

# ----------------------------------------------------------------------------------------------------------------------


def create_synphot(wavelengths, wave_array, flux_array):
    """ From the wavelength and flux data obtained from the phoenix model files, build the column data for the
        primary HDU objects that will become the synphot files
    """
    spectrum = pysyn.ArraySpectrum(wave=wave_array, flux=flux_array, waveunits='angstroms', fluxunits='flam')
    simulated_flux = spectrum.sample(wavelengths)

    return simulated_flux

# ----------------------------------------------------------------------------------------------------------------------


def create_fits(hdu, outname, loggs, wave_band_array, syn_fluxes):
    """ From the sorted list of phoenix model files extract the necessary information and produce synphot fits
        files.
    """
    # dictionary items
    # log_g file naming convention: (fits column name, fits header key)

    log_names = {'0.0': ('g00', 'LOGG1'),
                 '0.5': ('g05', 'LOGG2'),
                 '1.0': ('g10', 'LOGG3'),
                 '1.5': ('g15', 'LOGG4'),
                 '2.0': ('g20', 'LOGG5'),
                 '2.5': ('g25', 'LOGG6'),
                 '3.0': ('g30', 'LOGG7'),
                 '3.5': ('g35', 'LOGG8'),
                 '4.0': ('g40', 'LOGG9'),
                 '4.5': ('g45', 'LOGG10'),
                 '5.0': ('g50', 'LOGG11'),
                 '5.5': ('g55', 'LOGG12')}

    columns = []
    wavelength_column = fits.Column(name='WAVELENGTH', format='D', unit='ANGSTROM', array=wave_band_array)
    columns.append(wavelength_column)

    for logg, flux in zip(loggs, syn_fluxes):
        column_name = log_names[logg][0]
        header_keyword = log_names[logg][1]

        if not flux.any():
            hdu.header[header_keyword] = '-999'
        else:
            hdu.header[header_keyword] = logg

        column = fits.Column(name=column_name, format='D', unit='FLAM', array=flux)
        columns.append(column)

    fits_columns = fits.ColDefs(columns)
    table_hdu = fits.BinTableHDU.from_columns(fits_columns)

    hdulist = fits.HDUList([hdu, table_hdu])
    hdulist.writeto(outname)

# ----------------------------------------------------------------------------------------------------------------------


def clean_data(list_of_dataframes, log_g_list):
    """ Convert data to floats and proper units, and Fill in missing data with zeroes
    """

    wavelengths = []
    fluxes = []
    for df in list_of_dataframes:
        df = df.apply(lambda x: pandas.Series(x).str.replace('D', 'E').astype(float))
        df['flux'] = df['flux'].apply(lambda f: 1e-8 * 10**f)
        df[df.flux == 1e-8] = 0.0
        df = df[df.wavelength != 0]
        df = df.sort_values('wavelength')

        wavelengths.append(df['wavelength'].values)
        fluxes.append(df['flux'].values)

    # Fill missing data
    expected_loggs = ['0.0', '0.5', '1.0', '1.5', '2.0', '2.5', '3.0', '3.5', '4.0', '4.5', '5.0', '5.5']

    for lg in expected_loggs:
        if lg not in log_g_list:
            print('{} Not found.. setting flux to 0')
            log_g_list.append(lg)
            wavelengths.append(np.copy(wavelengths[0]))
            fluxes.append(np.zeros_like(fluxes[0]))

    return log_g_list, wavelengths, fluxes

# ----------------------------------------------------------------------------------------------------------------------


def make_synphot_files(phoenix_directory, output_directory):
    """ Put everything together.. from the list of phoenix model files construct synphot fits files
    """
    files = find_models(phoenix_directory)
    sorted_dictionary = sort_by_temp_metal(files)

    # Wave bands
    blue_band = np.logspace(1.0, 3.695, num=1000, endpoint=True, base=10.0)
    green_band = np.logspace(3.696, 5.455, num=3000, endpoint=True, base=10.0)
    red_band = np.logspace(5.456, 6.998, num=1000, endpoint=True, base=10.0)
    wavelengths = np.hstack((blue_band, green_band, red_band))

    for key, models in sorted_dictionary.items():
        hdu, output_filename = generate_fits(key)

        out = os.path.join(output_directory, output_filename)

        log_gs, wavelength, flux = get_data(models)

        synphot_fluxes = []
        for wave, flux in zip(wavelength, flux):
            syn_f = dask.delayed(create_synphot)(wavelengths, wave, flux)
            synphot_fluxes.append(syn_f)

        print('\nConverting to synphot data')
        with ProgressBar():
            synphot_results = dask.compute(*synphot_fluxes)

        create_fits(hdu, out, log_gs, wavelengths, synphot_results)

# ----------------------------------------------------------------------------------------------------------------------


def convert_phoenix_to_synphot():
    """ handles argument parsing and execution
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('--model_directory',
                        '-d',
                        action='store',
                        default=os.getcwd(),
                        help='Directory where the model files are located. Default is the current working directory')

    parser.add_argument('--output_directory',
                        '-o',
                        action='store',
                        default=os.getcwd(),
                        help='Directory in which to place the output')

    args = parser.parse_args()

    make_synphot_files(args.model_directory, args.output_directory)

# ----------------------------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    convert_phoenix_to_synphot()
