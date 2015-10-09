"""This script contains the class dk_clean.
dk_clean is used to move all old files from one directory to another"""

import re
import time
import shutil
import pwd

import threading
from queue import PriorityQueue

import sys, os
sys.path.append(os.path.abspath("../.."))
from dkmonitor.utilities import log_setup
from dkmonitor.stat.dir_scan import dir_scan

class DkClean:
    """The class dk_clean is used to move old files from one directory to an other.
    The process can be run with multithreading or just iterativly"""

    def __init__(self, search_dir='', move_to='', access_threshold='', host_name='127.0.0.1'):
        self.search_dir = search_dir
        self.move_to = move_to
        self.access_threshold = access_threshold
        self.host_name=host_name
        self.que = PriorityQueue()

        self.logger = log_setup.setup_logger("clean_log.log")


    def build_file_que(self):
        print("Moving Files")
        for file_path in dir_scan(self.search_dir):
            last_access = (time.time() - os.path.getatime(file_path)) / 86400
            if last_access > self.access_threshold:
                old_file_size = int(os.path.getsize(file_path))
                priority_num = - (old_file_size * last_access)
                self.que.put((priority_num, file_path))
        print("Done")


    def move_file(self, file_path, delete_if_full=False):
        """Moves individual file while still preseving its file path"""

        uid = os.stat(file_path).st_uid
        user = pwd.getpwuid(uid).pw_name

        root_dir = self.move_to + '/' + user +  '/' + self.host_name + '/' + self.search_dir.replace('/', '.')[1:]
        #self.create_file_tree(uid, root_dir)

        new_file_path = re.sub(r"^{old_path}".format(old_path=self.search_dir),
                                                     root_dir,
                                                     file_path)
        last_slash = new_file_path.rfind('/')
        dir_path = new_file_path[:last_slash]

        try:
            #self.create_file_tree(uid, dir_path)
            #shutil.move(file_path, new_file_path)
            pass
        except IOError as err:
            if delete_if_full is True:
                os.remove(file_path)
            raise(err)

    def delete_file(self, file_path):
        """Deletes file"""
        os.remove(file_path)

    def create_file_tree(self, uid, path):
        """Creates file tree after move_to with user ownership"""

        path = path.replace(self.move_to, "")
        dirs = path.split("/")
        current_path = self.move_to
        for d in dirs:
            try:
                new_dir = current_path + '/' + d
                os.mkdir(new_dir)
                os.chown(new_dir, uid, uid)
            except OSError:
                pass
            current_path = new_dir


####MULTI-THREADING######################################
    def worker(self, delete_or_move, delete_if_full):
        """Worker Function"""

        while True:
            path = self.que.get()
            if delete_or_move == "delete":
                self.delete_file(path[1])
            elif delete_or_move == "move":
                self.move_file(path[1], delete_if_full=delete_if_full)
            self.que.task_done()

    def build_pool(self, thread_number, delete_or_move, delete_if_full=False):
        """Builds Pool of thread workers"""

        for i in range(thread_number):
            thread = threading.Thread(target=self.worker,
                                      args=(delete_or_move, delete_if_full))
            thread.daemon = True
            thread.start()

    def move_all_threaded(self, thread_number, delete_if_full=False):
        """Moves all files with multithreading"""

        self.build_pool(thread_number, "move", delete_if_full=delete_if_full)
        self.build_file_que()
        self.que.join() #waits for threads to finish

    def delete_all_threaded(self, thread_number):
        """Deletes all old files multithreaded"""

        self.build_pool(thread_number, "delete")
        self.build_file_que()
        self.que.join()


####ITERATIVE###########################################
    def move_all(self, delete_if_full=False):
        """Moves all files sequentailly"""
        self.build_file_que()
        self.move_que(delete_if_full=delete_if_full)

    def delete_all(self):
        """Deletes all files iterativley"""
        self.build_file_que()
        self.delete_que()

    def move_que(self, delete_if_full=False):
        """Moves all files in queue sequentailly"""

        while not self.que.empty():
            file_path = self.que.get()
            self.move_file(file_path[1], delete_if_full=delete_if_full)

    def delete_que(self):
        """Deletes files in the que"""

        while not self.que.empty():
            file_path = self.que.get()
            self.delete_file(file_path[1])


