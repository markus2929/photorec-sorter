#!/usr/bin/env python

import os
import shutil
from time import strftime, strptime

# dependencies
import exifread
from loguru import logger

# project libraries
import jpgSorter
import numberOfFilesPerFolderLimiter

def getNumberOfFilesInFolderRecursively(start_path = '.'):
    numberOfFiles = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if(os.path.isfile(fp)):
                numberOfFiles += 1
    return numberOfFiles


def getNumberOfFilesInFolder(path):
    return len(os.listdir(path))


def do_organization(
        source: str, destination: str,
        max_files_per_folder: int,
        enable_split_months: bool, enable_keep_filename: bool, enable_datetime_filename: bool,
        min_event_delta_days: int
    ):

    if not os.path.isdir(source):
        raise ValueError("Source directory does not exist: " + source)
    if not os.path.isdir(destination):
        raise ValueError("Destination directory does not exist: " + destination)

    logger.info("Reading from source '%s', writing to destination '%s' (max %i files per directory, splitting by year %s)." %
        (source, destination, max_files_per_folder, enable_split_months and "and month" or "only"))
    if enable_keep_filename:
        logger.info("Filename Plan: Keep the original filenames.")
    elif enable_datetime_filename:
        logger.info("Filename Plan: If possible, rename files like <Date>_<Time>.jpg. Otherwise, keep the original filenames.")
    else:
        logger.info("Filename Plan: Rename files sequentially, like '1.jpg'")

    total_file_count = getNumberOfFilesInFolderRecursively(source)
    if total_file_count > 100:
        log_frequency_file_count = int(total_file_count/100)
    else:
        log_frequency_file_count = total_file_count
    logger.info(f"Total files to copy: {total_file_count:,}")

    cur_file_number = 0
    for root, dirs, files in os.walk(source, topdown=False):

        for file in files:
            extension = os.path.splitext(file)[1][1:].lower()
            source_file_path = os.path.join(root, file)

            if extension:
                dest_directory = os.path.join(destination, extension)
            else:
                dest_directory = os.path.join(destination, "no_extension")

            if not os.path.exists(dest_directory):
                os.mkdir(dest_directory)
            
            if enable_keep_filename:
                file_name = file
            
            elif enable_datetime_filename:
                index = 0
                image = open(source_file_path, 'rb')
                exifTags = exifread.process_file(image, details=False)
                image.close()
                creationTime = jpgSorter.getMinimumCreationTime(exifTags)
                try:
                    creationTime = strptime(str(creationTime), "%Y:%m:%d %H:%M:%S")
                    creationTime = strftime("%Y%m%d_%H%M%S", creationTime)
                    file_name = str(creationTime) + "." + extension.lower()
                    while os.path.exists(os.path.join(dest_directory, file_name)):
                        index += 1
                        file_name = str(creationTime) + "(" + str(index) + ")" + "." + extension.lower()
                except:
                    file_name = file

            else:
                if extension:
                    file_name = str(cur_file_number) + "." + extension.lower()
                else:
                    file_name = str(cur_file_number)

            dest_file_path = os.path.join(dest_directory, file_name)
            if not os.path.exists(dest_file_path):
                shutil.copy2(source_file_path, dest_file_path)

            cur_file_number += 1
            if((cur_file_number % log_frequency_file_count) == 0):
                logger.info(f"{cur_file_number} / {total_file_count} processed ({cur_file_number/total_file_count:.2%}).")

    logger.info("Starting special file treatment (JPG sorting and folder splitting)...")
    jpgSorter.postprocessImages(os.path.join(destination, "JPG"), min_event_delta_days, enable_split_months)

    logger.info("Applying max files-per-folder limit...")
    numberOfFilesPerFolderLimiter.limitFilesPerFolder(destination, max_files_per_folder)

    logger.info("Done.")



def get_args():
    import argparse

    description = (
        "Sort files recovered by PhotoRec.\n"
        "The input files are first copied to the destination, sorted by file type.\n"
        "Then JPG files are sorted based on creation year (and optionally month).\n"
        "Finally any directories containing more than a maximum number of files are accordingly split into separate directories."
    )

    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('source', metavar='src', type=str, help='source directory with files recovered by PhotoRec')
    parser.add_argument('destination', metavar='dest', type=str, help='destination directory to write sorted files to')
    parser.add_argument('-n', '--max-per-dir', type=int, default=500, required=False, help='maximum number of files per directory')
    parser.add_argument('-m', '--split-months', action='store_true', required=False, help='split JPEG files not only by year but by month as well')
    parser.add_argument('-k', '--keep_filename', action='store_true', required=False, help='keeps the original filenames when copying')
    parser.add_argument('-d', '--min-event-delta', type=int, default=4, required=False, help='minimum delta in days between two days')
    parser.add_argument('-j', '--enable_datetime_filename', action='store_true', required=False, help='sets the filename to the exif date and time if possible - otherwise keep the original filename')    

    return parser.parse_args()

def main():
    args = get_args()
    source = args.source
    destination = args.destination
    max_files_per_folder = args.max_per_dir
    enable_split_months = args.split_months
    enable_keep_filename = args.keep_filename
    enable_datetime_filename = args.enable_datetime_filename
    min_event_delta_days = args.min_event_delta

    logger.info(f"Arguments: {args}")

    do_organization(source, destination, max_files_per_folder, enable_split_months, enable_keep_filename, enable_datetime_filename, min_event_delta_days)


if __name__ == '__main__':
    main()
