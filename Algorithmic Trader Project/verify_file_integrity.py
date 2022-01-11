from __future__ import unicode_literals
import logging
import os
import glob
import openpyxl

logger = logging.getLogger(__name__)


class verifyFileIntegrity:
    def __init__(self):
        self.cwd = os.getcwd()
        self.directories = [r'\Bonds', r'\Options', r'\Trades']

    def check_files(self):
        for directory in self.directories:
            for file in glob.glob(self.cwd + r'\Daily Stock Analysis' + directory + r'\*.xlsx'):
                file_name = file.split("\\")[-1]
                try:
                    openpyxl.load_workbook(file)
                except Exception as e:
                    logger.debug(f"Error: {e}, file \"{file_name}\" is being removed")
                    os.remove(file)
