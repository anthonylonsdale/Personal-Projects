import datetime
import re
import glob
import os
import psutil
import logging

logger = logging.getLogger(__name__)


class filePruning:
    def __init__(self):
        self.today = datetime.date.today().strftime("%m-%d-%Y")
        self.cwd = os.getcwd()
        self.root_path = self.cwd + r'\Daily Stock Analysis'
        self.dir_list = [r'\Accum-Dist Ranks', r'\Options', r'\Stocks', r'\Portfolio-Analysis', r'\Trades']

    def initialize_directories(self):
        if not os.path.exists(self.root_path):
            os.mkdir(self.root_path)
        for i in range(len(self.dir_list)):
            if not os.path.exists(self.root_path + self.dir_list[i]):
                os.mkdir(self.root_path + self.dir_list[i])

    def prune_files(self):
        for i in range(len(self.dir_list)):
            if self.dir_list[i] == '/Stocks':
                continue
            files = glob.glob(self.root_path + self.dir_list[i] + '/*')
            if len(files) == 0:
                continue
            for file in files:
                try:
                    re_match = re.search(r'\d{4}-\d{2}-\d{2}', file)
                    date = datetime.datetime.strptime(re_match.group(), '%Y-%m-%d').date()
                    date_cutoff = datetime.date.today() - datetime.timedelta(days=7)
                    if date_cutoff > date:
                        pruned_backup = str(file)
                        os.remove(pruned_backup)
                except AttributeError:
                    continue

    def excel_handler(self):
        for proc in psutil.process_iter():
            if proc.name() == "EXCEL.EXE":
                proc.kill()
