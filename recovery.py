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
    parser.add_argument('-j', '--date_time_filename', action='store_true', required=False, help='sets the filename to the exif date and time if possible - otherwise keep the original filename')    

    return parser.parse_args()

def main():

    maxNumberOfFilesPerFolder = 500
    splitMonths = False
    source = None
    destination = None
    keepFilename = False
    date_time_filename = False

    args = get_args()
    source = args.source
    destination = args.destination
    maxNumberOfFilesPerFolder = args.max_per_dir
    splitMonths = args.split_months
    keepFilename = args.keep_filename
    date_time_filename = args.date_time_filename
    minEventDeltaDays = args.min_event_delta

    logger.info(f"Arguments: {args}")

    if not os.path.isdir(source):
        raise ValueError("Source directory does not exist: " + source)
    if not os.path.isdir(destination):
        raise ValueError("Destination directory does not exist: " + destination)

    logger.info("Reading from source '%s', writing to destination '%s' (max %i files per directory, splitting by year %s)." %
        (source, destination, maxNumberOfFilesPerFolder, splitMonths and "and month" or "only"))
    if keepFilename:
        logger.info("Filename Plan: Keep the original filenames.")
    elif date_time_filename:
        logger.info("Filename Plan: If possible, rename files like <Date>_<Time>.jpg. Otherwise, keep the original filenames.")
    else:
        logger.info("Filename Plan: Rename files sequentially, like '1.jpg'")

    fileNumber = getNumberOfFilesInFolderRecursively(source)
    if fileNumber > 100:
        onePercentFiles = int(fileNumber/100)
    else:
        onePercentFiles = fileNumber
    totalAmountToCopy = str(fileNumber)
    logger.info(f"Files to copy: {totalAmountToCopy:,}")


    fileCounter = 0
    for root, dirs, files in os.walk(source, topdown=False):

        for file in files:
            extension = os.path.splitext(file)[1][1:].upper()
            sourcePath = os.path.join(root, file)

            if extension:
                destinationDirectory = os.path.join(destination, extension)
            else:
                destinationDirectory = os.path.join(destination, "_NO_EXTENSION")

            if not os.path.exists(destinationDirectory):
                os.mkdir(destinationDirectory)
            
            if keepFilename:
                fileName = file
            
            elif date_time_filename:
                index = 0
                image = open(sourcePath, 'rb')
                exifTags = exifread.process_file(image, details=False)
                image.close()
                creationTime = jpgSorter.getMinimumCreationTime(exifTags)
                try:
                    creationTime = strptime(str(creationTime), "%Y:%m:%d %H:%M:%S")
                    creationTime = strftime("%Y%m%d_%H%M%S", creationTime)
                    fileName = str(creationTime) + "." + extension.lower()
                    while os.path.exists(os.path.join(destinationDirectory, fileName)):
                        index += 1
                        fileName = str(creationTime) + "(" + str(index) + ")" + "." + extension.lower()
                except:
                    fileName = file

            else:
                if extension:
                    fileName = str(fileCounter) + "." + extension.lower()
                else:
                    fileName = str(fileCounter)

            destinationFile = os.path.join(destinationDirectory, fileName)
            if not os.path.exists(destinationFile):
                shutil.copy2(sourcePath, destinationFile)

            fileCounter += 1
            if((fileCounter % onePercentFiles) == 0):
                logger.info(str(fileCounter) + " / " + totalAmountToCopy + " processed.")

    logger.info("start special file treatment")
    jpgSorter.postprocessImages(os.path.join(destination, "JPG"), minEventDeltaDays, splitMonths)

    logger.info("assure max file per folder number")
    numberOfFilesPerFolderLimiter.limitFilesPerFolder(destination, maxNumberOfFilesPerFolder)

if __name__ == '__main__':
    main()
